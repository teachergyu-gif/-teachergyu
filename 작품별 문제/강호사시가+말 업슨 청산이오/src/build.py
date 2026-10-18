"""작품별 문제(B: 한글 재작성) 조판: 전사 JSON → 변형문제 양식 HTML (브라우저에서 자동 쪽 나눔)."""
import json, html, re, sys, os

LOGO = '/home/user/-teachergyu/brand/logo_navy.png'
CIRC = '①②③④⑤'


def esc(s):
    s = html.escape(s, quote=False)
    for t in ('u', 'b', 'i'):
        s = s.replace(f'&lt;{t}&gt;', f'<{t}>').replace(f'&lt;/{t}&gt;', f'</{t}>')
    s = s.replace('&lt;box&gt;', '<span class="bx">').replace('&lt;/box&gt;', '</span>')
    s = s.replace('&lt;보기&gt;', '<span class="nw">&lt;보기&gt;</span>')
    return s


def work_html(w):
    out = []
    inline = w.get('label_inline') and w.get('label')
    if w.get('label') and not inline:
        out.append(f'<div class="ln tag">{esc(w["label"])}</div>')
    if w.get('prose'):
        for para in w['lines'].split('\n'):
            if para.strip() == '':
                continue
            if para.startswith('@'):
                out.append(f'<div class="ln au">{esc(para[1:].strip())}</div>')
            else:
                out.append(f'<div class="ln pr">{esc(para)}</div>')
        return lab_inline(out, inline)
    shape = w.get('shape')
    for l in w['lines'].split('\n'):
        if l.strip() == '':
            out.append('<div class="ln sp"></div>')
        elif l.startswith('@'):
            out.append(f'<div class="ln au">{esc(l[1:].strip())}</div>')
        elif re.fullmatch(r'>?\s*<제\d+수>', l.strip()):
            out.append('<div class="ln au">' + esc(l.lstrip('>').strip()) + '</div>')
        elif l.startswith('>'):
            out.append(f'<div class="ln ind">{esc(l[1:].strip())}</div>')
        else:
            out.append(f'<div class="ln{" shp" if shape else ""}">{esc(l)}</div>')
    return lab_inline(out, inline)


def lab_inline(out, inline):
    if inline and out:
        i = out[0].index('>') + 1
        out[0] = out[0][:i] + f'<b class="il">{esc(inline)}</b> ' + out[0][i:]
    return out


def set_html(s, rng):
    lines = []
    for i, w in enumerate(s['works']):
        if i and not (lines and 'sp' in lines[-1]):
            lines.append('<div class="ln sp"></div>')
        lines += work_html(w)
    while lines and 'ln sp' in lines[-1]:
        lines.pop()
    for n in s.get('notes') or []:
        lines.append(f'<div class="ln note">{esc(n)}</div>')
    head = s.get('head', '다음 글을 읽고 물음에 답하시오.').replace('※', '').strip()
    return (f'<div class="u set"><div class="sethd">[{rng}] {esc(head)}</div>'
            f'<div class="box">{"".join(lines)}</div></div>')


def bogi_html(b):
    if not b:
        return ''
    title = b.get('title') or '<보기>'
    txt = b['text']
    items = txt.split('\n')
    ITEM = re.compile(r'^[ㄱ-ㅎ]\.|^[ⓐ-ⓩ]|^[㉠-㉭]|^\(\S\)')
    body = ''.join('<div class="bl' + (' bi' if ITEM.match(x) else '') + (' au' if x.startswith('- ') else '') + '">' + (esc(x) if x.strip() else '&nbsp;') + '</div>' for x in items)
    return f'<div class="bogi"><div class="bt"><span>{esc(title)}</span></div>{body}</div>'


