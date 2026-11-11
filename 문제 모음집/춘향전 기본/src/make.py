"""문제 은행 PDF 만들기: 1쪽 목차(최근 교재와 같은 디자인) + 2쪽부터 작품별 문제 → 빠른 정답·정답 및 해설.
1) render.py(A3 문제 은행 양식, 쪽 번호 2부터) → print.js → A4로 줄임(2주차 교재 합본과 같은 배율·자리)
2) 머리말 문구·꼬리말 교재 이름·쪽 상자(쪽/전체 쪽수)를 2쪽부터
3) 1쪽 목차: 작품별 문제·해설 시작 쪽을 PDF에서 찾아 채움
사용: python3 make.py [데이터폴더]   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else H + '/data'
TITLE = '부산외고 1학년 기말고사 대비 「춘향전」 문제 은행'
FOOT = '부산외고 1학년 「춘향전」 문제 은행'
OUT = os.path.join(H, '..', '부산외고 1학년 기말고사 대비 「춘향전」 문제 은행.pdf')
WORKS = [('CH', '｢춘향전｣ 문제 은행', True), ('CH2', '｢춘향전｣ 실전 문제 은행', True)]


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
    memo = [i + 1 for i, p in enumerate(PdfReader(f'{t}/m0.pdf').pages) if (p.extract_text() or '').strip() == 'MEMO']
    skip = ','.join(str(x) for x in [1] + memo)   # 1쪽(목차)·MEMO 쪽은 머리말·꼬리말 없음
    print('MEMO 쪽', memo)
    run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', '리치아카데미 | 부산외고 1학년', '1', skip)
    run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', FOOT, '1', skip)
    run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '1', skip)
    # 목차 쪽 번호: 작품별 '문제 은행' 제목 쪽, 그 뒤 첫 '빠른 정답' 쪽
    texts = [(p.extract_text() or '') for p in PdfReader(f'{t}/m3.pdf').pages]
    start = 1
    pages = {}
    for key, name, has_ex in WORKS:
        q = next(i for i in range(start, total) if name in texts[i][:600])
        pages['Q_' + key] = q + 1; start = q + 1
        if has_ex:
            e = next(i for i in range(q, total) if '빠른 정답' in texts[i])
            pages['E_' + key] = e + 1; start = e + 1
    print(pages)
    sys.path.insert(0, f'{H}/toc')
    import toc_exam   # 1쪽: 시험지 머리 + <목 차> 상자(N제 모의고사와 같은 양식)
    secs = [('「춘향전」 문제 은행', [('문제', pages['Q_CH']), ('정답 및 해설', pages['E_CH']),
                                  ('실전 문제', pages['Q_CH2']), ('실전 정답 및 해설', pages['E_CH2'])])]
    toc = toc_exam.page(TITLE, secs, None, total)
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
