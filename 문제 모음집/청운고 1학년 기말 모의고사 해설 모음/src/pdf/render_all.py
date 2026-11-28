"""1~3회 해설 모음: 회마다 새 쪽에서 ‘N회 정답 및 해설’ → 빠른 정답 → 해설.
사용: python3 render_all.py exam.json 출력.html"""
import json, os, re, sys
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(D)
sys.path.insert(0, D); sys.path.insert(0, J)
os.environ.setdefault('MODE', 'a')
import render
from render import explanation, quick

HEAD = os.environ.get('HEAD', '')


def main(data_json, out_html):
    d = json.load(open(data_json))
    body = []
    for k, r in enumerate(d['rounds'], 1):
        if body:
            body.append('<div class="u brk"></div>')
        name = re.sub(r'^청운고 1학년 2학기 기말고사 대비 모의고사 ', '', r['title'])   # ‘1회 정답 및 해설’
        exs = [(e['no'], {'choices': ['-'] * 5}, e) for e in r['ex']]
        body.append(f'<div class="u extitle"><span>{name}</span></div>')
        body.append(quick(exs))
        body += [explanation(n, e) for n, q, e in exs]
    YH = re.compile(r'[가-힣ᄀ-ᇿ]*[ᄀ-ᇿㅥ-ㆎ][가-힣ᄀ-ᇿ]*')
    body = [re.sub(r'(<[^>]*>)|([^<]+)', lambda m: m.group(1) or YH.sub(lambda k: '<span class="yh' + (' yi' if re.search('[ᅌᇰ]', k.group(0)) else '') + '">' + k.group(0) + '</span>', m.group(2)), b) for b in body]
    css = (open(f'{D}/exam.css').read() + open(f'{D}/mock.css').read()
           + f'@font-face{{font-family:"YetHangul";src:url("file://{D}/fonts/NanumMyeongjo-YetHangul.woff2") format("woff2")}}.yh{{font-family:"YetHangul","Noto Serif CJK KR",serif}}'
           + '.yh.yi{font-family:"Noto Sans CJK KR",sans-serif;font-weight:350}'
           + '.qa{margin-bottom:5mm}')
    js = open(f'{D}/paginate.js').read()
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div id="src">{"".join(body)}</div>
<script>window.P0=0;window.HEAD="{HEAD}";window.KYO="정답 및 해설";window.SUB="";window.LOGO="file://{J}/logo2.jpg";</script>
<script>{js}</script></body></html>'''
    open(out_html, 'w').write(doc)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
