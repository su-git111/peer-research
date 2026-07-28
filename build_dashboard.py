import datetime as dt
import glob
import html
import os
import re

root = os.path.dirname(os.path.abspath(__file__))
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def checkboxes(lines):
    done = total = 0
    items = []
    for line in lines:
        m = re.match(r"\s*-\s*\[([ xX])\]\s*(.*)", line)
        if not m:
            continue
        text = m.group(2).strip()
        if not text:
            continue
        checked = m.group(1).lower() == "x"
        total += 1
        done += int(checked)
        items.append((checked, text))
    return done, total, items


def section(text, heading):
    out = []
    collecting = False
    for line in text.splitlines():
        if line.startswith("## "):
            collecting = line[3:].strip().startswith(heading)
            continue
        if collecting:
            out.append(line)
    return out


def latest(folder, pattern):
    hits = sorted(glob.glob(os.path.join(root, folder, pattern)))
    return hits[-1] if hits else None


def bar(done, total):
    pct = round(100 * done / total) if total else 0
    return f'<div class="bar"><span style="width:{pct}%"></span></div><small>{done}/{total} · {pct}%</small>'


def section_ln(text, heading):
    out, collecting = [], False
    for i, line in enumerate(text.split("\n")):
        if line.startswith("## "):
            collecting = line[3:].strip().startswith(heading)
            continue
        if collecting:
            out.append((i, line))
    return out


def checkboxes_ln(pairs):
    items = []
    for lineno, line in pairs:
        m = re.match(r"\s*-\s*\[([ xX])\]\s*(.*)", line)
        if not m:
            continue
        text = m.group(2).strip()
        if not text:
            continue
        items.append((m.group(1).lower() == "x", text, lineno))
    return items


def checklist(file, items):
    if not items:
        return '<p class="empty">항목 없음</p>'
    rows = []
    for checked, text, lineno in items:
        box = "checked" if checked else ""
        cls = "done" if checked else ""
        rows.append(
            f'<li class="{cls}"><input type="checkbox" {box} data-file="{html.escape(file)}" '
            f'data-line="{lineno}" onchange="toggle(this)"><span>{html.escape(text)}</span></li>'
        )
    return '<ul class="check">' + "".join(rows) + "</ul>"


projects = []
for block in re.split(r"\n(?=##\s+P)", read(os.path.join(root, "projects.md"))):
    head = block.splitlines()[0] if block.splitlines() else ""
    m = re.match(r"##\s+(P\d+\..*)", head)
    if not m:
        continue
    goal = ""
    for line in block.splitlines():
        gm = re.search(r"큰 목표:\s*(.*)", line)
        if gm:
            goal = gm.group(1).strip()
            break
    done, total, _ = checkboxes(block.splitlines())
    projects.append({"name": m.group(1).strip(), "goal": goal, "done": done, "total": total})

week = {"title": "-", "top": [], "file": ""}
wpath = latest("weekly", "2*.md")
if wpath:
    wtext = read(wpath)
    week["file"] = os.path.relpath(wpath, root).replace("\\", "/")
    week["title"] = wtext.splitlines()[0].lstrip("# ").strip()
    week["top"] = checkboxes_ln(section_ln(wtext, "이번 주 목표"))

day = {"title": "-", "focus": [], "slots": {}, "file": ""}
dpath = latest("daily", "2*.md")
if dpath:
    dtext = read(dpath)
    day["file"] = os.path.relpath(dpath, root).replace("\\", "/")
    day["title"] = dtext.splitlines()[0].lstrip("# ").strip()
    for line in section(dtext, "오늘의 초점"):
        m = re.match(r"\s*-\s*(.*)", line)
        if m and m.group(1).strip():
            day["focus"].append(m.group(1).strip())
    for slot in ["오전", "오후", "밤"]:
        day["slots"][slot] = checkboxes_ln(section_ln(dtext, slot))

night = {"title": None, "summary": []}
npath = latest("night/reports", "2*.md")
if npath:
    ntext = read(npath)
    night["title"] = ntext.splitlines()[0].lstrip("# ").strip()
    for line in section(ntext, "아침 요약"):
        m = re.match(r"\s*-\s*(.*)", line)
        if m and m.group(1).strip():
            night["summary"].append(m.group(1).strip())

