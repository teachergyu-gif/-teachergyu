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


def add_table(title, head, rows, intro=""):
    th = "".join(f"<th>{c}</th>" for c in head)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    intro = f'<p class="hp add-intro">{intro}</p>' if intro else ""
    return (f'<div class="addbox"><div class="add-h">{title}</div>{intro}'
            f'<table class="htb addtb"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')


# Inserted right after the source paragraph that starts with the key.
ADDITIONS = {
    "• 단어의 첫머리에 둘 이상의 자음이 결합한": (
        '<div class="addbox"><div class="add-h">합용 병서와 어두 자음군</div>'
        '<p class="hp li1">• ‘합용 병서’에는 <b>‘ㅂ-’계</b>(ㅳ, ㅄ, ㅶ, ㅷ), <b>‘ㅄ-’계</b>(ㅴ, ㅵ), <b>‘ㅅ-’계</b>(ㅺ, ㅼ, ㅽ) 합용 병서가 존재했음. '
        '‘ㅅ-’계는 지금의 된소리로 발음되었다고 보는 견해가 강하고, ‘ㅂ-’계·‘ㅄ-’계는 어두 자음군으로 발음되었다는 견해가 강함. '
        '물론 학교 수업에 따라 이 둘을 구분하기도 하고, 모든 합용 병서를 통틀어 어두 자음군으로 설명하기도 하므로 <b>학교 수업을 잘 들어 봐야 함.</b></p>'
        '<p class="hp li1">• 어두 자음군으로 발음되었다는 근거 : 현대 국어 합성어에 남은 <b>‘ㅂ’의 흔적</b></p>'
        '<p class="hp li2">‧ 중세 국어 ‘ᄡᆞᆯ(쌀)’, ‘ᄡᅵ(씨)’, ‘ᄣᅢ(때)’의 ‘ㅂ’이 실제로 소리 났기 때문에, 앞말과 결합하여 합성어가 될 때 그 ‘ㅂ’이 앞 음절의 받침으로 옮겨 가 지금까지 남아 있음.</p>'
        '<p class="hp ex">예 해＋ᄡᆞᆯ → <b>햅</b>쌀, 조＋ᄡᆞᆯ → <b>좁</b>쌀, 메＋ᄡᆞᆯ → <b>멥</b>쌀, 벼＋ᄡᅵ → <b>볍</b>씨, 이＋ᄣᅢ → <b>입</b>때, 저＋ᄣᅢ → <b>접</b>때</p>'
        '<p class="hp li2">‧ ‘ㅂ’이 소리 나지 않았다면 이런 ‘ㅂ’ 받침이 생길 수 없으므로, ‘ㅂ’계·‘ㅄ’계 합용 병서의 ‘ㅂ’도 발음되었다(어두 자음군)는 증거가 됨.</p>'
        '</div>'),
    "• 각 음절의 왼쪽에 방점을 찍어": add_table(
        "방점 체계",
        ["방점", "성조", "소리의 높낮이", "예"],
        [["없음 (0개)", "평성", "낮은 소리", "활[弓]"],
         ["1개 ( ‧ )", "거성", "높은 소리", "‧갈[刀]"],
         ["2개 ( : )", "상성", "낮다가 높아지는 소리", ":돌[石]"]],
        "") + '<p class="hp note add-note">※ <b>입성</b> : 빨리 닫는 소리로, 소리의 높낮이와는 무관한 개념임.</p>'
        '<p class="hp note add-warn">※ <b>방점이 찍혀 있지 않다고 해서 성조가 없는 것이 아니라 ‘평성’</b>이다. '
        '이 부분은 학교에서 함정 선지로 많이 만들기 때문에 반드시 인지하고 있을 것.</p>',
    "※ 중성자 11개는": [  # several boxes: the unit may continue on the next page between them
        add_table(
            "양성 모음 · 음성 모음 분류 (이중 · 삼중 모음 포함)",
            ["구분", "양성 모음", "음성 모음", "중성 모음"],
            [["기본자", "ㆍ", "ㅡ", "ㅣ"],
             ["초출자", "ㅗ, ㅏ", "ㅜ, ㅓ", "–"],
             ["재출자<br><span class='tr'>(‘ㅣ’계 상향 이중 모음)</span>", "ㅛ, ㅑ", "ㅠ, ㅕ", "–"],
             ["‘ㅗ/ㅜ’계 상향 이중 모음", "ㅘ", "ㅝ", "–"],
             ["‘ㅣ’계 하향 이중 모음", "ㆎ, ㅚ, ㅐ", "ㅢ, ㅟ, ㅔ", "–"],
             ["삼중 모음", "ㅒ, ㅙ, ㆉ", "ㅖ, ㅞ, ㆌ", "–"]],
            "이중 · 삼중 모음은 <b>그 모음을 이루는 단모음의 성질</b>을 따름. 양성 모음에 ‘ㅣ’(중성)가 붙으면 양성, 음성 모음에 ‘ㅣ’가 붙으면 음성임. "
            "<span class='tr'>(예: ㅐ = ㅏ＋ㅣ → 양성, ㅔ = ㅓ＋ㅣ → 음성, ㅙ = ㅗ＋ㅏ＋ㅣ → 양성)</span>"),
        '<div class="addbox"><div class="add-h">중세 국어의 단모음 체계</div>'
        '<p class="hp add-intro">「훈민정음」 해례는 모음을 <b>혀의 오그림(설축)</b>과 <b>입 모양(구축 · 구장)</b>으로 설명함. '
        '15세기 국어의 단모음은 <b>ㆍ, ㅡ, ㅣ, ㅗ, ㅏ, ㅜ, ㅓ의 7개</b>였음.</p>'
        '<table class="htb addtb vtb"><thead><tr><th>구분</th><th>설불축</th><th>설소축</th><th>설축</th></tr></thead><tbody>'
        '<tr><td>-구축, -구장</td><td>ㅣ</td><td>ㅡ</td><td>ㆍ</td></tr>'
        '<tr><td>+구축</td><td></td><td>ㅜ</td><td>ㅗ</td></tr>'
        '<tr><td>+구장</td><td></td><td>ㅓ</td><td>ㅏ</td></tr></tbody></table>'
        '<p class="hp note">※ <b>설축(舌縮)</b> : 혀를 오그림 → 소리가 깊음 / <b>설소축(舌小縮)</b> : 혀를 조금 오그림 → 깊지도 얕지도 않음 / <b>설불축(舌不縮)</b> : 혀를 오그리지 않음 → 소리가 얕음</p>'
        '<p class="hp note">※ <b>구축(口蹙)</b> : 입을 오므림(ㅗ, ㅜ) / <b>구장(口張)</b> : 입을 벌림(ㅏ, ㅓ) → ‘ㆍ’와 ‘ㅗ’·‘ㅏ’, ‘ㅡ’와 ‘ㅜ’·‘ㅓ’는 혀의 오그림은 같고 입 모양만 다름.</p>'
        '<p class="hp li1">• 오늘날의 단모음 체계 용어로 정리하면</p>'
        '<table class="htb addtb vtb2"><thead><tr><th></th><th>전설 모음</th><th>중설 모음</th><th>후설 모음</th></tr></thead><tbody>'
        '<tr><td>고모음</td><td>ㅣ</td><td>ㅡ</td><td>ㅜ</td></tr>'
        '<tr><td>중모음</td><td></td><td>ㅓ</td><td>ㅗ</td></tr>'
        '<tr><td>저모음</td><td></td><td>ㅏ</td><td>ㆍ</td></tr></tbody></table>'
        '<p class="hp note">※ 오늘날의 기준으로 정리한 15세기 단모음 체계임. 학교나 교재에 따라 ‘중설’을 ‘후설’에 묶어 전설 / 후설로만 나누기도 하므로 수업 기준을 따를 것. '
        '현대 국어의 단모음 ‘ㅐ, ㅔ, ㅚ, ㅟ’는 15세기에는 <b>하향 이중 모음</b>이었다가 근대 국어 이후 단모음이 되었음.</p></div>',
        '<p class="hp li1">• 종성자의 제자 원리</p>'
        '<p class="hp li2">‧ 종성부용초성(終聲復用初聲) : 종성자를 위한 글자를 따로 만들지 않고 초성자를 종성자에 사용하였음. '
        '이를 <b>‘종성부용초성’</b>이라고 함.</p>'],
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
         ["‘ㅣ’ 모음", "∅ (표시하지 않음)", "불휘(불휘＋∅) [뿌리가], ᄃᆞ리(ᄃᆞ리＋∅) [다리가]"]]),
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
