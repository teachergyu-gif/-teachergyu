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


def toc_html(title, part_name, items, total):
    t = open(f'{H}/toc/toc.html').read()
    i = t.index('  <div class="parts">'); j = t.index('<div class="fr">')
    rows = ''.join(f'      <div class="it"><span class="t">{n}. {tt}</span><span class="a">{r}</span><span class="d"></span><span class="p">p. {p}</span></div>\n'
                   for n, (tt, r, p) in enumerate(items, 1))
    block = (f'  <div class="parts">\n    <div class="part">\n      <div class="ph"><span class="no">PART 01</span><span class="nm">{part_name}</span></div>\n'
             f'{rows}    </div>\n  </div>\n</div>\n')
    t = t[:i] + block + t[j:]
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
        open(tmp, 'w').write(toc_html(f'{NAME} {BOOKS[mode]}', part, items, total))
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


if __name__ == '__main__':
    for m in (sys.argv[1:] or ['lecture', 'analysis', 'answer']):
        build(m)
