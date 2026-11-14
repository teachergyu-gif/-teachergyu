"""합본 PDF 머리말의 쪽 번호 옆에 문구(리치아카데미 | 국제고 1학년)를 넣는다.
짝수 쪽(번호 왼쪽)은 번호 오른쪽에, 홀수 쪽(번호 오른쪽)은 번호 왼쪽에. 번호 위치는 쪽마다 PDF에서 읽는다.
사용: python3 header_phrase.py 입력.pdf 출력.pdf [문구] [앞문서쪽수] [건너뛸 쪽,…]"""
import sys, re, subprocess, os, json, tempfile
from pypdf import PdfReader, PdfWriter

src, out = sys.argv[1], sys.argv[2]
PHRASE = sys.argv[3] if len(sys.argv) > 3 else '리치아카데미 | 국제고 1학년'
N0 = int(sys.argv[4]) if len(sys.argv) > 4 else 11
SKIP = {int(x) for x in (sys.argv[5] if len(sys.argv) > 5 else '').split(',') if x}   # 머리말이 감춰진 쪽(MEMO)
r = PdfReader(src)
W, H = float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)
BASE = {0: 81.0, 1: 78.5}   # 쪽 번호 글자 아래끝(pt, 위에서부터): 개념 교재 쪽 / 문제 은행 쪽
GAP, SIZE = 7.0, 8.5

items = []
for i in range(len(r.pages)):
    xml = subprocess.run(['pdftotext', '-f', str(i + 1), '-l', str(i + 1), '-bbox', src, '-'], capture_output=True, text=True).stdout
    num = None
    for x0, y0, x1, y1, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(\d+)</word>', xml):
        if float(y1) < 100 and int(t) == i + 1:
            num = (float(x0), float(x1)); break
    if not num or i + 1 in SKIP:
        items.append(None); continue
    base = BASE[0 if i < N0 else 1]
    even = num[0] < W / 2
    items.append({'x': num[1] + GAP if even else num[0] - GAP, 'anchor': 'start' if even else 'end', 'y': base})

svg = []
for it in items:
    t = '' if not it else (f'<text x="{it["x"]:.2f}" y="{it["y"]:.2f}" text-anchor="{it["anchor"]}" font-family="Noto Sans CJK KR" font-weight="700" '
                           f'font-size="{SIZE}" fill="#3A3A3A">{PHRASE}</text>')
    svg.append(f'<div class="pg"><svg width="{W}pt" height="{H}pt" viewBox="0 0 {W} {H}">{t}</svg></div>')
html = ('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:%spt %spt;margin:0}html,body{margin:0}'
        '.pg{width:%spt;height:%spt;page-break-after:always;overflow:hidden}svg{display:block}</style></head><body>%s</body></html>') % (W, H, W, H, ''.join(svg))
with tempfile.TemporaryDirectory() as t:
    open(t + '/o.html', 'w').write(html)
    js = ("let pw;try{pw=require('playwright-core')}catch(e){pw=require('playwright')}(async()=>{const b=await pw.chromium.launch({executablePath:'/opt/pw-browsers/chromium'});"
          "const p=await b.newPage();await p.goto('file://%s/o.html');await p.evaluate(()=>document.fonts.ready);await p.pdf({path:'%s/o.pdf',preferCSSPageSize:true});await b.close()})();" % (t, t))
    open(t + '/o.js', 'w').write(js)
    subprocess.run(['node', t + '/o.js'], check=True, env=dict(os.environ, NODE_PATH=os.environ.get('NODE_PATH', '/opt/node22/lib/node_modules')))
    ov = PdfReader(t + '/o.pdf')
    w = PdfWriter()
    for i, p in enumerate(r.pages):
        if items[i]:
            p.merge_page(ov.pages[i])
        w.add_page(p)
    w.write(out)
print('phrase on', sum(1 for x in items if x), 'pages; skipped', [i + 1 for i, x in enumerate(items) if not x])
