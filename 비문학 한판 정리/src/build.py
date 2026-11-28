"""비문학 한판 정리(학생 배부용) PDF·DOCX 만들기.
data/*.txt(정리 원문을 구조 표시만 붙여 옮긴 것) → HTML → Chromium 인쇄 → 머리말·꼬리말 덧입힘 → PDF
같은 데이터로 DOCX(편집용 원본)도 만든다.
사용: NODE_PATH=/opt/node22/lib/node_modules python3 build.py data/busanwoe.txt data/kukje.txt

데이터 표시
  @meta key 값 / @section 단원 / @passage 제목 | 목차 제목 / @sum ▶ 한 줄 요약 / @info ▶ 기타 안내
  @part (가) 제목 / @h 소제목 / - 항목, '  - ' 하위 항목 / 1. 번호 목록 / | 표 | 행 |(첫 행 = 머리)
  @box 제목 … @endbox(테두리 상자) / 그 밖의 줄 = 문단
"""
import os, re, sys, json, html, subprocess, tempfile
from pypdf import PdfReader, PdfWriter

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(H)

BODY_FONT = '"NanumMyeongjo","Noto Serif CJK KR",serif'
HEAD_FONT = '"NanumSquare","NanumBarunGothic","Noto Sans CJK KR",sans-serif'
TABLE_FONT = '"NanumBarunGothic","Noto Sans CJK KR",sans-serif'
# 서식(요청서 2번 빈칸을 이 값으로 정함)
MARGIN = dict(top=24, bottom=20, side=18)          # mm (머리말·꼬리말 자리 포함)
SIZE = dict(title=17, part=13.5, sub=12, body=10.5, table=9.5)   # pt
LINE = 165                                         # %


def parse(path):
    meta, items = {}, []
    cur = None
    box = None
    for raw in open(path, encoding='utf8').read().split('\n'):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith('@meta '):
            _, k, v = line.split(' ', 2); meta[k] = v; continue
        if line.startswith('@section '):
            section = line[9:].strip(); continue
        if line.startswith('@passage '):
            t, toc = [x.strip() for x in line[9:].split('|')]
            cur = {'section': section, 'title': t, 'toc': toc, 'sum': None, 'blocks': []}
            items.append(cur); continue
        if line.startswith('@sum '):
            cur['sum'] = line[5:].strip(); continue
        tgt = box['blocks'] if box is not None else cur['blocks']
        if line.startswith('@box '):
            box = {'type': 'box', 'title': line[5:].strip(), 'blocks': []}; cur['blocks'].append(box); continue
        if line.strip() == '@endbox':
            box = None; continue
        if line.startswith('@info '):
            tgt.append({'type': 'info', 'text': line[6:].strip()}); continue
        if line.startswith('@part '):
            tgt.append({'type': 'part', 'text': line[6:].strip()}); continue
        if line.startswith('@h '):
            tgt.append({'type': 'h', 'text': line[3:].strip()}); continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if tgt and tgt[-1]['type'] == 'table':
                tgt[-1]['rows'].append(cells)
            else:
                tgt.append({'type': 'table', 'rows': [cells]})
            continue
        m = re.match(r'^(\s*)- (.*)$', line)
        if m:
            lvl = 1 if m.group(1) else 0
            if lvl == 0:
                if not (tgt and tgt[-1]['type'] == 'ul'):
                    tgt.append({'type': 'ul', 'items': []})
                tgt[-1]['items'].append({'text': m.group(2), 'sub': []})
            else:
                tgt[-1]['items'][-1]['sub'].append(m.group(2))
            continue
        m = re.match(r'^1\. (.*)$', line)
        if m:
            if not (tgt and tgt[-1]['type'] == 'ol'):
                tgt.append({'type': 'ol', 'items': []})
            tgt[-1]['items'].append(m.group(1)); continue
        tgt.append({'type': 'p', 'text': line.strip()})
    return meta, items


def esc(t):
    return html.escape(t, quote=False)


