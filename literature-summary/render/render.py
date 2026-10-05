import json, html, re, os

R = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(R)
TITLE = "부산외고 2학년 중간고사 대비 문학 요약자료"
EXAM = "2024학년도 6월 모의평가"
SAME = {"(좌동)", "좌동", "(동일)", "동일", "-", "—", ""}


def md(s):
    """escape + **bold** → <strong>"""
    if s is None:
        return ""
    t = html.escape(str(s))
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub("[①-⑳]", lambda m: f'<span class="cn">{ord(m.group(0))-0x245F}</span>', t)
    return t


def load():
    d = os.path.join(S, "data")
    return [json.load(open(os.path.join(d, f), encoding="utf-8")) for f in sorted(os.listdir(d)) if f.endswith(".json")]


def row_html(r):
    """A row whose later cells repeat the first value cell (or say '좌동') becomes one merged cell."""
    head, first, rest = r[0], r[1], r[2:]
    if rest and all(c.strip() in SAME or c.strip() == first.strip() for c in rest):
        return f'<tr class="merged"><td>{md(head)}</td><td colspan="{len(r) - 1}">{md(first)}</td></tr>'
    return "<tr>" + "".join(f"<td>{md(c)}</td>" for c in r) + "</tr>"


def cover(sets):
    rows = []
    for n, st in enumerate(sets, 1):
        works = " · ".join(f'{md(w["title"])} <span class="toc-au">{md(w["author"])}</span>' for w in st["works"])
        rows.append(
            f'<tr><td class="toc-no">{n:02d}</td><td><span class="tag tag-sm">{md(st["set_label"])}</span></td>'
            f'<td class="toc-title">{works}</td></tr>'
        )
    return f"""
<section class="cover">
  <div class="cover-top">
    <div class="cover-school">RICH ACADEMY</div>
    <div class="cover-rule"></div>
    <div class="cover-author"><b>이재규T</b></div>
  </div>
  <div class="cover-main">
    <div class="cover-kicker">2학년 · 중간고사 대비</div>
    <h1 class="cover-title">부산외고 2학년<br>중간고사 대비<br><em>문학 요약자료</em></h1>
    <div class="cover-sub">{EXAM} 문학 {len(sets)}세트 · 작품 해제 · 작품 분석</div>
  </div>
  <div class="cover-toc">
    <div class="toc-head">수록 작품</div>
    <table class="toc">{''.join(rows)}</table>
  </div>
</section>"""


def work_html(st, w, idx, extra="", mode="both"):
    mark = f'<span class="w-mark">{md(w["mark"])}</span>' if w.get("mark") else ""
    facts = "".join(f'<tr><th>{md(f["k"])}</th><td>{md(f["v"])}</td></tr>' for f in w.get("facts", []))
    flow = "".join(
        f'<li><span class="st-label">{md(x["label"])}</span><div class="st-body">'
        + (f'<div class="fl-quote">{md(x["quote"])}</div>' if x.get("quote") else "")
        + f'{md(x["content"])}</div></li>'
        for x in w.get("flow", [])
    )
    chars = ""
    if w.get("characters"):
        chars = '<div class="sec"><div class="sec-h">주요 인물</div><div class="chars">' + "".join(
            f'<div class="ch"><div class="ch-name">{md(c["name"])}</div><div class="ch-desc">{md(c["desc"])}</div></div>'
            for c in w["characters"]
        ) + "</div></div>"
    pts = "".join(
        f'<div class="kp"><div class="kp-term">{md(k["term"])}</div><div class="kp-desc">{md(k["desc"])}</div></div>'
        for k in w.get("points", [])
    )
    run = (f'<div class="run"><span class="p-idx">{idx:02d}</span><span class="tag">{md(st["set_label"])}</span>'
           f'<span class="run-title">{mark}{md(w["title"])} <span class="w-author">{md(w["author"])}</span></span><span class="p-exam">{EXAM}</span></div>')
    page1 = f"""
<section class="pg"><div class="fit">
  <header class="p-head">
    <div class="p-meta"><span class="p-idx">{idx:02d}</span><span class="tag">{md(st["set_label"])}</span><span class="p-exam">{EXAM}</span></div>
    <h2 class="p-title">{mark}{md(w["title"])} <span class="w-author">{md(w["author"])}</span></h2>
  </header>
  <div class="sec"><div class="sec-h"><span class="sec-n">01</span>작품 해제</div>
    <table class="facts">{facts}</table>
    <div class="p-core"><span class="core-label">작품 개관</span>{md(w.get("overview"))}</div>
  </div>
  <div class="sec"><div class="sec-h"><span class="sec-n">02</span>작품 분석</div>
    <ol class="struct flow">{flow}</ol>
  </div>
</div></section>
"""
    page2 = f"""<section class="pg"><div class="fit">
  {run}
  {chars}
  <div class="sec"><div class="sec-h">감상 포인트</div><div class="kps">{pts}</div></div>
  {extra}
</div></section>"""
    return {"both": page1 + page2, "p1": page1, "p2": page2}[mode]



def set_html(st, idx):
    ct = st.get("compare_table")
    cmp = ""
    if ct and ct.get("headers"):
        th = "".join(f"<th>{md(h)}</th>" for h in ct["headers"])
        trs = "".join(row_html(r) for r in ct["rows"])
        cmp = f"""<div class="sec"><div class="sec-h">작품 비교 <small>{md(st["set_title"])}</small></div>
  <table class="cmp"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>"""
    ws = st["works"]
    if len(ws) == 1:
        return work_html(st, ws[0], idx, cmp)
    # multi-work set: each work's analysis page, then one shared page of points + comparison
    out = [work_html(st, w, idx, mode="p1") for w in ws]
    pts = []
    for w in ws:
        mark = f'<span class="w-mark">{md(w["mark"])}</span>' if w.get("mark") else ""
        cards = "".join(
            f'<div class="kp"><div class="kp-term">{md(k["term"])}</div><div class="kp-desc">{md(k["desc"])}</div></div>'
            for k in w.get("points", [])
        )
        pts.append(f'<div class="sec"><div class="sec-h">감상 포인트 <span class="sec-work">{mark}{md(w["title"])}</span></div><div class="kps">{cards}</div></div>')
    run = (f'<div class="run"><span class="p-idx">{idx:02d}</span><span class="tag">{md(st["set_label"])}</span>'
           f'<span class="run-title">{md(st["set_title"])}</span><span class="p-exam">{EXAM}</span></div>')
    out.append(f'<section class="pg"><div class="fit">{run}{"".join(pts)}{cmp}</div></section>')
    return "".join(out)


def build():
    sets = load()
    body = [cover(sets)] + [set_html(st, i) for i, st in enumerate(sets, 1)]
    with open(os.path.join(R, "style.css"), encoding="utf-8") as f:
        css = f.read()
    css = css.replace("FONTDIR", "file://" + os.environ.get("FONT_DIR", S + "/node_modules"))
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<style>{css}</style></head><body>{''.join(body)}</body></html>"""
    with open(os.path.join(R, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("sets:", len(sets), "works:", sum(len(s["works"]) for s in sets))


build()
