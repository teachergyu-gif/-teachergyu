"""비문학 한판 정리 — PPT 수정본 양식(A4 세로, 학생 배부용, 목차 없음) PDF·DOCX 만들기.
data/*_ppt.txt(PPT 내용을 그대로 옮긴 것) → HTML → Chromium 인쇄 → 머리말·꼬리말 덧입힘 → PDF / 같은 데이터로 DOCX
사용: NODE_PATH=/opt/node22/lib/node_modules python3 build_ppt.py data/busanwoe_ppt.txt data/kukje_ppt.txt

데이터 표시
  @meta key 값 / @passage 지문(새 쪽) / @slide 소주제(제목 줄 '지문 | 소주제') / @sum ▶ 한 줄 요약 / @info ▶ 안내
  @h 소제목('(가) …'는 큰 제목, '★ …'는 별 제목) / - 항목, '  - ' 하위 항목 / | 표 |(첫 행 = 머리)
  @col … @col …(좌우 비교 상자, ↔) / @steps … @endsteps('N) 내용' 단계 상자) / @box 제목 … @endbox
  @img 파일 [너비%] / @imgs 파일 파일 …(2열 배치) / **굵게** / ' // ' 줄 바꿈
"""
import os, re, sys, json, base64, tempfile
from pypdf import PdfReader, PdfWriter
from build import esc, chromium_pdf, overlay_html, BODY_FONT, HEAD_FONT, TABLE_FONT, MARGIN, SIZE, LINE

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(H)
ACC = '#B08000'      # 강조색(짙은 황색: 흑백 인쇄 시 중간 회색) — PPT 노랑을 흰 바탕용으로
HL = '#FFE780'       # 형광 밑줄(흑백 인쇄 시 옅은 회색)


def parse(path):
    meta, psgs = {}, []
    tgt = None; mode = None; box = None
    for raw in open(path, encoding='utf8').read().split('\n'):
        line = raw.rstrip()
        if not line.strip():
            mode = None if mode == 'col' else mode; continue
        if line.startswith('@meta '):
            _, k, v = line.split(' ', 2); meta[k] = v; continue
        if line.startswith('@passage '):
            psgs.append({'title': line[9:].strip(), 'slides': []}); continue
        if line.startswith('@slide '):
            sl = {'sub': line[7:].strip(), 'blocks': []}; psgs[-1]['slides'].append(sl); tgt = sl['blocks']; mode = None; continue
        root = psgs[-1]['slides'][-1]['blocks']
        if line == '@steps':
            root.append({'type': 'steps', 'items': []}); mode = 'steps'; continue
        if line == '@endsteps':
            mode = None; continue
        if mode == 'steps':
            n, x = re.match(r'^(\d+)\) (.*)$', line).groups(); root[-1]['items'].append(x); continue
        if line == '@col':
            if not (root and root[-1]['type'] == 'pair' and mode == 'col'):
                root.append({'type': 'pair', 'cols': []})
            root[-1]['cols'].append([]); tgt = root[-1]['cols'][-1]; mode = 'col'; continue
        if line.startswith('@box '):
            box = {'type': 'box', 'title': line[5:].strip(), 'blocks': []}; root.append(box); tgt = box['blocks']; continue
        if line == '@endbox':
            box = None; tgt = root; continue
        if mode != 'col' and box is None:
            tgt = root
        if line.startswith('@sum '):
            tgt.append({'type': 'sum', 'text': line[5:].strip()}); continue
        if line.startswith('@info '):
            tgt.append({'type': 'info', 'text': line[6:].strip()}); continue
        if line.startswith('@h '):
            tgt.append({'type': 'h', 'text': line[3:].strip()}); continue
        if line.startswith('@img '):
            a = line[5:].split(); tgt.append({'type': 'imgs', 'files': [a[0]], 'w': int(a[1]) if len(a) > 1 else 100}); continue
        if line.startswith('@imgs '):
            tgt.append({'type': 'imgs', 'files': line[6:].split(), 'w': 100}); continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if tgt and tgt[-1]['type'] == 'table': tgt[-1]['rows'].append(cells)
            else: tgt.append({'type': 'table', 'rows': [cells]})
            continue
        m = re.match(r'^(\s*)- (.*)$', line)
        if m:
            if not m.group(1):
                if not (tgt and tgt[-1]['type'] == 'ul'): tgt.append({'type': 'ul', 'items': []})
                tgt[-1]['items'].append({'text': m.group(2), 'sub': []})
            else:
                tgt[-1]['items'][-1]['sub'].append(m.group(2))
            continue
        tgt.append({'type': 'p', 'text': line.strip()})
    return meta, psgs


