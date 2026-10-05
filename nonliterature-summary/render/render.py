import json, html, re, os

R = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(R)
ORDER = ["2023_suneung", "2024_06", "2024_09", "2024_suneung"]
TITLE = "부산외고 2학년 중간고사 대비 비문학 요약자료"


def md(s):
    """escape + **bold** → <strong>"""
    if s is None:
        return ""
    t = html.escape(str(s))
    t = re.sub(r"([\u2460-\u2464])\(([0-9]+%)\)", r"\1(선택률 \2)", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\^\(([^)]*)\)|\^([0-9][0-9./]*[0-9]|[0-9])", lambda m: f"<sup>{m.group(1) or m.group(2)}</sup>", t)
    t = re.sub("[\u2460-\u2473]", lambda m: f'<span class="cn">{ord(m.group(0))-0x245F}</span>', t)
    return t


def load():
    exams = []
    for k in ORDER:
        p = os.path.join(S, "data", k + ".json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if all("field" in x for x in d.get("passages", [])):
                exams.append(d)
            else:
                print("SKIP (schema)", k)
    return exams


def cover(exams):
    rows = []
    n = 0
    for e in exams:
        for p in e["passages"]:
            n += 1
            rows.append(
                f'<tr><td class="toc-no">{n:02d}</td><td class="toc-exam">{md(e["exam_short"])}</td>'
                f'<td><span class="tag tag-sm">{md(p["field"])}</span></td>'
                f'<td class="toc-title">{md(p["title"])}</td><td class="toc-q">{md(p["qrange"])}</td></tr>'
            )
    return f"""
<section class="cover">
  <div class="cover-top">
    <div class="cover-school">RICH ACADEMY</div>
    <div class="cover-rule"></div>
    <div class="cover-author">제작 <b>이재규T</b></div>
  </div>
  <div class="cover-main">
    <div class="cover-kicker">2학년 · 중간고사 대비</div>
    <h1 class="cover-title">부산외고 2학년<br>중간고사 대비<br><em>비문학 요약자료</em></h1>
    <div class="cover-sub">평가원 기출 비문학 {n}지문 · 핵심 한 줄 · 문단별 요약 · 핵심 개념 정리</div>
  </div>
  <div class="cover-toc">
    <div class="toc-head">수록 지문</div>
    <table class="toc">{''.join(rows)}</table>
  </div>
  <div class="cover-guide">
    <div class="guide-item"><span class="gi-n">01</span><b>핵심 한 줄</b><span>지문 전체를 꿰는 한 문장과 키워드로 큰 그림을 잡습니다.</span></div>
    <div class="guide-item"><span class="gi-n">02</span><b>문단별 요약</b><span>문단의 흐름을 따라 지문 구조를 다시 세웁니다.</span></div>
    <div class="guide-item"><span class="gi-n">03</span><b>핵심 개념 정리</b><span>시험에 직결되는 개념과 비교표로 마무리합니다.</span></div>
  </div>
</section>"""


def passage(e, p, idx):
    kw = "".join(f'<span class="kw">{md(k)}</span>' for k in p.get("keywords", []))
    struct = "".join(
        f'<li><span class="st-label">{md(s["label"])}</span><span class="st-body">{md(s["content"])}</span></li>'
        for s in p.get("structure", [])
    )
    kp = "".join(
        f'<div class="kp"><div class="kp-term">{md(k["term"])}</div><div class="kp-desc">{md(k["desc"])}</div></div>'
        for k in p.get("key_points", [])
    )
    ct = p.get("compare_table")
    table = ""
    if ct and ct.get("headers"):
        th = "".join(f"<th>{md(h)}</th>" for h in ct["headers"])
        trs = "".join("<tr>" + "".join(f"<td>{md(c)}</td>" for c in r) + "</tr>" for r in ct["rows"])
        table = f'<div class="keep"><div class="sub-h">한눈에 비교</div><table class="cmp"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'

    qs = []
    for q in p.get("questions", []):
        trap = f'<div class="q-trap"><span>함정</span><div>{md(q["trap"])}</div></div>' if q.get("trap") else ""
        qs.append(f"""
<div class="q">
  <div class="q-side"><div class="q-no">{md(q["no"])}</div><div class="q-ans">정답 {md(q["answer"])}</div></div>
  <div class="q-main">
    <div class="q-type">{md(q["type"])}</div>
    <div class="q-ask">{md(q["ask"])}</div>
    <div class="q-point"><span>출제 포인트</span><div>{md(q["point"])}</div></div>
    <div class="q-why"><span>정답 근거</span><div>{md(q["why"])}</div></div>
    {trap}
  </div>
</div>""")
    ms = []
    for i, m in enumerate(p.get("misconceptions", []), 1):
        rel = f'<span class="mc-rel">{md(m["related"])}</span>' if m.get("related") else ""
        ms.append(f"""
<div class="mc">
  <div class="mc-wrong"><span class="mc-ic x">✕</span><div><span class="mc-n">오해 {i}</span>{rel}<p>{md(m["wrong"])}</p></div></div>
  <div class="mc-right"><span class="mc-ic o">✓</span><p>{md(m["correct"])}</p></div>
</div>""")

    return f"""
<section class="passage">
  <header class="p-head">
    <div class="p-meta"><span class="p-idx">{idx:02d}</span><span class="tag">{md(p["field"])}</span><span class="p-exam">{md(e["exam"])}</span><span class="p-q">{md(p["qrange"])}</span></div>
    <h2 class="p-title">{md(p["title"])}</h2>
    <div class="p-core"><span class="core-label">핵심 한 줄</span>{md(p.get("one_line"))}</div>
    <div class="kws">{kw}</div>
  </header>

  <div class="sec"><div class="sec-h">지문 요약</div>
    <ol class="struct">{struct}</ol>
    <div class="keep"><div class="sub-h">핵심 개념 정리</div>
    <div class="kps">{kp}</div></div>
    {table}
  </div>

</section>"""


def build():
    exams = load()
    body = [cover(exams)]
    idx = 0
    for e in exams:
        for p in e["passages"]:
            idx += 1
            body.append(passage(e, p, idx))
    with open(os.path.join(R, "style.css"), encoding="utf-8") as f:
        css = f.read()
    css = css.replace("FONTDIR", "file://" + os.environ.get("FONT_DIR", S + "/node_modules"))
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<style>{css}</style></head><body>{''.join(body)}</body></html>"""
    with open(os.path.join(R, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("passages:", idx)


build()
