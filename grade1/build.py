"""1학년 booklet: PART 1 문법 → PART 2 문학 → PART 3 교과서 4단원 → PART 4 모의고사(화법·작문, 비문학).

Grammar topics flow over as many pages as they need, so the table of contents is filled in a
second pass: build → print → find each section's start page in the PDF → build again.
"""
import importlib.util, json, os, re, subprocess, sys

G = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(G)
TITLE = os.environ.get("BOOK_TITLE", "부산외고 1학년 국어 요약 자료")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


nl = load_module("nl", os.path.join(ROOT, "nonliterature-summary/render/render.py"))
lit = load_module("lit", os.path.join(ROOT, "literature-summary/render/render.py"))
md = lit.md


def jload(name):
    with open(os.path.join(G, "data", name), encoding="utf-8") as f:
        return json.load(f)


# ---------- content order ----------
GRAMMAR_FILES = ["gram_1.json", "gram_2.json", "gram_3.json", "gram_4.json"]
LIT_FILES = ["lit_1.json", "lit_2.json", "lit_3.json", "lit_4.json"]
UNIT4_FILES = ["unit4_1.json", "unit4_2.json"]
MOCK_FILES = ["hj_2024.json", "hj_2025.json", "bm_2024.json", "bm_2025.json"]


MARKS = False


def mark(html, anchor):
    """Put an invisible, extractable marker on the block's first page (pass 1 only)."""
    if not MARKS:
        return html
    m = f'<span class="anchor-mark">QQ{anchor}QQ</span>'
    i = html.find('<div class="fit">')
    if i >= 0:
        j = i + len('<div class="fit">')
        return html[:j] + m + html[j:]
    j = html.find(">", html.find("<section")) + 1
    return html[:j] + m + html[j:]


def section_box(bx):
    """A titled box attached under a concept section: a reference table or a caution list."""
    if bx.get("kind") == "table":
        tb = bx["table"]
        hs = tb["headers"]
        if len(hs) > 1 and hs[1] == "":  # "구분" spans the group and row-label columns
            th = f'<th colspan="2">{md(hs[0])}</th>' + "".join(f"<th>{md(h)}</th>" for h in hs[2:])
        else:
            th = "".join(f"<th>{md(h)}</th>" for h in hs)
        trs = []
        for r in tb["rows"]:
            cells, labeled = [], False
            for c in r:
                if isinstance(c, dict):
                    cells.append(f'<td class="grp" rowspan="{c["rowspan"]}">{md(c["text"])}</td>')
                else:
                    cls = "" if labeled else ' class="row-l"'  # first plain cell is the row label (e.g. 하십시오체)
                    labeled = True
                    cells.append(f"<td{cls}>{md(c).replace(chr(10), '<br>')}</td>")
            trs.append("<tr>" + "".join(cells) + "</tr>")
        inner = f'<table class="cmp sb-tb"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'
    else:
        inner = '<ul class="g-pts">' + "".join(f"<li>{md(x)}</li>" for x in bx.get("points", [])) + "</ul>"
    return f'<div class="caution sbox keep"><div class="caution-h">{md(bx["title"])}</div><div class="caution-item">{inner}</div></div>'


