"""문제 은행 PDF 만들기: 1쪽 목차(최근 교재와 같은 디자인) + 2쪽부터 작품별 문제 → 빠른 정답·정답 및 해설.
1) render.py(A3 문제 은행 양식, 쪽 번호 2부터) → print.js → A4로 줄임(2주차 교재 합본과 같은 배율·자리)
2) 머리말 문구·꼬리말 교재 이름·쪽 상자(쪽/전체 쪽수)를 2쪽부터
3) 1쪽 목차: 작품별 문제·해설 시작 쪽을 PDF에서 찾아 채움
사용: python3 make.py [데이터폴더]   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else H + '/data'
TITLE = '국제고 1학년 기말고사 대비 문제 은행'
FOOT = '국제고 1학년 현대시 문제 은행'
OUT = os.path.join(H, '..', '국제고 1학년 기말고사 문제 은행 (진달래꽃·선운사에서·한 그리움이 다른 그리움에게).pdf')
WORKS = [('JD', '진달래꽃'), ('SW', '선운사에서'), ('HG', '한 그리움이 다른 그리움에게')]


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


with tempfile.TemporaryDirectory() as t:
    run('python3', '-I', f'{H}/pdf/render.py', DATA, f'{t}/qb.html', env=dict(os.environ, START_PAGE='2'))
    run('node', f'{H}/pdf/print.js', f'{t}/qb.html', f'{t}/qb.pdf', f'{H}/pdf/balanced.json')
    qb = PdfReader(f'{t}/qb.pdf').pages
    w = PdfWriter()
    w.add_blank_page(595, 841)
    for p in qb:
        w.add_page(a4(p))
    w.write(f'{t}/m0.pdf')
    total = len(w.pages)
    run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', '리치아카데미 | 국제고 1학년', '1', '1')
    run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', FOOT, '1', '1')
    run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '1', '1')
    # 목차 쪽 번호: 작품별 '문제 은행' 제목 쪽, 그 뒤 첫 '빠른 정답' 쪽
    texts = [(p.extract_text() or '') for p in PdfReader(f'{t}/m3.pdf').pages]
    toc = open(f'{H}/toc/toc.html').read().replace('TOTAL', str(total)).replace('TITLE', TITLE)
    start = 1
    for key, name in WORKS:
        q = next(i for i in range(start, total) if '문제 은행' in texts[i] and name in texts[i][:600])
        e = next(i for i in range(q, total) if '빠른 정답' in texts[i])
        toc = toc.replace(f'p. Q_{key}<', f'p. {q + 1}<').replace(f'p. E_{key}<', f'p. {e + 1}<')
        print(name, '문제', q + 1, '해설', e + 1)
        start = e + 1
    tmp = f'{H}/toc/_toc_out.html'
    open(tmp, 'w').write(toc)
    try:
        run('node', f'{H}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
    finally:
        os.remove(tmp)
    w = PdfWriter()
    w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
    for p in PdfReader(f'{t}/m3.pdf').pages[1:]:
        w.add_page(p)
    w.write(OUT)
    print('ok', OUT, total, 'pages')
