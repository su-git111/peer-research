# Claude 없이 도는 Cowork CLI. 워크플로를 결정론적으로 실행한다.
#   python cowork.py daily      오늘 체크리스트 생성 (어제 미완 이월)
#   python cowork.py weekly     이번주 계획 생성 (지난주 회고 자동 집계)
#   python cowork.py night      큐 작업 실행 + 논문 조회 → 아침 리포트
#   python cowork.py close       완료 업무를 포트폴리오에 기록
#   python cowork.py dashboard  대시보드만 다시 생성
#
# LLM 판단이 필요한 "제안/요약"은 결정론적 대안으로 낮춘다: 회고·이월·완료는 자동 집계,
# 계산은 큐 명령 실행, 논문은 Europe PMC 최신 목록. 판단이 필요한 칸은 사용자가 채운다.

import glob
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

root = os.path.dirname(os.path.abspath(__file__))
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
deny = ["rm ", "del ", "remove-item", "rmdir", "format ", "git push", "scp ", "curl -x post",
        "curl --request post", "upload", "mkfs", " > /dev/", "shutdown", "reg delete"]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def iso_week(d):
    c = d.isocalendar()
    return f"{c[0]}-W{c[1]:02d}"


def monday_of(d):
    return d - timedelta(days=d.weekday())


def section(text, heading):
    out, collecting = [], False
    for line in text.split("\n"):
        if line.startswith("## "):
            collecting = line[3:].strip().startswith(heading)
            continue
        if collecting:
            out.append(line)
    return out


def replace_section(text, heading, body):
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].startswith("## ") and lines[i][3:].strip().startswith(heading):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            out.append(body)
            out.append("")
            continue
        i += 1
    return "\n".join(out)


def open_items(text):
    items = []
    for line in text.split("\n"):
        m = re.match(r"\s*-\s*\[ \]\s*(.*)", line)
        if m and m.group(1).strip() and not m.group(1).startswith("("):
            items.append(m.group(1).strip())
    return items


def done_items(text):
    items = []
    for line in text.split("\n"):
        m = re.match(r"\s*-\s*\[[xX]\]\s*(.*)", line)
        if m and m.group(1).strip() and not m.group(1).startswith("("):
            items.append(m.group(1).strip())
    return items


def daily_files():
    hits = []
    for p in glob.glob(os.path.join(root, "daily", "*.md")):
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            hits.append((datetime.strptime(name, "%Y-%m-%d").date(), p))
        except ValueError:
            pass
    return sorted(hits)


def build_dashboard():
    subprocess.run([sys.executable, os.path.join(root, "build_dashboard.py")], cwd=root)


def cmd_daily():
    today = date.today()
    path = os.path.join(root, "daily", f"{today}.md")
    if os.path.exists(path):
        print("이미 있음:", os.path.relpath(path, root))
        return
    carry = []
    prev = [p for d, p in daily_files() if d < today]
    if prev:
        carry = open_items(read(prev[-1]))
    text = read(os.path.join(root, "templates", "daily.md"))
    text = text.replace("{DATE}", str(today)).replace("{WEEKDAY}", weekday_kr[today.weekday()])
    text = text.replace("{WEEK}", iso_week(today))
    body = "\n".join("- [ ] " + t for t in carry) if carry else "- [ ] "
    text = replace_section(text, "이월", body)
    write(path, text)
    print("생성:", os.path.relpath(path, root), f"(이월 {len(carry)}건)")
    build_dashboard()


def cmd_weekly():
    today = date.today()
    mon = monday_of(today)
    wk = iso_week(mon)
    path = os.path.join(root, "weekly", f"{wk}.md")
    if os.path.exists(path):
        print("이미 있음:", os.path.relpath(path, root))
        return
    pmon, psun = mon - timedelta(days=7), mon - timedelta(days=1)
    done, undone = [], []
    for d, p in daily_files():
        if pmon <= d <= psun:
            t = read(p)
            done += done_items(t)
            undone += open_items(t)
    text = read(os.path.join(root, "templates", "weekly.md"))
    text = text.replace("{WEEK}", wk).replace("{START}", str(mon))
    text = text.replace("{END}", str(mon + timedelta(days=6))).replace("{PREV_WEEK}", iso_week(pmon))
    lines = [f"- 완료 ({len(done)}건):"]
    lines += ["  - [x] " + t for t in done] or ["  - (기록 없음)"]
    lines += [f"- 미완 / 이월 ({len(undone)}건):"]
    lines += ["  - [ ] " + t for t in undone] or ["  - (없음)"]
    lines += ["- 배운 점 / 메모:", "  - "]
    text = replace_section(text, "지난주 회고", "\n".join(lines))
    write(path, text)
    print("생성:", os.path.relpath(path, root), f"(지난주 완료 {len(done)}, 미완 {len(undone)})")
    build_dashboard()


def fetch_papers(keyword, n=3):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": keyword, "format": "json", "pageSize": 15, "sort": "P_PDATE_D desc"})
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    out = []
    for h in data.get("resultList", {}).get("result", []):
        doi = h.get("doi")
        link = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/abstract/{h.get('source','')}/{h.get('id','')}"
        title = re.sub("<[^>]+>", "", html.unescape(h.get("title") or "")).rstrip(".")
        out.append({"date": h.get("firstPublicationDate", "?"), "title": title,
                    "authors": (h.get("authorString") or "")[:60], "source": h.get("source", ""), "link": link})
        if len(out) >= n:
            break
    return out


def parse_queue():
    text = read(os.path.join(root, "night", "queue.md"))
    cmds, in_wait = [], False
    for line in text.split("\n"):
        if line.startswith("## "):
            in_wait = line[3:].strip().startswith("실행 대기")
            continue
        if in_wait:
            m = re.match(r"\s*-\s*\[ \]\s*(.*)", line)
            if m and m.group(1).strip() and not m.group(1).startswith("("):
                cmds.append(m.group(1).strip())
    return cmds


