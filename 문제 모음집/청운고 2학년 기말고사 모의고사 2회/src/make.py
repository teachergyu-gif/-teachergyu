"""문제 은행 PDF 만들기: 1쪽 목차(최근 교재와 같은 디자인) + 2쪽부터 작품별 문제 → 빠른 정답·정답 및 해설.
1) render.py(A3 문제 은행 양식, 쪽 번호 2부터) → print.js → A4로 줄임(2주차 교재 합본과 같은 배율·자리)
2) 머리말 문구·꼬리말 교재 이름·쪽 상자(쪽/전체 쪽수)를 2쪽부터
3) 1쪽 목차: 작품별 문제·해설 시작 쪽을 PDF에서 찾아 채움
사용: python3 make.py [데이터폴더]   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = H + '/data/qb.json'
TITLE = '청운고 2학년 기말고사 모의고사 2회'
FOOT = '청운고 2학년 기말고사 모의고사 2회'
OUT = os.path.join(H, '..', '청운고 2학년 기말고사 모의고사 2회.pdf')
PARTS = [('문제', '청운고 2학년 기말고사 모의고사 2회')]


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


with tempfile.TemporaryDirectory() as t:
    run('python3', '-I', f'{H}/pdf/render.py', DATA, f'{t}/qb.html', env=dict(os.environ, START_PAGE='1'))
    run('node', f'{H}/pdf/print.js', f'{t}/qb.html', f'{t}/qb.pdf', f'{H}/pdf/balanced.json')
    w = PdfWriter()
    for p in PdfReader(f'{t}/qb.pdf').pages:
        w.add_page(a4(p))
    w.write(f'{t}/m0.pdf')
    total = len(w.pages)
    # 목차 없음: 1쪽 머리(제목·로고) 아래부터 바로 문제(사용자 지정)
    run('python3', '-I', f'{H}/footer_box.py', f'{t}/m0.pdf', OUT, str(total), '0', '')
    print('ok', OUT, total, 'pages')
