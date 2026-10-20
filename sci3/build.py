"""Ⅲ. 과학 평가원 기출 독서 분석서: 지문마다 (1) 원본 지문 및 문제 (2) 문제 해설 (3) 지문 분석서.

Usage: python3 build.py <out.pdf>

Exam text is re-typeset from the source HWP (data/pNN.json); the table of contents is filled in a second pass.
"""
import importlib.util, json, os, re, subprocess, sys, html

B = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(B)
TITLE = os.environ.get("BOOK_TITLE", "Ⅲ. 과학 평가원 기출 독서 분석서")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


nl = load_module("nl", os.path.join(ROOT, "nonliterature-summary/render/render.py"))
MARKS = False


def load_all():
    d = os.path.join(B, "data")
    ps = []
    for f in sorted(os.listdir(d)):
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            p = json.load(fh)
        # question numbers follow the book (001~099), whatever the data file used
        start = int(p["qrange"][:3])
        old = [q["no"] for q in p["exam"]["questions"] if "no" in q]
        ren = {o: start + i for i, o in enumerate(old)}
        for q in p["exam"]["questions"]:
            if "no" in q:
                q["no"] = ren[q["no"]]
        for a in p["answers"]:
            a["no"] = ren[a["no"]]
        ps.append(p)
    return ps


def xmd(s):
    """exam text: escape, **bold**, __underline__ (circled digits kept as text so the exam font draws them)"""
    t = html.escape(str(s or ""))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"__(.+?)__", r"<u>\1</u>", t)
    t = re.sub(r"\{\{(.+?)\}\}", r'<span class="bx">\1</span>', t)  # boxed term (네모 표시)
    t = t.replace("[3점]", '<span class="pt3">[3점]</span>')
    # 기호(ⓐ ㉠ ㉮ Ⓐ)와 바로 뒤 말은 한 줄에: 사이를 줄 바꿈 없는 공백으로
    t = re.sub(r"([㉠-㉭ⓐ-ⓩ㉮-㉻Ⓐ-Ⓩ]) ", "\\1\u00a0", t)
    t = re.sub(r"&lt;보기( \d)?&gt;", lambda m: '<span class="nw">' + m.group(0) + '</span>', t)   # ‘<보기 2>’를 끊지 않음
    # 빈칸 괄호 ‘( ㉠ )’, ‘( [가] )’는 끊지 않음
    t = re.sub(r"\((\s+)([^()\s]{1,16})(\s+)\)", lambda m: "(" + "\u00a0" * len(m.group(1)) + m.group(2) + "\u00a0" * len(m.group(3)) + ")", t)
    return t


def mark(anchor):
    return f'<span class="anchor-mark">QQ{anchor}QQ</span>' if MARKS else ""


def img(name, cls="fig"):
    return f'<img class="{cls}" src="file://{B}/img/{name}" alt="">'


def head(p, idx, part, anchor):
    return (f'{mark(anchor)}<div class="x-head"><span class="p-idx">{idx:02d}</span><span class="tag">{nl.md(p["field"])}</span>'
            f'<span class="x-q">{nl.md(p["qrange"])}</span><span class="x-title">{nl.md(p["title"])}</span>'
            f'<span class="x-exam">{nl.md(p["src"])}</span><span class="x-part">{part}</span></div>')


def passage_block(items):
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("table"):
            tb = it["table"]
            trs = "".join("<tr>" + "".join((f"<th>{xmd(c)}</th>" if i == 0 and tb.get("header") else f"<td>{xmd(c)}</td>") for c in r) + "</tr>"
                          for i, r in enumerate(tb["rows"]))
            cap = f'<div class="fig-cap">{xmd(it.get("caption"))}</div>' if it.get("caption") else ""
            out.append(f'<div class="x-figure">{cap}<table class="x-tb">{trs}</table></div>')
        elif isinstance(it, dict):
            cap = f'<div class="fig-cap">{xmd(it.get("caption"))}</div>' if it.get("caption") else ""
            out.append(f'<div class="x-figure">{img(it["img"])}{cap}</div>')
        else:
            fn = it.lstrip().startswith("*")
            out.append(f'<p class="{"x-fn" if fn else "x-p"}">{xmd(it)}</p>')
    return "".join(out)


