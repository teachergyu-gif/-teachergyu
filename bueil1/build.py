"""부일고 1학년 모의고사 파트 요약본: 2023~2026 고1 9월 모의고사 — PART 1 독서 → PART 2 문학.

Same page formats as the earlier booklets (비문학: 핵심 한 줄·지문 요약 / 핵심 개념·한눈에 비교,
문학: 작품 해제·작품 분석). The table of contents is filled in a second pass.
"""
import importlib.util, json, os, re, subprocess, sys

B = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(B)
TITLE = os.environ.get("BOOK_TITLE", "부일고 1학년 모의고사 파트 요약본")
YEARS = ["2023", "2024", "2025", "2026"]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


nl = load_module("nl", os.path.join(ROOT, "nonliterature-summary/render/render.py"))
lit = load_module("lit", os.path.join(ROOT, "literature-summary/render/render.py"))
md = lit.md
MARKS = False


def jload(name):
    with open(os.path.join(B, "data", name), encoding="utf-8") as f:
        return json.load(f)


def mark(html, anchor):
    """Put an invisible, extractable marker on the block's first page (pass 1 only)."""
    if not MARKS:
        return html
    m = f'<span class="anchor-mark">QQ{anchor}QQ</span>'
    i = html.find('<div class="fit">')
    j = i + len('<div class="fit">') if i >= 0 else html.find(">", html.find("<section")) + 1
    return html[:j] + m + html[j:]


def lit_sets():
    sets = []
    for y in YEARS:
        for f in sorted(os.listdir(os.path.join(B, "data"))):
            if f.startswith(f"lit_{y}_"):
                st = jload(f)
                st["source"] = f"{y} 고1 9월"
                sets.append(st)
    cat = lambda st: next((i for i, c in enumerate(lit.CAT_ORDER) if st["set_label"].startswith(c)), len(lit.CAT_ORDER))
    return sorted(sets, key=lambda st: (cat(st), st["source"]))  # stable: genre, then year


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
    <div class="cover-kicker">1학년 · 2023~2026 고1 9월 모의고사</div>
    <h1 class="cover-title">부일고 1학년<br>모의고사 파트<br><em>요약본</em></h1>
    <div class="cover-sub">{' · '.join(f'PART {i} {n}' for i, (n, _) in enumerate(parts, 1))}</div>
  </div>
  <div class="parts">{cards}</div>
</section>"""


def toc(blocks, pages):
    out = ['<section class="toc-page"><div class="toc-title-h">목차</div>']
    for i, (name, rows) in enumerate(blocks, 1):
        out.append(f'<div class="toc-part"><span class="part-no">PART {i}</span><span class="toc-part-name">{name}</span>'
                   f'<span class="toc-part-pg">{pages.get(rows[0][0], "")}</span></div><table class="toc">')
        for anchor, cells in rows:
            out.append(f'<tr>{cells}<td class="toc-pg">{pages.get(anchor, "")}</td></tr>')
        out.append("</table>")
    out.append("</section>")
    return "".join(out)


def build(pages):
    body, blocks = [], []

    rows, i = [], 0
    for y in YEARS:
        e = jload(f"nl_{y}.json")
        for p in e["passages"]:
            i += 1
            body.append(mark(nl.passage(e, p, i), f"N{i}"))
            rows.append((f"N{i}", f'<td class="toc-no">{i:02d}</td><td class="toc-exam">{md(e["exam_short"])}</td>'
                                  f'<td><span class="tag tag-sm">{md(p["field"])}</span></td><td class="toc-title">{md(p["title"])}</td>'))
    blocks.append(("독서", rows))
    n_pass = i

    sets = lit_sets()
    rows = []
    for i, st in enumerate(sets, 1):
        body.append(mark(lit.set_html(st, i), f"L{i}"))
        works = " · ".join(f'{md(w["title"])} <span class="toc-au">{md(w["author"])}</span>' for w in st["works"])
        rows.append((f"L{i}", f'<td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">{md(st["set_label"])}</span></td>'
                              f'<td class="toc-title">{works}</td><td class="toc-exam">{md(st["source"])}</td>'))
    blocks.append(("문학", rows))
    n_works = sum(len(st["works"]) for st in sets)

    parts = [("독서", f"2023~2026 고1 9월 {n_pass}지문<br>핵심 한 줄 · 지문 요약 · 핵심 개념 정리 · 한눈에 비교"),
             ("문학", f"{len(sets)}세트 {n_works}작품 (고전시가 · 현대시 · 현대소설 · 고전소설)<br>작품 해제 · 작품 분석 · 감상 포인트 · 작품 비교")]
    html_body = cover(parts) + toc(blocks, pages) + "".join(body)

    css = "".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in
                  ["literature-summary/render/style.css", "combined/extra.css", "bueil1/bueil1.css", "brand/brand.css"])
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{html_body}</body></html>"""
    with open(os.path.join(B, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    return [a for _, rows in blocks for a, _ in rows]


def find_pages(pdf, anchors):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ([NL]\d+)QQ", txt):
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
