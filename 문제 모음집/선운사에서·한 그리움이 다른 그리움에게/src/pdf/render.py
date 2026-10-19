"""「선운사에서」·「한 그리움이 다른 그리움에게」 교재 PDF판(문제 은행 양식): 진달래꽃 render.py와 같은 함수로 HTML을 만든다.
사용: python3 render.py 데이터폴더(work/{sw1,sw2,hg1,hg2}/out.json) 출력.html"""
import json, html, re, sys, os
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, J)
import fixes
from layout_overrides import Q_BREAK, SET_BREAK, ANSWER_LINES, CLOSE

CIRC = '①②③④⑤'
HEAD = '국제고 1학년 선운사에서 · 한 그리움이 다른 그리움에게 교재'
WORKS = [('선운사에서', '최영미, ｢선운사에서｣', ['sw1', 'sw2']),
         ('한 그리움이 다른 그리움에게', '정희성, ｢한 그리움이 다른 그리움에게｣', ['hg1', 'hg2'])]


def esc(s):
    s = html.escape(s, quote=False)
    for t in ('u', 'b'):
        s = s.replace(f'&lt;{t}&gt;', f'<{t}>').replace(f'&lt;/{t}&gt;', f'</{t}>')
    s = re.sub(r'([\u3400-\u9fff\uf900-\ufaff]+)', lambda m: '<span class="hj">' + m.group(1) + '</span>', s)
    # 한자 묶음 앞뒤에서 줄이 바뀌지 않게(괄호·조사와 붙임): 단어 결합자 U+2060
    def nb(m):
        t = m.group(0)
        # 한자어 앞 한글이 4음절 이상이면(산화공덕 등) 가운데에서 끊길 수 있게(줄 간격이 지나치게 벌어지는 것 방지)
        k = re.search(r'([가-힣]{4,})\(?<span class="hj">', t)
        if k:
            h = k.group(1); cut = k.start(1) + len(h) // 2
            return '<span class="nb">' + t[:cut] + '</span>\u200b<span class="nb">' + t[cut:] + '</span>'
        return '<span class="nb">' + t + '</span>'
    s = re.sub(r'[^\s<>]*(?:<span class="hj">[^<]*</span>[^\s<>]*)+', nb, s)
    return s.replace('&lt;box&gt;', '<span class="bx">').replace('&lt;/box&gt;', '</span>')


def passage(s, rng=''):
    out = []
    for wi, w in enumerate(s['works']):
        if wi:
            out.append('<div class="ln sp"></div>')
        if w.get('label'):
            out.append(f'<div class="ln tag">{esc(w["label"])}</div>')
        group = None
        for l in w['lines'].split('\n'):
            m = re.match(r'^\{(\w+)\}', l)
            if m:
                group = [m.group(1), []]; l = l[m.end():]
            end = re.search(r'\{/\w+\}$', l)
            if end:
                l = l[:end.start()]
            cell = '<div class="ln sp"></div>' if l.strip() == '' else f'<div class="ln">{esc(l)}</div>'
            if group:
                group[1].append(cell)
                if end:
                    out.append(f'<div class="ln brk"><div class="bx2"><span class="lab2">[{group[0]}]</span><span class="br2"></span><div>{"".join(group[1])}</div></div></div>')
                    group = None
            else:
                out.append(cell)
        if w.get('author'):
            out.append(f'<div class="ln au">{esc(w["author"])}</div>')
    for n in s.get('notes') or []:
        out.append(f'<div class="ln note">{esc(n)}</div>')
    return f'<div class="u set"><div class="sethd">【{rng}】 다음 글을 읽고 물음에 답하시오.</div><div class="box">{"".join(out)}</div></div>'


def bogi(b):
    if not b:
        return ''
    if b.get('table'):
        rows = [list(r) for r in b['table']]
        trs = []
        for r, row in enumerate(rows):
            tds = []
            for c, v in enumerate(row):
                if v == '' and r and c < 2:
                    continue
                rs = 1
                if r + 1 < len(rows) and rows[r + 1][c] == '' and c < 2 and v:
                    rs = 2
                tds.append(f'<td rowspan="{rs}">{esc(v)}</td>')
            trs.append('<tr>' + ''.join(tds) + '</tr>')
        return '<table class="ctab grid"><colgroup><col class="a"><col class="b"><col></colgroup>' + ''.join(trs) + '</table>'
    title = '<보기>' if b.get('title') is None else b['title']
    ITEM = re.compile(r'^([ㄱ-ㅎ]\.|[㉠-㉭]|[ⓐ-ⓩ]|\(\S\))')
    body = ''.join('<div class="bl' + (' bi' if ITEM.match(x) else '') + '">' + (esc(x) if x.strip() else '&nbsp;') + '</div>' for x in b['text'].split('\n'))
    t = f'<div class="bt"><span>{esc(title)}</span></div>' if title else ''
    return f'<div class="bogi">{t}{body}</div>'