def bogi_html(bg):
    if not bg:
        return ""
    body = img(bg["img"], "fig bg-img") if bg.get("img") else ""
    if bg.get("imgs"):  # several captioned figures in a row (A · B · C)
        body += '<div class="bg-imgs">' + "".join(
            f'<figure>{img(f["img"], "fig")}<figcaption>{xmd(f.get("caption"))}</figcaption></figure>' for f in bg["imgs"]) + "</div>"
    HANG = re.compile(r"^((?:\*\*)?(?:\([가-힣A-Za-z]\)|[ⓐ-ⓩ㉠-㉭㉮-㉻Ⓐ-Ⓩ]|[ㄱ-ㅎ]\.|\[[가-힣]+ ?\d*\]|[◦•※∘▪])(?:\*\*)?)\s+")

    def para(t):
        if re.match(r"^-.*-$|^[⇩↓⇓]$", t.strip()):
            return f'<p class="bg-p bg-c">{xmd(t)}</p>'
        m = HANG.match(t.strip())
        if m:   # 기호로 시작하는 항목: 내어쓰기(기호 다음 글자에 둘째 줄을 맞춤)
            return f'<p class="bg-p bg-hang"{fix}><span class="hl">{xmd(m.group(1))}\u00a0</span>{xmd(t.strip()[m.end():])}</p>'
        return f'<p class="bg-p"{fix}>{xmd(t)}</p>'
    # 손으로 정한 문단 자간(para_ls: {"문단 번호": "-0.05em"}) — 자동 조정에서 제외
    paras = ""
    for i, t in enumerate(bg.get("paras") or []):
        ls = (bg.get("para_ls") or {}).get(str(i))
        if ls and "|" in ls:   # "자간|띄어쓰기 폭"
            a, b = ls.split("|"); fix = f' style="letter-spacing:{a};word-spacing:{b}" data-fixed="1"'
        else:
            fix = f' style="letter-spacing:{ls}" data-fixed="1"' if ls else ""
        paras += para(t)
    if not bg.get("imgs"):
        body += paras  # text first, then tables (the usual layout)
    tbs = bg.get("tables")
    if tbs:  # several captioned tables side by side (e.g. [진리표 1] · [진리표 2])
        cells = []
        for t in tbs:
            trs = "".join("<tr>" + "".join((f"<th>{xmd(c)}</th>" if i == 0 and t.get("header") else f"<td>{xmd(c)}</td>") for c in r) + "</tr>"
                          for i, r in enumerate(t["rows"]))
            cap = f'<div class="bg-cap">{xmd(t.get("caption"))}</div>' if t.get("caption") else ""
            cells.append(f'<div>{cap}<table class="bg-tb bg-tb-c">{trs}</table></div>')
        body += f'<div class="bg-tbs">{"".join(cells)}</div>'
    tb = bg.get("table")
    if tb and tb.get("rows"):
        rows = tb["rows"]
        hdr = tb.get("header")
        trs = "".join(
            "<tr>" + "".join((f"<th>{xmd(c)}</th>" if (hdr and i == 0) else f"<td>{xmd(c)}</td>") for c in r) + "</tr>"
            for i, r in enumerate(rows))
        body += f'<table class="bg-tb">{trs}</table>'
    if bg.get("imgs"):
        body += paras  # figure row → tables → notes, as on the paper
    if bg.get("note"):
        body += f'<div class="bg-note">{xmd(bg["note"])}</div>'
    label = bg.get("label", "< 보 기 >")
    h = f'<div class="bogi-h">{html.escape(label)}</div>' if label else ""
    return f'<div class="bogi{"" if label else " plain"}">{h}{body}</div>'


