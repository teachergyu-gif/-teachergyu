"""모의고사 PDF 만들기: data/exam.json → render.py(A3 시험지 양식) → print.js → A4로 줄임 → 머리말(2쪽부터)·꼬리말·쪽 상자
사용: python3 data/build.py … 로 exam.json을 만든 뒤 python3 make.py   (NODE_PATH에 playwright)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
TITLE = '국제고 2학년 실전모의고사 3회'
FOOT = TITLE
OUT = os.path.join(H, '..', TITLE + '.pdf')


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


for mode, name in (('q', '문제지'), ('a', '해설지')):
  OUT = os.path.join(H, '..', f'{TITLE} ({name}).pdf')
  with tempfile.TemporaryDirectory() as t:
    run('python3', '-I', f'{H}/pdf/render.py', f'{H}/data/exam.json', f'{t}/m.html', env=dict(os.environ, HEAD=TITLE, MODE=mode))
    run('node', f'{H}/pdf/print.js', f'{t}/m.html', f'{t}/m.pdf', f'{H}/pdf/balanced.json')
    w = PdfWriter()
    for p in PdfReader(f'{t}/m.pdf').pages:
        w.add_page(a4(p))
    w.write(f'{t}/m0.pdf')
    total = len(w.pages)
    # 머리말 문구('리치아카데미 | 부산외고 1학년')·꼬리말 교재 이름은 넣지 않음(사용자 지정)
    run('python3', '-I', f'{H}/footer_box.py', f'{t}/m0.pdf', f'{t}/m3.pdf', str(total), '0', '')
    os.replace(f'{t}/m3.pdf', OUT)
    print('ok', OUT, total, 'pages')
