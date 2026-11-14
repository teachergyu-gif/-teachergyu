"""합본 PDF 꼬리말에 교재 이름을 넣는다(진달래꽃 추가 문제집과 같은 자리: 짝수 쪽 왼쪽 아래, 홀수 쪽 오른쪽 아래, 쪽 상자 아래끝에 맞춤).
사용: python3 footer_text.py 입력.pdf 출력.pdf [문구] [앞문서쪽수] [건너뛸 쪽,…]"""
import sys, subprocess, os, tempfile
from pypdf import PdfReader, PdfWriter

src, out = sys.argv[1], sys.argv[2]
TEXT = sys.argv[3] if len(sys.argv) > 3 else '국제고 1학년 문학 교재'
N0 = int(sys.argv[4]) if len(sys.argv) > 4 else 11
SKIP = {int(x) for x in (sys.argv[5] if len(sys.argv) > 5 else '').split(',') if x}
r = PdfReader(src)
W, H = float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)
# (본문 왼쪽 끝, 오른쪽 끝, 글자 아래끝 y) — 개념 교재 쪽 / 문제 은행 쪽(쪽 상자 아래끝에 맞춤)
EDGE = {0: (48.0, 518.7, 764.5), 1: (62.3, 532.7, 815.0)}
SIZE = 6.5

pages = []
for i in range(len(r.pages)):
    n = i + 1
    if n in SKIP:
        pages.append(''); continue
    l, rt, y = EDGE[0 if i < N0 else 1]
    x, anchor = (l, 'start') if n % 2 == 0 else (rt, 'end')
    pages.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Noto Serif CJK KR" font-size="{SIZE}" fill="#6E6E6E">{TEXT}</text>')
html = ('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:%spt %spt;margin:0}html,body{margin:0}'
        '.pg{width:%spt;height:%spt;page-break-after:always;overflow:hidden}svg{display:block}</style></head><body>%s</body></html>'
        % (W, H, W, H, ''.join(f'<div class="pg"><svg width="{W}pt" height="{H}pt" viewBox="0 0 {W} {H}">{t}</svg></div>' for t in pages)))
with tempfile.TemporaryDirectory() as t:
    open(t + '/o.html', 'w').write(html)
    open(t + '/o.js', 'w').write("let pw;try{pw=require('playwright-core')}catch(e){pw=require('playwright')}(async()=>{const b=await pw.chromium.launch({executablePath:'/opt/pw-browsers/chromium'});"
                                 "const p=await b.newPage();await p.goto('file://%s/o.html');await p.evaluate(()=>document.fonts.ready);await p.pdf({path:'%s/o.pdf',preferCSSPageSize:true});await b.close()})();" % (t, t))
    subprocess.run(['node', t + '/o.js'], check=True, env=dict(os.environ, NODE_PATH=os.environ.get('NODE_PATH', '/opt/node22/lib/node_modules')))
    ov = PdfReader(t + '/o.pdf')
    w = PdfWriter()
    for i, p in enumerate(r.pages):
        if pages[i]:
            p.merge_page(ov.pages[i])
        w.add_page(p)
    w.write(out)
print('footer text on', sum(1 for x in pages if x), 'pages; skipped', sorted(SKIP))
