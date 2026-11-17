"""「흰 바람벽이 있어」·「탄궁가」 문제 은행 PDF판: 작품마다 문제 → 빠른 정답 + 정답 및 해설.
사용: START_PAGE=2 python3 render.py 데이터폴더({s01..s05}/out.json) 출력.html"""
import json, html, re, sys, os
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, J)
from layout_overrides import Q_BREAK
try:
    from layout_overrides import SPLIT_CH
except ImportError:
    SPLIT_CH = set()
try:
    from layout_overrides import KEEP_Q
except ImportError:
    KEEP_Q = set()

CIRC = '①②③④⑤'
HEAD = os.environ.get('HEAD', '청운고 2학년 기말고사 모의고사 2회')
J_IMG = J + '/img/'


def esc(s):
    return html.escape(s, quote=False)


def fix_img(h):
    return h.replace('src="IMG/', f'src="file://{J_IMG}').replace('href="IMG/', f'href="file://{J_IMG}')


def block_html(b):
    t = b['type']
    if t == 'bogi':
        return f'<div class="bogi hb"><div class="bt"><span>{esc(b["title"])}</span></div>{fix_img(b["html"])}</div>'
    if t == 'html':
        return f'<div class="hblk">{fix_img(b["html"])}</div>'
    if t == 'line':
        return f'<div class="ln qline">{fix_img(b["html"])}</div>'
    if t == 'tabrows':
        rows = b['rows']; m = max(len(r) for r in rows)
        trs = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '<td></td>' * (m - len(r)) + '</tr>' for r in rows)
        return f'<table class="tabrows">{trs}</table>'
    return ''