def question(n, q, key=None):
    ex = q.get('extra')
    extra = ''
    if isinstance(ex, dict):
        extra = bogi({'title': ex.get('title') or '', 'text': ex.get('text') or ''})
    elif ex:
        extra = bogi({'title': '', 'text': ex})
    ch = ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{esc(t)}</span></div>' for i, t in enumerate(q.get('choices') or []))
    ans = '' if q.get('choices') else f'<div class="ans" style="height:{ANSWER_LINES * 1.75 * 11.2}pt"></div>'
    close = ' data-close="1"' if key in CLOSE else ''
    return (f'<div class="u q"{close}><div class="qh"><span class="n">{n}.</span><span class="s">{esc(q["stem"])}</span></div>'
            f'{bogi(q.get("bogi"))}{extra}{ch}{ans}</div>')


def explanation(n, e):
    a = e['answer']
    short = len(a) < 12
    out = [f'<div class="eh"><span>{n}. {esc(a) if short else ""}</span></div>']
    if not short:
        out.append(f'<div class="ep"><b>[모범 답안]</b> {esc(a)}</div>')
    def hang(t):
        m = re.match(r'^([①②③④⑤])\s*(.*)$', t, re.S)
        if m:
            return f'<div class="ep hang"><span class="c">{m.group(1)}</span><span>{esc(m.group(2))}</span></div>'
        return f'<div class="ep">{esc(t)}</div>'
    if e.get('plain'):
        out += [hang(p) for p in e['plain'].split('\n') if p.strip()]
    else:
        if e.get('correct'):
            c = a[:1] if a[:1] in CIRC else ''
            out.append(hang((c + ' ' if c else '') + e['correct']))
        if e.get('wrong'):
            out.append('<div class="ep wr">[오답풀이]</div>')
            out += [hang(f'{k} {t}'.strip()) for k, t in e['wrong']]
    return '<div class="u ex">' + ''.join(out) + '</div>'


def load(work_dir):
    """작품마다 나눠 옮긴 out.json(앞·뒤 절반)을 하나로 합친다. 경계에서 같은 지문 묶음이 이어지면 한 묶음으로."""
    data = []
    for name, _, parts in WORKS:
        src = {'source': name, 'sets': [], 'ex': [], 'issues': []}
        for p in parts:
            d = json.load(open(f'{work_dir}/{p}/out.json'))
            for s in d['sets']:
                if src['sets'] and src['sets'][-1]['works'] == s['works']:
                    src['sets'][-1]['questions'] += s.get('questions') or []
                else:
                    src['sets'].append(s)
            src['ex'] += d['ex']
            src['issues'] += d.get('issues') or []
        data.append(src)
    return data


def main(work_dir, out_html):
    data = load(work_dir)
    log = []
    fixes.apply(data, log)
    open(f'{J}/fixlog.txt', 'w').write('\n'.join(log) + '\n')
    # 작품마다: 문제 모음 → 정답 및 해설
    body, n = [], 0
    for wi, ((name, label, _), src) in enumerate(zip(WORKS, data)):
        exm = {e['orig']: e for e in src['ex']}
        a0 = n + 1
        exs = []
        n = 0   # 작품마다 1번부터
        if wi:
            body.append('<div class="u brk"></div>')
        body.append(f'<div class="u qtitle"><span>{label.split(", ")[1]} 문제 은행</span></div>')
        for s in src['sets']:
            qs = s.get('questions') or []
            if not qs:
                continue
            rng = f'{n + 1}' if len(qs) == 1 else f'{n + 1}～{n + len(qs)}'
            if SET_BREAK.get((name, n + 1)) == 'page': body.append('<div class="u brk"></div>')
            elif SET_BREAK.get((name, n + 1)) == 'col': body.append('<div class="u colbrk"></div>')
            body.append(passage(s, rng))
            for q in qs:
                n += 1
                if Q_BREAK.get((name, n)) == 'col': body.append('<div class="u colbrk"></div>')
                elif Q_BREAK.get((name, n)) == 'page': body.append('<div class="u brk"></div>')
                body.append(question(n, q, (name, n))); exs.append((n, exm[q['orig']]))
        body += ['<div class="u brk"></div>', f'<div class="u extitle"><span>정답 및 해설</span></div>']
        body += [explanation(k, e) for k, e in exs]
    units = body   # 1쪽 목차 없음: 머리 아래부터 바로 문제
    units.append('<div class="u memo"></div>')
    css = open(f'{D}/exam.css').read() 
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(units)}</div>
<script>window.HEAD="{HEAD}";window.SUB="";window.LOGO="file://{J}/logo2.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)
    print('questions', n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