def md(t, hl=True):
    s = esc(t)
    s = re.sub(r'\*\*(.+?)\*\*', (lambda m: f'<b class="k">{m.group(1)}</b>') if hl else (lambda m: f'<b>{m.group(1)}</b>'), s)
    return s.replace(' // ', '<br>')


def plain(t):
    return t.replace('**', '').replace(' // ', ' ')


def img_uri(f):
    return 'data:image/png;base64,' + base64.b64encode(open(os.path.join(H, f), 'rb').read()).decode()


def table_html(rows):
    head, body = rows[0], rows[1:]
    ncol = len(head)
    rowlab = head[0] == '' or all(re.fullmatch(r'\*\*.*\*\*', r[0] or '') for r in body)
    h = '<tr>' + ''.join(f'<th>{md(c, False)}</th>' for c in head) + '</tr>'
    b = ''
    for r in body:
        r = r + [''] * (ncol - len(r))
        b += '<tr>' + ''.join(f'<td class="{"rl" if (j == 0 and rowlab) else ""}">{md(c, False)}</td>' for j, c in enumerate(r)) + '</tr>'
    return f'<table class="t c{ncol}"><thead>{h}</thead><tbody>{b}</tbody></table>'


def blocks_html(bl):
    out = []
    for b in bl:
        t = b['type']
        if t == 'sum':
            out.append(f'<div class="sum">{md(b["text"], False)}</div>')
        elif t == 'info':
            out.append(f'<div class="info">{md(b["text"], False)}</div>')
        elif t == 'h':
            x = b['text']
            cls = 'part' if re.match(r'^\([가-하]\)', x) else 'star' if x.startswith('★') else 'sub'
            out.append(f'<h3 class="{cls}">{esc(x)}</h3>')
        elif t == 'p':
            out.append(f'<p>{md(b["text"])}</p>')
        elif t == 'ul':
            lis = ''
            for it in b['items']:
                sub = ''.join(f'<li>{md(s)}</li>' for s in it['sub'])
                lis += f'<li>{md(it["text"])}' + (f'<ul class="l2">{sub}</ul>' if sub else '') + '</li>'
            out.append(f'<ul class="l1">{lis}</ul>')
        elif t == 'table':
            out.append(table_html(b['rows']))
        elif t == 'steps':
            s = ''
            for k, x in enumerate(b['items'], 1):
                if k > 1: s += '<div class="arr">▼</div>'
                s += f'<div class="st"><span class="n">{k}</span><span class="x">{md(x)}</span></div>'
            out.append(f'<div class="steps">{s}</div>')
        elif t == 'pair':
            cols = []
            for c in b['cols']:
                first = c[0]
                ttl = ''
                if first['type'] == 'p' and re.fullmatch(r'\*\*[^*]+\*\*', first['text']):
                    ttl = f'<div class="ct">{esc(first["text"].strip("*"))}</div>'; c = c[1:]
                cols.append(f'<div class="col">{ttl}{blocks_html(c)}</div>')
            out.append(f'<div class="pair">{cols[0]}<div class="vs">↔</div>{cols[1]}</div>')
        elif t == 'box':
            out.append(f'<div class="box"><div class="bt">{esc(b["title"])}</div>{blocks_html(b["blocks"])}</div>')
        elif t == 'imgs':
            if len(b['files']) == 1:
                out.append(f'<div class="fig"><img src="{img_uri(b["files"][0])}" style="width:{b["w"]}%"></div>')
            else:
                out.append('<div class="fig g2">' + ''.join(f'<img src="{img_uri(f)}">' for f in b['files']) + '</div>')
    return ''.join(out)