def grammar_topic(t, idx):
    secs = []
    for s in t.get("sections", []):
        pts = "".join(f"<li>{md(p)}</li>" for p in s.get("points", []))
        exs = "".join(f'<div class="g-ex">{md(e)}</div>' for e in s.get("examples", []))
        exs = f'<div class="g-exs"><span class="g-ex-label">예문</span><div class="g-ex-list">{exs}</div></div>' if exs else ""
        secs.append(f'<div class="g-sec keep"><div class="g-sec-h">{md(s["heading"])}</div><ul class="g-pts">{pts}</ul>{exs}</div>')
        if s.get("box"):
            secs.append(section_box(s["box"]))
    cautions = ""
    if t.get("cautions"):
        items = []
        for n, c in enumerate(t["cautions"], 1):
            exs = "".join(f'<div class="g-ex">{md(e)}</div>' for e in c.get("examples", []))
            exs = f'<div class="g-exs"><span class="g-ex-label">예문</span><div class="g-ex-list">{exs}</div></div>' if exs else ""
            ctb = ""
            if c.get("table"):
                th = "".join(f"<th>{md(h)}</th>" for h in c["table"]["headers"])
                trs = "".join("<tr>" + "".join(f"<td>{md(x).replace(chr(10), '<br>')}</td>" for x in r) + "</tr>" for r in c["table"]["rows"])
                ctb = f'<table class="cmp caution-tb"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'
            pts = "".join(f"<li>{md(x)}</li>" for x in c.get("points", []))
            pts = f'<ul class="g-pts caution-pts">{pts}</ul>' if pts else ""
            items.append(f'<div class="caution-item keep"><div class="caution-q"><span class="caution-no">({n})</span>{md(c["title"])}</div>'
                         f'<div class="caution-a">{md(c["desc"])}</div>{exs}{ctb}{pts}</div>')
        cautions = f'<div class="caution"><div class="caution-h">{md(t.get("cautions_title") or "주의할 유형 !")}</div>{"".join(items)}</div>'
    table = ""
    tb = t.get("table")
    if tb and tb.get("headers"):
        th = "".join(f"<th>{md(h)}</th>" for h in tb["headers"])
        trs = "".join(lit.row_html(r) for r in tb["rows"])
        table = f'<div class="sec keep"><div class="sec-h">한눈에 정리</div><table class="cmp"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'
    tips = ""
    if t.get("tips"):
        cards = "".join(f'<div class="kp"><div class="kp-term">{md(k["term"])}</div><div class="kp-desc">{md(k["desc"])}</div></div>' for k in t["tips"])
        tips = f'<div class="sec keep"><div class="sec-h">{md(t.get("tips_heading") or "구별 포인트")}</div><div class="kps">{cards}</div></div>'
    return f"""
<section class="gtopic">
  <header class="p-head">
    <div class="p-meta"><span class="p-idx">{idx:02d}</span><span class="tag">문법</span><span class="p-exam">문법 개념</span></div>
    <h2 class="p-title">{md(t["title"])}</h2>
    <div class="p-core"><span class="core-label">핵심 한 줄</span>{md(t.get("one_line"))}</div>
  </header>
  <div class="sec"><div class="sec-h">개념 정리</div>{''.join(secs)}{cautions}</div>
  {table}
  {tips}
</section>"""


def cover(parts):
    cards = "".join(
        f'<div class="part-card"><div class="part-no">PART {i}</div><div class="part-name">{name}</div><div class="part-desc">{desc}</div></div>'
        for i, (name, desc) in enumerate(parts, 1)
    )
    return f"""
<section class="cover">
  <div class="cover-top">
    <div class="cover-school">RICH ACADEMY</div>
    <div class="cover-rule"></div>
    <div class="cover-author"><b>이재규T</b></div>
  </div>
  <div class="cover-main">
    <img class="cover-logo" src="file://{ROOT}/brand/logo_beige.png" alt="RICH ACADEMY">
    <div class="cover-kicker">1학년 · 시험 대비</div>
    <h1 class="cover-title">{md(TITLE).replace(' 국어 ', '<br>국어 ').replace('요약 자료', '<em>요약 자료</em>')}</h1>
    <div class="cover-sub">{' · '.join(f'PART {i} {n}' for i, (n, _) in enumerate(parts, 1))}</div>
  </div>
  <div class="parts parts4">{cards}</div>
<div class="cover-slogan"><img class="cover-slogan-logo" src="file://{ROOT}/brand/logo_navy.png" alt="">특별한 학생을 위한 특별한 교육<br>특목/자사고 전문 온라인 내신학원</div>
</section>"""


