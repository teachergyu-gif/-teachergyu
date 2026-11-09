"""언어와 매체 N제 모의고사: 회마다 문제(35~39번) → 해설(이게 정답! / 왜 답이 아니지?).
사용: START_PAGE=2 python3 render_nj.py 데이터폴더(r01.json …) 출력.html"""
import json, os, re, sys, glob
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, D)
sys.path.insert(0, J)
import render
from render import esc, hbr, bogi, CIRC

BOOK = '청운고 2학년 문법 2차 N제 모의고사'


OFFSET = 34   # 원본 35~39번 → 교재 1~5번


def qno(q):
    return int(q['orig']) - OFFSET


def rng_no(r):
    return re.sub(r'\d+', lambda m: str(int(m.group()) - OFFSET), r)


def hbox(title, inner):
    t = f'<div class="bt"><span>{esc(title)}</span></div>' if title else ''
    return f'<div class="bogi">{t}{inner}</div>'


def question(q):
    ex = q.get('extra')
    extra = bogi({'title': ex.get('title') or '', 'text': ex.get('text') or ''}) if isinstance(ex, dict) else ''
    boxes = ''.join(hbox(t, h) for t, h in q.get('html') or [])
    if q.get('pair_head'):
        rows = ''.join(f'<tr><td class="c">{CIRC[i]}</td>' + ''.join(f'<td{" class=l" if len(x.strip()) > 14 else ""}>{esc(x.strip()).replace(chr(10), "<br>")}</td>' for x in t.split(' / ')) + '</tr>'
                       for i, t in enumerate(q['choices']))
        ch = '<table class="pairch3"><tr><td></td>' + ''.join(f'<th>{esc(h)}</th>' for h in q['pair_head']) + f'</tr>{rows}</table>'
    else:
        ch = ''.join(f'<div class="ch"><span class="c">{CIRC[i]}</span><span class="t">{esc(t).replace(chr(10), "<br>")}</span></div>' for i, t in enumerate(q['choices']))
    return (f'<div class="u q"><div class="qh"><span class="n">{qno(q)}.</span><span class="s">{esc(q["stem"])}</span></div>'
            f'{bogi(q.get("bogi"))}{boxes}{extra}{ch}</div>')


def explanation(q, e):
    hang = lambda k, t: f'<div class="ep hang"><span class="c">{k}</span><span>{esc(t)}</span></div>'
    out = [f'<div class="njh"><span class="no">{qno(q):02d}</span><span class="an">답 {esc(e["answer"])}</span></div>',
           '<div class="njl ok"><span>이게 정답!</span></div>', f'<div class="ep">{esc(e["correct"])}</div>',
           '<div class="njl no"><span>왜 답이 아니지?</span></div>']
    out += [hang(k, t) for k, t in e['wrong']]
    return '<div class="u ex nj">' + ''.join(out) + '</div>'


def rounds(data_dir):
    return [json.load(open(f)) for f in sorted(glob.glob(f'{data_dir}/r[0-9][0-9].json'))]


def main(data_dir, out_html):
    body = []
    for k, r in enumerate(rounds(data_dir), 1):
        if body:
            body.append('<div class="u brk"></div>')
        body.append(f'<div class="u qtitle"><span>문법 모의고사 N제 {k}회</span></div>')
        for s in r['sets']:
            if s.get('works'):
                ph = render.passage(s, rng_no(s['rng']))
                for w in s['works']:   # 지문 속 그림(도식): '@@FIG@@' 줄 자리에 html
                    if w.get('fig_html'):
                        ph = re.sub(r'<div class="ln[^"]*">@@FIG@@</div>', lambda m: w['fig_html'], ph, count=1)
                body.append(ph)
            for q in s['questions']:
                if q.get('colbrk'):   # 단 나눔 지정(두 단 여백 고르게)
                    body.append('<div class="u colbrk"></div>')
                body.append(question(q))
        body.append('<div class="u brk"></div>')
        body.append(f'<div class="u qtitle ans"><span>문법 N제 제{k}회 해설</span></div>')
        for s in r['sets']:
            for q in s['questions']:
                body.append(explanation(q, r['ex'][str(q['orig'])]))
    css = open(f'{D}/exam.css').read() + open(f'{D}/book.css').read() + open(f'{D}/nj.css').read()
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(body)}</div>
<script>window.P0={int(os.environ.get("START_PAGE", "1")) - 1};window.HEAD="{BOOK}";window.SUB="";window.LOGO="file://{J}/logo2.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
