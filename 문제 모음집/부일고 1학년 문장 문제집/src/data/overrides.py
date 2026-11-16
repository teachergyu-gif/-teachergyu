"""변환으로 바로잡기 어려운 문항을 손으로 고친다(문항 번호 → 함수)."""
def _q193(q):
    rows = [('①', '묻었다', '이르러', '일러, 우러러', '파래'), ('②', '일러', '이르러, 파래', '묻었다', '우러러'),
            ('③', '이르러', '묻었다, 우러러', '파래', '일러'), ('④', '묻었다, 우러러', '일러', '이르러', '파래'),
            ('⑤', '일러, 우러러', '묻었다', '파래', '이르러')]
    head = '<tr><td></td>' + ''.join(f'<td style="text-align:center"><u>{k}</u></td>' for k in '㉠㉡㉢㉣') + '</tr>'
    body = ''.join('<tr>' + ''.join(f'<td style="text-align:center">{c}</td>' for c in r) + '</tr>' for r in rows)
    q['ctab'] = f'<table class="ht plain">{head}{body}</table>'
    q['choices'] = []
    q['blocks'] = [b for b in q['blocks'] if b['type'] != 'tabrows']
FIX = {}


import re


def _dialog(q):
    """37·41번: 원본의 ⓐ~ⓒ 표지 + A·B 대화 상자(그리기 개체) → 선지 ①~⑤마다 표지와 대화 상자"""
    src = ''.join(b.get('html', '') for b in q['blocks'] if b['type'] == 'html')
    lines = re.findall(r'<div class="ln[^"]*">(.*?)</div>', src)
    labs = [x.strip() for x in lines if re.fullmatch(r'\s*[ⓐ-ⓩ]\s*', x)]
    dl = [x for x in lines if re.match(r'\s*[AB] :', x)]
    assert len(labs) == 5 and len(dl) == 10, (q['no'], labs, len(dl))
    q['choices'] = [f'{"①②③④⑤"[k]} <span class="lab">{labs[k]}</span><span class="dlg">{dl[2 * k]}<br>{dl[2 * k + 1]}</span>' for k in range(5)]
    q['blocks'] = [b for b in q['blocks'] if b['type'] != 'html']


def _q84(q):
    for b in q['blocks']:
        if b['type'] == 'bogi':
            b['html'] = re.sub(r'<svg.*?</svg>', '', b['html'], flags=re.S)


def _q128(q):
    q['choices'] = ['① 아이들이 <u>뛰노는</u> 소리가 밖에서 들렸다.'] + q['choices']


def _q184(q):
    b = [x for x in q['blocks'] if x['type'] == 'bogi'][0]
    box = lambda t: f'<div class="fbox">{t}</div>'
    b['html'] = (
        '<div class="ln"><b>[복합어]</b></div>'
        '<div class="fbox wide">헛수고, 어느새, 톱질, 마음껏, 꺾쇠, 지우개</div>'
        '<div class="ln" style="margin-top:2mm"><b>[분류 과정]</b></div>'
        '<table class="flow">'
        f'<tr><td>{box("둘 이상의 어근으로만 구성되어 있나요?")}</td><td class="ar">예 →</td><td>{box("㉠")}</td></tr>'
        '<tr><td class="dn">↓ 아니요</td><td></td><td></td></tr>'
        f'<tr><td>{box("접사가 어근의 앞에 붙어서 특정한 뜻을 더하거나 제한해 주나요?")}</td><td class="ar">예 →</td><td>{box("&nbsp;")}</td></tr>'
        '<tr><td class="dn">↓ 아니요</td><td></td><td></td></tr>'
        f'<tr><td>{box("접사가 어근의 뒤에 붙어서 어근의 품사를 바꾸어 주나요?")}</td><td class="ar">예 →</td><td>{box("㉡")}</td></tr>'
        '<tr><td class="dn">↓ 아니요</td><td></td><td></td></tr>'
        f'<tr><td>{box("&nbsp;")}</td><td></td><td></td></tr>'
        '</table>')




LAB = re.compile(r'^(?:[㉠-㉭ⓐ-ⓩ]|\[[A-Z]\]|[A-Z])$')


def choice_tables(q):
    """선지 위 머리(㉠ ㉡ … / [A] [B])와 칸을 맞춘 선지 → 표"""
    def clean(h): return re.sub(r'<[^>]+>', '', h).strip()
    heads = None; hb = None
    for b in q['blocks']:
        if b['type'] == 'line':
            toks = clean(b['html']).split()
            if toks and all(LAB.match(t) for t in toks): heads, hb = re.findall(r'<u>.*?</u>|\S+', b['html'].strip()), b
        elif b['type'] == 'tabrows' and b['rows'] and all(LAB.match(clean(c)) for c in b['rows'][0]):
            heads, hb = b['rows'][0], b
            rows = b['rows'][1:]
            if rows and all(r and r[0][:1] in '①②③④⑤' for r in rows):
                q['choices'] = [' '.join(r) for r in rows] if not q['choices'] else q['choices']
                q['_cells'] = [r[1:] if clean(r[0]) in '①②③④⑤' else [re.sub(r'^\s*[①-⑤]\s*', '', r[0])] + r[1:] for r in rows]
    if not heads or not q['choices']: return
    cells = q.get('_cells') or [re.split(r'\s{2,}|\t', re.sub(r'^\s*[①-⑤]\s*', '', c).strip()) for c in q['choices']]
    if any(len(c) != len(heads) for c in cells):
        print('선지 표 칸 수 불일치', q['no'], [len(c) for c in cells], len(heads)); return
    head = '<tr><td></td>' + ''.join(f'<td>{h}</td>' for h in heads) + '</tr>'
    body = ''.join(f'<tr><td>{"①②③④⑤"[k]}</td>' + ''.join(f'<td>{x.strip()}</td>' for x in c) + '</tr>' for k, c in enumerate(cells))
    q['ctab'] = f'<table class="ht chtab">{head}{body}</table>'
    q['choices'] = []
    q['blocks'] = [b for b in q['blocks'] if b is not hb]
    q.pop('_cells', None)


def _unwrap_table_svg(q):
    """그리기 개체(글상자) 안에 표가 든 경우: SVG를 풀어 보통 상자로(상자 밖으로 넘치지 않게)"""
    def rep(m):
        s = m.group(0)
        if '<table' not in s: return s
        inner = re.findall(r'<foreignObject[^>]*><div[^>]*>(.*?)</div></foreignObject>', s, flags=re.S)
        inner = [x for x in inner if '<table' in x] or inner
        return '<div class="tbox">' + ''.join(inner) + '</div>'
    for b in q['blocks']:
        if 'html' in b:
            b['html'] = re.sub(r'<svg class="gso.*?</svg>', rep, b['html'], flags=re.S)



