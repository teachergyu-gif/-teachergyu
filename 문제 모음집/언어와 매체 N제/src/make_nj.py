"""언어와 매체 N제 모의고사 PDF: 1쪽 목차 + 회마다 문제 → 해설.
사용: python3 make_nj.py   (NODE_PATH에 playwright-core)"""
import os, re, sys, json, glob, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = H + '/data'
OUTDIR = os.path.join(H, '..')
NAME = '청운고 2학년 문법 2차 N제 모의고사'
PHRASE = '리치아카데미 | 청운고 2학년'


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


def toc_html(title, part_name, rows, total):
    """rows = [(회 이름, 범위, 문제 쪽, 해설 쪽)] — 회 하나를 한 줄로"""
    t = open(f'{H}/toc/toc.html').read()
    i = t.index('  <div class="parts">'); j = t.index('<div class="fr">')
    body = ''.join(f'      <div class="it"><span class="t">{tt}</span><span class="a">{r}</span><span class="d"></span>'
                   f'<span class="p"><span class="k2">문제</span> p. {p1}</span><span class="p"><span class="k2">해설</span> p. {p2}</span></div>\n'
                   for tt, r, p1, p2 in rows)
    block = (f'  <div class="parts">\n    <div class="part">\n      <div class="ph"><span class="no">PART 01</span><span class="nm">{part_name}</span></div>\n'
             f'{body}    </div>\n  </div>\n</div>\n')
    t = t[:i] + block + t[j:]
    css = ('.parts{margin-top:18px!important}.part{gap:6.5px!important}.it{font-size:13px!important}'
           '.it .p{min-width:62px;text-align:right}.it .k2{font-family:"Noto Sans CJK KR",sans-serif;font-weight:500;font-size:11px;color:#6B7785;margin-right:3px}')
    t = t.replace('</style>', css + '</style>', 1)
    return t.replace('TOTAL', str(total)).replace('TITLE', title)


def build(out_name):
    rounds = [json.load(open(f)) for f in sorted(glob.glob(f'{DATA}/r[0-9][0-9].json'))]
    out = os.path.join(OUTDIR, out_name)
    with tempfile.TemporaryDirectory() as t:
        run('python3', '-I', f'{H}/pdf/render_nj.py', DATA, f'{t}/b.html', env=dict(os.environ, START_PAGE='2'))
        run('node', f'{H}/pdf/print.js', f'{t}/b.html', f'{t}/b.pdf')
        w = PdfWriter(); w.add_blank_page(595, 841)
        for p in PdfReader(f'{t}/b.pdf').pages:
            w.add_page(a4(p))
        w.write(f'{t}/m0.pdf')
        total = len(w.pages)
        run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', PHRASE, '1', '1')
        run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', NAME, '1', '1')
        run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '1', '1')
        texts = [re.sub(r'\s+', '', p.extract_text() or '') for p in PdfReader(f'{t}/m3.pdf').pages]
        items, start = [], 1
        for k, r in enumerate(rounds, 1):
            pq = next(i for i in range(start, total) if f'문법모의고사N제{k}회' in texts[i])
            pa = next(i for i in range(pq, total) if f'문법N제제{k}회해설' in texts[i])
            items.append((f'N제 {k}회', '1~5번', pq + 1, pa + 1)); start = pa
        tmp = f'{H}/toc/_toc_out.html'
        sys.path.insert(0, f'{H}/toc')
        import toc_exam
        open(tmp, 'w').write(toc_exam.page(f'{NAME} {len(rounds)}회', '문법 모의고사', [(f'N제 {k}회', p1) for k, (n, r, p1, p2) in enumerate(items, 1)], total))
        try:
            run('node', f'{H}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
        finally:
            os.remove(tmp)
        w = PdfWriter()
        w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
        for p in PdfReader(f'{t}/m3.pdf').pages[1:]:
            w.add_page(p)
        w.write(out)
        print('ok', total, 'pages', items)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else f'{NAME}.pdf')
