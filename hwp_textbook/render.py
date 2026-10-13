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
# typos in the source file, fixed in the output
CORRECTIONS = [("⑭ ‘반설음’의 ‘불청불탁’", "⑤ ‘반설음’의 ‘불청불탁’")]
SKIP_IMG = {"img01.png"}  # the source's '국어 영역' page-header banner, not content
PASSAGE_RE = re.compile(r"^다음 글을 읽고 물음에 답하시오\.?$")
GLOSS_RE = re.compile(r"→\s*\[현대어 풀이\]")
FRAME_LABEL = re.compile(r"^\s*<\s*.+?\s*>\s*$|^\s*\[.+\]\s*$")


# ---------------------------------------------------------------- text
def run_html(r):
    t = html.escape(r["text"])
    if r.get("circle"):
        return f'<span class="circ">{t}</span>'
    if r.get("overlay"):
        return f'<span class="ov">{t}<i>{html.escape(r["overlay"])}</i></span>'
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


SUB_OK = [True]  # '○' lines are sub-headings only in theory text, never inside questions or boxes


def kind(text, num=None):
    t = text.strip()
    if num and num != "•":
        return "q"
    if num == "•":
        return "li1"
    if SRC_RE.match(t):
        return "src"
    if t.startswith("○") and SUB_OK[0]:
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
    if t and t[0] in CIRC + "⑭":
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
        extra += " orig" + (" lec" if p.get("orig") == "lec" else "")
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
    cls = "hch" if k == "ch" else k  # '.ch' is taken by the literature character cards
    return f'<p class="hp {cls}{pre}{al}{extra}">{body}</p>'


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
    saved, SUB_OK[0] = SUB_OK[0], False
    try:
        return _cell_html(paras)
    finally:
        SUB_OK[0] = saved


def _cell_html(paras):
    out = []
    for p in paras:
        if ptext(p).strip():
            out.append(para_html(p))
        for im in p.get("imgs", []):
            if im["src"] in SKIP_IMG:
                continue
            out.append(img_html(im["src"], im.get("w")))
        for t in p.get("tables", []):
            if len(t) == 1 and len(t[0]) == 1:  # one-cell table / text box inside a cell
                if not "".join(ptext(q) for q in t[0][0]["paras"]).strip() and not any(q.get("imgs") or q.get("tables") for q in t[0][0]["paras"]):
                    continue  # empty answer bubble
                out.append(f'<div class="hbox">{cell_html(t[0][0]["paras"])}</div>')
            else:
                out.append(table_html(t))
    return "".join(out)


def _cell_empty(c):
    h = cell_html(c["paras"])
    if "<img" in h or "<table" in h:
        return False
    return re.sub(r"<[^>]+>|&nbsp;|\s|\u3000", "", h) == ""


def clean_rows(rows):
    """HWP draws brackets and gaps with empty spacer rows/columns: drop every row or column made only of empty cells."""
    grid, pos, cells = {}, [], []
    for r, row in enumerate(rows):
        c = 0
        for cell in row:
            while (r, c) in grid:
                c += 1
            pos.append((r, c))
            cells.append(cell)
            for dr in range(cell["rs"]):
                for dc in range(cell["cs"]):
                    grid[(r + dr, c + dc)] = len(cells) - 1
    if not grid:
        return rows
    nr, nc = max(r for r, _ in grid) + 1, max(c for _, c in grid) + 1
    empty = [_cell_empty(c) for c in cells]

    def lines(axis):
        n, m = (nr, nc) if axis == 0 else (nc, nr)
        drop = set()
        for i in range(n):
            ks = {grid.get((i, j) if axis == 0 else (j, i)) for j in range(m)} - {None}
            span = (lambda k: cells[k]["rs"]) if axis == 0 else (lambda k: cells[k]["cs"])
            if all(empty[k] or span(k) > 1 for k in ks):
                drop.add(i)
        # a cell with content must keep at least one of its rows / columns
        for k, (r0, c0) in enumerate(pos):
            if empty[k]:
                continue
            st, ln = (r0, cells[k]["rs"]) if axis == 0 else (c0, cells[k]["cs"])
            if all(x in drop for x in range(st, st + ln)):
                drop.discard(st)
        return drop

    drop_r, drop_c = lines(0), lines(1)
    if not (drop_r or drop_c) or len(drop_r) >= nr or len(drop_c) >= nc:
        return rows
    out = {r: [] for r in range(nr) if r not in drop_r}
    for k, (r0, c0) in sorted(enumerate(pos), key=lambda kv: (kv[1][0], kv[1][1])):
        kr = [x for x in range(r0, r0 + cells[k]["rs"]) if x not in drop_r]
        kc = [x for x in range(c0, c0 + cells[k]["cs"]) if x not in drop_c]
        if not kr or not kc:
            continue
        out[kr[0]].append((c0, dict(cells[k], rs=len(kr), cs=len(kc))))
    res = [[c for _, c in sorted(v, key=lambda t: t[0])] for _, v in sorted(out.items())]
    return [r for r in res if r] or rows


