"""2026년 2학기 공통국어2 기말고사 대비 교재 PDF 세 권(강의용·분석지·해설지) 만들기.
각 권: 1쪽 목차(최근 교재와 같은 디자인) + 2쪽부터 본문(문제 은행 양식, A3로 짜서 A4로 줄임).
사용: python3 make_book.py [lecture analysis answer]   (NODE_PATH에 playwright-core)"""
import os, re, sys, json, subprocess, tempfile
from pypdf import PdfReader, PdfWriter, Transformation

H = os.path.dirname(os.path.abspath(__file__))
DATA = H + '/data'
OUTDIR = os.path.join(H, '..')
NAME = '2026년 2학기 공통국어2 기말고사 대비'
BOOKS = {'lecture': '강의용 교재', 'analysis': '지문 분석지', 'answer': '정답 및 해설'}
PHRASE = '리치아카데미 | 공통국어2'
# 지문 묶음 제목(목차)
SET_TITLES = ['매체의 발달과 의사소통', '사이버 레커와 악성 댓글', '사랑천 산책로를 둘러싼 협상', '청소년의 금융 이해력',
              '마녀사냥은 사라졌나', '매카시즘의 유래와 언론', '제정신이라는 착각']


def run(*a, **kw):
    subprocess.run(list(a), check=True, **kw)


def a4(p):
    k = 841 / 1191.12
    p.add_transformation(Transformation().scale(k, k).translate((595 - 841.92 * k) / 2, 0))
    for b in (p.mediabox, p.cropbox):
        b.lower_left = (0, 0); b.upper_right = (595, 841)
    return p


def sets_info():
    sets = []
    for p in 'ABCDE':
        sets += json.load(open(f'{DATA}/{p}/out.json'))['sets']
    out = []
    for i, s in enumerate(sets):
        qs = s['questions']
        nums = [q.get('label') or str(q['orig']) for q in qs]
        mc = [str(q['orig']) for q in qs if not q.get('label')]
        sd = [q['label'].replace('서답형 ', '') for q in qs if q.get('label')]
        rng = (f'{mc[0]}~{mc[-1]}번' if len(mc) > 1 else f'{mc[0]}번') if mc else ''
        if sd:
            rng += (', ' if rng else '') + '서답형 ' + '·'.join(sd)
        head = re.sub(r'\s*-\s*', '～', re.match(r'^\[\s*([^\],]+?)\s*[,\]]', s['head']).group(1).strip())
        out.append({'title': SET_TITLES[i] if i < len(SET_TITLES) else f'지문 {i + 1}', 'rng': rng, 'head': head,
                    'first': nums[0], 'first_mc': mc[0] if mc else None})
    return out


def toc_html(title, parts, total):
    """parts = [(파트 이름, [(제목, 범위, 쪽), …]), …]"""
    t = open(f'{H}/toc/toc.html').read()
    i = t.index('  <div class="parts">'); j = t.index('<div class="fr">')
    block = '  <div class="parts">\n'
    for k, (part_name, items) in enumerate(parts, 1):
        rows = ''.join(f'      <div class="it"><span class="t">{n}. {tt}</span><span class="a">{r}</span><span class="d"></span><span class="p">p. {p}</span></div>\n'
                       for n, (tt, r, p) in enumerate(items, 1))
        block += (f'    <div class="part">\n      <div class="ph"><span class="no">PART {k:02d}</span><span class="nm">{part_name}</span></div>\n'
                  f'{rows}    </div>\n')
    block += '  </div>\n</div>\n'
    t = t[:i] + block + t[j:]
    if len(parts) > 3:   # 지문별 파트(7개): 2단 격자
        t = t.replace('</style>', 'h1{margin-top:28px!important}.parts{display:grid!important;grid-template-columns:1fr 1fr;column-gap:36px;row-gap:34px!important;margin-top:26px!important}.part{gap:9px!important}.ph{margin-bottom:4px}.ph .nm{font-size:15px!important}.it{font-size:13px!important}</style>', 1)
    elif len(parts) > 1:   # 세 파트가 한 쪽에 들어가게 간격을 줄임
        t = t.replace('</style>', 'h1{margin-top:28px!important}.parts{gap:18px!important;margin-top:14px!important}.part{gap:2px!important}.ph{margin-bottom:4px}.it{font-size:12.5px!important;line-height:16px}</style>', 1)
    return t.replace('TOTAL', str(total)).replace('TITLE', title)