now = dt.datetime.now()
stamp = f"{now:%Y-%m-%d %H:%M} ({weekday_kr[now.weekday()]})"

project_cards = []
for p in projects:
    goal = html.escape(p["goal"]) if p["goal"] else '<span class="empty">큰 목표 미정</span>'
    project_cards.append(
        f'<div class="card"><h3>{html.escape(p["name"])}</h3>'
        f'<p class="goal">{goal}</p>{bar(p["done"], p["total"])}</div>'
    )
project_html = "".join(project_cards) or '<p class="empty">projects.md에 프로젝트를 추가하세요</p>'

night_html = ""
if night["title"]:
    rows = "".join(f"<li>{html.escape(s)}</li>" for s in night["summary"]) or "<li>요약 없음</li>"
    night_html = (
        f'<div class="night"><h4>🌙 {html.escape(night["title"])}</h4>'
        f'<ul>{rows}</ul></div>'
    )

focus_html = ""
if day["focus"]:
    focus_html = '<p class="focus">🎯 ' + " · ".join(html.escape(f) for f in day["focus"]) + "</p>"

slot_html = []
slot_icon = {"오전": "🌅", "오후": "☀️", "밤": "🌙"}
day_done = day_total = 0
for slot in ["오전", "오후", "밤"]:
    items = day["slots"].get(slot, [])
    d = sum(1 for c, _, _ in items if c)
    day_done += d
    day_total += len(items)
    slot_html.append(
        f'<div class="slot"><h4>{slot_icon[slot]} {slot} '
        f'<small>{d}/{len(items)}</small></h4>{checklist(day["file"], items)}</div>'
    )

week_phases = {"주초": [], "주중": [], "주말": []}
week_other = []
for checked, text, lineno in week["top"]:
    ph = next((k for k in week_phases if text.startswith(k)), None)
    if ph:
        week_phases[ph].append((checked, text[len(ph):].lstrip(" ·—-").strip(), lineno))
    else:
        week_other.append((checked, text, lineno))

phase_meta = [("주초", "🟦", "#3b6ef5", 2), ("주중", "🟨", "#f5a623", 3), ("주말", "🟩", "#2fb37a", 2)]
if any(week_phases.values()):
    segs, cols = [], []
    for name, icon, color, days in phase_meta:
        items = week_phases[name]
        d = sum(1 for c, _, _ in items if c)
        pct = round(100 * d / len(items)) if items else 0
        segs.append(
            f'<div class="wseg" style="flex:{days}">'
            f'<div class="wfill" style="width:{pct}%;background:{color}33"></div>'
            f'<div class="wtxt">{icon} {name} <b>{d}/{len(items)}</b></div></div>'
        )
        cols.append(
            f'<div class="slot" style="border-top:3px solid {color}">'
            f'<h4>{icon} {name} <small>{d}/{len(items)}</small></h4>{checklist(week["file"], items)}</div>'
        )
    if week_other:
        od = sum(1 for c, _, _ in week_other if c)
        cols.append(f'<div class="slot"><h4>🔹 기타 <small>{od}/{len(week_other)}</small></h4>{checklist(week["file"], week_other)}</div>')
    week_html = f'<div class="wtl">{"".join(segs)}</div><div class="grid">{"".join(cols)}</div>'
else:
    wd = sum(1 for c, _, _ in week["top"] if c)
    week_html = f'<div class="slot">{bar(wd, len(week["top"]))}{checklist(week["file"], week["top"])}</div>'

page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>연구 일지 봇 대시보드</title>
<link rel="icon" href="icon.ico">
<style>
:root {{
  --bg:#f6f7f9; --card:#fff; --fg:#1c2430; --muted:#7a8699;
  --line:#e6e9ef; --accent:#3b6ef5; --done:#2fb37a; --barbg:#e6e9ef;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#12151b; --card:#1b1f27; --fg:#e6ebf2; --muted:#8b96a7;
    --line:#2a2f3a; --accent:#5b86f7; --done:#38c78a; --barbg:#2a2f3a; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg);
  font-family:'Segoe UI',system-ui,-apple-system,'Malgun Gothic',sans-serif; }}
