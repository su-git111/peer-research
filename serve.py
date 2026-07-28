# 연구일지봇 대시보드 로컬 서버 — 체크박스 클릭을 마크다운에 되쓴다.
# 실행: python serve.py  (브라우저가 열림, 이 창을 닫으면 종료)
# 마크다운이 여전히 단일 소스: 체크 클릭 -> 해당 파일의 [ ] <-> [x] 만 바꾸고 대시보드 재생성.

import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import webbrowser

root = os.path.dirname(os.path.abspath(__file__))
PORT = 8787


def rebuild():
    subprocess.run([sys.executable, os.path.join(root, "build_dashboard.py")], cwd=root)


def toggle_line(relfile, line):
    p = os.path.normpath(os.path.join(root, relfile))
    if os.path.commonpath([p, root]) != root or not p.endswith(".md") or not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not isinstance(line, int) or not (0 <= line < len(lines)):
        return False
    m = re.match(r"(\s*-\s*\[)([ xX])(\].*)", lines[line])
    if not m:
        return False
    lines[line] = m.group(1) + (" " if m.group(2).lower() == "x" else "x") + m.group(3)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=root, **k)

    def do_GET(self):
        if self.path in ("/", "", "/index.html", "/dashboard.html"):
            rebuild()
            self.path = "/dashboard.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/toggle":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or "{}")
            ok = toggle_line(str(data.get("file", "")), data.get("line", -1))
        except Exception:
            ok = False
        if ok:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(400)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    url = f"http://localhost:{PORT}/dashboard.html"
    try:
        srv = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print("대시보드 서버가 이미 실행 중입니다. 브라우저를 엽니다.")
        webbrowser.open(url)
        sys.exit()
    print(f"연구일지봇 대시보드: {url}")
    print("체크박스를 클릭하면 바로 저장됩니다. (이 창을 닫으면 종료)")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
