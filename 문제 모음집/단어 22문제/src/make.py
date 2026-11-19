"""문제 은행 PDF 만들기: 1쪽 목차(최근 교재와 같은 디자인) + 2쪽부터 작품별 문제 → 빠른 정답·정답 및 해설.
1) render.py(A3 문제 은행 양식, 쪽 번호 2부터) → print.js → A4로 줄임(2주차 교재 합본과 같은 배율·자리)
2) 머리말 문구·꼬리말 교재 이름·쪽 상자(쪽/전체 쪽수)를 2쪽부터
3) 1쪽 목차: 작품별 문제·해설 시작 쪽을 PDF에서 찾아 채움
사용: python3 make.py [데이터폴더]   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = H + '/data/qb.json'
TITLE = '단어 22문제'
FOOT = TITLE
OUT = os.path.join(H, '..', f'{TITLE}.pdf')


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


for mode, out in (('', os.path.join(H, '..', f'{TITLE} (문제 은행).pdf')),):   # 문제 → 정답 및 해설(사용자 요청으로 해설 추가)
  with tempfile.TemporaryDirectory() as t:   
    run('python3', '-I', f'{H}/pdf/render.py', DATA, f'{t}/qb.html', env=dict(os.environ, START_PAGE='1', MODE=mode, HEAD=TITLE))
    run('node', f'{H}/pdf/print.js', f'{t}/qb.html', f'{t}/qb.pdf', f'{H}/pdf/balanced.json')
    w = PdfWriter()
    for p in PdfReader(f'{t}/qb.pdf').pages:
        w.add_page(a4(p))
    w.write(f'{t}/m0.pdf')
    total = len(w.pages)
    run('python3', '-I', f'{H}/footer_box.py', f'{t}/m0.pdf', out, str(total), '0', '')
    print('ok', out, total, 'pages')