def q_html(q):
    if (q.get('extra') or '').startswith('선택지는 표 형식'):
        heads = q['extra'].split(':', 1)[1].replace('열 머리', '').split('/')
        th = '<tr><th></th>' + ''.join(f'<th>{esc(h.strip())}</th>' for h in heads) + '</tr>'
        rows = ''.join('<tr><td>' + CIRC[i] + '</td>' + ''.join(f'<td>{esc(c.strip())}</td>' for c in t.split(' / ')) + '</tr>'
                       for i, t in enumerate(q['choices']))
        return (f'<div class="u q"><div class="qh"><span class="n">{q["n"]}.</span><span class="s">{esc(q["stem"])}</span></div>'
                f'{bogi_html(q.get("bogi"))}<table class="ctab">{th}{rows}</table></div>')
    ch = ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{esc(t)}</span></div>'
                 for i, t in enumerate(q.get('choices') or []))
    extra = ''
    if q.get('extra'):
        extra = '<div class="extra">' + ''.join(f'<div>{esc(x) if x.strip() else "&nbsp;"}</div>' for x in q['extra'].split('\n')) + '</div>'
    cls = ' long' if q.get('choices') and max(len(t) for t in q['choices']) > 0 else ''
    return (f'<div class="u q"><div class="qh"><span class="n">{q["n"]}.</span><span class="s">{esc(q["stem"])}</span></div>'
            f'{bogi_html(q.get("bogi"))}{extra}{ch}</div>')


def ex_html(e):
    paras = []
    for p in e['body'].split('\n'):
        if not p.strip():
            continue
        m = re.match(r'^([①②③④⑤]|[ㄱ-ㅎ]\.)\s*(.*)$', p)
        if m:
            paras.append(f'<div class="ep hang"><span class="c">{m.group(1)}</span><span>{esc(m.group(2))}</span></div>')
        else:
            paras.append(f'<div class="ep">{esc(p)}</div>')
    ans = e['answer']
    if re.fullmatch(r'[①②③④⑤ ,]+', ans):
        hd = f'<span class="n">{e["n"]}.</span><span class="jd">정답</span><span class="a">{esc(ans)}</span>'
        sa = ''
    else:
        hd = f'<span class="n">{e["n"]}.</span><span class="jd">정답</span>'
        sa = '<div class="model">' + ''.join(f'<div>{esc(x)}</div>' for x in ans.split('\n') if x.strip()) + '</div>'
    return f'<div class="u ex"><div class="eh">{hd}</div>{sa}{"".join(paras)}</div>'


def quick_html(exs):
    cells = []
    for e in exs:
        a = e['answer'] if re.fullmatch(r'[①②③④⑤ ,]+', e['answer']) else '서술형'
        cells.append(f'<td><b>{e["n"]}</b></td><td>{esc(a)}</td>')
    rows = ''.join('<tr>' + ''.join(cells[i:i + 5]) + '</tr>' for i in range(0, len(cells), 5))
    return f'<div class="u quick"><table>{rows}</table></div>'


def build(data, out, head, sub):
    css = open(os.path.join(os.path.dirname(__file__), 'exam.css')).read()
    js = open(os.path.join(os.path.dirname(__file__), 'paginate.js')).read()
    qs = {q['n']: q for q in data['questions']}
    units = []
    used = set()
    for s in data['sets']:
        ns = s['questions']
        rng = f'{ns[0]}' if len(ns) == 1 else f'{ns[0]}～{ns[-1]}'
        units.append(set_html(s, rng))
        for n in ns:
            units.append(q_html(qs[n])); used.add(n)
    missing = sorted(set(qs) - used)
    assert not missing, f'세트에 없는 문항: {missing}'
    units.append('<div class="u brk"></div>')
    units.append('<div class="u extitle"><span>정답 및 해설</span></div>')
    units.append(quick_html(data['ex']))
    units += [ex_html(e) for e in data['ex']]
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(units)}</div>
<script>window.HEAD={json.dumps(head)};window.SUB={json.dumps(sub)};window.LOGO={json.dumps("file://" + LOGO)};</script>
<script>{js}</script></body></html>'''
    open(out, 'w').write(doc)


if __name__ == '__main__':
    data = json.load(open(sys.argv[1]))
    build(data, sys.argv[2], sys.argv[3], sys.argv[4])