def label(t):
    """‘용어: 설명’ 꼴 항목은 용어를 굵게(정리 원문에서 굵게 쓴 용어)"""
    m = re.match(r'^([^:：]{1,28}?):\s(.*)$', t)
    if m and not re.search(r'[.。!?]', m.group(1)):
        return f'<b>{esc(m.group(1))}:</b> {esc(m.group(2))}'
    return esc(t)


def table_html(rows):
    head, body = rows[0], rows[1:]
    rowlab = head[0] == '' or len(head) > 2 and all(len(r[0]) <= 18 for r in body)
    ncol = len(head)
    h = '<tr>' + ''.join(f'<th>{esc(c)}</th>' for c in head) + '</tr>'
    b = ''
    for r in body:
        r = r + [''] * (ncol - len(r))
        b += '<tr>' + ''.join(f'<td class="{"rl" if (j == 0 and rowlab) else ""}">{esc(c)}</td>' for j, c in enumerate(r)) + '</tr>'
    return f'<table class="t{" w2" if ncol == 2 else ""}"><thead>{h}</thead><tbody>{b}</tbody></table>'


def blocks_html(blocks):
    out = []
    for b in blocks:
        t = b['type']
        if t == 'info':
            out.append(f'<p class="info">{label(b["text"])}</p>')
        elif t == 'part':
            out.append(f'<h2 class="part">{esc(b["text"])}</h2>')
        elif t == 'h':
            out.append(f'<h3 class="sub">{esc(b["text"])}</h3>')
        elif t == 'p':
            out.append(f'<p class="{"star" if b["text"].startswith("★") else "para"}">{label(b["text"]) if not b["text"].startswith("★") else esc(b["text"])}</p>')
        elif t == 'ul':
            lis = ''
            for it in b['items']:
                sub = ''.join(f'<li>{label(s)}</li>' for s in it['sub'])
                lis += f'<li>{label(it["text"])}' + (f'<ul class="l2">{sub}</ul>' if sub else '') + '</li>'
            out.append(f'<ul class="l1">{lis}</ul>')
        elif t == 'ol':
            out.append('<ol class="num">' + ''.join(f'<li>{label(x)}</li>' for x in b['items']) + '</ol>')
        elif t == 'table':
            out.append(table_html(b['rows']))
        elif t == 'box':
            out.append(f'<div class="box"><div class="bt">{esc(b["title"])}</div>{blocks_html(b["blocks"])}</div>')
    return ''.join(out)


