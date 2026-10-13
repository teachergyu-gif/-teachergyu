"""Stand-alone series cover (ALL AROUND KOREAN, academy navy) → one-page PDF.
Usage: python3 make_cover.py out.pdf "<line 1>" "<line 2>" "<tag>"  (FONT_DIR/NODE_PATH = fontsource node_modules)"""
import html, os, subprocess, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, l1, l2, tag = sys.argv[1:5]
fd = os.environ["FONT_DIR"]
page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{fd}/@fontsource/nanum-myeongjo/800.css">
<style>@page{{size:A4;margin:0}} body{{margin:0}}
.cv{{position:relative;width:210mm;height:297mm;background:#fff url('file://{R}/brand/cover_all_around_korean_navy.jpg') no-repeat;background-size:210mm 297mm;overflow:hidden}}
.l{{position:absolute;right:14mm;bottom:21mm;text-align:right;font-family:'Nanum Myeongjo',serif;font-weight:800;color:#29334A}}
.l1{{font-size:19pt;margin-bottom:5.5mm}} .l2{{font-size:21pt}}
.t{{position:absolute;left:15mm;bottom:18.5mm;font-family:'Nanum Myeongjo',serif;font-weight:800;font-size:31pt;color:#29334A}}</style></head>
<body><div class="cv"><div class="l"><div class="l1">{html.escape(l1)}</div><div class="l2">{html.escape(l2)}</div></div>
<div class="t">{html.escape(tag)}</div></div></body></html>"""
src = os.path.join(os.path.dirname(os.path.abspath(out)), ".cover_tmp.html")
open(src, "w", encoding="utf-8").write(page)
js = f"""const {{ chromium }} = require('playwright-core');
(async () => {{ const b = await chromium.launch({{executablePath:'/opt/pw-browsers/chromium', args:['--allow-file-access-from-files']}});
 const p = await b.newPage(); await p.goto('file://{src}'); await p.evaluate(() => document.fonts.ready);
 await p.pdf({{path: {out!r}, format:'A4', printBackground:true, preferCSSPageSize:true}}); await b.close(); }})();"""
subprocess.run(["node", "-e", js], check=True)
os.remove(src)
print("wrote", out)
