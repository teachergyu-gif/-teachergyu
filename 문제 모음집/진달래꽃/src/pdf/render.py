"""진달래꽃 문제 은행 PDF판: 한글 파일과 같은 데이터·순서로 양식 모양 HTML을 만든다."""
import json, html, re, sys, os
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, J)
import fixes_jd

CIRC = '①②③④⑤'


def esc(s):
    s = html.escape(s, quote=False)
    for t in ('u', 'b'):
        s = s.replace(f'&lt;{t}&gt;', f'<{t}>').replace(f'&lt;/{t}&gt;', f'</{t}>')
    return s.replace('&lt;box&gt;', '<span class="bx">').replace('&lt;/box&gt;', '</span>')


def passage(s):
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
                    out.append(f'<div class="ln brk"><div class="bx2"><span class="lab">[{group[0]}]</span><div>{"".join(group[1])}</div></div></div>')
                    group = None
            else:
                out.append(cell)
        if w.get('author'):
            out.append(f'<div class="ln au">{esc(w["author"])}</div>')
    for n in s.get('notes') or []:
        out.append(f'<div class="ln note">{esc(n)}</div>')
    return f'<div class="u set"><div class="sethd">다음 글을 읽고 물음에 답하시오.</div><div class="box">{"".join(out)}</div></div>'


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


def question(n, q):
    ex = q.get('extra')
    extra = ''
    if isinstance(ex, dict):
        extra = bogi({'title': ex.get('title') or '', 'text': ex.get('text') or ''})
    elif ex:
        extra = bogi({'title': '', 'text': ex})
    ch = ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{esc(t)}</span></div>' for i, t in enumerate(q.get('choices') or []))
    return (f'<div class="u q"><div class="qh"><span class="n">{n}.</span><span class="s">{esc(q["stem"])}</span></div>'
            f'{bogi(q.get("bogi"))}{extra}{ch}</div>')


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


def main(out_html):
    data = [json.load(open(f'{J}/work/s{i}/out.json')) for i in range(1, 5)]
    fixes_jd.apply(data, [])
    units, exs, toc, n = [], [], [], 0
    for src in data:
        exm = {e['orig']: e for e in src['ex']}
        a0 = n + 1
        for s in src['sets']:
            qs = s.get('questions') or []
            if not qs:
                continue
            units.append(passage(s))
            for q in qs:
                n += 1
                units.append(question(n, q)); exs.append((n, exm[q['orig']]))
        toc.append(f'{src["source"]} ············ {a0}～{n}번')
    head = ('<div class="u toc"><div class="tt">&lt;목 차&gt;</div><div class="t1">[진달래꽃 문제 은행]</div>'
            '<div class="t2">김소월, ｢진달래꽃｣</div>' + ''.join(f'<div class="t3">{esc(t)}</div>' for t in toc) + '</div>')
    units = [head, '<div class="u brk"></div>'] + units
    units += ['<div class="u brk"></div>', '<div class="u extitle"><span>정답 및 해설</span></div>']
    units += [explanation(k, e) for k, e in exs]
    units.append('<div class="u memo"></div>')
    css = open(f'{D}/exam.css').read()
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(units)}</div>
<script>window.HEAD="진달래꽃 문제 은행";window.SUB="";window.LOGO="file://{J}/logo.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)
    print('questions', n)


if __name__ == '__main__':
    main(sys.argv[1])
