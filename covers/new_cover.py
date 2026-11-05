"""One-shot cover: render PDF + preview PNG, then commit & push.
Usage:
  python3 covers/new_cover.py concept "<폴더>/<파일명>.pdf" "<제목>" "<학교 학년>" "<과목>"
  python3 covers/new_cover.py monthly "<폴더>/<파일명>.pdf" "<문구>"
Paths are relative to covers/. Fonts/playwright come from the session scratchpad node_modules."""
import os, subprocess, sys

COV = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(COV)
NM = "/tmp/claude-0/-home-user/7daa3587-3e11-50f3-879d-8fd5436a77fe/scratchpad/node_modules"
OLD_NM = "/tmp/claude-0/-home-user--teachergyu/ccaedf91-0008-5bf5-a455-13038ab5cfd7/scratchpad/node_modules"
env = dict(os.environ, FONT_DIR=NM, NODE_PATH=NM)

kind, rel = sys.argv[1], sys.argv[2]
out = os.path.join(COV, rel)
os.makedirs(os.path.dirname(out), exist_ok=True)

if kind == "concept":
    l1, l2, tag = sys.argv[3:6]
    subprocess.run(["python3", os.path.join(COV, "make_cover.py"), out, l1, l2, tag], check=True, env=env)
    label = f"{l2} {l1}"
else:
    text = sys.argv[3]
    tpl = open(os.path.join(COV, "부산외고 2학년", "monthly_cover.html"), encoding="utf-8").read()
    page = (tpl.replace(OLD_NM, NM).replace("/home/user/-teachergyu/", R + "/")
               .replace("부산외고 2학년 2025학년도 6월 변형문제", text))
    src = os.path.join(os.path.dirname(out), ".monthly_tmp.html")
    open(src, "w", encoding="utf-8").write(page)
    js = """const { chromium } = require('playwright-core');
(async () => { const b = await chromium.launch({executablePath:'/opt/pw-browsers/chromium', args:['--allow-file-access-from-files']});
 const p = await b.newPage(); await p.goto('file://' + process.argv[1]); await p.evaluate(() => document.fonts.ready);
 await p.pdf({path: process.argv[2], format:'A4', printBackground:true, preferCSSPageSize:true}); await b.close(); })();"""
    subprocess.run(["node", "-e", js, src, out], check=True, env=env)
    os.remove(src)
    label = text

png = os.path.join(os.path.dirname(NM), "preview")
subprocess.run(["pdftoppm", "-png", "-r", "50", "-singlefile", out, png], check=True)
print("wrote", out, "\npreview", png + ".png")

subprocess.run(["git", "-C", R, "add", "covers"], check=True)
msg = f"{label} 표지 추가\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_016r59Tk41juewQugUdkdmUS"
subprocess.run(["git", "-C", R, "-c", "user.name=teachergyu", "-c", "user.email=teachergyu@naver.com", "commit", "-q", "-m", msg], check=True)
subprocess.run(["git", "-C", R, "push", "-q", "-u", "origin", "HEAD"], check=True)
print("pushed")