def choices_html(q):
    if q.get('ctab'):
        return f'<div class="ctab-h">{fix_img(q["ctab"])}</div>'
    chs = q.get('choices') or []
    if not chs:
        return ''
    plain = [re.sub(r'<[^>]+>', '', c) for c in chs]
    body = [re.sub(r'^\s*[①-⑤]\s*', '', c) for c in chs]
    L = max(len(p) for p in plain)
    if L <= 9 and '<br>' not in ''.join(chs):
        per = 5 if L <= 6 else 3
        return (f'<div class="chg g{per}">' + ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{t}</span></div>' for i, t in enumerate(body)) + '</div>')
    out = ''
    for i, t in enumerate(body):
        pre = ' pre' if re.search(r'\S {3,}\S', re.sub(r'<[^>]+>', '', t)) else ''
        if 'class="dlg' in t: pre += ' dl'
        out += f'<div class="ch{pre}"><span class="c">{CIRC[i]}</span><span class="t">{t}</span></div>'
    return out


def passage(st, n):
    """지문 묶음: {A}…{/A}는 [A] 괄호 묶음, 줄 앞 <span class="exl">은 들여쓰지 않는 예시 줄"""
    out, group = [], None
    for l in st['lines']:
        m = re.match(r'^\{(\w+)\}', l)
        if m:
            group = [m.group(1), []]; l = l[m.end():]
        end = l.endswith('{/' + (group[0] if group else 'A') + '}')
        if end:
            l = l[:l.rindex('{/')]
        cell = f'<div class="ln{"" if l.startswith('<span class="exl">') else " fi"}">{l}</div>'
        if group:
            group[1].append(cell)
            if end:
                out.append(f'<div class="ln brk"><div class="bx2"><span class="lab2">[{group[0]}]</span><span class="br2"></span><div>{"".join(group[1])}</div></div></div>')
                group = None
        else:
            out.append(cell)
    k = n + st.get('count', 2) - 1
    return f'<div class="u set"><div class="sethd">【{n}～{k}】 다음 글을 읽고 물음에 답하시오.</div><div class="box">{"".join(out)}</div></div>'


def question(n, q):
    hamp = not re.search(r'모의평가|대학수학능력|예비평가', q['src'])
    src = ''   # 출처 띠는 넣지 않음(사용자 지정)
    stem = re.sub(r'\s*\[\d+점\]', '', re.sub(r'^\s+', '', q['stem']))   # 배점 표시 없음(사용자 지정)
    bl = ''.join(block_html(b) for b in q['blocks'])
    return (f'<div class="u q" data-key="{n}">{src}<div class="qh"><span class="n">{n}.</span><span class="s">{fix_img(stem)}</span></div>'
            f'{bl}{choices_html(q)}</div>')


def explanation(n, e):
    a = e['answer']
    short = len(a) < 12
    out = [f'<div class="eh"><span>{n}. {esc(a) if short else ""}</span></div>']
    if not short:
        out.append(f'<div class="ep"><b>[모범 답안]</b> {esc(a)}</div>')
    ITEM = r'[ㄱ-ㅎ]\s?[:.]\s'
    def items(body):
        parts = [x.strip() for x in re.split(r'\s+(?=' + ITEM + ')', body) if x.strip()]
        return ''.join(f'<div class="ep gi{" hi" if re.match(ITEM, x) else ""}">{esc(x)}</div>' for x in parts)
    def hang(t):
        m = re.match(r'^((?:[①②③④⑤][\s,·]*)+)(.*)$', t, re.S)
        if m and re.match(ITEM, m.group(2).strip()):   # ㄱ~ㄹ 항목 해설: 선지 번호는 빼고 항목만 줄마다(내어쓰기)
            return items(m.group(2).strip())
        if m and len(re.findall(r'[①②③④⑤]', m.group(1))) > 1:   # 여러 선지를 묶은 해설: ‘②, ③, ④, ⑤ …’ 한 문단, 둘째 줄부터 들여쓰기
            lab = ', '.join(re.findall(r'[①②③④⑤]', m.group(1)))
            return f'<div class="ep gp">{lab} {esc(m.group(2).strip())}</div>'
        m = re.match(r'^([①②③④⑤])\s*(.*)$', t, re.S)
        if m:
            return f'<div class="ep hang"><span class="c">{m.group(1)}</span><span>{esc(m.group(2))}</span></div>'
        if re.match(ITEM, t.strip()):
            return items(t.strip())
        return f'<div class="ep">{esc(t)}</div>'
    if e.get('plain'):
        out += [('<div class="ep wr">[오답풀이]</div>' if p.strip() == '[오답풀이]' else hang(p)) for p in e['plain'].split('\n') if p.strip()]
    else:
        if e.get('correct'):
            c = a[:1] if a[:1] in CIRC else ''
            out.append(hang((c + ' ' if c else '') + e['correct']))
        if e.get('wrong'):
            out.append('<div class="ep wr">[오답풀이]</div>')
            out += [hang(f'{k} {t}'.strip()) for k, t in e['wrong']]
    return '<div class="u ex">' + ''.join(out) + '</div>'


def qlabel(q, e):
    """빠른 정답 칸: 객관식은 원문자, 선지 없는 문항은 서술형/주관식"""
    a = e['answer'].strip()
    if q.get('choices'):
        return ' '.join(re.findall(r'[①②③④⑤]', a)) or a
    return '서술형'


def quick(exs, per=5):
    """<빠른 정답> 표: 한 줄에 다섯 문항(번호 칸 하늘색)"""
    cells = [(n, qlabel(q, e)) for n, q, e in exs]
    rows = []
    for i in range(0, len(cells), per):
        r = cells[i:i + per]
        r += [('', '')] * (per - len(r))
        rows.append('<tr>' + ''.join(f'<td class="qn">{n}</td><td class="qv{" sm" if len(v) > 1 and v[0] not in CIRC else ""}">{esc(v)}</td>' for n, v in r) + '</tr>')
    return f'<div class="u qa"><div class="qat">빠른 정답</div><table class="qat-t">{"".join(rows)}</table></div>'


def qlabel(q, e):
    """빠른 정답 칸: 객관식은 원문자, 선지 없는 문항은 서술형/주관식"""
    a = e['answer'].strip()
    if q.get('choices'):
        return ' '.join(re.findall(r'[①②③④⑤]', a)) or a
    return '서술형'


def quick(exs, per=5):
    """<빠른 정답> 표: 한 줄에 다섯 문항(번호 칸 하늘색)"""
    cells = [(n, qlabel(q, e)) for n, q, e in exs]
    rows = []
    for i in range(0, len(cells), per):
        r = cells[i:i + per]
        r += [('', '')] * (per - len(r))
        rows.append('<tr>' + ''.join(f'<td class="qn">{n}</td><td class="qv{" sm" if len(v) > 1 and v[0] not in CIRC else ""}">{esc(v)}</td>' for n, v in r) + '</tr>')
    return f'<div class="u qa"><div class="qat">빠른 정답</div><table class="qat-t">{"".join(rows)}</table></div>'



def main(data_json, out_html):
    d = json.load(open(data_json, encoding='utf8'))
    exs = {}
    exdir = os.path.join(os.path.dirname(data_json), 'ex')
    if os.path.isdir(exdir):
        for f in sorted(os.listdir(exdir)):
            for e in json.load(open(os.path.join(exdir, f), encoding='utf8')):
                exs[e['no']] = e
    body = []; part = None; done = []
    for q in d['questions']:
        if q['part'] != part:
            if part is not None:
                body.append('<div class="u brk"></div>')
            part = q['part']
            pass   # 1쪽 머리에 제목이 있으므로 제목 상자 없음
        if Q_BREAK.get(q['no']) == 'col': body.append('<div class="u colbrk"></div>')
        elif Q_BREAK.get(q['no']) == 'page': body.append('<div class="u brk"></div>')
        if q.get('set'):
            body.append(passage(q['set'], q['no']))
        body.append(question(q['no'], q))
        if q['no'] in exs:
            done.append((q['no'], {'choices': q['choices'] or ['x'] * 5}, exs[q['no']]))
    if done:
        body += ['<div class="u brk"></div>', '<div class="u extitle"><span>정답 및 해설</span></div>'] + [quick(done[i:i + 100]).replace('<div class="qat">빠른 정답</div>', '' if i else '<div class="qat">빠른 정답</div>') for i in range(0, len(done), 100)]
        def post(h):
            h = re.sub(r'「([12])」', r'<span class="bnum">\1</span>', h)
            h = re.sub(r'\^(\d)', r'<sup>\1</sup>', h)                       # 어깨번호
            h = re.sub(r'‘(-?[^‘’\s<>]{1,6}-?)’', r'<span class="nb">‘\1’</span>', h)   # ‘-다’ 같은 짧은 인용이 줄 끝에서 갈라지지 않게
            return h
        body += [post(explanation(k, e)) for k, q, e in done]
    # 원문자(㉠ ⓐ 등)는 글자 폭이 넓어 뒤 조사와 띄어 보이므로 오른쪽 여백을 줄여 붙여 보이게
    # (양쪽 맞춤 때 원문자 뒤가 벌어지지 않게 기호와 뒤 조사를 한 덩어리로)
    body = [re.sub(r'([㉠-㉭㉮-㉻ⓐ-ⓩⒶ-Ⓩ])([가-힣]{1,3}(?=[\s.,’”)<]))', r'<span class="sym">\1\2</span>', b) for b in body]
    YH = re.compile(r'[\uAC00-\uD7A3\u1100-\u11FF]*[\u1100-\u11FF][\uAC00-\uD7A3\u1100-\u11FF]*')
    body = [YH.sub(lambda m: '<span class="yh">' + m.group(0) + '</span>', b) for b in body]   # 옛한글 낱말은 옛한글 글꼴로
    css = (open(f'{D}/exam.css').read() + open(f'{D}/qb.css').read()
           + f'@font-face{{font-family:"YetHangul";src:url("file://{D}/fonts/NanumMyeongjo-YetHangul.woff2") format("woff2")}}.yh{{font-family:"YetHangul","Noto Serif CJK KR",serif}}')
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(body)}</div>
<script>window.P0={int(os.environ.get("START_PAGE", "1")) - 1};window.HEAD="{HEAD}";window.SUB="";window.LOGO="file://{J}/logo2.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)
    print('questions', len(d['questions']), 'explanations', len(done))


PART_TITLE = {}

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
