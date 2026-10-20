"""교과서 문학 교재 합본: PART 01 작품 분석(1~11쪽, 기존 합본에서) + 선운사·한 그리움 문제 은행 + 진달래꽃 추가 문제 은행.
1) 문제 은행 두 부분을 데이터에서 다시 짠다(A3, 쪽 번호 이어서) → A4로 줄임(기존 합본과 같은 배율·자리)
2) 12쪽부터 머리말 문구·꼬리말 교재 이름, 모든 쪽의 쪽 상자(쪽/전체 쪽수)를 새 전체 쪽수로
3) PART 01 오탈자 고침(patch_part1.py), 1쪽 목차를 '「진달래꽃」 추가 문제 은행'이 들어간 목차로
사용: python3 merge.py 기존합본.pdf 출력.pdf   (NODE_PATH에 playwright-core)"""
import os, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(H)
base, out = sys.argv[1], sys.argv[2]
N_FRONT = 11   # PART 01 작품 분석(목차 포함) 쪽수
MEMO = '7'     # 7쪽 MEMO(머리말·꼬리말 없음)
FOOT = '국제고 1학년 2주차 교재'        # 꼬리말 교재 이름(짝수 쪽 왼쪽·홀수 쪽 오른쪽 아래)


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    """A3 문제 은행 쪽 → A4(기존 합본 문제 은행 쪽과 같은 변환: 배율 841/1191.12, 가로 가운데)"""
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


with tempfile.TemporaryDirectory() as t:
    # 선운사·한 그리움 문제 은행(12쪽부터, 끝의 MEMO 쪽은 뺌)
    run('python3', '-I', f'{SRC}/pdf/render.py', f'{SRC}/data', f'{t}/sw.html', env=dict(os.environ, START_PAGE=str(N_FRONT + 1)))
    run('node', f'{SRC}/pdf/print.js', f'{t}/sw.html', f'{t}/sw.pdf')
    sw = PdfReader(f'{t}/sw.pdf').pages
    while 'MEMO' in (sw[-1].extract_text() or '') and len((sw[-1].extract_text() or '').split()) < 8:
        sw = sw[:-1]
    # 진달래꽃 추가 문제 은행(이어서)
    run('python3', '-I', f'{H}/render_jd.py', f'{t}/jd.html', env=dict(os.environ, START_PAGE=str(N_FRONT + len(sw) + 1)))
    run('node', f'{SRC}/pdf/print.js', f'{t}/jd.html', f'{t}/jd.pdf')
    jd = PdfReader(f'{t}/jd.pdf').pages
    w = PdfWriter()
    for p in PdfReader(base).pages[:N_FRONT]:
        w.add_page(p)
    for p in list(sw) + list(jd):
        w.add_page(a4(p))
    w.write(f'{t}/m00.pdf')
    total = len(w.pages)
    # PART 01 쪽에 이미 찍혀 있던 꼬리말 교재 이름은 지우고, 아래에서 모든 쪽에 새 이름으로 다시 넣음
    import pymupdf
    doc = pymupdf.open(f'{t}/m00.pdf')
    for i, pg in enumerate(doc[:N_FRONT]):
        if str(i + 1) in ('1', MEMO):
            continue
        # footer_text.py가 PART 01 쪽에 넣었던 자리(짝수 쪽 왼쪽 48pt~, 홀수 쪽 오른쪽 ~518.7pt, 글자 아래끝 764.5pt, 6.5pt)
        r = pymupdf.Rect(46.5, 757.5, 116, 766.5) if (i + 1) % 2 == 0 else pymupdf.Rect(450, 757.5, 520.2, 766.5)
        pg.add_redact_annot(r, fill=False)
        pg.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        pg.draw_rect(r, color=None, fill=(1, 1, 1), width=0, overlay=True)   # 덧씌운 층 안에 있어 안 지워지는 쪽도 덮음
    doc.save(f'{t}/m0.pdf')
    front = ','.join(str(i) for i in range(1, N_FRONT + 1))
    run('python3', '-I', f'{SRC}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', '리치아카데미 | 국제고 1학년', str(N_FRONT), front)
    run('python3', '-I', f'{SRC}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', FOOT, str(N_FRONT), '1,' + MEMO)
    run('python3', '-I', f'{SRC}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), str(N_FRONT), MEMO + ',1')
    run('python3', '-I', f'{H}/patch_part1.py', f'{t}/m3.pdf', f'{t}/m4.pdf')
    # 목차(1쪽): 쪽 번호는 실제 시작 쪽으로
    hg = next(i for i in range(N_FRONT, total) if '그리움' in (PdfReader(f'{t}/m4.pdf').pages[i].extract_text() or '')[:400] and '문제 은행' in (PdfReader(f'{t}/m4.pdf').pages[i].extract_text() or '')[:400]) + 1
    toc = (open(f'{SRC}/toc/toc_jd.html').read().replace('TOTAL', str(total))
           .replace('p. 42</span>', f'p. {hg}</span>').replace('p. 64</span>', f'p. {N_FRONT + len(sw) + 1}</span>'))
    tmp = f'{SRC}/toc/_toc_out.html'
    open(tmp, 'w').write(toc)
    try:
        run('node', f'{SRC}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
    finally:
        os.remove(tmp)
    r = PdfReader(f'{t}/m4.pdf')
    w = PdfWriter()
    w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
    for p in r.pages[1:]:
        w.add_page(p)
    w.write(out)
print('pages', total, '| 선운사·한 그리움', N_FRONT + 1, '~', N_FRONT + len(sw), '(한 그리움', hg, ') | 진달래꽃', N_FRONT + len(sw) + 1, '~', total)