CSS = f'''
@page{{size:A4;margin:{MARGIN["top"]}mm {MARGIN["side"]}mm {MARGIN["bottom"]}mm}}
html,body{{margin:0;padding:0;background:#fff}}
body{{font-family:{BODY_FONT};font-size:{SIZE["body"]}pt;line-height:{LINE}%;color:#000;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.pg{{break-before:page}}
.cover{{height:253mm;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;font-family:{HEAD_FONT}}}
.cover .sc{{font-size:15pt;font-weight:700;letter-spacing:1pt;border-bottom:1.2pt solid #000;padding-bottom:2mm}}
.cover .tt{{font-size:27pt;font-weight:800;line-height:1.35;margin:14mm 0 6mm;word-break:keep-all}}
.cover .tt .y{{background:linear-gradient(transparent 58%,{HL} 58%)}}
.cover .ex{{font-size:14pt;border:1pt solid #000;padding:1.5mm 6mm}}
.cover .ac{{margin-top:auto;font-size:13pt;font-weight:700;letter-spacing:.5pt}}
.sl{{margin:0 0 2mm}}
.sl+.sl{{margin-top:7mm}}
.bar{{font-family:{HEAD_FONT};font-size:12.5pt;font-weight:800;line-height:1.4;padding:0 0 1.6mm;margin:0 0 3mm;border-bottom:1.3pt solid #595959;break-after:avoid;break-inside:avoid;word-break:keep-all}}
.bar .ps{{color:#000}}
.bar .sep{{color:#8c8c8c;font-weight:400;margin:0 2mm}}
.bar .sb{{background:linear-gradient(transparent 55%,{HL} 55%);padding:0 .6mm}}
.first .bar{{font-size:{SIZE["title"]}pt;border-bottom-width:1.8pt}}
.sum{{border:1.2pt solid #000;border-left:4pt solid #000;padding:2.4mm 4mm;margin:0 0 2.5mm;font-family:{HEAD_FONT};font-weight:400;font-size:10.5pt;line-height:155%;break-inside:avoid}}
.sum b,.info b{{font-weight:800}}
.info{{padding:0 1mm 0 5mm;margin:0 0 3mm;font-family:{HEAD_FONT};font-size:10pt;line-height:155%;text-indent:-4mm;padding-left:5mm}}
p{{margin:0 0 1.6mm}}
b{{font-weight:700}}
b.k{{font-weight:800;background:linear-gradient(transparent 62%,{HL} 62%)}}
h3{{break-after:avoid;break-inside:avoid;font-family:{HEAD_FONT}}}
h3.sub{{font-size:{SIZE["sub"]}pt;font-weight:800;margin:4mm 0 1.8mm;padding:.2mm 0 .2mm 3mm;border-left:3.5pt solid {ACC}}}
h3.part{{font-size:{SIZE["part"]}pt;font-weight:800;margin:5mm 0 2.5mm;padding:1.2mm 3mm;border:1.2pt solid #000;border-left:5pt solid {ACC}}}
h3.star{{font-size:{SIZE["sub"]}pt;font-weight:800;margin:4mm 0 1.8mm}}
ul.l1{{margin:0 0 2mm;padding-left:5.5mm}}
ul.l1>li{{list-style:none;position:relative;margin:0 0 1.2mm;break-inside:avoid}}
ul.l1>li:before{{content:"•";position:absolute;left:-4mm}}
ul.l2{{margin:.8mm 0 0;padding-left:5mm}}
ul.l2>li{{list-style:none;position:relative;margin:0 0 .8mm}}
ul.l2>li:before{{content:"–";position:absolute;left:-4mm}}
table.t{{width:100%;border-collapse:collapse;margin:1.5mm 0 3mm;font-family:{TABLE_FONT};font-size:{SIZE["table"]}pt;line-height:145%;break-inside:avoid}}
table.t th,table.t td{{border:.7pt solid #000;padding:1.4mm 2mm;vertical-align:middle;word-break:keep-all}}
table.t th{{background:#FFF0B0;font-weight:800;text-align:center}}
table.t td.rl{{background:#f2f2f2;font-weight:700;text-align:center}}
table.t tr{{break-inside:avoid}}
.steps{{margin:1.5mm 0 3mm;break-inside:avoid}}
.st{{display:flex;border:1pt solid #000;border-radius:2mm;overflow:hidden;font-size:10pt;line-height:150%}}
.st .n{{flex:0 0 8mm;display:flex;align-items:center;justify-content:center;background:{HL};border-right:1pt solid #000;font-family:{HEAD_FONT};font-weight:800;font-size:11pt}}
.st .x{{padding:1.6mm 3mm}}
.arr{{text-align:center;color:{ACC};font-size:8pt;line-height:1;margin:.6mm 0}}
.pair{{display:flex;align-items:stretch;gap:0;margin:1.5mm 0 3mm;break-inside:avoid}}
.pair .col{{flex:1;border:1pt solid #000;border-radius:2.5mm;padding:2.5mm 3mm 1.5mm;font-size:10pt}}
.pair .ct{{font-family:{HEAD_FONT};font-weight:800;font-size:11pt;margin:0 0 1.8mm;padding-bottom:1mm;border-bottom:.6pt solid #000}}
.pair .vs{{flex:0 0 9mm;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15pt;color:{ACC};font-family:{HEAD_FONT}}}
.pair ul.l1{{padding-left:4.5mm}}
.box{{border:1.3pt solid #000;border-radius:2.5mm;padding:2.5mm 4mm 1.5mm;margin:2mm 0 3mm;break-inside:avoid}}
.box .bt{{font-family:{HEAD_FONT};font-weight:800;font-size:{SIZE["sub"]}pt;margin:0 0 2mm}}
.fig{{text-align:center;margin:2mm 0 3mm;break-inside:avoid}}
.fig img{{border:.6pt solid #bbb}}
.fig.g2{{display:grid;grid-template-columns:1fr 1fr;gap:3mm;break-inside:auto}}
.fig.g2 img{{break-inside:avoid}}
.fig.g2 img{{width:100%}}
'''


