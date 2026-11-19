"""문법 기출문제(품사·단어) 합본: 품사 문제(원본 PDF 그대로) → 품사 정답 및 해설 → 단어 문제(원본) → 단어 정답 및 해설.
해설 쪽은 render.py(MODE=x, A3 문제 은행 양식) → print.js → A4로 줄임 → 쪽 상자. 쪽 번호는 각 부분 원본에 이어서.
사용: python3 fix_raw.py && python3 data/build.py && python3 make.py   (NODE_PATH에 playwright)"""
import os, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
TITLE = '문법 기출문제(2021년~2025년 시행) 품사·단어'
OUT = os.path.join(H, '..', TITLE + '.pdf')
PARTS = [('품사', 'raw/fixed/1_품사.pdf', 'pum'), ('단어', 'raw/fixed/2_단어.pdf', 'dan')]


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


w = PdfWriter()
for name, raw, key in PARTS:
    orig = PdfReader(f'{H}/{raw}')
    n0 = len(orig.pages)
    with tempfile.TemporaryDirectory() as t:
        run('python3', '-I', f'{H}/pdf/render.py', f'{H}/data/{key}/qb.json', f'{t}/x.html',
            env=dict(os.environ, MODE='x', EXT=f'{name} 정답 및 해설', START_PAGE=str(n0 + 1), HEAD=TITLE))
        run('node', f'{H}/pdf/print.js', f'{t}/x.html', f'{t}/x.pdf')
        x = PdfWriter()
        for p in PdfReader(f'{t}/x.pdf').pages:
            x.add_page(a4(p))
        x.write(f'{t}/x0.pdf')
        total = n0 + len(x.pages)
        run('python3', '-I', f'{H}/footer_box.py', f'{t}/x0.pdf', f'{t}/x1.pdf', str(total), '0', '', str(n0))
        for p in orig.pages:          # 문제: 원본 그대로
            w.add_page(p)
        for p in PdfReader(f'{t}/x1.pdf').pages:
            w.add_page(p)
        print(name, '문제', n0, '쪽 + 해설', len(x.pages), '쪽')
w.write(OUT)
print('ok', OUT, len(w.pages), 'pages')
