"""2026년 2학기 공통국어2 기말고사 대비 교재: 한 데이터로 세 권(강의용·분석지·해설지) HTML을 만든다.
사용: MODE=lecture|analysis|answer START_PAGE=2 python3 render_book.py 데이터폴더 출력.html
데이터폴더: A~E/out.json(전사), answers.json(정답·해설), analysis.json(지문 분석)"""
import json, os, re, sys
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, D)
sys.path.insert(0, J)
import render   # esc, bogi, explanation, quick 등 문제 은행 양식 함수
from render import esc, hbr, bogi, CIRC

PARTS = ['A', 'B', 'C', 'D', 'E']
TITLES = {'lecture': '강의용 교재', 'analysis': '지문 분석지', 'answer': '정답 및 해설', 'perset': ''}
HEAD = '2026년 2학기 공통국어2 기말고사 대비'


def load(work_dir):
    sets = []
    for p in PARTS:
        d = json.load(open(f'{work_dir}/{p}/out.json'))
        sets += d['sets']
    for i, s in enumerate(sets):
        s['no'] = i + 1
    ans = json.load(open(f'{work_dir}/answers.json')) if os.path.exists(f'{work_dir}/answers.json') else {}
    ana = json.load(open(f'{work_dir}/analysis.json')) if os.path.exists(f'{work_dir}/analysis.json') else {}
    return sets, ans, ana


def qkey(q):
    return str(q['orig'])


def qnum(q):
    return q.get('label') or str(q['orig'])


def set_head(s):
    h = s.get('head') or '다음 글을 읽고 물음에 답하시오.'
    h = re.sub(r'^\[\s*([^\]]+?)\s*\]\s*', lambda m: '【' + re.sub(r'\s*-\s*', '～', m.group(1)) + '】 ', h)
    return h


def passage(s, numbered=False):
    """지문 상자. numbered=True면 문단 앞에 ①②… 문단 번호(분석지)"""
    out = []
    pn = 0
    for wi, w in enumerate(s['works']):
        if wi:
            out.append('<div class="ln sp"></div>')
        if w.get('label'):
            out.append(f'<div class="ln tag">{esc(w["label"])}</div>')
        lines = w['lines'].split('\n')
        prose = max(len(re.sub(r'<[^>]+>', '', x)) for x in lines) > 60
        for l in lines:
            if not l.strip():
                out.append('<div class="ln sp"></div>'); continue
            l = re.sub(r'([㉠-㉭㉮-㉻ⓐ-ⓩⒶ-Ⓩ]) (?=\S)', '\\1\u00a0', l)
            sub = re.match(r'^<b>.*</b>$', l.strip())
            item = re.match(r'^\(\d+\)', l.strip())
            cls = 'ln'
            if prose and not sub and not item:
                cls += ' pr'
            if sub:
                cls += ' subh'
            if item:
                cls += ' itm'
            mark = ''
            if numbered and prose and not sub and not item:
                pn += 1
                mark = f'<span class="pno">{pn}</span>'
            out.append(f'<div class="{cls}">{mark}{hbr(esc(l))}</div>')
        if w.get('author'):
            out.append(f'<div class="ln au">{esc(w["author"])}</div>')
    return f'<div class="u set"><div class="sethd">{esc(set_head(s))}</div><div class="box">{"".join(out)}</div></div>'


def question(q):
    ex = q.get('extra')
    extra = ''
    if isinstance(ex, dict):
        extra = bogi({'title': ex.get('title') or '', 'text': ex.get('text') or ''})
    elif ex:
        extra = bogi({'title': '', 'text': ex})
    ch = ''
    if q.get('pair_head'):   # ⓑ·ⓒ 두 칸 선지(표)
        rows = ''.join(f'<tr><td class="c">{CIRC[i]}</td>' + ''.join(f'<td>{esc(x.strip())}</td>' for x in t.split(' / ')) + '</tr>' for i, t in enumerate(q['choices']))
        ch = f'<table class="pairch"><tr><td></td>' + ''.join(f'<th>{esc(h)}</th>' for h in q['pair_head']) + f'</tr>{rows}</table>'
    else:
        ch = ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{esc(t)}</span></div>' for i, t in enumerate(q.get('choices') or []))
    ans = '' if q.get('choices') else '<div class="ans" style="height:150pt"></div>'
    n = qnum(q)
    nh = f'<span class="n sd">[{esc(n)}]</span>' if q.get('label') else f'<span class="n">{esc(n)}.</span>'
    return (f'<div class="u q"><div class="qh">{nh}<span class="s">{esc(q["stem"])}</span></div>'
            f'{bogi(q.get("bogi"))}{extra}{ch}{ans}</div>')


