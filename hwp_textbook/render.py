"""HWP 교재 (blocks.json from hwp5blocks.py) → RICH ACADEMY booklet HTML; print.js paginates and prints.

Usage: python3 render.py data/blocks.json out.pdf "<cover kicker>" "<title line 1>" "<title line 2>"

Sections start at the source's title boxes. Every section is a list of "units" (a question with its
<보기>/<조건> boxes and choices, an explanation, a heading glued to what follows, a table ...);
print.js packs units into fixed A4 pages so that no unit is ever split across pages, and spreads the
spare space between questions. The table of contents is filled in a second pass.
"""
import html, json, os, re, subprocess, sys

H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(H)
MARKS = False

CIRC = "①②③④⑤⑥⑦⑧⑨⑩"
SRC_RE = re.compile(r"^\s*[｜|]?\s*(\d{4}(학년도|년).*(번|문항))\s*[｜|]?\s*$")
GLOSS_RE = re.compile(r"→\s*\[현대어 풀이\]")
FRAME_LABEL = re.compile(r"^\s*<\s*.+?\s*>\s*$|^\s*\[.+\]\s*$")


# ---------------------------------------------------------------- text
def run_html(r):
    t = html.escape(r["text"])
    if r.get("circle"):
        return f'<span class="circ">{t}</span>'
    if r.get("boxed"):
        return f'<span class="ibox">{t}</span>'
    if r.get("b"):
        t = f"<b>{t}</b>"
    if r.get("u"):
        t = f"<u>{t}</u>"
    style = []
    col = (r.get("color") or "#000000").lower()
    if col not in ("#000000", "#000", "black"):
        style.append(f"color:{tone(col)}")
    sh = (r.get("shade") or "#ffffff").lower()
    if sh not in ("#ffffff", "#fff", "none", "white"):
        style.append("background:var(--gold-l)")
    if style:
        t = f'<span style="{";".join(style)}">{t}</span>'
    return t


def tone(col):
    """Map the source's highlight colours onto the brand palette (red stays red for 강조)."""
    try:
        r, g, b = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
    except ValueError:
        return col
    if r > 150 and g < 110 and b < 110:
        return "#b4473f"
    if b > 150 and r < 120:
        return "#2f4f8f"
    if r > 200 and g > 200 and b > 200:
        return "#3b404b"
    return "var(--navy)"


def ptext(p):
    return "".join(r["text"] for r in p.get("runs", []))


def runs_html(runs):
    return "".join(run_html(r) for r in runs).replace("\n", "<br>")


def strip_lead(runs):
    """Drop the source's manual indentation (leading spaces) of a paragraph."""
    runs = [dict(r) for r in runs]
    while runs and not runs[0]["text"].strip():
        runs.pop(0)
    if runs:
        runs[0]["text"] = runs[0]["text"].lstrip()
    return runs


def kind(text, num=None):
    t = text.strip()
    if num and num != "•":
        return "q"
    if num == "•":
        return "li1"
    if SRC_RE.match(t):
        return "src"
    if t.startswith("○"):
        return "sub"
    if t.startswith("•"):
        return "li1"
    if t.startswith("‧") or t.startswith("·") and not re.match(r"^·\S", t):
        return "li2"
    if t.startswith("- ") or t.startswith("-‘") or t.startswith("- ‘"):
        return "li3"
    if t.startswith("※"):
        return "note"
    if re.match(r"^예\s", t):
        return "ex"
    if t and t[0] in CIRC:
        return "ch"
    if t.startswith("☞") or t in ("[오답풀이]", "[현대어 풀이]") or re.match(r"^\[[^\]]{2,12}\]$", t):
        return "lab"
    if t.startswith("→[현대어 풀이]") or t.startswith("→ [현대어 풀이]"):
        return "gloss"
    if re.match(r"^답\s*[:：]", t):
        return "ans"
    return "p"


