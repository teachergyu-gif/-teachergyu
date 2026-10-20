"""교과서 문학 교재 합본(63쪽) 뒤에 진달래꽃 추가 문제 은행을 붙여 하나의 PDF로 만든다.
1) render_jd.py → A3 문제 은행(64쪽부터) → A4로 줄임(앞 합본의 문제 은행 쪽과 같은 배율·자리)
2) 머리말 문구·꼬리말 교재 이름은 새로 붙인 쪽에만, 쪽 상자(쪽/전체 쪽수)는 모든 쪽을 새 전체 쪽수로 다시 그림
3) 1쪽 목차를 '「진달래꽃」 추가 문제 은행'이 들어간 목차로 바꿈
사용: python3 merge.py 앞합본.pdf 출력.pdf   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(H)
base, out = sys.argv[1], sys.argv[2]
N_BASE = len(PdfReader(base).pages)
MEMO = '7'   # 앞 합본 7쪽 MEMO(머리말·꼬리말 없음)


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


with tempfile.TemporaryDirectory() as t:
    env = dict(os.environ, START_PAGE=str(N_BASE + 1))
    run('python3', '-I', f'{H}/render_jd.py', f'{t}/jd.html', env=env)
    run('node', f'{SRC}/pdf/print.js', f'{t}/jd.html', f'{t}/jd_a3.pdf')
    # A3 → A4: 앞 합본 문제 은행 쪽과 같은 변환(배율 841/1191.12, 가로 가운데)
    a3 = PdfReader(f'{t}/jd_a3.pdf')
    w = PdfWriter()
    for p in PdfReader(base).pages:
        w.add_page(p)
    k = 841 / 1191.12
    for p in a3.pages:
        p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
        p.mediabox.lower_left = (0, 0); p.mediabox.upper_right = (595, 841)
        p.cropbox.lower_left = (0, 0); p.cropbox.upper_right = (595, 841)
        w.add_page(p)
    w.write(f'{t}/m0.pdf')
    total = len(w.pages)
    old = ','.join(str(i) for i in range(1, N_BASE + 1))
    run('python3', '-I', f'{SRC}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', '리치아카데미 | 국제고 1학년', '11', old)
    run('python3', '-I', f'{SRC}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', '국제고 1학년 문학 교재', '11', old)
    run('python3', '-I', f'{SRC}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '11', MEMO + ',1')
    # 목차(1쪽)
    toc = open(f'{SRC}/toc/toc_jd.html').read().replace('TOTAL', str(total))
    tmp = f'{SRC}/toc/_toc_out.html'
    open(tmp, 'w').write(toc)
    try:
        run('node', f'{SRC}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
    finally:
        os.remove(tmp)
    r = PdfReader(f'{t}/m3.pdf')
    w = PdfWriter()
    w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
    for p in r.pages[1:]:
        w.add_page(p)
    w.write(out)
print('pages', total)