def explanation(q, e):
    n = qnum(q)
    a = e.get('answer', '')
    if q.get('choices'):
        return render.explanation(n, e).replace('<div class="ep">[오답풀이]</div>', '<div class="ep wr">[오답풀이]</div>')
    # 서답형: 모범 답안 + 채점 기준
    out = [f'<div class="eh"><span>[{esc(n)}]</span></div>', f'<div class="ep"><b>[모범 답안]</b></div>']
    out += [f'<div class="ep hang"><span class="c">·</span><span>{esc(x)}</span></div>' for x in a.split('\n') if x.strip()]
    if e.get('points'):
        out.append('<div class="ep wr">[채점 기준]</div>')
        out += [f'<div class="ep hang"><span class="c">·</span><span>{esc(x)}</span></div>' for x in e['points']]
    if e.get('plain'):
        out.append('<div class="ep wr">[해설]</div>')
        out += [f'<div class="ep">{esc(x)}</div>' for x in e['plain'].split('\n') if x.strip()]
    return '<div class="u ex">' + ''.join(out) + '</div>'


def quick(sets, ans, per=5, note='서답형 1~4는 해설의 모범 답안 참고'):
    cells = []
    for s in sets:
        for q in s['questions']:
            if q.get('choices'):
                cells.append((qnum(q), ' '.join(re.findall('[①-⑤]', (ans.get(qkey(q)) or {}).get('answer', '')))))
    rows = []
    for i in range(0, len(cells), per):
        r = cells[i:i + per] + [('', '')] * (per - len(cells[i:i + per]))
        rows.append('<tr>' + ''.join(f'<td class="qn">{n}</td><td class="qv">{esc(v)}</td>' for n, v in r) + '</tr>')
    return f'<div class="u qa"><div class="qat">빠른 정답</div><table class="qat-t">{"".join(rows)}</table>' + (f'<div class="qanote">{note}</div>' if note else '') + '</div>'


def analysis_units(s, a):
    """지문 분석: 주제·구조·문단 요약·핵심 어휘·출제 포인트 (해설처럼 단 끝에서 나뉨)"""
    if not a:
        return []
    units = []
    for part in a.get('works', [a]):
        rows = []
        lab = part.get('label')
        if lab:
            rows.append(f'<div class="eh"><span>{esc(lab)} {esc(part.get("title", ""))}</span></div>')
        if part.get('topic'):
            rows.append(f'<div class="ep"><b class="ak">주제</b> {esc(part["topic"])}</div>')
        if part.get('structure'):
            rows.append(f'<div class="ep"><b class="ak">글의 구조</b> {esc(part["structure"])}</div>')
        for p in part.get('paras', []):
            rows.append(f'<div class="ep hang"><span class="c pno">{esc(str(p["n"]))}</span><span>{esc(p["summary"])}</span></div>')
        if part.get('vocab'):
            rows.append('<div class="ep wr">[핵심 어휘]</div>')
            rows += [f'<div class="ep hang"><span class="c">·</span><span><b>{esc(w)}</b>: {esc(m)}</span></div>' for w, m in part['vocab']]
        if part.get('points'):
            rows.append('<div class="ep wr">[출제 포인트]</div>')
            rows += [f'<div class="ep hang"><span class="c">✔</span><span>{esc(x)}</span></div>' for x in part['points']]
        units.append('<div class="u ex an">' + ''.join(rows) + '</div>')
    return units


def main(work_dir, out_html):
    mode = os.environ.get('MODE', 'lecture')
    sets, ans, ana = load(work_dir)
    body = [f'<div class="u qtitle"><span>{TITLES[mode]}</span></div>']
    if mode == 'lecture':
        for i, s in enumerate(sets):
            if i:
                body.append('<div class="u colbrk"></div>')
            body.append(passage(s))
            body += [question(q) for q in s['questions']]
    elif mode == 'analysis':
        for i, s in enumerate(sets):
            if i:
                body.append('<div class="u colbrk"></div>')
            body.append(passage(s, numbered=True))
            body.append('<div class="u colbrk"></div>')
            body += analysis_units(s, ana.get(str(s['no'])))
    elif mode == 'perset':   # 지문마다 강의용 → 지문 분석 → 정답 및 해설
        body = []
        for i, s in enumerate(sets):
            no = f'{i + 1:02d}'
            for k, name in enumerate(('강의용', '지문 분석', '정답 및 해설')):
                if body:
                    body.append('<div class="u brk"></div>')
                body.append(f'<div class="u qtitle"><span>{no} {name}</span></div>')
                if k == 0:
                    body.append(passage(s))
                    body += [question(q) for q in s['questions']]
                elif k == 1:
                    body.append(passage(s, numbered=True))
                    body.append('<div class="u colbrk"></div>')
                    body += analysis_units(s, ana.get(str(s['no'])))
                else:
                    sd = [q for q in s['questions'] if q.get('label')]
                    body.append(quick([s], ans, note=('서답형은 해설의 모범 답안 참고' if sd else '')))
                    for q in s['questions']:
                        e = ans.get(qkey(q))
                        if e:
                            body.append(explanation(q, e))
    else:
        body.append(quick(sets, ans))
        for s in sets:
            for q in s['questions']:
                e = ans.get(qkey(q))
                if e:
                    body.append(explanation(q, e))
    css = open(f'{D}/exam.css').read() + open(f'{D}/book.css').read()
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(body)}</div>
<script>window.P0={int(os.environ.get("START_PAGE", "1")) - 1};window.HEAD="{HEAD}";window.SUB="";window.LOGO="file://{J}/logo2.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)
    print(mode, 'sets', len(sets))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