h1 {{ font-size:20px; margin:0 0 4px; }}
h2 {{ font-size:15px; margin:28px 0 12px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }}
h3 {{ font-size:15px; margin:0 0 6px; }}
h4 {{ font-size:14px; margin:0 0 8px; display:flex; justify-content:space-between; align-items:center; }}
h4 small, .stamp {{ color:var(--muted); font-weight:400; }}
.stamp {{ font-size:13px; }}
.grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }}
.card, .slot {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }}
.goal {{ color:var(--muted); font-size:13px; margin:0 0 12px; min-height:18px; }}
.bar {{ height:8px; background:var(--barbg); border-radius:6px; overflow:hidden; margin-bottom:4px; }}
.bar span {{ display:block; height:100%; background:var(--accent); }}
small {{ font-size:12px; color:var(--muted); }}
.focus {{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent);
  border-radius:8px; padding:10px 14px; font-size:14px; margin:0 0 14px; }}
.night {{ background:var(--card); border:1px solid var(--line); border-left:3px solid #8a6bf5;
  border-radius:12px; padding:14px 18px; margin:16px 0 4px; }}
.night h4 {{ display:block; margin:0 0 8px; }}
.night ul {{ margin:0; padding-left:18px; }}
.night li {{ font-size:14px; line-height:1.6; }}
ul.check {{ list-style:none; padding:0; margin:0; }}
ul.check li {{ display:flex; gap:8px; align-items:flex-start; padding:5px 0; font-size:14px; line-height:1.4; }}
ul.check li.done span {{ color:var(--muted); text-decoration:line-through; }}
ul.check input {{ margin-top:3px; accent-color:var(--done); }}
.empty {{ color:var(--muted); font-size:13px; font-style:italic; }}
.top {{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px; }}
.wtl {{ display:flex; gap:8px; margin:6px 0 14px; }}
.wseg {{ position:relative; height:44px; border-radius:10px; overflow:hidden;
  background:var(--barbg); border:1px solid var(--line); min-width:76px; }}
.wfill {{ position:absolute; left:0; top:0; bottom:0; }}
.wtxt {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  gap:5px; font-size:13px; font-weight:600; z-index:1; white-space:nowrap; }}
.wtxt b {{ color:var(--muted); font-weight:600; }}
.hint {{ color:var(--muted); font-size:12px; margin:18px 0 0; text-align:center; }}
</style></head><body>
<div class="top"><h1>📓 연구 일지 봇 대시보드</h1><span class="stamp">갱신 {stamp}</span></div>
{night_html}
<h2>진행 프로젝트</h2>
<div class="grid">{project_html}</div>

<h2>이번 주 · {html.escape(week["title"])}</h2>
{week_html}

<h2>오늘 · {html.escape(day["title"])}</h2>
{focus_html}
<div class="slot" style="margin-bottom:14px">{bar(day_done, day_total)}</div>
<div class="grid">{"".join(slot_html)}</div>
<p class="hint" id="hint"></p>
<script>
var served = location.protocol === 'http:' || location.protocol === 'https:';
if (!served) {{
  document.querySelectorAll('ul.check input').forEach(function(c){{ c.disabled = true; }});
  document.getElementById('hint').textContent = '읽기 전용 · 체크해서 저장하려면 연구일지봇 메뉴 [6]으로 여세요';
}} else {{
  document.getElementById('hint').textContent = '체크박스를 클릭하면 바로 저장됩니다';
}}
function toggle(el) {{
  fetch('/toggle', {{method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{file: el.dataset.file, line: parseInt(el.dataset.line)}})}})
   .then(function(r){{ if(!r.ok) throw 0; location.reload(); }})
   .catch(function(){{ el.checked = !el.checked; alert('저장 실패 — 서버로 열어야 합니다.'); }});
}}
</script>
</body></html>"""

with open(os.path.join(root, "dashboard.html"), "w", encoding="utf-8") as f:
    f.write(page)
print("dashboard.html 갱신됨:", stamp)