CSS = f'''
@page{{size:A4;margin:{MARGIN["top"]}mm {MARGIN["side"]}mm {MARGIN["bottom"]}mm}}
html,body{{margin:0;padding:0}}
body{{font-family:{BODY_FONT};font-size:{SIZE["body"]}pt;line-height:{LINE}%;color:#000;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.pg{{break-before:page}}
.cover{{height:253mm;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;font-family:{HEAD_FONT}}}
.cover .sc{{font-size:15pt;font-weight:700;letter-spacing:1pt;border-bottom:1.2pt solid #000;padding-bottom:2mm}}
.cover .tt{{font-size:27pt;font-weight:800;line-height:1.35;margin:14mm 0 6mm;word-break:keep-all}}
.cover .ex{{font-size:14pt;border:1pt solid #000;padding:1.5mm 6mm}}
.cover .ac{{margin-top:auto;font-size:13pt;font-weight:700;letter-spacing:.5pt}}
.toc h1{{font-family:{HEAD_FONT};font-size:{SIZE["title"]}pt;font-weight:800;margin:0 0 7mm;padding-bottom:2mm;border-bottom:1.5pt solid #000}}
.toc .grp{{font-family:{HEAD_FONT};font-weight:700;font-size:11.5pt;margin:6mm 0 2mm;padding:1mm 2.5mm;background:#e6e6e6}}
.toc .row{{display:flex;align-items:baseline;font-size:11pt;margin:0 0 3.2mm 3mm}}
.toc .row .d{{flex:1;border-bottom:.8pt dotted #000;margin:0 2mm;transform:translateY(-1mm)}}
.toc .row .p{{font-family:{HEAD_FONT};font-weight:700;min-width:8mm;text-align:right}}
.kick{{font-family:{HEAD_FONT};font-size:9.5pt;font-weight:700;letter-spacing:.3pt;margin:0 0 1mm}}
h1.ttl{{font-family:{HEAD_FONT};font-size:{SIZE["title"]}pt;font-weight:800;line-height:1.35;margin:0 0 4mm;padding-bottom:2mm;border-bottom:1.5pt solid #000;word-break:keep-all}}
.sum{{background:#e4e4e4;border-left:3pt solid #000;padding:2.5mm 4mm;margin:0 0 3mm;font-family:{HEAD_FONT};font-weight:700;font-size:10.5pt;line-height:155%;break-inside:avoid}}
p{{margin:0 0 1.6mm}}
p.info{{margin:0 0 3mm;padding-left:1mm}}
p.star{{margin:1.5mm 0 2mm;font-weight:700}}
h2.part{{font-family:{HEAD_FONT};font-size:{SIZE["part"]}pt;font-weight:800;margin:6mm 0 2.5mm;padding:1.2mm 3mm;border:1.2pt solid #000;background:#f0f0f0;break-after:avoid;break-inside:avoid}}
h3.sub{{font-family:{HEAD_FONT};font-size:{SIZE["sub"]}pt;font-weight:700;margin:4.5mm 0 1.8mm;padding-bottom:.8mm;border-bottom:.6pt solid #000;break-after:avoid;break-inside:avoid}}
ul.l1,ol.num{{margin:0 0 2mm;padding-left:5.5mm}}
ul.l1>li{{list-style:none;position:relative;margin:0 0 1.2mm;break-inside:avoid}}
ul.l1>li:before{{content:"•";position:absolute;left:-4mm}}
ul.l2{{margin:.8mm 0 0;padding-left:5mm}}
ul.l2>li{{list-style:none;position:relative;margin:0 0 .8mm}}
ul.l2>li:before{{content:"–";position:absolute;left:-4mm}}
ol.num{{break-inside:avoid;padding-left:7mm}}
ol.num>li{{margin:0 0 1.2mm;padding-left:1mm}}
table.t{{width:100%;border-collapse:collapse;margin:1.5mm 0 3mm;font-family:{TABLE_FONT};font-size:{SIZE["table"]}pt;line-height:145%;break-inside:avoid}}
table.t th,table.t td{{border:.7pt solid #000;padding:1.4mm 2mm;vertical-align:middle;word-break:keep-all}}
table.t th{{background:#d9d9d9;font-weight:700;text-align:center}}
table.t td.rl{{background:#f0f0f0;font-weight:700;text-align:center}}
table.t tr{{break-inside:avoid}}
.box{{border:1.3pt solid #000;padding:2.5mm 4mm 1.5mm;margin:5mm 0 3mm;break-inside:avoid}}
.box .bt{{font-family:{HEAD_FONT};font-weight:800;font-size:{SIZE["sub"]}pt;margin:0 0 2mm}}
.box table.t{{margin:1mm 0 2mm}}
b{{font-weight:700}}
'''


def build_html(meta, items, pages=None):
    pages = pages or {}
    body = [f'<section class="cover"><div class="sc">{esc(meta["school"])}</div><div class="tt">{"<br>".join(esc(x) for x in meta.get("cover", meta["title"]).split("|"))}</div>'
            f'<div class="ex">{esc(meta["exam"])}</div><div class="ac">리치아카데미 이재규T</div></section>']
    toc = ['<section class="toc pg"><h1>목차</h1>']
    last = None
    for k, it in enumerate(items):
        if it['section'] != last:
            toc.append(f'<div class="grp">{esc(it["section"])}</div>'); last = it['section']
        toc.append(f'<div class="row"><span>{esc(it["toc"])}</span><span class="d"></span><span class="p">{pages.get(k, "")}</span></div>')
    toc.append('</section>')
    body += toc
    for k, it in enumerate(items):
        kick = '' if it['section'] == it['title'] else f'<div class="kick">{esc(it["section"])}</div>'
        s = f'<div class="sum">{esc(it["sum"])}</div>' if it['sum'] else ''
        body.append(f'<section class="pg psg" data-k="{k}">{kick}<h1 class="ttl">{esc(it["title"])}</h1>{s}{blocks_html(it["blocks"])}</section>')
    css = CSS
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(body)}</body></html>'