def build_html(meta, psgs):
    tt = meta.get('cover', meta['title']).split('|')
    tt_html = '<br>'.join(esc(x) if k < len(tt) - 1 else f'<span class="y">{esc(x)}</span>' for k, x in enumerate(tt))
    body = [f'<section class="cover"><div class="sc">{esc(meta["school"])}</div><div class="tt">{tt_html}</div>'
            f'<div class="ex">{esc(meta["exam"])}</div><div class="ac">리치아카데미 이재규T</div></section>']
    for p in psgs:
        s = ''
        for k, sl in enumerate(p['slides']):
            bar = f'<div class="bar"><span class="ps">{esc(p["title"])}</span><span class="sep">|</span><span class="sb">{esc(sl["sub"])}</span></div>'
            s += f'<div class="sl{" first" if k == 0 else ""}">{bar}{blocks_html(sl["blocks"])}</div>'
        body.append(f'<section class="pg">{s}</section>')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(body)}</body></html>'


def make_pdf(meta, psgs, out_pdf):
    with tempfile.TemporaryDirectory() as tmp:
        chromium_pdf(build_html(meta, psgs), f'{tmp}/b.pdf', tmp)
        open(os.path.join(H, 'last_ppt.html'), 'w').write(build_html(meta, psgs)) if os.environ.get('KEEP_HTML') else None
        n = len(PdfReader(f'{tmp}/b.pdf').pages)
        chromium_pdf(overlay_html(meta, n), f'{tmp}/o.pdf', tmp)
        base, ov = PdfReader(f'{tmp}/b.pdf'), PdfReader(f'{tmp}/o.pdf')
        w = PdfWriter()
        for p, o in zip(base.pages, ov.pages):
            p.merge_page(o); w.add_page(p)
        w.write(out_pdf)
        return n


