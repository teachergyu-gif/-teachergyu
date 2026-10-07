"""부일고 2학년 독서 요약 자료 (상세판): PART 1 평가원 기출 → PART 2 수능특강 독서.

Each passage gets a flowing summary (핵심 한 줄 · 지문 요약 · 흐름 정리) and, from a fresh page,
핵심 개념 정리 · 한눈에 비교 · 시험 직전 체크. The table of contents is filled in a second pass.
"""
import importlib.util, json, os, re, subprocess, sys

B = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(B)
TITLE = os.environ.get("BOOK_TITLE", "부일고 2학년 중간고사 독서 요약 자료")

PARTS = [
    ("평가원 기출", "2018 수능 · 2024 9월 · 2027 9월", ["bigdata", "digital", "trans"]),
    ("수능특강 독서", "수능특강 4지문", ["jaspers", "neo", "land", "embed"]),
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


nl = load_module("nl", os.path.join(ROOT, "nonliterature-summary/render/render.py"))
md = nl.md
MARKS = False


def jload(name):
    with open(os.path.join(B, "data", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def mark(anchor):
    return f'<span class="anchor-mark">QQ{anchor}QQ</span>' if MARKS else ""


def flow_html(fl):
    if not fl or not fl.get("steps"):
        return ""
    steps = "".join(
        f'<li><span class="fl-no">{i}</span><div><div class="fl-name">{md(s["name"])}</div><div class="fl-desc">{md(s["desc"])}</div></div></li>'
        for i, s in enumerate(fl["steps"], 1)
    )
    return f'<div class="sec fl-sec"><div class="sec-h">흐름 정리<small>{md(fl.get("title"))}</small></div><ol class="flow">{steps}</ol></div>'


def passage(p, idx, anchor):
    meta = f'<span class="p-idx">{idx:02d}</span><span class="tag">{md(p["field"])}</span><span class="p-exam">{md(p["source"])}</span>'
    kw = "".join(f'<span class="kw">{md(k)}</span>' for k in p.get("keywords", []))
    struct = "".join(
        f'<li><span class="st-label">{md(s["label"])}</span><span class="st-body">{md(s["content"])}</span></li>'
        for s in p["structure"]
    )
    kp = "".join(
        f'<div class="kp"><div class="kp-term">{md(k["term"])}</div><div class="kp-desc">{md(k["desc"])}</div></div>'
        for k in p.get("key_points", [])
    )
    ct = p.get("compare_table")
    table = ""
    if ct and ct.get("headers"):
        th = "".join(f"<th>{md(h)}</th>" for h in ct["headers"])
        trs = "".join(nl.row_html(r) for r in ct["rows"])
        table = f'<div class="sec cmp-whole"><div class="sec-h">한눈에 비교</div><table class="cmp"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'
    chk = "".join(
        f'<div class="ck"><div class="ck-q"><span class="ck-mark">Q</span><span>{md(c["q"])}</span></div><div class="ck-a"><span class="ck-mark">A</span><span>{md(c["a"])}</span></div></div>'
        for c in p.get("check_points", [])
    )
    checks = f'<div class="sec ck-sec"><div class="sec-h">시험 직전 체크</div><div class="cks">{chk}</div></div>' if chk else ""
    run = f'<div class="run">{meta.replace("p-exam", "p-exam run-src")}<span class="run-title">{md(p["title"])}</span></div>'
    return f"""
<section class="dsec">{mark(anchor)}
  <header class="p-head">
    <div class="p-meta">{meta}</div>
    <h2 class="p-title">{md(p["title"])}</h2>
    <div class="p-core"><span class="core-label">핵심 한 줄</span>{md(p.get("one_line"))}</div>
    <div class="kws">{kw}</div>
  </header>
  <div class="sec"><div class="sec-h">지문 요약</div><ol class="struct">{struct}</ol></div>
  {flow_html(p.get("flow"))}
</section>
<section class="dsec">
  {run}
  <div class="sec"><div class="sec-h">핵심 개념 정리</div><div class="kps">{kp}</div></div>
  {table}
  {checks}
</section>"""


def cover(n):
    cards = "".join(
        f'<div class="part-card"><div class="part-no">PART {i}</div><div class="part-name">{name}</div>'
        f'<div class="part-desc">{desc}<br>' + " · ".join(md(jload(k)["title"]) for k in keys) + "</div></div>"
        for i, (name, desc, keys) in enumerate(PARTS, 1)
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
    <div class="cover-kicker">2학년 · 중간고사 대비</div>
    <h1 class="cover-title">부일고 2학년<br>중간고사<br><em>독서 요약 자료</em></h1>
    <div class="cover-sub">독서 {n}지문 · 핵심 한 줄 · 문단별 상세 요약 · 핵심 개념 정리 · 시험 직전 체크</div>
  </div>
  <div class="parts">{cards}</div>
</section>"""


def build(pages):
    body, toc, anchors, idx = [], [], [], 0
    for pi, (name, _, keys) in enumerate(PARTS, 1):
        rows = []
        for k in keys:
            idx += 1
            p = jload(k)
            a = f"P{idx}"
            anchors.append(a)
            body.append(passage(p, idx, a))
            rows.append(f'<tr><td class="toc-no">{idx:02d}</td><td class="toc-exam">{md(p["source"])}</td>'
                        f'<td><span class="tag tag-sm">{md(p["field"])}</span></td><td class="toc-title">{md(p["title"])}</td>'
                        f'<td class="toc-pg">{pages.get(a, "")}</td></tr>')
        first = f"P{idx - len(keys) + 1}"
        toc.append(f'<div class="toc-part"><span class="part-no">PART {pi}</span><span class="toc-part-name">{name}</span>'
                   f'<span class="toc-part-pg">{pages.get(first, "")}</span></div><table class="toc">{"".join(rows)}</table>')
    html_body = cover(idx) + '<section class="toc-page"><div class="toc-title-h">목차</div>' + "".join(toc) + "</section>" + "".join(body)

    css = "".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in
                  ["literature-summary/render/style.css", "combined/extra.css", "bueil2/bueil2.css", "brand/brand.css"])
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{html_body}</body></html>"""
    with open(os.path.join(B, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    return anchors


def find_pages(pdf, anchors):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ(P\d+)QQ", txt):
            found.setdefault(a, p)
    missing = [a for a in anchors if a not in found]
    if missing:
        sys.exit(f"anchors not found: {missing}")
    return found


if __name__ == "__main__":
    out_pdf = sys.argv[1]
    MARKS = True
    anchors = build({})
    subprocess.run(["node", os.path.join(B, "print.js"), out_pdf], check=True)
    pages = find_pages(out_pdf, anchors)
    MARKS = False
    build(pages)
    subprocess.run(["node", os.path.join(B, "print.js"), out_pdf], check=True)
    print("pages:", pages)