def question_html(q):
    if "group_stem" in q:
        return f'<div class="xq xg"><div class="xg-stem">{xmd(q["group_stem"])}</div>{bogi_html(q.get("bogi"))}</div>'
    ct = q.get("choices_table")
    if ct and ct.get("rows"):
        rows = ct["rows"]
        trs = "".join("<tr>" + "".join((f"<th>{xmd(c)}</th>" if i == 0 and ct.get("header") else f"<td>{xmd(c)}</td>") for c in r) + "</tr>"
                      for i, r in enumerate(rows))
        chs = f'<table class="xq-ct">{trs}</table>'
    elif q.get("choices_imgs"):  # choices drawn as graphs: ① img ② img …
        chs = '<div class="xq-ci">' + "".join(
            f'<figure><figcaption>{xmd(c)}</figcaption>{img(f, "fig")}</figure>'
            for c, f in zip(q.get("choices") or "①②③④⑤", q["choices_imgs"])) + "</div>"
    else:
        chs = '<ol class="xq-ch">' + "".join(f'<li>{xmd(c)}</li>' for c in q.get("choices", [])) + "</ol>"
    cb = ' data-colbreak="1"' if q.get("colbreak") else ""   # 손 배치: 이 문항은 다음 단에서 시작
    return (f'<div class="xq"{cb}><div class="xq-stem"><span class="xq-no">{q["no"]:03d}</span><span>{xmd(q["stem"])}</span></div>'
            f'{bogi_html(q.get("bogi"))}{bogi_html(q.get("bogi2"))}{chs}</div>')


def exam_section(p, idx):
    """Raw blocks; print.js lays them out into fixed pages (passage full width, questions in two columns)."""
    ex = p["exam"]
    qs = "".join(question_html(q) for q in ex["questions"])
    return f"""
<section class="xsec xflow">
  <div class="xf-head">{head(p, idx, "원본 지문 및 문제", f"X{idx}a")}
  <div class="x-direct">[{p["qrange"].replace("~", " ~ ")}] 다음 글을 읽고 물음에 답하시오.</div></div>
  <div class="xf-pass">{passage_block(ex["passage"])}</div>
  <div class="xf-qs">{qs}</div>
</section>"""


def split_others(s):
    """'① … ② …' → one line per choice"""
    # 묶인 번호(‘①, ④, ⑤는’)는 나누지 않음: 앞이 쉼표·가운뎃점이거나 뒤에 쉼표·가운뎃점이 오는 번호에서는 줄을 나누지 않음
    parts = re.split(r"(?<![,·])(?<![,·] )\s*(?=[①②③④⑤])(?<![①②③④⑤][,·] )(?<![①②③④⑤][,·])", s or "")
    return "".join(f'<div class="an-o">{xmd(t)}</div>' for t in parts if t.strip())


def answer_section(p, idx):
    strip = "".join(f'<span class="ak"><b>{a["no"]:03d}</b>{nl.md(a["answer"])}</span>' for a in p["answers"])
    cards = "".join(
        f'<div class="an"><div class="an-h"><span class="an-no">{a["no"]:03d}번</span><span class="an-ans">정답 {nl.md(a["answer"])}</span>'
        f'<span class="an-int">출제의도 · {xmd(a.get("intent"))}</span></div>'
        f'<div class="an-e">{xmd(a["explain"])}</div>{split_others(a.get("others"))}</div>'
        for a in p["answers"])
    src = f'<div class="an-src">&lt;출전&gt; {xmd(p.get("source_note"))}</div>' if p.get("source_note") else ""
    return f"""
<section class="xsec">{head(p, idx, "문제 해설", f"X{idx}b")}
  <div class="akey"><span class="akey-h">정답</span>{strip}</div>
  {cards}{src}
</section>"""


def analysis(p, idx):
    e = {"exam": p["src"], "exam_short": p["src"]}
    h = nl.passage(e, dict(p, qrange=""), idx)
    if MARKS:
        h = h.replace('<div class="fit">', f'<div class="fit">{mark(f"X{idx}c")}', 1)
    return h