def pitch_html(rows):
    """Syllables with a pitch contour drawn by thick cell borders and diagonals (방점 → 높낮이 선)."""
    trs = []
    for r in rows:
        tds = []
        for c in r:
            ln = c.get("lines") or {}
            st = ";".join(f"border-{side}:{'2px solid #1b1f27' if ln.get(k) else '0'}"
                          for k, side in (("l", "left"), ("r", "right"), ("t", "top"), ("b", "bottom")))
            for key, (y1, y2) in (("slash", (100, 0)), ("bslash", (0, 100))):  # '/' and '\\' as crisp vector lines
                if ln.get(key):
                    st += (";background:url(&quot;data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' "
                           f"preserveAspectRatio='none'><line x1='0' y1='{y1}' x2='100' y2='{y2}' stroke='%231b1f27' stroke-width='2' "
                           "vector-effect='non-scaling-stroke'/></svg>&quot;) no-repeat;background-size:100% 100%")
            txt = html.escape(re.sub(r"\s", "", "".join(ptext(p) for p in c["paras"])))
            tds.append(f'<td style="{st}">{txt}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table class="pitch">{"".join(trs)}</table>'


def table_html(rows):
    if is_frame(rows):
        lab = "".join(ptext(p) for p in rows[0][1]["paras"]).strip()
        lab = re.sub(r"\s+", " ", lab)
        return f'<div class="bogi"><div class="bogi-h">{html.escape(lab)}</div>{cell_html(rows[-1][0]["paras"])}</div>'
    if is_plain_frame(rows):
        return f'<div class="bogi plain">{cell_html(rows[1][0]["paras"])}</div>'
    cells_all = [c for r in rows for c in r]
    if (len(rows) <= 2 and any(c.get("lines") for c in cells_all)
            and all(re.fullmatch(r"[가-힣\u1100-\u11ff]{1,3}", re.sub(r"\s", "", "".join(ptext(p) for p in c["paras"]))) for c in cells_all)):
        return pitch_html(rows)
    rows = clean_rows(rows)
    if len(rows) > 1 and len(rows[0]) == 1:  # '<보 기>' title row over the rest → a 보기 frame
        lab = re.sub(r"\s+", " ", "".join(ptext(p) for p in rows[0][0]["paras"])).strip()
        if re.fullmatch(r"<\s*보\s*기\s*\d?\s*>", lab):
            return f'<div class="bogi"><div class="bogi-h">{html.escape(lab)}</div>{table_html(rows[1:])}</div>'
    if len(rows) == 1 and len(rows[0]) == 1:
        only = re.sub(r"\s+", "", "".join(ptext(p) for p in rows[0][0]["paras"]))
        if re.fullmatch(r"\[[A-Z가-하]\]", only):
            return f'<div class="amark">{only}</div>'
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


def img_html(src, w_mm):
    style = f' style="width:{w_mm}mm"' if w_mm else ""
    return f'<div class="himg"><img src="file://{H}/img/{src}"{style} alt=""></div>'


def block_html(b):
    t = b["t"]
    if t == "para":
        return para_html(b)
    if t == "table":
        return table_html(b["rows"])
    if t == "box":
        return box_html(b)
    if t == "img":
        return img_html(b["src"], b.get("w"))
    if t == "addwrap":
        return f'<div class="addbox"><div class="add-h">{html.escape(b["title"])}</div>{table_html(b["rows"])}</div>'
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
    ex_no = 0  # explanations after a 빠른 정답 table follow the question order
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
                cur = {"cls": "u-ex", "html": []}
                out.append(cur)
                if bare:
                    ex_no += 1
                    cur["html"].append(f'<div class="hex-h"><span class="hex-n">{ex_no}번</span>정답 {html.escape(t.strip())}</div>')
                    i += 1
                    continue
            cur["html"].append(block_html(b))
            i += 1
            continue
        if b["t"] == "para" and PASSAGE_RE.match(t.strip()) and k == "quiz":
            inner = []
            i += 1
            while i < len(blocks):
                nb = blocks[i]
                if nb["t"] == "para" and (nb.get("num") and nb["num"] != "•" or SRC_RE.match(ptext(nb).strip())) or is_src_box(nb) or is_section_title(nb):
                    break
                inner.append(block_html(nb))
                i += 1
            cur = {"cls": "u-q", "html": [f'<div class="hp-dir">{html.escape(t.strip())}</div><div class="hpass">{"".join(inner)}</div>'],
                   "src_only": True}  # the next numbered question joins this unit
            out.append(cur)
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
        extra = addition_for(b)
        if extra and kind(t) == "sub":  # heading with an inline example: keep heading + table together
            cur = {"cls": "u-t", "html": [h, extra]}
            out.append(cur)
            i += 1
            continue
        if isinstance(extra, list):  # several added boxes: may continue on the next page between boxes
            cur = {"cls": "u-t split", "html": [h] + extra}
            out.append(cur)
            i += 1
            continue
        if extra:  # the paragraph and the box added under it stay on the same page
            cur = {"cls": "u-t", "html": [h, extra]}
            out.append(cur)
            i += 1
            continue
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



# ---------------------------------------------------------------- teacher's additions
# Sections that continue on the same page as the previous one (no page break).
JOIN_PREV = {"중세 국어 체언과 조사"}


def add_table(title, head, rows, intro="", cls=""):
    th = "".join(f"<th>{c}</th>" for c in head)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    intro = f'<p class="hp add-intro">{intro}</p>' if intro else ""
    return (f'<div class="addbox"><div class="add-h">{title}</div>{intro}'
            f'<table class="htb addtb {cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')


def tidy_diph(out):
    """Give the source's 상향/하향 이중 모음 table even columns and breathing room."""
    k = out.find("반모음 ‘ㅣ’ 계 상향 이중 모음")
    t = out.rfind('<table class="htb">', 0, k)
    if k < 0 or t < 0:
        return out
    out = out[:t] + '<table class="htb dtb"><colgroup><col style="width:46%"><col style="width:54%"></colgroup>' + out[t + len('<table class="htb">'):]
    return out.replace("<b>ㅘ, ㅝ, </b>", "<b>ㅘ, ㅝ</b>").replace("ㆉ ㆌ</b>", "ㆉ, ㆌ</b>")


CHOICE_HEAD_RE = re.compile(r'<p class="hp p pre">((?:[^<]|</?u>){1,160})</p>((?:<p class="hp hch[^"]*">(?:[^<]|</?u>)*</p>)+)')
CHOICE_ROW_RE = re.compile(r'<p class="hp hch[^"]*">((?:[^<]|</?u>)*)</p>')
LABEL_RE = re.compile(r'[㉠-㉭ⓐ-ⓩ]|\([A-Z가-하]\)')
SPIRIT_BOX = (
    '<div class="addbox"><div class="add-h">세종어제 훈민정음 서문에 나타난 창제 정신</div>'
    '<table class="htb addtb hon2 spirit"><colgroup><col style="width:15%"><col style="width:45%"><col style="width:40%"></colgroup>'
    '<thead><tr><th>정신</th><th>근거가 되는 구절</th><th>의미</th></tr></thead><tbody>'
    '<tr><td>자주 정신</td><td>나랏 말ᄊᆞ미 中國에 달아 文字와로 서르 ᄉᆞᄆᆞᆺ디 아니ᄒᆞᆯᄊᆡ</td><td>우리말이 중국말과 다르다는 인식 → 우리말에 맞는 우리 글자가 필요함.</td></tr>'
    '<tr><td>애민 정신</td><td>어린 百姓이 니르고져 호ᇙ 배 이셔도 ᄆᆞᄎᆞᆷ내 제 ᄠᅳ들 시러 펴디 몯ᄒᆞᇙ 노미 하니라 내 이ᄅᆞᆯ 爲ᄒᆞ야 어엿비 너겨</td><td>뜻을 펴지 못하는 백성을 불쌍히 여기는 마음</td></tr>'
    '<tr><td>창제 정신<br><span class="tr">(창조 정신)</span></td><td>새로 스믈여듧 字ᄅᆞᆯ ᄆᆡᇰᄀᆞ노니</td><td>다른 문자를 빌리지 않고 새로운 글자 28자를 만듦.</td></tr>'
    '<tr><td>실용 정신</td><td>사ᄅᆞᆷ마다 ᄒᆡᅇᅧ 수ᄫᅵ 니겨 날로 ᄡᅮ메 便安킈 ᄒᆞ고져 ᄒᆞᇙ ᄯᆞᄅᆞ미니라</td><td>누구나 쉽게 익혀 날마다 편하게 쓰도록 함.</td></tr>'
    '</tbody></table></div>')
MEANING_TYPES = (
    '<div class="addbox"><div class="add-h">의미 변동의 세 가지 유형</div>'
    '<div class="mtype"><span class="mt-k">의미 확대</span><span>중세 국어 시절에 쓰이던 의미의 범위보다 현대로 오며 그 의미가 <b>확대</b>된 경우</span></div>'
    '<div class="mtype"><span class="mt-k">의미 축소</span><span>중세 국어 시절에 쓰이던 의미의 범위보다 현대로 오며 그 의미가 <b>축소</b>된 경우</span></div>'
    '<div class="mtype"><span class="mt-k">의미 이동</span><span>중세 국어 시절에 쓰이던 의미가 현대로 오며 <b>다른 의미로 바뀐</b> 경우</span></div>'
    '</div>')
BREAK_BEFORE = ["중세 국어의 주격 조사", "중세 국어의 관형격 조사", "중세 국어의 의문문", "중세 국어의 높임법", "중세 국어의 시제"]


def choice_grid(m):
    """㉠ ㉡ ㉢ column labels over ① 애 예 에 rows → an aligned grid (also two choices per line)."""
    head = re.sub(r'</?u>', '', m.group(1)).split()
    if not head or not all(LABEL_RE.fullmatch(h) for h in head):
        return m.group(0)
    lines = CHOICE_ROW_RE.findall(m.group(2))
    rows = []
    for ln in lines:
        parts = re.split('([①②③④⑤])', ln)
        cs = [[parts[i]] + [x for x in re.split(r'\s{2,}', parts[i + 1].strip()) if x] for i in range(1, len(parts) - 1, 2)]
        rows.append(cs)
    slots = max(len(r) for r in rows)
    if len(head) % slots:
        return m.group(0)
    k = len(head) // slots
    if any(len(c) != k + 1 for r in rows for c in r):
        return m.group(0)
    gap = '<td class="cg-gap"></td>'
    th = '<tr>' + gap.join('<td></td>' + ''.join(f'<td class="cg-h">{h}</td>' for h in head[j * k:(j + 1) * k]) for j in range(slots)) + '</tr>'
    trs = ''.join('<tr>' + gap.join(''.join(f'<td>{x}</td>' for x in c) for c in r) + '</tr>' for r in rows)
    return f'<table class="cgrid">{th}{trs}</table>'


PRE_P_RE = re.compile(r'<p class="hp ([a-z0-9 ]*?)pre">(.*?)</p>')
NUMS = "①②③④⑤"
LBL = r'(?:[㉠-㉭ⓐ-ⓩ]|\([가-하A-Z]\)|\[[가-하A-Z]\])'


def _plain(h):
    return re.sub(r'<[^>]+>', '', h).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _blanks(t):
    """'(   ㉠   )', '학생 :     (가)     .' → a fill-in blank of fixed width."""
    t = re.sub(r'<u>(\s*' + LBL + r'\s*)</u>', r'\1', t)
    t = re.sub(r'\(\s{2,}(' + LBL + r')\s{2,}\)', r'( <span class="blank">\1</span> )', t)
    t = re.sub(r'(?<=\S)\s{3,}(' + LBL + r')\s{3,}(?=\S|$)', r' <span class="blank">\1</span> ', t)
    t = re.sub(r'(?<=\S)\s{3,}(' + LBL + r')\s*$', r' <span class="blank">\1</span>', t)
    t = re.sub(r'^\s*(' + LBL + r')\s{3,}(?=[.。]?\s*$)', r'<span class="blank">\1</span>', t)
    return t


def _choices(line):
    """split '① a     ② b' into [('①','a'), ('②','b')]"""
    parts = re.split('([' + NUMS + '])', line)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def _cell(t):
    return re.sub(r'\s{2,}', ' ', t).strip()


def _choice_run(lines):
    opts = [_choices(l) for l in lines]
    cols = max(len(o) for o in opts)
    cells = []
    for o in opts:
        for n, t in o:
            cells.append(f'<div class="cg2"><span class="cn">{n}</span><span>{_cell(t)}</span></div>')
        cells += ['<div></div>'] * (cols - len(o))
    return f'<div class="cgrid2 c{cols}">{"".join(cells)}</div>'


def _aligned_run(cls, rows):
    """short lines laid out with space gaps → a borderless table so the columns really line up"""
    n = max(len(r) for r in rows)
    trs = []
    for r in rows:
        tds = "".join(f'<td class="{"src" if re.fullmatch(r"&lt;.*?&gt;", c) else ""}">{c}</td>' for c in r + [""] * (n - len(r)))
        trs.append(f"<tr>{tds}</tr>")
    return f'<table class="atb {cls}">{"".join(trs)}</table>'


def _ex_row(cls, t):
    """'• 설명 …        예 …' → explanation and example in two fixed columns"""
    a, b = re.split(r'\s{3,}(?=<span class="circ">예</span>|예 )', t, maxsplit=1)
    return f'<div class="exrow {cls}"><p class="hp {cls}">{a.strip()}</p><p class="hp exr">{_cell(b)}</p></div>'


EXROW_RE = re.compile(r'<p class="hp (li1)">((?:(?!</p>).)*?) (<span class="circ">예</span> (?:(?!</p>).)*)</p>')


def join_exrows(out):
    """'• 설명 … 예 …' paragraphs next to an aligned bullet/example row get the same columns."""
    for _ in range(3):
        def rep(m):
            before, after = out[max(0, m.start() - 700):m.start()], out[m.end():m.end() + 120]
            prev_ok = re.search(r'</p></div></div><div class="hu[^"]*">$', before) and '<div class="exrow li1">' in before
            next_ok = re.match(r'</div><div class="hu[^"]*"><div class="exrow li1">', after)
            if prev_ok or next_ok:
                return f'<div class="exrow li1"><p class="hp li1">{m.group(2).strip()}</p><p class="hp exr">{m.group(3)}</p></div>'
            return m.group(0)
        out = EXROW_RE.sub(rep, out)
    return out


def tidy_pre(out):
    """Space-aligned HWP lines (choices, glosses, blanks) never line up in another font: rebuild them."""
    items = []  # (start, end, cls, text)
    for m in PRE_P_RE.finditer(out):
        items.append([m.start(), m.end(), m.group(1).strip(), m.group(2)])
    res, pos, i = [], 0, 0
    while i < len(items):
        st, en, cls, t = items[i]
        res.append(out[pos:st])
        t = re.sub(r'학\s+생\s*:', '학생 :', t)
        t = _blanks(t)
        pl = _plain(t)
        # several choices on one line: gather the consecutive choice lines into one grid
        if cls.startswith("hch") and len(re.findall('[' + NUMS + ']', pl)) >= 2:
            run, j = [t], i + 1
            while j < len(items) and items[j][2].startswith("hch") and out[items[j - 1][1]:items[j][0]] == "" \
                    and len(re.findall('[' + NUMS + ']', _plain(items[j][3]))) >= 1:
                run.append(items[j][3]); j += 1
            pos = items[j - 1][1]
            # a last choice line without wide gaps (e.g. a lone '⑤ …') belongs to the same grid
            while True:
                m2 = re.match(r'<p class="hp hch">((?:(?!</p>).)*[①②③④⑤](?:(?!</p>).)*)</p>', out[pos:])
                if not m2:
                    break
                run.append(m2.group(1)); pos += m2.end()
            while j < len(items) and items[j][0] < pos:
                j += 1
            res.append(_choice_run(run)); i = j
            continue
        # bullet + example on one line
        if cls.startswith("li") and re.search(r'\s{3,}(?:<span class="circ">예</span>|예 )', t) and len(pl) < 140:
            res.append(_ex_row(cls, t)); pos = en; i += 1
            continue
        segs = [x for x in re.split(r'\s{3,}', t.strip()) if x]
        # text followed by its source '<용비어천가>': put the source at the right edge
        if len(segs) >= 2 and re.fullmatch(r'&lt;[^&]*&gt;', segs[-1].strip()):
            left = _cell(" ".join(segs[:-1]))
            res.append(f'<p class="hp {cls} with-src"><span>{left}</span><span class="src-r">{segs[-1].strip()}</span></p>'); pos = en; i += 1
            continue
        if 2 <= len(segs) <= 4 and len(pl) <= 70 and all(len(_plain(x)) <= 34 for x in segs):
            run, j = [segs], i + 1
            while j < len(items) and items[j][2] == cls and out[items[j - 1][1]:items[j][0]] == "":
                s2 = [x for x in re.split(r'\s{3,}', _blanks(items[j][3]).strip()) if x]
                if not (2 <= len(s2) <= 4 and len(_plain(items[j][3])) <= 70):
                    break
                run.append(s2); j += 1
            if len(run[0]) == 2:
                mprev = re.search(r'<p class="hp ' + re.escape(cls) + r'">((?:(?!</?p).)*?) (\([^()]*\)|\[[^\[\]]*\])</p>$', res[-1])
                if mprev and re.match(r'\s*(?:[ㄱ-ㅎ]\.|[ⓐ-ⓩ]|\([가-하]\))', _plain(mprev.group(1))) \
                        and re.match(r'\s*(?:[ㄱ-ㅎ]\.|[ⓐ-ⓩ]|\([가-하]\))', _plain(run[0][0])):
                    res[-1] = res[-1][:mprev.start()]
                    run.insert(0, [mprev.group(1), mprev.group(2)])
            res.append(_aligned_run(cls, run)); pos = items[j - 1][1]; i = j
            continue
        # a whole-line blank box '(      [가]      )'
        if re.fullmatch(r'\(\s*' + LBL + r'\s*\)', pl.strip()):
            res.append(f'<div class="blankbox">{pl.strip()[1:-1].strip()}</div>'); pos = en; i += 1
            continue
        # anything else: the gaps were only line-wrap artefacts of the original page
        res.append(f'<p class="hp {cls}">{_cell(t)}</p>'); pos = en; i += 1
    res.append(out[pos:])
    return "".join(res)


def tidy_more(out):
    out = CHOICE_HEAD_RE.sub(choice_grid, out)
    # 서술형 answer line: drop the cramped ( ) and leave room to write
    out = re.sub(r'<p class="hp ans pre">답 ?: ?\(\s*\)</p>', '<p class="hp ans ans-line">답 :</p>', out)
    out = tidy_pre(out)
    out = re.sub(r'(<p class="hp [^"]*">(?:(?!</p>).)*</p>)<div class="amark">(\[[^\]]+\])</div>',
                 r'<div class="abrk">\1<span class="abrk-l">\2</span></div>', out)
    out = out.replace('<p class="hp p">[272～273] ', '<p class="hp p">')  # stray workbook numbering
    # every 빠른 정답 table starts a new page; its explanations follow right after
    out = out.replace('<div class="hu u-key">', '<div class="hu u-key pb">')
    # a blank is already a line; drop the underline the original drew around it
    out = re.sub(r'<u>\s*(<span class="blank">[^<]*</span>)\s*(\.?)\s*(<br>)?\s*</u>', r'\1\2\3', out)
    # bullet + example rows: neighbouring single-spaced rows join the same two-column layout
    out = join_exrows(out)
    # 복습용 분석: the four founding spirits close the section
    k = out.find('세종어제 훈민정음 분석(복습용)</h2>')
    if k > 0:
        e = out.find('</div></section>', k)
        out = out[:e] + '<div class="hu u-t">' + SPIRIT_BOX + '</div>' + out[e:]
    # 어휘 의미 변동: the three types are defined before the table
    out = out.replace('중세 국어 어휘 의미 변동</h2></div><div class="hs-units">',
                      '중세 국어 어휘 의미 변동</h2></div><div class="hs-units"><div class="hu u-t">' + MEANING_TYPES + '</div>', 1)
    out = out.replace(MEANING_TYPES + '</div><div class="hu u-t split"><table class="htb">',
                      MEANING_TYPES + '</div><div class="hu u-t split"><table class="htb mvtb">', 1)
    # source quirks: an example split over two paragraphs, a note glued to the next original line
    out = out.replace('＋-아)</p></div><div class="hu u-t split"><p class="hp p">보ᅀᆞᆸ고', '＋-아)‖보ᅀᆞᆸ고')
    out = re.sub(r'‖', ' <span class="sep">|</span> ', out)
    out = re.sub(r'<p class="hp hch">(① 동국정운식 한자음 표기)\s*(?:<br>\s*)+(.*?)</p>', r'<p class="hp hch">\1</p><p class="hp p orig">\2</p>', out)
    for t in BREAK_BEFORE:
        out = out.replace(f'<div class="hu u-t"><h3 class="hsub">{t}', f'<div class="hu u-t pb"><h3 class="hsub">{t}')
    return out


# Inserted right after the source paragraph that starts with the key.
ADDITIONS = {
    "• 관형사형의 수식을 받는 명사가": [
        '<div class="addbox roomy"><div class="add-h">더 알고 있으면 좋을 중세 문법 지식</div>'
        '<p class="hp li1">• <b>(1) 차자 표기 : 한자의 음(音)과 뜻(訓)을 빌려 우리말을 적던 방법</b> (훈민정음 창제 이전)</p>'
        '<table class="htb addtb kntb"><colgroup><col style="width:13%"><col style="width:52%"><col style="width:35%"></colgroup>'
        '<thead><tr><th>종류</th><th>방법</th><th>예</th></tr></thead><tbody>'
        '<tr><td>향찰</td><td>우리말 문장 전체를 한자로 적음. 실질 형태소는 뜻(訓)으로, 형식 형태소는 음(音)으로 적는 경향(훈주음종)</td><td>향가 표기</td></tr>'
        '<tr><td>이두</td><td>한문을 <b>우리말 어순</b>으로 바꾸고 조사 · 어미를 차자로 덧붙여 적음. 주로 관청의 공문서에 쓰임.</td><td>爲去乙[ᄒᆞ거늘], 爲彌[ᄒᆞ며]</td></tr>'
        '<tr><td>구결</td><td>한문 원문은 <b>그대로 두고</b> 구절 끝에 토(조사 · 어미)를 달아 읽기 쉽게 함. 한자의 일부를 딴 약자도 씀.</td><td>天地之間 萬物之中<u>厓</u> 唯人<u>伊</u> 最貴<u>爲尼</u></td></tr>'
        '</tbody></table>'
        '<p class="hp note">※ 이두와 구결의 차이 : 이두는 어순까지 우리말로 바꾸지만, 구결은 한문 어순을 그대로 두고 토만 붙임.</p>'
        '<p class="hp li1">• <b>(2) 이영보래(以影補來) : ‘影(ㆆ)으로 來(ㄹ)를 보충한다’</b></p>'
        '<p class="hp li2">‧ 우리 한자음에서 ‘ㄹ’로 끝나는 한자(본래 중국음은 입성 ‘ㄷ’)의 받침에 ‘ㆆ’을 덧붙여 ‘ㅭ’으로 적은 동국정운식 한자음 표기 규정 '
        '→ 입성(빨리 닫는 소리)임을 나타내기 위함.</p>'
        '<p class="hp ex"><span class="circ">예</span> 不[<b>붏</b>], 佛[<b>뿛</b>], 彆[<b>볋</b>], 戌[<b>슗</b>]</p>'
        '<p class="hp li1">• <b>(3) 명사 파생 접사와 명사형 전성 어미 : 현대 국어와 달리 형태가 달라 구별이 쉬움</b></p>'
        '<table class="htb addtb kntb"><colgroup><col style="width:18%"><col style="width:17%"><col style="width:36%"><col style="width:29%"></colgroup>'
        '<thead><tr><th>구분</th><th>형태</th><th>특징</th><th>예</th></tr></thead><tbody>'
        '<tr><td>명사 파생 접사</td><td><b>-(ᄋᆞ/으)ㅁ</b><br><b>-이 / -의(-ᄋᆡ)</b></td>'
        '<td>새로운 <b>명사</b>를 만듦 → 서술어로 쓰일 수 없고, 관형어의 수식을 받음.</td>'
        '<td>거<u>름</u>(걷- ＋ -음)[걸음]<br>노<u>ᄑᆡ</u>(높- ＋ -ᄋᆡ)[높이]</td></tr>'
        '<tr><td>명사형 전성 어미</td><td><b>-옴 / -움</b><br><span class="tr">(‘-오-’＋‘-ㅁ’)</span></td>'
        '<td>품사는 그대로 <b>용언</b> → 서술어 기능을 유지하고, 부사어의 수식을 받음.</td>'
        '<td>거<u>룸</u>(걷- ＋ -움)[걸음]<br>머<u>굼</u>(먹- ＋ -움)[먹음]</td></tr>'
        '</tbody></table>'
        '<p class="hp ex"><span class="circ">예</span> ᄒᆞᆫ <b>거름</b>(명사) 나ᅀᅩ <b>거룸</b>(동사의 명사형)[한 걸음 나아가도록 걸음] / 나못 <b>노ᄑᆡ</b>(명사)[나무의 높이] ↔ <b>노피</b>(부사) ᄂᆞᄂᆞᆫ 져비[높이 나는 제비]</p>'
        '<p class="hp note">※ 현대 국어에서는 둘 다 ‘-(으)ㅁ’으로 형태가 같지만, 중세 국어에서는 <b>‘-ㅁ’이면 접사, ‘-옴 / -움’이면 어미</b>로 구별됨. '
        '부사 파생 접사는 모음 조화와 상관없이 ‘-이’만 쓰였음(노피).</p>'
        '</div>'],
    "예 아자비 쇼ᄅᆞᆯ 소아 주기": [
        '<div class="addbox"><div class="add-h">상대 높임의 종결 어미 체계</div>'
        '<table class="htb addtb hon"><colgroup><col style="width:19%"><col style="width:19%"><col style="width:27%"><col style="width:19%"><col style="width:16%"></colgroup>'
        '<thead><tr><th>등급</th><th>평서형</th><th>의문형</th><th>명령형</th><th>청유형</th></tr></thead><tbody>'
        '<tr><td>하쇼셔체 <span class="tr">(아주 높임)</span></td><td><b>-ᅌᅵ다</b> <span class="tr">호리ᅌᅵ다</span></td>'
        '<td><b>-니ᅌᅵᆺ가 / -니ᅌᅵᆺ고</b><br><span class="tr">ᄒᆞᄂᆞ니ᅌᅵᆺ가, 오시니ᅌᅵᆺ고</span></td>'
        '<td><b>-쇼셔</b> <span class="tr">아ᄅᆞ쇼셔</span></td><td><b>-사ᅌᅵ다</b></td></tr>'
        '<tr><td>하야쎠체 <span class="tr">(예사 높임)</span></td><td><b>-ㆁ다</b> <span class="tr">ᄒᆞ댕다</span></td>'
        '<td><b>-닛가</b> <span class="tr">잇ᄂᆞ닛가</span></td><td><b>-아쎠 / -야쎠</b><br><span class="tr">ᄉᆞᆯᄫᅡ쎠</span></td><td>–</td></tr>'
        '<tr><td>반말체 <span class="tr">(하라~하야쎠 사이)</span></td><td><b>-니 / -리</b> <span class="tr">가ᄂᆞ니</span></td>'
        '<td><b>-니 / -리</b> <span class="tr">ᄡᅳ시리</span></td><td><b>-고라</b> <span class="tr">ᄒᆞ고라</span></td><td>–</td></tr>'
        '<tr><td>하라체 <span class="tr">(아주 낮춤)</span></td><td><b>-다 / -라</b> <span class="tr">주그니라</span></td>'
        '<td><b>-녀 / -뇨, -ㄴ다</b><br><span class="tr">잇ᄂᆞ니여, 잇ᄂᆞ뇨, 가던다</span></td>'
        '<td><b>-라</b> <span class="tr">ᄡᅳ라</span></td><td><b>-져</b></td></tr>'
        '</tbody></table>'
        '<div class="add-sub">상대 높임 선어말 어미 : 의문문이면 ‘-잇-’, 그 밖에는 ‘-이-’</div>'
        '<table class="htb addtb hon2"><colgroup><col style="width:17%"><col style="width:21%"><col style="width:62%"></colgroup>'
        '<thead><tr><th>문장 유형</th><th>선어말 어미</th><th>예</th></tr></thead><tbody>'
        '<tr><td>평서문</td><td><b>-이- (-ᅌᅵ-)</b></td><td>니ᄅᆞ샨 야ᇰᄋᆞ로 호리<u>ᅌᅵ</u>다[말씀하신 대로 하겠습니다]</td></tr>'
        '<tr><td>의문문</td><td><b>-잇- (-ᅌᅵᆺ-)</b></td><td>世尊이 ᄀᆞᆺ봄 내시게 아니 ᄒᆞᄂᆞ니<u>ᅌᅵᆺ</u>가[합니까?], 므스므라 오시니<u>ᅌᅵᆺ</u>고[오셨습니까?]</td></tr>'
        '</tbody></table></div>',
        '<div class="addbox"><div class="add-h">조사와 특수 어휘를 통한 높임</div>'
        '<table class="htb addtb hon2 hon3"><colgroup><col style="width:13%"><col style="width:13%"><col style="width:34%"><col style="width:40%"></colgroup>'
        '<thead><tr><th>유형</th><th>구분</th><th>내용</th><th>예</th></tr></thead><tbody>'
        '<tr><td rowspan="3" class="grp">문법적 높임<br><span class="tr">(조사)</span></td><td>주격 조사</td><td>주체 높임의 주격 조사(현대의 ‘께서’)는 쓰이지 않음.</td><td>주체 높임은 ‘-시- / -샤-’로만 실현</td></tr>'
        '<tr><td>부사격 조사</td><td>높임의 대상에는 ‘ᄭᅴ(ㅅ긔), ㅅ그에’(현대의 ‘께’)</td><td>王<u>ᄭᅴ</u> 그 ᄭᅮ믈 ᄉᆞᆯᄫᅡ시ᄂᆞᆯ[왕께 그 꿈을 아뢰시니]</td></tr>'
        '<tr><td>관형격 · 호격</td><td>관형격 ‘ㅅ’(높임의 유정 명사), 호격 ‘하’</td><td>大王<u>ㅅ</u> 말ᄊᆞᆷ, 님금<u>하</u> 아ᄅᆞ쇼셔</td></tr>'
        '<tr><td rowspan="2" class="grp">어휘적 높임<br><span class="tr">(특수 어휘)</span></td><td>주체 높임</td><td>좌시다[잡수시다], 겨시다[계시다]</td><td>비론 바ᄇᆞᆯ 엇뎨 <u>좌시ᄂᆞᆫ가</u>, 舍衛國에 <u>겨실</u> 쩌긔</td></tr>'
        '<tr><td>객체 높임</td><td>ᄉᆞᆲ다[아뢰다], 뫼시다 · 뫼ᅀᆞᆸ다[모시다], 뵈다, 엳ᄌᆞᆸ다[여쭙다], 마ᄍᆞᄫᅵ[마중]</td><td>夫人ᄭᅴ <u>뫼셔</u> 오니, 王ᄭᅴ 가아 말ᄆᆡ <u>엳ᄌᆞᆸ고</u></td></tr>'
        '</tbody></table></div>'],
    "예 네 겨집 그려 가던다": (
        '<div class="addbox"><div class="add-h">의문 보조사 : 체언 뒤에 바로 붙어 의문문을 만듦</div>'
        '<p class="hp add-intro">중세 국어에서는 종결 어미뿐 아니라, <b>체언 뒤에 바로 붙는 의문 보조사</b>로도 의문문을 만들었음. '
        '종결 어미와 마찬가지로 <b>판정 의문문은 ‘가’, ‘아’</b>, <b>설명 의문문은 ‘고’, ‘오’</b>가 쓰임.</p>'
        '<table class="htb addtb qtb"><colgroup><col style="width:20%"><col style="width:16%"><col style="width:64%"></colgroup>'
        '<thead><tr><th>구분</th><th>의문 보조사</th><th>예</th></tr></thead><tbody>'
        '<tr><td>판정 의문문</td><td><b>가 / 아</b></td><td>이 ᄯᆞ리 너희 죵<u>가</u>[이 딸이 너희 종이냐?]<br>이ᄂᆞᆫ 賞<u>가</u> 罰<u>아</u>[이것은 상이냐, 벌이냐?]</td></tr>'
        '<tr><td>설명 의문문</td><td><b>고 / 오</b></td><td>얻논 藥이 므스것<u>고</u>[얻는 약이 무엇이냐?]<br>이 ᄠᅳ디 엇뎨<u>오</u>[이 뜻이 무엇이냐?]</td></tr>'
        '</tbody></table>'
        '<p class="hp note">※ ‘아’, ‘오’는 ‘ㄹ’이나 반모음 ‘ㅣ’ 뒤에서 ‘가’, ‘고’의 ‘ㄱ’이 탈락한 형태임. (예: 罰<b>아</b>, 엇뎨<b>오</b>)</p>'
        '<p class="hp note">※ 의문사(므스, 엇뎨, 어느, 누 …)가 있으면 ‘고 / 오’, 없으면 ‘가 / 아’ → 의문사의 유무로 구별하는 원리는 종결 어미와 같음.</p></div>'
        '<div class="addbox add-caution"><div class="add-h">의문문 문제 풀이 시 주의할 사항</div>'
        '<p class="hp li1">• <b>(1) ‘반드시’ 주어의 인칭을 먼저 확인할 것</b> → 2인칭인지 아닌지 따지는 습관 들이기</p>'
        '<p class="hp li2">‧ 2인칭 주어면 판정 · 설명 의문문 구분 없이 ‘-ㄴ다 / -ㄹ다’가 쓰임.</p>'
        '<p class="hp li1">• <b>(2) ‘의문사’가 무엇인지 꾸준히 눈에 익혀 놓을 것</b></p>'
        '<p class="hp li2">‧ 므스 · 므슴[무엇], 엇뎨[어찌], 어느 · 어듸[어디], 누[누구], 언제, 몇 …</p>'
        '<p class="hp li1">• <b>(3) 종결 어미인지 의문 보조사인지는 결합하는 덩어리가 용언인지 체언인지 구분할 것</b></p>'
        '<p class="hp li2">‧ 용언 어간＋<b>종결 어미</b> : 미드니ᅌᅵᆺ<u>가</u>, 잇ᄂᆞ<u>뇨</u> / 체언＋<b>의문 보조사</b> : 죵<u>가</u>, 므스것<u>고</u></p>'
        '</div>'),
    "• 단어의 첫머리에 둘 이상의 자음이 결합한": (
        '<div class="addbox"><div class="add-h">합용 병서와 어두 자음군</div>'
        '<p class="hp li1">• ‘합용 병서’에는 <b>‘ㅂ-’계</b>(ㅳ, ㅄ, ㅶ, ㅷ), <b>‘ㅄ-’계</b>(ㅴ, ㅵ), <b>‘ㅅ-’계</b>(ㅺ, ㅼ, ㅽ) 합용 병서가 존재했음. '
        '‘ㅅ-’계는 지금의 된소리로 발음되었다고 보는 견해가 강하고, ‘ㅂ-’계·‘ㅄ-’계는 어두 자음군으로 발음되었다는 견해가 강함. '
        '물론 학교 수업에 따라 이 둘을 구분하기도 하고, 모든 합용 병서를 통틀어 어두 자음군으로 설명하기도 하므로 <b>학교 수업을 잘 들어 봐야 함.</b></p>'
        '<p class="hp li1">• 어두 자음군으로 발음되었다는 근거 : 현대 국어 합성어에 남은 <b>‘ㅂ’의 흔적</b></p>'
        '<p class="hp li2">‧ 중세 국어 ‘ᄡᆞᆯ(쌀)’, ‘ᄡᅵ(씨)’, ‘ᄣᅢ(때)’의 ‘ㅂ’이 실제로 소리 났기 때문에, 앞말과 결합하여 합성어가 될 때 그 ‘ㅂ’이 앞 음절의 받침으로 옮겨 가 지금까지 남아 있음.</p>'
        '<p class="hp ex">예 해＋ᄡᆞᆯ → <b>햅</b>쌀, 조＋ᄡᆞᆯ → <b>좁</b>쌀, 메＋ᄡᆞᆯ → <b>멥</b>쌀, 벼＋ᄡᅵ → <b>볍</b>씨, 이＋ᄣᅢ → <b>입</b>때, 저＋ᄣᅢ → <b>접</b>때</p>'
        '<p class="hp li2">‧ ‘ㅂ’이 소리 나지 않았다면 이런 ‘ㅂ’ 받침이 생길 수 없음.<br>→ ‘ㅂ’계·‘ㅄ’계 합용 병서의 ‘ㅂ’도 실제로 발음되었다(어두 자음군)는 증거가 됨.</p>'
        '</div>'),
    "• 각 음절의 왼쪽에 방점을 찍어": add_table(
        "방점 체계",
        ["방점", "성조", "소리의 높낮이", "예"],
        [["없음 (0개)", "평성", "낮은 소리", "활[弓]"],
         ["1개 ( ‧ )", "거성", "높은 소리", "‧갈[刀]"],
         ["2개 ( : )", "상성", "낮다가 높아지는 소리", ":돌[石]"]],
        "") + '<p class="hp note add-note">※ <b>입성</b> : 빨리 닫는 소리로, 소리의 높낮이와는 무관한 개념임.</p>'
        '<p class="hp note add-warn">※ <b>방점이 찍혀 있지 않다고 해서 성조가 없는 것이 아니라 ‘평성’</b>이다.<br>'
        '이 부분은 학교에서 함정 선지로 많이 만들기 때문에 반드시 인지하고 있을 것.</p>',
    "※ 중성자 11개는": [  # several boxes: the unit may continue on the next page between them
        add_table(
            "양성 모음 · 음성 모음 분류 (이중 · 삼중 모음 포함)",
            ["구분", "양성 모음", "음성 모음", "중성 모음"],
            [["기본자", '<span class="ar">ㆍ</span>', "ㅡ", "ㅣ"],
             ["초출자", "ㅗ, ㅏ", "ㅜ, ㅓ", "–"],
             ["재출자<br><span class='tr'>(‘ㅣ’계 상향 이중 모음)</span>", "ㅛ, ㅑ", "ㅠ, ㅕ", "–"],
             ["‘ㅗ/ㅜ’계 상향 이중 모음", "ㅘ", "ㅝ", "–"],
             ["‘ㅣ’계 하향 이중 모음", "ㆎ, ㅚ, ㅐ", "ㅢ, ㅟ, ㅔ", "–"],
             ["삼중 모음", "ㅒ, ㅙ, ㆉ", "ㅖ, ㅞ, ㆌ", "–"]],
            "이중 · 삼중 모음은 <b>그 모음을 이루는 단모음의 성질</b>을 따름. 양성 모음에 ‘ㅣ’(중성)가 붙으면 양성, 음성 모음에 ‘ㅣ’가 붙으면 음성임."
            "</p><p class='hp add-ex'>예  ㅐ = ㅏ＋ㅣ → 양성  /  ㅔ = ㅓ＋ㅣ → 음성  /  ㅙ = ㅗ＋ㅏ＋ㅣ → 양성", "vtb3"),
        '<div class="addbox"><div class="add-h">중세 국어의 단모음 체계</div>'
        '<p class="hp add-intro">「훈민정음」 해례는 모음을 <b>혀의 오그림(설축)</b>과 <b>입 모양(구축 · 구장)</b>으로 설명함. '
        '15세기 국어의 단모음은 <b>ㆍ, ㅡ, ㅣ, ㅗ, ㅏ, ㅜ, ㅓ의 7개</b>였음.</p>'
        '<table class="htb addtb vtb"><colgroup><col style="width:28%"><col style="width:24%"><col style="width:24%"><col style="width:24%"></colgroup>'
        '<thead><tr><th>구분</th><th>설불축</th><th>설소축</th><th>설축</th></tr></thead><tbody>'
        '<tr><td>-구축, -구장</td><td>ㅣ</td><td>ㅡ</td><td><span class="ar">ㆍ</span></td></tr>'
        '<tr><td>+구축</td><td></td><td>ㅜ</td><td>ㅗ</td></tr>'
        '<tr><td>+구장</td><td></td><td>ㅓ</td><td>ㅏ</td></tr></tbody></table>'
        '<div class="vnote"><div class="vnote-h">※ 용어 정리</div><div class="vgrid">'
        '<b>설축(舌縮)</b><span>혀를 오그림 → 소리가 깊음</span>'
        '<b>구축(口蹙)</b><span>입을 오므림 (ㅗ, ㅜ)</span>'
        '<b>설소축(舌小縮)</b><span>혀를 조금 오그림 → 소리가 깊지도 얕지도 않음</span>'
        '<b>구장(口張)</b><span>입을 벌림 (ㅏ, ㅓ)</span>'
        '<b>설불축(舌不縮)</b><span>혀를 오그리지 않음 → 소리가 얕음</span>'
        '<i></i><i></i></div>'
        '<p class="vnote-f">→ <b>( <span class="ar">ㆍ</span>, ㅗ, ㅏ )</b>와 <b>( ㅡ, ㅜ, ㅓ )</b>는 각각 혀의 오그림은 같고 입 모양만 다름.</p></div>'
        '<p class="hp li1">• 오늘날의 단모음 체계 용어로 정리하면</p>'
        '<table class="htb addtb vtb2"><thead><tr><th></th><th>전설 모음</th><th>중설 모음</th><th>후설 모음</th></tr></thead><tbody>'
        '<tr><td>고모음</td><td>ㅣ</td><td>ㅡ</td><td>ㅜ</td></tr>'
        '<tr><td>중모음</td><td></td><td>ㅓ</td><td>ㅗ</td></tr>'
        '<tr><td>저모음</td><td></td><td>ㅏ</td><td><span class="ar">ㆍ</span></td></tr></tbody></table>'
        '<p class="hp note">※ 오늘날의 기준으로 정리한 15세기 단모음 체계임. 학교나 교재에 따라 ‘중설’을 ‘후설’에 묶어 전설 / 후설로만 나누기도 하므로 수업 기준을 따를 것. '
        '현대 국어의 단모음 ‘ㅐ, ㅔ, ㅚ, ㅟ’는 15세기에는 <b>하향 이중 모음</b>이었다가 근대 국어 이후 단모음이 되었음.</p></div>',
        '<p class="hp li1">• 종성자의 제자 원리</p>'
        '<p class="hp li2">‧ 종성부용초성(終聲復用初聲) : 종성자를 위한 글자를 따로 만들지 않고,<br>'
        '초성자를 종성자에 그대로 사용하였음. 이를 <b>‘종성부용초성’</b>이라고 함.</p>'],
    "예 암ㅎ＋ᄃᆞᆰ": add_table(
        "‘ㅎ’ 종성 체언의 실현 양상",
        ["뒤따르는 조사", "‘ㅎ’ 종성 체언의 실현 양상", "예"],
        [["모음으로 시작하는 조사", "‘ㅎ’은 뒤따르는 모음에 이어 적는다.", "<b>ᄯᅡ히</b>(ᄯᅡᇂ＋이) 즐어늘<br><span class='tr'>(땅이 질거늘)</span>"],
         ["‘ㄱ, ㄷ’으로 시작하는 조사", "‘ㅎ’은 뒤따르는 ‘ㄱ’, ‘ㄷ’과 어울려 ‘ㅋ’, ‘ㅌ’으로 나타난다.", "<b>ᄯᅡ토</b>(ᄯᅡᇂ＋도) 뮈더니<br><span class='tr'>(땅도 움직이더니)</span>"],
         ["관형격 조사 ‘ㅅ’", "‘ㅎ’은 나타나지 않는다.", "다ᄅᆞᆫ <b>ᄯᅡᆺ</b>(ᄯᅡᇂ＋ㅅ) 風俗은<br><span class='tr'>(다른 땅의 풍속은)</span>"]],
        "중세 국어 체언 중에는 ‘ㅎ’을 끝소리로 가진 것들이 있다. 이러한 체언을 ‘ㅎ’ 종성 체언이라고 하는데, 조사가 뒤따를 경우에 다음과 같이 나타난다."),
    "※ 근대 국어에서부터 주격 조사": add_table(
        "한눈에 보기 · 주격 조사",
        ["앞 체언의 끝소리", "형태", "예"],
        [["자음", "이", "ᄉᆡ미(ᄉᆡᆷ＋이) [샘이]"],
         ["‘ㅣ’ 이외의 모음", "ㅣ", "부톄(부텨＋ㅣ) [부처가]"],
         ["‘ㅣ’ 모음", "∅ (표시하지 않음)", "불휘(불휘＋∅) [뿌리가], ᄃᆞ리(ᄃᆞ리＋∅) [다리가]"]]) +
        '<div class="addbox"><div class="add-h">주격 조사 주의할 사항</div>'
        '<p class="hp li1">• <b>(1) 이어 적기에 속지 말 것</b><br>'
        '중세 국어는 ‘이어 적기(연철)’ 경향이 강해서, 주격 조사 ‘이’가 쓰였더라도 앞말의 받침이 뒤로 넘어가 적힘. '
        '그래서 자료 속에서는 주격 조사가 ‘ㅣ’인 것처럼 오해하기 쉬우므로, <b>항상 형태소를 분석하여 ‘체언＋주격 조사’로 나눈 뒤</b> 주격 조사의 종류를 파악할 것.</p>'
        '<p class="hp ex"><span class="circ">예</span> ᄉᆡ미 → ᄉᆡᆷ＋<b>이</b> (‘ㅣ’가 아니라 ‘이’), 사ᄅᆞ미 → 사ᄅᆞᆷ＋<b>이</b></p>'
        '<p class="hp li1">• <b>(2) ‘ㅣ’ 모음 = 단모음 ‘ㅣ’ ＋ 반모음 ‘ㅣ’</b><br>'
        '‘ㅣ’ 모음으로 끝난다는 것은 단모음 ‘ㅣ’와 반모음 ‘ㅣ’를 모두 포함하는 말임. 따라서 <b>반모음 ‘ㅣ’계 하향 이중 모음</b>으로 끝날 때에도 '
        '‘ㅣ’ 모음으로 끝난 것이므로 주격 조사를 아무것도 표기하지 않음(영형태, ∅).</p>'
        '<p class="hp ex"><span class="circ">예</span> 불휘(불휘＋∅) : ‘ㅟ’는 단모음 ‘ㅜ’＋반모음 ‘ㅣ’로 이루어진 하향 이중 모음 → 주격 조사를 표기하지 않음.</p>'
        '</div>',
    "○ 중세 국어의 목적격 조사": add_table(
        "한눈에 보기 · 목적격 조사",
        ["앞 체언의 모음", "자음으로 끝날 때", "모음으로 끝날 때", "예"],
        [["양성 모음", "ᄋᆞᆯ", "ᄅᆞᆯ", "ᄆᆞᅀᆞᄆᆞᆯ(ᄆᆞᅀᆞᆷ＋ᄋᆞᆯ)"],
         ["음성 모음", "을", "를", "누ᇇ므를(누ᇇ믈＋을)"]]),
    "• 무정 명사일 경우에는 관형격 조사로": add_table(
        "한눈에 보기 · 관형격 조사",
        ["앞 체언", "형태", "예"],
        [["유정 명사 · 양성 모음", "ᄋᆡ", "ᄂᆞᄆᆡ(ᄂᆞᆷ＋ᄋᆡ) ᄠᅳᆮ [남의 뜻]"],
         ["유정 명사 · 음성 모음", "의", "거부븨(거붑＋의) 털 [거북의 털]"],
         ["높임의 유정 명사", "ㅅ", "大王ㅅ(대왕＋ㅅ) 말ᄊᆞᆷ [대왕의 말씀]"],
         ["무정 명사", "ㅅ", "나못(나모＋ㅅ) 여름 [나무의 열매]"]]),
    "• 앞 체언의 모음이 ‘ㅣ’일 경우에는 부사격 조사로": add_table(
        "한눈에 보기 · 부사격 조사",
        ["앞 체언의 모음", "형태", "예"],
        [["양성 모음", "애", "바ᄅᆞ래(바ᄅᆞᆯ＋애) 가ᄂᆞ니 [바다에 가느니]"],
         ["음성 모음", "에", "그르세(그릇＋에) 담아 [그릇에 담아]"],
         ["‘ㅣ’", "예", "萬里예(만리＋예) 녀 가 [만리에 가서]"]]),
}


def addition_for(b):
    if b["t"] != "para":
        return None
    t = ptext(b).strip()
    return next((h for k, h in ADDITIONS.items() if t.startswith(k)), None)


# ---------------------------------------------------------------- page assembly
def mark(anchor):
    return f'<span class="anchor-mark">QQ{anchor}QQ</span>' if MARKS else ""


def section_html(sec, idx):
    k = section_kind(sec["title"])
    SUB_OK[0] = k == "theory"
    if "분석" in sec["title"]:
        for b in sec["blocks"]:
            if b["t"] == "para" and kind(ptext(b), b.get("num")) == "p" and re.search("[\u1100-\u11ff\u4e00-\u9fff]", ptext(b)):
                b["orig"] = "lec" if "강의용" in sec["title"] else True
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
    for b in blocks:
        if b["t"] == "para" and b["runs"]:
            for old, new in CORRECTIONS:
                if old in ptext(b):
                    joined = ptext(b).replace(old, new)
                    b["runs"] = [dict(b["runs"][0], text=joined)]
    # teacher's edits on the source text
    for b in blocks:
        if b["t"] == "para":
            for i, r in enumerate(b["runs"]):
                if "만을 사용하였으며, 종성에서" in r["text"]:
                    a, z = r["text"].split("만을 사용하였으며,", 1)
                    b["runs"][i:i + 1] = [dict(r, text=a + "만을 사용하였으며("), dict(r, text="8종성법", b=True), dict(r, text="),") , dict(r, text=z)]
                    break
    # '음운 소실 순서' moves up, right under the line about consonants that no longer exist
    k = next(i for i, b in enumerate(blocks) if b["t"] == "para" and ptext(b).strip().startswith("○ 음운 소실 순서"))
    moved = {"t": "addwrap", "title": "음운의 소실 순서", "rows": blocks[k + 1]["rows"]}
    del blocks[k:k + 2]
    j = next(i for i, b in enumerate(blocks) if b["t"] == "para" and ptext(b).strip().startswith("• 현대 국어에 없는 자음"))
    blocks.insert(j + 1, moved)
    first_break = next(i for i, b in enumerate(blocks) if b["t"] == "pagebreak")
    blocks = merge_continuations(blocks[first_break + 1:])  # the source's own cover + 목차 are replaced
    secs = sections(blocks)
    parts = []
    for i, sec in enumerate(secs, 1):
        h = section_html(sec, i)
        if sec["title"] in JOIN_PREV and parts:
            inner = h[h.index('<div class="hs-units">') + len('<div class="hs-units">'):h.rindex("</div></section>")]
            head = (f'<div class="hu u-t glue hs-inline">{mark(f"S{i}")}<span class="p-idx">{i:02d}</span>'
                    f'<h2 class="hs-title">{html.escape(sec["title"])}</h2></div>')
            parts[-1] = parts[-1][:parts[-1].rindex("</div></section>")] + head + inner + "</div></section>"
        else:
            parts.append(h)
    body = cover(kicker, t1, t2, secs) + toc(secs, pages) + "".join(parts)
    css = "".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in
                  ["literature-summary/render/style.css", "combined/extra.css", "textbook/textbook.css", "hwp_textbook/hwp_textbook.css", "brand/brand.css"])
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{body}</body></html>"""
    out = tidy_more(tidy_diph(out))
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