def para_html(p, extra=""):
    if p.get("orig"):
        extra += " orig"
    text = ptext(p)
    k = kind(text, p.get("num"))
    runs = strip_lead(p["runs"])
    body = runs_html(runs)
    pre = " pre" if re.search(r"\S {3,}\S", text.strip()) else ""
    al = {"center": " center", "right": " right"}.get(p.get("align"), "")
    if k == "q":
        return f'<div class="hq"><span class="hq-no">{html.escape(p["num"].rstrip("."))}</span><span class="hq-t">{body}</span></div>'
    if k == "src":
        return f'<div class="hsrc">{html.escape(SRC_RE.match(text.strip()).group(1))}</div>'
    if k == "sub":
        return f'<h3 class="hsub">{runs_html(strip_lead([dict(runs[0], text=runs[0]["text"].lstrip("○ ").lstrip())] + runs[1:]))}</h3>'
    if k == "gloss":
        tag = '<span class="gl-tag">현대어 풀이</span>'
        g = GLOSS_RE.sub(tag, body, count=1)
        return f'<p class="hgloss{pre}">{g}</p>'
    return f'<p class="hp {k}{pre}{al}{extra}">{body}</p>'


# ---------------------------------------------------------------- tables & boxes
def is_frame(rows):
    """3-row picture frame used for <보기>/<조건>: label cell on top, content in the last row."""
    if len(rows) == 3 and len(rows[0]) == 3 and len(rows[-1]) == 1:
        lab = "".join(ptext(p) for p in rows[0][1]["paras"])
        return FRAME_LABEL.match(lab) is not None
    return False


def is_plain_frame(rows):
    return len(rows) == 2 and len(rows[0]) == 1 and len(rows[1]) == 1 and not "".join(ptext(p) for p in rows[0][0]["paras"]).strip()


def cell_html(paras):
    out = []
    for p in paras:
        if ptext(p).strip():
            out.append(para_html(p))
        for t in p.get("tables", []):
            out.append(table_html(t))
    return "".join(out)