def build(mode):
    out = os.path.join(OUTDIR, f'{NAME} {BOOKS[mode]}.pdf')
    info = sets_info()
    with tempfile.TemporaryDirectory() as t:
        env = dict(os.environ, START_PAGE='2', MODE=mode)
        run('python3', '-I', f'{H}/pdf/render_book.py', DATA, f'{t}/b.html', env=env)
        run('node', f'{H}/pdf/print.js', f'{t}/b.html', f'{t}/b.pdf')
        w = PdfWriter(); w.add_blank_page(595, 841)
        for p in PdfReader(f'{t}/b.pdf').pages:
            w.add_page(a4(p))
        w.write(f'{t}/m0.pdf')
        total = len(w.pages)
        foot = f'{NAME} {BOOKS[mode]}'
        run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', PHRASE, '1', '1')
        run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', foot, '1', '1')
        run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '1', '1')
        texts = [re.sub(r'\s+', '', p.extract_text() or '').replace('〜', '～').replace(f'ACADEMY{k + 1}', 'ACADEMY|', 1)
                 for k, p in enumerate(PdfReader(f'{t}/m3.pdf').pages)]
        items = []
        start = 1
        for s in info:
            if mode == 'answer':
                key = (s['first_mc'] + '.') if s['first_mc'] else f'[{s["first"]}]'
                pat = re.compile(r'(?<![0-9])' + re.escape(key))
            else:
                pat = re.compile(re.escape('【' + s['head'].replace(' ', '')) + r'[】,]')
            pg = next((k for k in range(start, total) if pat.search(texts[k])), start)
            items.append((s['title'], s['rng'], pg + 1))
            start = pg
        part = {'lecture': '지문별 문제', 'analysis': '지문별 분석', 'answer': '문항별 정답 및 해설'}[mode]
        tmp = f'{H}/toc/_toc_out.html'
        open(tmp, 'w').write(toc_html(f'{NAME} {BOOKS[mode]}', [(part, items)], total))
        try:
            run('node', f'{H}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
        finally:
            os.remove(tmp)
        w = PdfWriter()
        w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
        for p in PdfReader(f'{t}/m3.pdf').pages[1:]:
            w.add_page(p)
        w.write(out)
        print('ok', mode, total, 'pages', [(i[0], i[2]) for i in items])


def build_all(modes=('lecture', 'analysis', 'answer')):
    """세 권을 한 PDF로: 1쪽 목차(PART 01~03) + 이어지는 쪽 번호"""
    out = os.path.join(OUTDIR, f'{NAME}.pdf')
    info = sets_info()
    with tempfile.TemporaryDirectory() as t:
        w = PdfWriter(); w.add_blank_page(595, 841)
        starts = {}
        for m in modes:
            starts[m] = len(w.pages)
            env = dict(os.environ, START_PAGE=str(len(w.pages) + 1), MODE=m)
            run('python3', '-I', f'{H}/pdf/render_book.py', DATA, f'{t}/{m}.html', env=env)
            run('node', f'{H}/pdf/print.js', f'{t}/{m}.html', f'{t}/{m}.pdf')
            for p in PdfReader(f'{t}/{m}.pdf').pages:
                w.add_page(a4(p))
        w.write(f'{t}/m0.pdf')
        total = len(w.pages)
        run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', PHRASE, '1', '1')
        run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', NAME, '1', '1')
        run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m3.pdf', str(total), '1', '1')
        texts = [re.sub(r'\s+', '', p.extract_text() or '').replace('〜', '～').replace(f'ACADEMY{k + 1}', 'ACADEMY|', 1)
                 for k, p in enumerate(PdfReader(f'{t}/m3.pdf').pages)]
        parts = []
        for m in modes:
            items, start = [], starts[m]
            for s in info:
                if m == 'answer':
                    key = (s['first_mc'] + '.') if s['first_mc'] else f'[{s["first"]}]'
                    pat = re.compile(r'(?<![0-9])' + re.escape(key))
                else:
                    pat = re.compile(re.escape('【' + s['head'].replace(' ', '')) + r'[】,]')
                pg = next((k for k in range(start, total) if pat.search(texts[k])), start)
                items.append((s['title'], s['rng'], pg + 1))
                start = pg
            parts.append((BOOKS[m], items))
        tmp = f'{H}/toc/_toc_out.html'
        open(tmp, 'w').write(toc_html(NAME, parts, total))
        try:
            run('node', f'{H}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
        finally:
            os.remove(tmp)
        w = PdfWriter()
        w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
        for p in PdfReader(f'{t}/m3.pdf').pages[1:]:
            w.add_page(p)
        w.write(out)
        print('ok all', total, 'pages', [(n, [i[2] for i in it]) for n, it in parts])


def build_perset():
    """지문마다 강의용 → 지문 분석 → 정답 및 해설 순서로 한 PDF"""
    out = os.path.join(OUTDIR, f'{NAME}.pdf')
    info = sets_info()
    with tempfile.TemporaryDirectory() as t:
        env = dict(os.environ, START_PAGE='2', MODE='perset')
        run('python3', '-I', f'{H}/pdf/render_book.py', DATA, f'{t}/b.html', env=env)
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
        parts, start = [], 1
        for i, s in enumerate(info):
            items = []
            for name in ('강의용', '지문 분석', '정답 및 해설'):
                key = f'{i + 1:02d}' + name.replace(' ', '')
                pg = next((k for k in range(start, total) if key in texts[k]), None)
                assert pg is not None, key
                items.append(({'강의용': '강의용 교재', '지문 분석': '지문 분석지'}.get(name, name), '', pg + 1))
                start = pg
            parts.append((s, items))
        tmp = f'{H}/toc/_toc_out.html'
        html = toc_html(NAME, [('', [])], total)
        rows = ''.join(
            f'    <div class="part"><div class="ph"><span class="no">PART {k:02d}</span><span class="nm">{s["title"]}</span><span class="nm2">{s["rng"]}</span></div>\n'
            f'      <div class="row">' + ''.join(f'<span class="it2"><span class="t">{n}</span><span class="d"></span><span class="p">p. {p}</span></span>' for n, _, p in items) + '</div></div>\n'
            for k, (s, items) in enumerate(parts, 1))
        html = re.sub(r'<div class="parts">.*?</div>\s*</div>\s*</div>\n', '<div class="parts">\n' + rows + '  </div>\n', html, count=1, flags=re.S)
        html = html.replace('</style>', '.parts{gap:30px!important;margin-top:30px!important}.part{gap:10px!important}.ph .nm{font-size:15.5px!important}'
                            '.ph .nm2{font-size:12.5px;color:#6B7785}.row{display:flex;gap:26px;padding-left:4px}'
                            '.it2{flex:1;display:flex;align-items:baseline;gap:8px;font-size:13px}.it2 .d{flex:1;border-bottom:1.5px dotted #C3CAD3}'
                            '.it2 .p{font-family:Montserrat,sans-serif;font-weight:600}</style>', 1)
        open(tmp, 'w').write(html)
        try:
            run('node', f'{H}/toc/print_toc.js', f'{t}/toc.pdf', '_toc_out.html')
        finally:
            os.remove(tmp)
        w = PdfWriter()
        w.add_page(PdfReader(f'{t}/toc.pdf').pages[0])
        for p in PdfReader(f'{t}/m3.pdf').pages[1:]:
            w.add_page(p)
        w.write(out)
        print('ok perset', total, 'pages', [[i[2] for i in it] for n, it in parts])


if __name__ == '__main__':
    if sys.argv[1:] == ['perset']:
        build_perset()
        sys.exit()
    if sys.argv[1:] == ['all']:
        build_all()
        sys.exit()
    for m in (sys.argv[1:] or ['lecture', 'analysis', 'answer']):
        build(m)
