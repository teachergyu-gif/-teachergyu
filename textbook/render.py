"""Render HWPX-extracted blocks (hwpx2blocks.py) as a RICH ACADEMY-styled class textbook PDF.

usage: python3 render.py <blocks.json> <out.pdf> "<표지 1행>" "<표지 2행>" "<부제>"
Two passes: the first finds the page each section starts on, the second fills the 목차.
"""
import html, json, os, re, subprocess, sys

T = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(T)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
BANK_WORDS = ("기출 문제", "서술형", "문제 은행", "정답 및 해설")


def esc(s):
    return html.escape(s).replace("\n", "<br>")


def color_class(c):
    if not c or c in ("#000000", "none"):
        return ""
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    if r > 150 and g < 110 and b < 110:
        return "tc-red"
    if b > 120 and r < 110:
        return "tc-blue"
    if r > 150 and g > 100 and b < 90:
        return "tc-gold"
    return ""


def runs_html(runs, strip_lead=False):
    out = []
    for i, r in enumerate(runs):
        t = r["text"].lstrip() if (strip_lead and i == 0) else r["text"]
        s = esc(t)
        if not s:
            continue
        cls = [c for c in (color_class(r.get("color")), "u" if r.get("u") else "", "b" if r.get("b") else "") if c]
        if r.get("shade") not in (None, "none", "#ffffff"):
            cls.append("shade")
        out.append(f'<span class="{" ".join(cls)}">{s}</span>' if cls else s)
    return "".join(out)


def text_of(runs):
    return "".join(r["text"] for r in runs)


def paras_html(paras):
    out = []
    for p in paras:
        al = {"CENTER": " center", "RIGHT": " right"}.get(p.get("align"), "")
        inner = runs_html(p["runs"])
        tabs = "".join(table_html(t) for t in p.get("tables", []))
        if inner or tabs:
            out.append(f'<div class="cp{al}">{inner}</div>{tabs}')
    return "".join(out)