def table_html(rows):
    if is_frame(rows):
        lab = "".join(ptext(p) for p in rows[0][1]["paras"]).strip()
        lab = re.sub(r"\s+", " ", lab)
        return f'<div class="bogi"><div class="bogi-h">{html.escape(lab)}</div>{cell_html(rows[-1][0]["paras"])}</div>'
    if is_plain_frame(rows):
        return f'<div class="bogi plain">{cell_html(rows[1][0]["paras"])}</div>'
    trs = []
    for r in rows:
        tds = []
        for c in r:
            span = (f' colspan="{c["cs"]}"' if c["cs"] > 1 else "") + (f' rowspan="{c["rs"]}"' if c["rs"] > 1 else "")
            cls = ' class="hc"' if c.get("fill") else ""
            tds.append(f"<td{span}{cls}>{cell_html(c['paras'])}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table class="htb">{"".join(trs)}</table>'


def box_html(b):
    ps = b["paras"]
    first = ptext(ps[0]).strip() if ps else ""
    if first.startswith("★"):
        return (f'<div class="hcard"><div class="hcard-h">{html.escape(first.lstrip("★ ").strip())}</div>'
                f'{cell_html(ps[1:])}</div>')
    return f'<div class="hbox">{cell_html(ps)}</div>'


def block_html(b):
    t = b["t"]
    if t == "para":
        return para_html(b)
    if t == "table":
        return table_html(b["rows"])
    if t == "box":
        return box_html(b)
    if t == "img":
        return f'<div class="himg"><img src="file://{H}/img/{b["src"]}" alt=""></div>'
    if t == "heading":
        return f'<div class="hflag">{html.escape(b["text"])}</div>'
    return ""


# ---------------------------------------------------------------- structure
def box_text(b):
    return " ".join(ptext(p) for p in b.get("paras", [])).strip()


def is_section_title(b):
    if b["t"] != "box" or len(b["paras"]) != 1:
        return False
    t = box_text(b)
    return (0 < len(t) <= 40 and not t.startswith("★") and not SRC_RE.match(t) and not re.match(r"^\d{4}년", t)
            and re.search(r"국어|기출|분석|문제|해설|훈민정음|용비어천가", t) is not None)


def is_src_box(b):
    return b["t"] == "box" and len(b["paras"]) == 1 and re.match(r"^\d{4}(년|학년도).*(번|문항)\s*$", box_text(b)) is not None


def merge_continuations(blocks):
    """The answer pages were typed with a hard line break at every line; glue those lines back."""
    out = []
    in_expl = False
    for b in blocks:
        if b["t"] == "box" and is_section_title(b):
            in_expl = "해설" in box_text(b)
        if b["t"] == "para" and "<빠른 정답>" in ptext(b):
            in_expl = True
        if (b["t"] == "para" and out and out[-1]["t"] == "para" and not b.get("num") and not out[-1].get("num")):
            prev, cur = ptext(out[-1]).rstrip(), ptext(b).strip()
            ck = kind(cur)
            pk = kind(prev)
            ends = prev.endswith((".", "?", "!", "」", ")", "]", ":")) or not prev
            if ck == "p" and not ends and (in_expl or pk == "ch") and pk not in ("lab", "src", "sub"):
                out[-1] = dict(out[-1], runs=out[-1]["runs"] + [{"text": " "}] + strip_lead(b["runs"]))
                continue
        out.append(b)
    return out


def sections(blocks):
    secs, cur = [], None
    for b in blocks:
        if is_section_title(b):
            cur = {"title": box_text(b), "blocks": []}
            secs.append(cur)
        elif cur is not None and b["t"] != "pagebreak":
            cur["blocks"].append(b)
    return secs


def section_kind(title):
    if "해설" in title:
        return "expl"
    if "문제" in title or "기출" in title:
        return "quiz"
    return "theory"


def units(sec):
    """Group blocks into unbreakable units."""
    out, cur = [], None
    k = section_kind(sec["title"])
    blocks = sec["blocks"]
    i = 0
    explain_mode = False
    while i < len(blocks):
        b = blocks[i]
        t = ptext(b) if b["t"] == "para" else ""
        starts_q = (b["t"] == "para" and (b.get("num") and b["num"] != "•" or SRC_RE.match(t.strip()))) or is_src_box(b)
        if b["t"] == "para" and "<빠른 정답>" in t:
            explain_mode = True
            cur = {"cls": "u-key", "html": [f'<div class="hkey-h">{html.escape(t.strip())}</div>']}
            out.append(cur)
            i += 1
            continue
        if explain_mode or k == "expl":
            # an explanation starts at a bare answer mark ("③") or at the 문항 번호/정답 table
            bare = b["t"] == "para" and re.fullmatch(r"\s*[①②③④⑤]\s*", t or "")
            ktab = b["t"] == "table" and b["rows"] and "".join(ptext(p) for p in b["rows"][0][0]["paras"]).strip() == "문항 번호"
            if bare or ktab or cur is None or cur.get("cls") == "u-key" and b["t"] != "table":
                cur = {"cls": "u-ex split", "html": []}
                out.append(cur)
                if bare:
                    cur["html"].append(f'<div class="hex-h"><span class="hex-n"></span>정답 {html.escape(t.strip())}</div>')
                    i += 1
                    continue
            cur["html"].append(block_html(b))
            i += 1
            continue
        if starts_q:
            # a source label (para or box) opens the question; the numbered stem that follows joins it
            if cur is not None and cur.get("src_only") and b["t"] == "para" and b.get("num"):
                cur["html"].append(block_html(b))
                cur["src_only"] = False
                i += 1
                continue
            cur = {"cls": "u-q", "html": []}
            out.append(cur)
            if is_src_box(b):
                cur["html"].append(f'<div class="hsrc">{html.escape(box_text(b))}</div>')
                cur["src_only"] = True
                i += 1
                continue
            cur["html"].append(block_html(b))
            i += 1
            if b["t"] == "para" and SRC_RE.match(t.strip()) and i < len(blocks) and blocks[i]["t"] == "para":
                cur["html"].append(block_html(blocks[i]))
                i += 1
            continue
        if cur is not None and cur["cls"] == "u-q" and k == "quiz":
            cur["html"].append(block_html(b))
            i += 1
            continue
        h = block_html(b)
        if b["t"] == "para" and kind(t) == "sub" or b["t"] == "heading":
            cur = {"cls": "u-t glue", "html": [h]}  # heading glued to the next block
            out.append(cur)
        elif cur is not None and "glue" in cur["cls"] and len(cur["html"]) == 1:
            cur["html"].append(h)
            cur["cls"] = "u-t"
        else:
            cur = {"cls": "u-t split", "html": [h]}
            out.append(cur)
        i += 1
    return out


# ---------------------------------------------------------------- page assembly
def mark(anchor):
    return f'<span class="anchor-mark">QQ{anchor}QQ</span>' if MARKS else ""


def section_html(sec, idx):
    k = section_kind(sec["title"])
    if "분석" in sec["title"]:
        for b in sec["blocks"]:
            if b["t"] == "para" and kind(ptext(b), b.get("num")) == "p" and re.search("[\u1100-\u11ff\u4e00-\u9fff]", ptext(b)):
                b["orig"] = True
    us = "".join(f'<div class="hu {u["cls"]}">{"".join(u["html"])}</div>' for u in units(sec))
    return (f'<section class="hsec hk-{k}" data-kind="{k}"><div class="hs-head">{mark(f"S{idx}")}'
            f'<span class="p-idx">{idx:02d}</span><h2 class="hs-title">{html.escape(sec["title"])}</h2></div>'
            f'<div class="hs-units">{us}</div></section>')


def cover(kicker, t1, t2, secs):
    groups = [("중세 국어 기본 이론", "음운 · 표기 · 체언과 조사 · 어휘 · 문법 요소"),
              ("자료 분석", "세종어제 훈민정음 · 용비어천가 · 소학언해"),
              ("문제 풀이", "부산외고 기출 · 대표 문제 · 교육청·사관학교 기출 · 해설")]
    cards = "".join(f'<div class="part-card"><div class="part-no">PART {i}</div><div class="part-name">{n}</div><div class="part-desc">{d}</div></div>'
                    for i, (n, d) in enumerate(groups, 1))
    return f"""
<section class="cover">
  <div class="cover-top"><div class="cover-school">RICH ACADEMY</div><div class="cover-rule"></div><div class="cover-author"><b>이재규T</b></div></div>
  <div class="cover-main">
    <img class="cover-logo" src="file://{ROOT}/brand/logo_beige.png" alt="RICH ACADEMY">
    <div class="cover-kicker">{html.escape(kicker)}</div>
    <h1 class="cover-title">{html.escape(t1)}<br><em>{html.escape(t2)}</em></h1>
  </div>
  <div class="parts parts3">{cards}</div>
</section>"""


KIND_LABEL = {"theory": "이론", "quiz": "문제", "expl": "해설"}


def toc(secs, pages):
    rows = "".join(
        f'<tr><td class="toc-no">{i:02d}</td><td><span class="tag tag-sm">{KIND_LABEL[section_kind(s["title"])]}</span></td>'
        f'<td class="toc-title">{html.escape(s["title"])}</td><td class="toc-pg">{pages.get(f"S{i}", "")}</td></tr>'
        for i, s in enumerate(secs, 1))
    return f'<section class="toc-page"><div class="toc-title-h">목차</div><table class="toc">{rows}</table></section>'


def build(blocks_path, kicker, t1, t2, title, pages):
    blocks = json.load(open(blocks_path, encoding="utf-8"))
    first_break = next(i for i, b in enumerate(blocks) if b["t"] == "pagebreak")
    blocks = merge_continuations(blocks[first_break + 1:])  # the source's own cover + 목차 are replaced
    secs = sections(blocks)
    body = cover(kicker, t1, t2, secs) + toc(secs, pages) + "".join(section_html(s, i) for i, s in enumerate(secs, 1))
    css = "".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in
                  ["literature-summary/render/style.css", "combined/extra.css", "textbook/textbook.css", "hwp_textbook/hwp_textbook.css", "brand/brand.css"])
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{body}</body></html>"""
    open(os.path.join(H, "summary.html"), "w", encoding="utf-8").write(out)
    return [f"S{i}" for i in range(1, len(secs) + 1)]


def find_pages(pdf, anchors):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ(S\d+)QQ", txt):
            found.setdefault(a, p)
    missing = [a for a in anchors if a not in found]
    if missing:
        sys.exit(f"anchors not found: {missing}")
    return found


if __name__ == "__main__":
    src, out_pdf, kicker, t1, t2 = sys.argv[1:6]
    title = f"{t1} {t2}"
    MARKS = True
    anchors = build(src, kicker, t1, t2, title, {})
    subprocess.run(["node", os.path.join(H, "print.js"), out_pdf], check=True)
    pages = find_pages(out_pdf, anchors)
    MARKS = False
    build(src, kicker, t1, t2, title, pages)
    subprocess.run(["node", os.path.join(H, "print.js"), out_pdf], check=True)
    print("pages:", pages)
