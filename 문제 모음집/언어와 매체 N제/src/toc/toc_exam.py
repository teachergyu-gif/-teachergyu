"""1쪽 목차: 예시(청운고 문법 N제 HWP) 1쪽 양식 — 시험지 머리 + 2단 + 왼쪽 단 <목 차> 상자."""
from html import escape


def page(title, section, items, total):
    """items = [(이름, 쪽)]"""
    rows = ''.join(f'<div class="r"><span class="t">{escape(n)}</span><span class="d"></span><span class="p">p.{p}</span></div>' for n, p in items)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page{{size:595pt 841pt;margin:0}}
html,body{{margin:0;padding:0}}
body{{width:595pt;height:841pt;position:relative;font-family:"Noto Serif CJK KR",serif;color:#111}}
.pn{{position:absolute;right:46pt;top:44pt;font-size:24pt;font-weight:700;line-height:1}}
#h{{position:absolute;left:0;right:0;top:50pt;text-align:center;font-size:12.5pt;letter-spacing:-.2pt}}
.big{{position:absolute;left:0;right:0;top:70pt;text-align:center;font-family:"Noto Sans CJK KR",sans-serif;font-weight:900;font-size:26pt;letter-spacing:1pt}}
.tbox{{position:absolute;right:46pt;top:84pt;border:1.3pt solid #111;border-radius:3pt;padding:1.5pt 4pt;font-family:"Noto Sans CJK KR",sans-serif;font-weight:900;font-size:12pt}}
.rule{{position:absolute;left:46pt;right:46pt;top:118pt;border-top:1pt solid #111}}
.mid{{position:absolute;left:297.5pt;top:118pt;bottom:62pt;border-left:.8pt solid #111}}
.box{{position:absolute;left:54pt;width:206pt;top:130pt;border:.8pt solid #111;padding:16pt 12pt 10pt}}
.bt{{position:absolute;left:0;right:0;top:-7pt;text-align:center;line-height:1}}
.bt span{{background:#fff;padding:0 5pt;font-size:9.5pt;letter-spacing:4pt}}
.sec{{font-weight:700;font-size:9.5pt;margin:0 0 8pt}}
.r{{display:flex;align-items:baseline;font-size:9.5pt;line-height:1;margin:0 0 19.6pt 6pt}}
.r:last-child{{margin-bottom:4pt}}
.r .d{{flex:1;border-bottom:.9pt dotted #555;margin:0 3pt;transform:translateY(-2pt)}}
.fr{{position:absolute;left:279pt;top:784pt;width:37pt;height:16pt;box-sizing:border-box;border:.6pt solid #000;font-family:'Liberation Serif','Times New Roman',serif;font-size:8.6px;line-height:1}}
.fr .a{{position:absolute;left:3pt;top:1.5pt}}.fr .b{{position:absolute;right:3pt;bottom:1.5pt}}
.fr svg{{position:absolute;left:0;top:0}}
</style></head><body>
<div class="pn">1</div>
<div id="h">{escape(title)}</div>
<div class="big">국어 영역</div>
<div class="tbox">이재규T</div>
<div class="rule"></div><div class="mid"></div>
<div class="box"><div class="bt"><span>&lt;목 차&gt;</span></div>
<div class="sec">[{escape(section)}]</div>{rows}</div>
<div class="fr"><svg width="37pt" height="16pt" viewBox="0 0 37 16" preserveAspectRatio="none"><line x1="0" y1="16" x2="37" y2="0" stroke="#000" stroke-width=".5"/></svg><span class="a">1</span><span class="b">{total}</span></div>
<script>document.fonts.ready.then(()=>{{document.body.dataset.done='1'}})</script>
</body></html>'''
