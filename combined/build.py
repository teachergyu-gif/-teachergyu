"""One booklet: 비문학 (Part 1) then 문학 (Part 2), with a shared cover and a two-part table of contents."""
import importlib.util, os

C = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(C)
TITLE = "부산외고 2학년 중간고사 비문학, 문학 요약 자료"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


nl = load_module("nl", os.path.join(ROOT, "nonliterature-summary/render/render.py"))
lit = load_module("lit", os.path.join(ROOT, "literature-summary/render/render.py"))
md = lit.md


def cover(n_pass, n_sets, n_works):
    return f"""
<section class="cover">
  <div class="cover-top">
    <div class="cover-school">RICH ACADEMY</div>
    <div class="cover-rule"></div>
    <div class="cover-author"><b>이재규T</b></div>
  </div>
  <div class="cover-main">
    <div class="cover-kicker">2학년 · 중간고사 대비</div>
    <h1 class="cover-title">부산외고 2학년<br>중간고사<br><em>비문학, 문학 요약 자료</em></h1>
    <div class="cover-sub">PART 1 비문학 {n_pass}지문 · PART 2 문학 {n_sets}세트 {n_works}작품</div>
  </div>
  <div class="parts">
    <div class="part-card"><div class="part-no">PART 1</div><div class="part-name">비문학</div>
      <div class="part-desc">평가원 기출 {n_pass}지문<br>핵심 한 줄 · 지문 요약 · 핵심 개념 정리 · 한눈에 비교</div></div>
    <div class="part-card"><div class="part-no">PART 2</div><div class="part-name">문학</div>
      <div class="part-desc">{n_sets}세트 {n_works}작품 (고전시가 · 현대시 · 현대소설 · 고전소설)<br>작품 해제 · 작품 분석 · 감상 포인트 · 작품 비교</div></div>
  </div>
</section>"""


def toc(nl_rows, lit_rows, nl_start, lit_start):
    def table(rows):
        return '<table class="toc">' + "".join(rows) + "</table>"
    return f"""
<section class="toc-page">
  <div class="toc-title-h">목차</div>
  <div class="toc-part"><span class="part-no">PART 1</span><span class="toc-part-name">비문학</span><span class="toc-part-pg">{nl_start}</span></div>
  {table(nl_rows)}
  <div class="toc-part"><span class="part-no">PART 2</span><span class="toc-part-name">문학</span><span class="toc-part-pg">{lit_start}</span></div>
  {table(lit_rows)}
</section>"""


def build():
    exams = nl.load()
    sets = lit.load()
    page = 3  # 1: cover, 2: 목차

    nl_rows, nl_body, idx = [], [], 0
    nl_start = page
    for e in exams:
        for p in e["passages"]:
            idx += 1
            nl_rows.append(
                f'<tr><td class="toc-no">{idx:02d}</td><td class="toc-exam">{md(e["exam_short"])}</td>'
                f'<td><span class="tag tag-sm">{md(p["field"])}</span></td>'
                f'<td class="toc-title">{md(p["title"])}</td><td class="toc-pg">{page}</td></tr>'
            )
            nl_body.append(nl.passage(e, p, idx))
            page += 2

    lit_rows, lit_body = [], []
    lit_start = page
    for i, st in enumerate(sets, 1):
        works = " · ".join(f'{md(w["title"])} <span class="toc-au">{md(w["author"])}</span>' for w in st["works"])
        lit_rows.append(
            f'<tr><td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">{md(st["set_label"])}</span></td>'
            f'<td class="toc-title">{works}</td><td class="toc-pg">{page}</td></tr>'
        )
        lit_body.append(lit.set_html(st, i))
        n = len(st["works"])
        page += 2 if n == 1 else n + 1

    n_works = sum(len(s["works"]) for s in sets)
    body = [cover(idx, len(sets), n_works), toc(nl_rows, lit_rows, nl_start, lit_start)] + nl_body + lit_body
    with open(os.path.join(ROOT, "literature-summary/render/style.css"), encoding="utf-8") as f:
        css = f.read()
    with open(os.path.join(C, "extra.css"), encoding="utf-8") as f:
        css += f.read()
    css = css.replace("FONTDIR", "file://" + os.environ.get("FONT_DIR", ROOT + "/node_modules"))
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<style>{css}</style></head><body>{''.join(body)}</body></html>"""
    with open(os.path.join(C, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("passages:", idx, "sets:", len(sets), "works:", n_works, "expected pages:", page - 1)


if __name__ == "__main__":
    build()