PRINT_JS = r'''
const { chromium } = require('playwright');
(async () => {
  const [,, inp, out] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + inp, { waitUntil: 'load' }); await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
  await b.close();
})();
'''


def chromium_pdf(html_text, out, tmp):
    hp = os.path.join(tmp, 'x.html'); open(hp, 'w').write(html_text)
    js = os.path.join(tmp, 'p.js'); open(js, 'w').write(PRINT_JS)
    subprocess.run(['node', js, hp, out], check=True)


def overlay_html(meta, n):
    """머리말(왼쪽: 학교·학년 + 자료 제목 / 오른쪽: 시험명), 꼬리말(왼쪽: RICH ACADEMY 이재규T / 가운데: 쪽 번호). 표지에는 넣지 않음"""
    pages = []
    for i in range(1, n + 1):
        if i == 1:
            pages.append('<div class="pp"></div>'); continue
        pages.append(f'<div class="pp"><div class="hd"><span>{esc(meta["school"])} | {esc(meta["title"])}</span><span>{esc(meta["exam"])}</span></div>'
                     f'<div class="ft"><span class="l">RICH ACADEMY 이재규T</span><span class="c">{i}</span></div></div>')
    css = (f'@page{{size:A4;margin:0}}html,body{{margin:0}}.pp{{width:210mm;height:297mm;position:relative;break-after:page;font-family:{HEAD_FONT}}}'
           f'.hd{{position:absolute;left:{MARGIN["side"]}mm;right:{MARGIN["side"]}mm;top:10mm;display:flex;justify-content:space-between;font-size:8.5pt;padding-bottom:1.2mm;border-bottom:.6pt solid #000}}'
           f'.ft{{position:absolute;left:{MARGIN["side"]}mm;right:{MARGIN["side"]}mm;bottom:9mm;font-size:8.5pt;height:5mm}}'
           '.ft .l{position:absolute;left:0;font-weight:700;letter-spacing:.3pt}.ft .c{position:absolute;left:0;right:0;text-align:center;font-weight:700;font-size:9.5pt}')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(pages)}</body></html>'


def make_pdf(meta, items, out_pdf):
    with tempfile.TemporaryDirectory() as tmp:
        # 지문 시작 쪽 찾기: 조판한 PDF에서 지문 제목이 처음 나오는 쪽(목차 쪽 번호가 바뀌지 않을 때까지 되풀이)
        pages = {}
        for _ in range(2):
            chromium_pdf(build_html(meta, items, pages), f'{tmp}/b.pdf', tmp)
            r = PdfReader(f'{tmp}/b.pdf')
            texts = [re.sub(r'[\s\x01]+', '', p.extract_text() or '') for p in r.pages]
            new = {}
            for k, it in enumerate(items):
                key = re.sub(r'\s+', '', it['title'])[:18]
                new[k] = next(i + 1 for i in range(2, len(texts)) if key in texts[i] and all(i + 1 > v for v in new.values()))
            if new == pages:
                break
            pages = new
        chromium_pdf(build_html(meta, items, pages), f'{tmp}/b.pdf', tmp)
        n = len(PdfReader(f'{tmp}/b.pdf').pages)
        chromium_pdf(overlay_html(meta, n), f'{tmp}/o.pdf', tmp)
        base, ov = PdfReader(f'{tmp}/b.pdf'), PdfReader(f'{tmp}/o.pdf')
        w = PdfWriter()
        for p, o in zip(base.pages, ov.pages):
            p.merge_page(o); w.add_page(p)
        w.write(out_pdf)
        return pages, n