def table_html(rows):
    # drop spacer columns that are empty in every row (only for span-free tables)
    if all(c["cs"] == 1 and c["rs"] == 1 for r in rows for c in r) and len({len(r) for r in rows}) == 1:
        keep = [j for j in range(len(rows[0])) if any(text_of([x for p in r[j]["paras"] for x in p["runs"]]).strip() or r[j]["paras"] and any(p.get("tables") for p in r[j]["paras"]) for r in rows)]
        rows = [[r[j] for j in keep] for r in rows]
        rows = [r for r in rows if any(text_of([x for p in c["paras"] for x in p["runs"]]).strip() for c in r)]
    if not rows:
        return ""
    head_row = len(rows) > 1 and all(c.get("fill") for c in rows[0]) and not all(r[0].get("fill") for r in rows[1:])
    head_col = len(rows[0]) >= 2 and all(r[0].get("fill") for r in rows[(1 if head_row else 0):]) if rows[0] else False
    trs = []
    for i, r in enumerate(rows):
        tds = []
        for j, c in enumerate(r):
            tag = "th" if (head_row and i == 0) else "td"
            cls = "hc" if (head_col and j == 0 and tag == "td") else ""
            span = (f' colspan="{c["cs"]}"' if c["cs"] > 1 else "") + (f' rowspan="{c["rs"]}"' if c["rs"] > 1 else "")
            tds.append(f'<{tag}{span}{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>{paras_html(c["paras"])}</{tag}>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table class="tb">{"".join(trs)}</table>'


def notes_html(notes):
    chips, digits = [], []
    def flush():
        if digits:
            chips.append(f'<div class="note note-num">{" · ".join(digits)}</div>')
            digits.clear()
    for n in notes:
        t = text_of([x for p in n["paras"] for x in p["runs"]]).strip()
        if re.fullmatch(r"\d", t):
            digits.append(t)
            continue
        flush()
        chips.append(f'<div class="note">{paras_html(n["paras"])}</div>')
    flush()
    return "".join(chips)


def parse_heading(text):
    m = re.match(r"^\d-\(\d\)\s*(.+?)(?:\((강의용|복습용)\))?$", text)
    if m:
        return m.group(1).strip(), m.group(2) or "작품 분석"
    for w in BANK_WORDS:
        if text.endswith(w):
            return text, w
    return text, text


def render(blocks, title1, title2, subtitle, pages, marks):
    sections, cur = [], None
    for b in blocks[1:]:  # block 0 is the original table of contents
        if b["t"] == "heading":
            name, kind = parse_heading(b["text"])
            if kind == "정답 및 해설" and cur:
                cur["blocks"].append({"t": "anshead"})  # answers follow the questions they belong to
                continue
            cur = {"name": name, "kind": kind, "blocks": [], "bank": kind in BANK_WORDS, "parent": None}
            sections.append(cur)
        elif cur:
            cur["blocks"].append(b)

    body, toc_rows = [], []
    for si, s in enumerate(sections):
        anchor = f"S{si}"
        title = s["parent"] + " · 정답 및 해설" if s["parent"] else s["name"]
        tag = s["kind"]
        parts, in_ans = [], False
        for b in s["blocks"]:
            ac = " in-ans" if in_ans else ""
            if b["t"] == "anshead":
                in_ans = True
                parts.append('<div class="ans-h">정답 및 해설</div>')
                continue
            if b["t"] == "para" and re.match(r"^(【.+】|다음 (글|시|자료)을? 읽고)", text_of(b["runs"]).strip()):
                in_ans, ac = False, ""
            if b["t"] == "label":
                parts.append('<div class="lbl">정답</div>')
            elif b["t"] == "box":
                parts.append(f'<div class="box{ac}">{paras_html(b["paras"])}</div>')
            elif b["t"] == "table":
                parts.append(table_html(b["rows"]))
            else:
                txt = text_of(b["runs"]).strip()
                if txt == "MEMO":
                    continue
                al = {"CENTER": " center", "RIGHT": " right"}.get(b.get("align"), "")
                if re.match(r"^-\s.*-$", txt) or re.match(r"^-\s", txt) and txt.endswith("-"):
                    parts.append(f'<div class="src">{runs_html(b["runs"])}</div>')
                elif in_ans and b.get("num"):
                    parts.append(f'<div class="ans"><span class="ans-no">{b["num"].rstrip(".")}</span><span class="ans-tag">정답</span> {runs_html(b["runs"], True)}</div>')
                elif b.get("num"):
                    parts.append(f'<div class="qn"><span class="qn-no">{b["num"].rstrip(".")}</span><div>{runs_html(b["runs"], True)}</div></div>')
                elif s["bank"] and txt[:1] in CIRCLED:
                    parts.append(f'<div class="chc{ac}">{runs_html(b["runs"])}</div>')
                elif re.match(r"^(【.+】|다음 (글|시|자료)을? 읽고)", txt):
                    parts.append(f'<div class="setq">{runs_html(b["runs"])}</div>')
                elif in_ans and re.match(r"^\d+\.\s*(정답)?\s*\S", txt) and not b.get("num"):
                    m = re.match(r"^(\d+)\.\s*(?:정답)?\s*(.*)$", txt, re.S)
                    parts.append(f'<div class="ans"><span class="ans-no">{m.group(1)}</span><span class="ans-tag">정답</span> {esc(m.group(2))}</div>')
                elif in_ans and txt in ("[오답풀이]", "[오답 풀이]", "[해설]"):
                    parts.append(f'<div class="lbl lbl-ex">{esc(txt.strip("[]"))}</div>')
                elif not s["bank"] and txt[:1] in CIRCLED and len(txt) < 30:
                    parts.append(f'<div class="sub-h">{esc(txt)}</div>')
                elif txt in ("예시 답", "예시답"):
                    parts.append('<div class="lbl lbl-ex">예시 답</div>')
                elif b["notes"] and not s["bank"]:
                    parts.append(f'<div class="ln"><div class="ln-t">{runs_html(b["runs"])}</div><div class="ln-n">{notes_html(b["notes"])}</div></div>')
                elif b["notes"]:
                    parts.append(f'<div class="p{al}">{runs_html(b["runs"])}</div><div class="ln-n inline">{notes_html(b["notes"])}</div>')
                else:
                    parts.append(f'<div class="p{al}{ac}">{runs_html(b["runs"])}</div>')
        mark = f'<span class="anchor-mark">QQ{anchor}QQ</span>' if marks else ""
        cols = " cols2" if s["bank"] else ""
        body.append(f"""
<section class="tsec{cols}">{mark}
  <header class="t-head"><span class="tag">{esc(tag)}</span><h2 class="t-title">{esc(title)}</h2></header>
  <div class="t-body">{''.join(parts)}</div>
</section>""")
        toc_rows.append((anchor, tag, title))

    toc = ['<section class="toc-page"><div class="toc-title-h">목차</div><table class="toc">']
    for i, (a, tag, title) in enumerate(toc_rows, 1):
        toc.append(f'<tr><td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">{esc(tag)}</span></td>'
                   f'<td class="toc-title">{esc(title)}</td><td class="toc-pg">{pages.get(a, "")}</td></tr>')
    toc.append("</table></section>")

    cover = f"""
<section class="cover">
  <div class="cover-top"><div class="cover-school">RICH ACADEMY</div><div class="cover-rule"></div><div class="cover-author"><b>이재규T</b></div></div>
  <div class="cover-main">
    <img class="cover-logo" src="file://{ROOT}/brand/logo_beige.png" alt="RICH ACADEMY">
    <div class="cover-kicker">수업용 교재</div>
    <h1 class="cover-title">{esc(title1)}<br><em>{esc(title2)}</em></h1>
    <div class="cover-sub">{esc(subtitle)}</div>
  </div>
  <div class="parts">
    <div class="part-card"><div class="part-no">수록 작품</div><div class="part-name" style="font-size:15pt">청산별곡 · 십 년을 경영ᄒᆞ여</div>
      <div class="part-desc">작자 미상 「청산별곡」 · 송순 「십 년을 경영ᄒᆞ여」</div></div>
    <div class="part-card"><div class="part-no">교재 구성</div><div class="part-name" style="font-size:15pt">분석 → 문제</div>
      <div class="part-desc">작품 분석 · 강의용 · 복습용 · 학습 활동<br>기출 문제 · 서술형 · 문제 은행 (정답 및 해설 포함)</div></div>
  </div>
  <div class="cover-slogan"><img class="cover-slogan-logo" src="file://{ROOT}/brand/logo_navy.png" alt="">특별한 학생을 위한 특별한 교육<br>특목/자사고 전문 온라인 내신학원</div>
</section>"""

    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = "".join(open(os.path.join(ROOT, p), encoding="utf-8").read() for p in
                  ["literature-summary/render/style.css", "combined/extra.css", "brand/brand.css", "textbook/textbook.css"])
    css = css.replace("FONTDIR", "file://" + font_dir)
    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{esc(title1)} {esc(title2)}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{cover}{''.join(toc)}{''.join(body)}</body></html>"""
    open(os.path.join(T, "summary.html"), "w", encoding="utf-8").write(doc)
    return [a for a, _, _ in toc_rows]


def find_pages(pdf, anchors):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ(S\d+)QQ", txt):
            found.setdefault(a, p)
    return found


if __name__ == "__main__":
    blocks = json.load(open(sys.argv[1], encoding="utf-8"))
    out, t1, t2, sub = sys.argv[2:6]
    anchors = render(blocks, t1, t2, sub, {}, True)
    subprocess.run(["node", os.path.join(T, "print.js"), out], check=True)
    pages = find_pages(out, anchors)
    render(blocks, t1, t2, sub, pages, False)
    subprocess.run(["node", os.path.join(T, "print.js"), out], check=True)
    print("sections:", len(anchors), "pages:", pages)