def update_queue(finished):
    text = read(os.path.join(root, "night", "queue.md"))
    head = text.split("## 실행 대기")[0].rstrip()
    existing = [l for l in text.split("\n") if l.startswith("- [x]")]
    new = head + "\n\n## 실행 대기\n- [ ] (여기에 밤에 돌릴 명령을 추가하세요)\n\n## 완료 (자동 기록)\n"
    new += "\n".join(existing + finished) + "\n"
    write(os.path.join(root, "night", "queue.md"), new)


def cmd_night():
    today = date.today()
    jobs, held, finished = [], [], []
    for i, cmd in enumerate(parse_queue(), 1):
        if any(bad in cmd.lower() for bad in deny):
            held.append(cmd)
            continue
        logfile = f"night/logs/{today}_job{i}.log"
        logpath = os.path.join(root, logfile)
        os.makedirs(os.path.dirname(logpath), exist_ok=True)
        with open(logpath, "w", encoding="utf-8") as lf:
            code = subprocess.run(cmd, cwd=root, shell=True, stdout=lf,
                                  stderr=subprocess.STDOUT, timeout=3600).returncode
        tail = [l for l in read(logpath).split("\n") if l.strip()][-4:]
        jobs.append({"cmd": cmd, "code": code, "log": logfile, "tail": tail})
        finished.append(f"- [x] {cmd} — {today}, exit {code}, 로그 {logfile}")

    papers, net_ok = {}, True
    kw_text = read(os.path.join(root, "night", "watchlist.md"))
    keywords = [k for k in open_items_plain(section(kw_text, "키워드")) if k]
    for kw in keywords:
        try:
            papers[kw] = fetch_papers(kw)
        except Exception as e:
            papers[kw] = []
            net_ok = False

    n_done = sum(1 for j in jobs if j["code"] == 0)
    n_paper = sum(len(v) for v in papers.values())
    attention = []
    if any(j["code"] != 0 for j in jobs):
        attention.append("실패한 계산 작업 확인")
    if held:
        attention.append(f"보류된 명령 {len(held)}건(파괴적 패턴)")
    if not net_ok:
        attention.append("논문 조회 네트워크 오류")

    out = [f"# 야간 리포트 — {today} ({weekday_kr[today.weekday()]})", "",
           "## 아침 요약",
           f"- 계산: {n_done}/{len(jobs)}건 성공" + (f", 보류 {len(held)}건" if held else ""),
           f"- 논문: {n_paper}건 발견",
           "- 확인 필요: " + ("; ".join(attention) if attention else "없음"), "",
           "## 계산 작업 결과"]
    if not jobs and not held:
        out.append("- 실행 대기 큐가 비어 있었습니다.")
    for j in jobs:
        out += [f"### {j['cmd']}",
                f"- 상태: {'성공' if j['code'] == 0 else '실패'} (exit {j['code']})",
                f"- 로그: {j['log']}",
                "- 핵심 출력: " + (" / ".join(j["tail"]) if j["tail"] else "(없음)")]
    for c in held:
        out += [f"### {c}", "- 상태: 보류 (파괴적 패턴 감지, 실행 안 함)"]
    out += ["", "## 논문 모니터링"]
    for kw in keywords:
        out.append(f"### {kw}")
        if papers[kw]:
            for p in papers[kw]:
                out.append(f"- **{p['title']}** ({p['source']}, {p['date']}) — {p['authors']}. {p['link']}")
        else:
            out.append("- (결과 없음)")
    out += ["", "## 아침 액션 제안", "- [ ] 위 '확인 필요' 항목 검토",
            "- [ ] 관심 논문 저장 / 읽기"]
    write(os.path.join(root, "night", "reports", f"{today}.md"), "\n".join(out) + "\n")
    if finished:
        update_queue(finished)
    print(f"리포트 생성: night/reports/{today}.md (계산 {n_done}/{len(jobs)}, 논문 {n_paper})")
    build_dashboard()


def open_items_plain(lines):
    out = []
    for line in lines:
        m = re.match(r"\s*-\s*(.*)", line)
        if m and m.group(1).strip() and not m.group(1).startswith("("):
            out.append(m.group(1).strip())
    return out


def cmd_close():
    today = date.today()
    path = os.path.join(root, "daily", f"{today}.md")
    if not os.path.exists(path):
        print("오늘 daily 파일이 없습니다. 먼저 daily를 실행하세요.")
        return
    done = done_items(read(path))
    if not done:
        print("오늘 완료(- [x]) 항목이 없습니다.")
        return
    ppath = os.path.join(root, "portfolio", f"{today:%Y-%m}.md")
    header = f"# 업무일지 / 포트폴리오 — {today:%Y-%m}\n" if not os.path.exists(ppath) else ""
    block = [f"\n## {today} ({weekday_kr[today.weekday()]})"]
    for t in done:
        block.append(f"- {t}")
        block += ["  - 산출물:", "  - 결과 / 수치:", "  - 배운 점:"]
    with open(ppath, "a", encoding="utf-8") as f:
        f.write(header + "\n".join(block) + "\n")
    print(f"기록: portfolio/{today:%Y-%m}.md (완료 {len(done)}건). 산출물/수치/배운 점을 채워주세요.")
    build_dashboard()


cmds = {"daily": cmd_daily, "weekly": cmd_weekly, "night": cmd_night,
        "close": cmd_close, "dashboard": build_dashboard}

if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    if key in cmds:
        cmds[key]()
    else:
        print("사용법: python cowork.py [daily|weekly|night|close|dashboard]")