def toc(blocks, pages):
    out = ['<section class="toc-page"><div class="toc-title-h">목차</div>']
    for i, (name, rows) in enumerate(blocks, 1):
        first = rows[0][0] if rows else None
        out.append(f'<div class="toc-part"><span class="part-no">PART {i}</span><span class="toc-part-name">{name}</span>'
                   f'<span class="toc-part-pg">{pages.get(first, "")}</span></div><table class="toc">')
        for anchor, cells in rows:
            out.append(f'<tr>{cells}<td class="toc-pg">{pages.get(anchor, "")}</td></tr>')
        out.append("</table>")
    out.append("</section>")
    return "".join(out)


def build(pages):
    body, blocks = [], []

    # PART 1 문법
    topics = [t for f in GRAMMAR_FILES for t in jload(f)["topics"]]
    rows = []
    for i, t in enumerate(topics, 1):
        body.append(mark(grammar_topic(t, i), f"G{i}"))
        rows.append((f"G{i}", f'<td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">문법</span></td><td class="toc-title">{md(t["title"])}</td>'))
    blocks.append(("문법", rows))

    # PART 2 문학
    sets = [jload(f) for f in LIT_FILES]
    rows = []
    for i, st in enumerate(sets, 1):
        body.append(mark(lit.set_html(st, i), f"L{i}"))
        works = " · ".join(f'{md(w["title"])} <span class="toc-au">{md(w["author"])}</span>' for w in st["works"])
        rows.append((f"L{i}", f'<td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">{md(st["set_label"])}</span></td>'
                              f'<td class="toc-title">{works}</td><td class="toc-exam">{md(st.get("source"))}</td>'))
    blocks.append(("문학", rows))

    # PART 3 교과서 4단원, PART 4 모의고사
    for part, files, key in [("교과서 4단원", UNIT4_FILES, "U"), ("모의고사 · 화법과 작문, 비문학", MOCK_FILES, "M")]:
        rows, i = [], 0
        for f in files:
            e = jload(f)
            for p in e["passages"]:
                i += 1
                body.append(mark(nl.passage(e, p, i), f"{key}{i}"))
                rows.append((f"{key}{i}", f'<td class="toc-no">{i:02d}</td><td class="toc-exam">{md(e["exam_short"])}</td>'
                                          f'<td><span class="tag tag-sm">{md(p["field"])}</span></td><td class="toc-title">{md(p["title"])}</td>'))
        blocks.append((part, rows))

    parts = [("문법", "문장 성분 · 서술어의 자릿수 · 높임 · 시간 · 피동 · 사동 · 부정 표현"),
             ("문학", "교과서 1-(1) · 1-(2) · 부교재 (해바라기 씨 · 낙타 · 모순)"),
             ("교과서 4단원", "주제 통합적 읽기 · 사회적 독서와 발표"),
             ("모의고사", "2024 · 2025 9월 고1 화법과 작문 · 비문학")]
    html_body = cover(parts) + toc(blocks, pages) + "".join(body)

    css = open(os.path.join(ROOT, "literature-summary/render/style.css"), encoding="utf-8").read()
    css += open(os.path.join(ROOT, "combined/extra.css"), encoding="utf-8").read()
    css += open(os.path.join(G, "grade1.css"), encoding="utf-8").read()
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css += open(os.path.join(ROOT, "brand/brand.css"), encoding="utf-8").read()
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{html_body}</body></html>"""
    with open(os.path.join(G, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    return [a for _, rows in blocks for a, _ in rows]


def find_pages(pdf, anchors):
    """Locate each section's first page by the invisible anchor marker text."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ([GLUM]\d+)QQ", txt):
            found.setdefault(a, p)
    missing = [a for a in anchors if a not in found]
    if missing:
        sys.exit(f"anchors not found: {missing}")
    return found


if __name__ == "__main__":
    out_pdf = sys.argv[1]
    # pass 1: render with marker text so we can find where each section lands
    MARKS = True
    anchors = build({})
    subprocess.run(["node", os.path.join(G, "print.js"), out_pdf], check=True)
    pages = find_pages(out_pdf, anchors)
    # pass 2: final render with page numbers in the table of contents
    MARKS = False
    build(pages)
    subprocess.run(["node", os.path.join(G, "print.js"), out_pdf], check=True)
    print("pages:", pages)