def make_docx(meta, items, pages, out_docx):
    from docx import Document
    from docx.shared import Pt, Mm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    BF, HF, TF = '나눔명조', '나눔스퀘어', '나눔바른고딕'
    d = Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(MARGIN['top']), Mm(MARGIN['bottom'])
    sec.left_margin = sec.right_margin = Mm(MARGIN['side'])
    sec.header_distance, sec.footer_distance = Mm(10), Mm(9)
    sec.different_first_page_header_footer = True

    def font(run, name, size, bold=False):
        run.font.name = name; run.font.size = Pt(size); run.font.bold = bold
        run._element.rPr.rFonts.set(qn('w:eastAsia'), name)

    st = d.styles['Normal']; st.font.name = BF; st.font.size = Pt(SIZE['body'])
    st.element.rPr.rFonts.set(qn('w:eastAsia'), BF)
    st.paragraph_format.line_spacing = LINE / 100; st.paragraph_format.space_after = Pt(2)

    def shade(el, color):
        tcPr = el.get_or_add_tcPr(); s = OxmlElement('w:shd')
        s.set(qn('w:val'), 'clear'); s.set(qn('w:color'), 'auto'); s.set(qn('w:fill'), color); tcPr.append(s)

    def para(container, text, size=None, bold=False, fn=None, align=None, keep=False, indent=None, space_after=None):
        p = container.add_paragraph()
        m = re.match(r'^([^:：]{1,28}?):\s(.*)$', text) if not bold else None
        if m and not re.search(r'[.。!?]', m.group(1)):
            font(p.add_run(m.group(1) + ': '), fn or BF, size or SIZE['body'], True)
            font(p.add_run(m.group(2)), fn or BF, size or SIZE['body'])
        else:
            font(p.add_run(text), fn or BF, size or SIZE['body'], bold)
        if align: p.alignment = align
        if keep: p.paragraph_format.keep_with_next = True
        if indent is not None: p.paragraph_format.left_indent = Mm(indent)
        if space_after is not None: p.paragraph_format.space_after = Pt(space_after)
        return p

    def table(container, rows):
        ncol = len(rows[0])
        t = container.add_table(rows=len(rows), cols=ncol); t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        rowlab = rows[0][0] == '' or ncol > 2 and all(len(r[0]) <= 18 for r in rows[1:])
        for i, r in enumerate(rows):
            r = r + [''] * (ncol - len(r))
            for j, c in enumerate(r):
                cell = t.cell(i, j); cell.text = ''
                p = cell.paragraphs[0]; p.paragraph_format.keep_with_next = True; p.paragraph_format.line_spacing = 1.3
                font(p.add_run(c), TF, SIZE['table'], i == 0 or (j == 0 and rowlab))
                if i == 0 or (j == 0 and rowlab):
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER; shade(cell._tc, 'D9D9D9' if i == 0 else 'F0F0F0')
            tr = t.rows[i]._tr; trPr = tr.get_or_add_trPr(); cs = OxmlElement('w:cantSplit'); trPr.append(cs)
        return t

    def blocks(container, bl):
        for b in bl:
            t = b['type']
            if t == 'info':
                para(container, b['text'], space_after=6)
            elif t == 'part':
                p = para(container, b['text'], SIZE['part'], True, HF, keep=True); p.paragraph_format.space_before = Pt(10)
            elif t == 'h':
                p = para(container, b['text'], SIZE['sub'], True, HF, keep=True); p.paragraph_format.space_before = Pt(8)
            elif t == 'p':
                para(container, b['text'], bold=b['text'].startswith('★'))
            elif t == 'ul':
                for it in b['items']:
                    p = para(container, '• ' + it['text'], indent=3); p.paragraph_format.first_line_indent = Mm(-3)
                    p.paragraph_format.keep_together = True
                    if it['sub']: p.paragraph_format.keep_with_next = True
                    for k, s in enumerate(it['sub']):
                        q = para(container, '– ' + s, indent=8); q.paragraph_format.first_line_indent = Mm(-3)
                        if k < len(it['sub']) - 1: q.paragraph_format.keep_with_next = True
            elif t == 'ol':
                for k, x in enumerate(b['items'], 1):
                    p = para(container, f'{k}. ' + x, indent=5); p.paragraph_format.first_line_indent = Mm(-5)
                    if k < len(b['items']): p.paragraph_format.keep_with_next = True
            elif t == 'table':
                table(container, b['rows']); container.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == 'box':
                bx = container.add_table(rows=1, cols=1); bx.style = 'Table Grid'
                c = bx.cell(0, 0); c.paragraphs[0].text = ''
                font(c.paragraphs[0].add_run(b['title']), HF, SIZE['sub'], True)
                c.paragraphs[0].paragraph_format.keep_with_next = True
                blocks(c, b['blocks'])
                container.add_paragraph()

    # 표지
    for _ in range(9): d.add_paragraph()
    para(d, meta['school'], 15, True, HF, WD_ALIGN_PARAGRAPH.CENTER, space_after=18)
    para(d, meta['title'], 26, True, HF, WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    para(d, meta['exam'], 14, False, HF, WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(14): d.add_paragraph()
    para(d, '리치아카데미 이재규T', 13, True, HF, WD_ALIGN_PARAGRAPH.CENTER)
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    # 목차
    para(d, '목차', SIZE['title'], True, HF, space_after=10)
    last = None
    for k, it in enumerate(items):
        if it['section'] != last:
            p = para(d, it['section'], 11.5, True, HF); p.paragraph_format.space_before = Pt(8); last = it['section']
        p = d.add_paragraph(); p.paragraph_format.left_indent = Mm(3)
        p.paragraph_format.tab_stops.add_tab_stop(Mm(170), alignment=2, leader=1)
        font(p.add_run(f'{it["toc"]}\t{pages.get(k, "")}'), HF, 11)
    # 지문
    for k, it in enumerate(items):
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        if it['section'] != it['title']:
            para(d, it['section'], 9.5, True, HF, keep=True, space_after=1)
        para(d, it['title'], SIZE['title'], True, HF, keep=True, space_after=6)
        if it['sum']:
            s = d.add_table(rows=1, cols=1); s.style = 'Table Grid'; c = s.cell(0, 0); c.text = ''
            font(c.paragraphs[0].add_run(it['sum']), HF, 10.5, True); shade(c._tc, 'E4E4E4'); d.add_paragraph()
        blocks(d, it['blocks'])
    # 머리말·꼬리말(둘째 쪽부터)
    hp = sec.header.paragraphs[0]; hp.paragraph_format.tab_stops.add_tab_stop(Mm(173), alignment=2)
    font(hp.add_run(f'{meta["school"]} | {meta["title"]}\t{meta["exam"]}'), HF, 8.5)
    fp = sec.footer.paragraphs[0]; fp.paragraph_format.tab_stops.add_tab_stop(Mm(87), alignment=1)
    font(fp.add_run('RICH ACADEMY 이재규T\t'), HF, 8.5, True)
    r = fp.add_run(); font(r, HF, 9.5, True)
    for tag, txt in (('begin', None), (None, 'PAGE'), ('end', None)):
        if tag:
            e = OxmlElement('w:fldChar'); e.set(qn('w:fldCharType'), tag); r._r.append(e)
        else:
            e = OxmlElement('w:instrText'); e.set(qn('xml:space'), 'preserve'); e.text = txt; r._r.append(e)
    d.save(out_docx)


if __name__ == '__main__':
    for src in sys.argv[1:]:
        meta, items = parse(os.path.join(H, src) if not os.path.isabs(src) else src)
        out = os.path.join(OUT, meta['file'])
        pages, n = make_pdf(meta, items, out + '.pdf')
        make_docx(meta, items, pages, out + '.docx')
        json.dump({'pages': pages, 'total': n, 'toc': [it['toc'] for it in items]}, open(os.path.join(H, 'data', os.path.basename(src) + '.pages.json'), 'w'), ensure_ascii=False)
        print('ok', meta['file'], n, 'pages', pages)
