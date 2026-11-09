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


def toc_html(title, part_name, items, total):
    t = open(f'{H}/toc/toc.html').read()
    i = t.index('  <div class="parts">'); j = t.index('<div class="fr">')
    rows = ''.join(f'      <div class="it{" ex" if e else ""}"><span class="t">{tt}</span><span class="a">{r}</span><span class="d"></span><span class="p">p. {p}</span></div>\n'
                   for tt, r, p, e in items)
    block = (f'  <div class="parts">\n    <div class="part">\n      <div class="ph"><span class="no">PART 01</span><span class="nm">{part_name}</span></div>\n'
             f'{rows}    </div>\n  </div>\n</div>\n')
    t = t[:i] + block + t[j:]
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
            for key, label, rng, e in ((f'문법모의고사N제{k}회', f'N제 {k}회', '35~39번', False), (f'문법N제제{k}회해설', f'N제 {k}회 해설', '', True)):
                pg = next(i for i in range(start, total) if key in texts[i])
                items.append((label, rng, pg + 1, e)); start = pg
        tmp = f'{H}/toc/_toc_out.html'
        open(tmp, 'w').write(toc_html(NAME, '문법 모의고사', items, total))
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