def make_docx(meta, psgs, out_docx):
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

    def font(run, name, size, bold=False, hl=False):
        run.font.name = name; run.font.size = Pt(size); run.font.bold = bold
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), name)
        if hl:
            from docx.enum.text import WD_COLOR_INDEX
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    st = d.styles['Normal']; st.font.name = BF; st.font.size = Pt(SIZE['body'])
    st.element.rPr.rFonts.set(qn('w:eastAsia'), BF)
    st.paragraph_format.line_spacing = LINE / 100; st.paragraph_format.space_after = Pt(2)

    def shade(cell, color):
        tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement('w:shd')
        s.set(qn('w:val'), 'clear'); s.set(qn('w:color'), 'auto'); s.set(qn('w:fill'), color); tcPr.append(s)

    def rich(p, text, fn=BF, size=None, bold_all=False, hl=False):
        size = size or SIZE['body']
        parts = re.split(r'(\*\*.+?\*\*| // )', text)
        for x in parts:
            if not x: continue
            if x == ' // ':
                p.add_run().add_break(); continue
            if x.startswith('**'):
                font(p.add_run(x[2:-2]), fn, size, True, hl)
            else:
                font(p.add_run(x), fn, size, bold_all)
        return p

    def para(c, text, fn=BF, size=None, bold=False, keep=False, indent=None, first=None, after=None, before=None, align=None):
        p = c.add_paragraph(); rich(p, text, fn, size, bold, hl=not bold)
        f = p.paragraph_format
        if keep: f.keep_with_next = True
        if indent is not None: f.left_indent = Mm(indent)
        if first is not None: f.first_line_indent = Mm(first)
        if after is not None: f.space_after = Pt(after)
        if before is not None: f.space_before = Pt(before)
        if align is not None: p.alignment = align
        return p

    def widths(tb, mm):
        tb.autofit = False
        for j, w in enumerate(mm):
            tb.columns[j].width = Mm(w)
            for cell in tb.columns[j].cells: cell.width = Mm(w)

    def cellbox(c, fill=None):
        t = c.add_table(rows=1, cols=1); t.style = 'Table Grid'; cell = t.cell(0, 0); cell.text = ''
        if fill: shade(cell, fill)
        return t, cell

    def blocks(c, bl):
        for b in bl:
            t = b['type']
            if t == 'sum':
                _, cell = cellbox(c); rich(cell.paragraphs[0], b['text'], HF, 10.5); c.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == 'info':
                para(c, b['text'], HF, 10, after=6)
            elif t == 'h':
                x = b['text']; part = re.match(r'^\([가-하]\)', x)
                p = para(c, x, HF, SIZE['part'] if part else SIZE['sub'], True, keep=True, before=8)
            elif t == 'p':
                para(c, b['text'])
            elif t == 'ul':
                for it in b['items']:
                    p = para(c, '• ' + it['text'], indent=3, first=-3); p.paragraph_format.keep_together = True
                    if it['sub']: p.paragraph_format.keep_with_next = True
                    for k, s in enumerate(it['sub']):
                        q = para(c, '– ' + s, indent=8, first=-3)
                        if k < len(it['sub']) - 1: q.paragraph_format.keep_with_next = True
            elif t == 'table':
                rows = b['rows']; ncol = len(rows[0])
                tb = c.add_table(rows=len(rows), cols=ncol); tb.style = 'Table Grid'; tb.alignment = WD_TABLE_ALIGNMENT.CENTER
                rowlab = rows[0][0] == '' or all(re.fullmatch(r'\*\*.*\*\*', r[0] or '') for r in rows[1:])
                for i, r in enumerate(rows):
                    r = r + [''] * (ncol - len(r))
                    for j, x in enumerate(r):
                        cell = tb.cell(i, j); cell.text = ''; p = cell.paragraphs[0]
                        p.paragraph_format.keep_with_next = True; p.paragraph_format.line_spacing = 1.3
                        lab = i == 0 or (j == 0 and rowlab)
                        font(p.add_run(plain(x)), TF, SIZE['table'], lab)
                        if lab:
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER; shade(cell, 'FFF0B0' if i == 0 else 'F2F2F2')
                    trPr = tb.rows[i]._tr.get_or_add_trPr(); trPr.append(OxmlElement('w:cantSplit'))
                c.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == 'steps':
                tb = c.add_table(rows=len(b['items']), cols=2); tb.style = 'Table Grid'
                for i, x in enumerate(b['items']):
                    n, cell = tb.cell(i, 0), tb.cell(i, 1); n.width = Mm(9); cell.width = Mm(165)
                    n.text = ''; font(n.paragraphs[0].add_run(str(i + 1)), HF, 11, True); n.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    shade(n, 'FFE780'); cell.text = ''; rich(cell.paragraphs[0], x, BF, 10)
                    n.paragraphs[0].paragraph_format.keep_with_next = True
                widths(tb, [9, 165])
                c.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == 'pair':
                tb = c.add_table(rows=1, cols=3); tb.style = 'Table Grid'
                for j, col in enumerate(b['cols']):
                    cell = tb.cell(0, 0 if j == 0 else 2); cell.text = ''
                    if col and col[0]['type'] == 'p' and re.fullmatch(r'\*\*[^*]+\*\*', col[0]['text']):
                        font(cell.paragraphs[0].add_run(col[0]['text'].strip('*')), HF, 11, True); col = col[1:]
                    blocks(cell, col)
                mid = tb.cell(0, 1); mid.width = Mm(9); mid.text = ''
                font(mid.paragraphs[0].add_run('↔'), HF, 14, True); mid.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                widths(tb, [82.5, 9, 82.5])
                c.add_paragraph().paragraph_format.space_after = Pt(0)
            elif t == 'box':
                _, cell = cellbox(c); font(cell.paragraphs[0].add_run(b['title']), HF, SIZE['sub'], True)
                cell.paragraphs[0].paragraph_format.keep_with_next = True
                blocks(cell, b['blocks']); c.add_paragraph()
            elif t == 'imgs':
                if len(b['files']) == 1:
                    p = c.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.add_run().add_picture(os.path.join(H, b['files'][0]), width=Mm(174 * b['w'] / 100))
                else:
                    tb = c.add_table(rows=(len(b['files']) + 1) // 2, cols=2)
                    for k, f in enumerate(b['files']):
                        cell = tb.cell(k // 2, k % 2); cell.text = ''
                        cell.paragraphs[0].add_run().add_picture(os.path.join(H, f), width=Mm(84))
                    c.add_paragraph()

    # 표지
    for _ in range(9): d.add_paragraph()
    para(d, meta['school'], HF, 15, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
    for x in meta.get('cover', meta['title']).split('|'):
        para(d, x, HF, 26, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
    para(d, meta['exam'], HF, 14, align=WD_ALIGN_PARAGRAPH.CENTER, before=10)
    for _ in range(13): d.add_paragraph()
    para(d, '리치아카데미 이재규T', HF, 13, True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for p in psgs:
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        for k, sl in enumerate(p['slides']):
            q = d.add_paragraph(); q.paragraph_format.keep_with_next = True
            q.paragraph_format.space_before = Pt(0 if k == 0 else 14); q.paragraph_format.space_after = Pt(6)
            sz = SIZE['title'] if k == 0 else 12.5
            font(q.add_run(p['title']), HF, sz, True); font(q.add_run('  |  '), HF, sz)
            font(q.add_run(sl['sub']), HF, sz, True, hl=True)
            pPr = q._p.get_or_add_pPr(); bd = OxmlElement('w:pBdr'); bt = OxmlElement('w:bottom')
            for a, v in (('val', 'single'), ('sz', '10'), ('space', '1'), ('color', '595959')): bt.set(qn('w:' + a), v)
            bd.append(bt); pPr.append(bd)
            blocks(d, sl['blocks'])
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
        meta, psgs = parse(os.path.join(H, src) if not os.path.isabs(src) else src)
        out = os.path.join(OUT, meta['file'])
        n = make_pdf(meta, psgs, out + '.pdf')
        make_docx(meta, psgs, out + '.docx')
        print('ok', meta['file'], n, 'pages')