def desc(d):
    return f'<div class="part-desc">{d}</div>' if d else ""


def cover(ps):
    cards = "".join(
        f'<div class="part-card"><div class="part-no">STEP {i}</div><div class="part-name">{n}</div>{desc(d)}</div>'
        for i, (n, d) in enumerate([("원본 지문 및 문제", ""),
                                    ("문제 해설", "문항별 정답 · 출제의도 · 선지 해설"),
                                    ("지문 분석서", "핵심 한 줄 · 지문 요약 · 핵심 개념 정리 · 한눈에 비교")], 1))
    return f"""
<section class="cover">
  <div class="cover-top">
    <div class="cover-school">RICH ACADEMY</div>
    <div class="cover-rule"></div>
    <div class="cover-author"><b>이재규T</b></div>
  </div>
  <div class="cover-main">
    <img class="cover-logo" src="file://{ROOT}/brand/logo_beige.png" alt="RICH ACADEMY">
    <div class="cover-kicker">수능 · 평가원 모의평가 기출</div>
    <h1 class="cover-title">기말고사 마더텅 과학<br><em>지문 분석서</em></h1>
    <div class="cover-sub">수능 · 6월/9월 모의평가 과학 독서 {len(ps)}지문 · {sum(len(p["exam"]["questions"]) for p in ps)}문항</div>
  </div>
  <div class="parts parts3">{cards}</div>
</section>"""


def toc(ps, pages):
    rows = "".join(
        f'<tr><td class="toc-no">{i:02d}</td><td class="toc-exam">{nl.md(p["qrange"])}</td><td><span class="tag tag-sm">{nl.md(p["field"])}</span></td>'
        f'<td class="toc-title">{nl.md(p["title"])}<div class="toc-src">{nl.md(p["src"])}</div></td>'
        + "".join(f'<td class="toc-sub"><span>{lab}</span>{pages.get(f"X{i}{k}", "")}</td>' for k, lab in (("a", "지문·문제"), ("b", "해설"), ("c", "분석서")))
        + "</tr>"
        for i, p in enumerate(ps, 1))
    return f'''
<section class="toc-page"><div class="toc-title-h">목차</div>
  <div class="toc-part"><span class="part-no">Ⅲ</span><span class="toc-part-name">과학</span><span class="toc-part-pg">{pages.get("X1a", "")}</span></div>
  <table class="toc">{rows}</table>
  <div class="toc-note">지문마다 ① 원본 지문 및 문제 → ② 문제 해설 → ③ 지문 분석서 순서로 실려 있습니다.</div>
</section>'''


def build(pages):
    ps = load_all()
    body = [cover(ps), toc(ps, pages)]
    anchors = []
    for i, p in enumerate(ps, 1):
        body += [exam_section(p, i), answer_section(p, i), analysis(p, i)]
        anchors += [f"X{i}a", f"X{i}b", f"X{i}c"]
    css = "".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in
                  ["literature-summary/render/style.css", "combined/extra.css", "sci3/mock_nov.css", "brand/brand.css"])
    body = [re.sub(r"([A-Za-z]{1,3})\u20d7", r'<span class="vec">\1</span>', b) for b in body]  # vector arrow over letters
    font_dir = os.environ.get("FONT_DIR", ROOT + "/node_modules")
    css = css.replace("FONTDIR", "file://" + font_dir)
    out = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{TITLE}</title>
<link rel="stylesheet" href="file://{font_dir}/@fontsource/do-hyeon/index.css">
<style>{css}</style></head><body>{''.join(body)}</body></html>"""
    with open(os.path.join(B, "summary.html"), "w", encoding="utf-8") as f:
        f.write(out)
    return anchors


def find_pages(pdf, anchors):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        for a in re.findall(r"QQ(X\d+[abc])QQ", txt):
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
