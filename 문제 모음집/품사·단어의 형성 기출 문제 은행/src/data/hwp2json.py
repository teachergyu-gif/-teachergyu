"""원본 한글 파일(raw/원본.hwp) → 문항 데이터(data/qb.json).
문항마다: 번호, 단원, 출처, 발문(html), 내용 덩어리(<보기> 상자·표·그림 html), 선지(html 5개 또는 표).
밑줄·굵게·위첨자는 글자 모양에서, 표는 칸 합치기·테두리까지 옮긴다. 그리기 개체(선·도형)는 'draw' 표시만 남긴다."""
import html, json, os, re, struct, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
from hwplib import parse_records, inflate, read_hwp

S = read_hwp(os.path.join(H, '..', 'raw', '원본.hwp'))
SEC = parse_records(inflate(S['BodyText/Section0']))
DI = parse_records(inflate(S['DocInfo']))
CS = [p for t, l, p in DI if t == 21]
PS = [p for t, l, p in DI if t == 25]
BF = [p for t, l, p in DI if t == 20]
BINS = []
for t, l, p in DI:
    if t == 18:
        typ = struct.unpack_from('<H', p, 0)[0] & 0xF
        BINS.append(struct.unpack_from('<H', p, 2)[0] if typ == 1 else None)
CIRC = '①②③④⑤'
JOINLOG = []
EXT = (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23)


def cs_style(k):
    a, = struct.unpack_from('<I', CS[k], 46)
    return {'b': bool(a & 2), 'u': ((a >> 2) & 3) != 0, 'sup': ((a >> 15) & 3) == 1, 'sub': ((a >> 15) & 3) == 2}


def ps_align(k):
    a, = struct.unpack_from('<I', PS[k], 0)
    return (a >> 2) & 7   # 0 양쪽 1 왼쪽 2 오른쪽 3 가운데 4 배분


# ---------- 문단 트리 ----------
class Para:
    def __init__(self, i):
        self.i = i
        t, l, p = SEC[i]
        self.level = l
        self.ps, = struct.unpack_from('<H', p, 8)
        self.style = p[10]
        j = i + 1
        self.text = b''; self.cs = [(0, 0)]; self.ctrls = []
        while j < len(SEC) and SEC[j][1] > l:
            tj, lj, pj = SEC[j]
            if lj == l + 1:
                if tj == 67: self.text = pj
                elif tj == 68: self.cs = [struct.unpack_from('<II', pj, k) for k in range(0, len(pj), 8)]
                elif tj == 71: self.ctrls.append(j)
            j += 1
        self.end = j

    def chars(self):
        """[(ch or ('ctrl', idx), pos)]"""
        out = []; j = 0; pos = 0; k = 0
        raw = self.text
        while j + 1 < len(raw):
            c, = struct.unpack_from('<H', raw, j)
            if c < 32:
                if c in EXT:
                    if c in (11, 3, 2, 1, 21, 22, 23, 15, 16, 17, 18) and k < len(self.ctrls):
                        out.append((('ctrl', self.ctrls[k]), pos)); k += 1
                    j += 16; pos += 8; continue
                if c == 9: out.append(('\t', pos)); j += 16; pos += 8; continue
                j += 2; pos += 1; continue
            hi = raw[j:j + 2]
            if 0xD800 <= c < 0xDC00:
                ch = raw[j:j + 4].decode('utf-16le', 'replace'); out.append((ch, pos)); j += 4; pos += 2; continue
            out.append((hi.decode('utf-16le', 'replace'), pos)); j += 2; pos += 1
        return out

    def shape_at(self, pos):
        s = self.cs[0][1]
        for a, b in self.cs:
            if a <= pos: s = b
        return s

    def plain(self):
        return ''.join(c if isinstance(c, str) else '￼' for c, _ in self.chars())


def children(start, end, level):
    """start~end 안에서 level 문단들"""
    out = []; i = start
    while i < end:
        if SEC[i][0] == 66 and SEC[i][1] == level:
            p = Para(i); out.append(p); i = p.end
        else:
            i += 1
    return out


def ctrl_id(j):
    return SEC[j][2][:4][::-1].decode('latin1')


# ---------- html ----------
def runs_html(p, inline=True):
    out = []; cur = None; buf = ''
    def flush():
        nonlocal buf
        if not buf: return
        s = html.escape(buf, quote=False)
        st = cur
        if st['sup']: s = f'<sup>{s}</sup>'
        if st['sub']: s = f'<sub>{s}</sub>'
        if st['u'] and s.strip(): s = f'<u>{s}</u>'
        if st['b'] and s.strip(): s = f'<b>{s}</b>'
        out.append(s); buf = ''
    for c, pos in p.chars():
        if isinstance(c, tuple):
            flush(); out.append(ctrl_html(c[1])); continue
        st = cs_style(p.shape_at(pos))
        if st != cur: flush(); cur = st
        buf += c
    flush()
    return ''.join(out)


def bf_css(k):
    if not k or k > len(BF): return ''
    p = BF[k - 1]; o = 2; css = []
    for side in ('left', 'right', 'top', 'bottom'):
        ty, w = p[o], p[o + 1]; o += 6
        css.append(f'border-{side}:{"none" if ty == 0 else ("1.4px" if w >= 3 else "0.8px") + " solid #111"}')
    # 바탕색
    if len(p) > o + 6 + 4 and p[o + 6] & 1:
        col, = struct.unpack_from('<I', p, o + 6 + 4)
        if col != 0xFFFFFF and col != 0xFFFFFFFF:
            r, g, b = col & 255, (col >> 8) & 255, (col >> 16) & 255
            css.append(f'background:#{r:02x}{g:02x}{b:02x}')
    return ';'.join(css)


def table_cells(j):
    """j = tbl 컨트롤 레코드: [(row,col,rs,cs,width,bf,[Para…])], nrows, ncols"""
    L = SEC[j][1]
    k = j + 1
    while SEC[k][0] != 77: k += 1
    rows, cols = struct.unpack_from('<HH', SEC[k][2], 4)
    end = k + 1
    while end < len(SEC) and SEC[end][1] > L: end += 1
    hdrs = [i for i in range(k + 1, end) if SEC[i][0] == 72 and SEC[i][1] == L + 1]
    cells = []
    for n, i in enumerate(hdrs):
        e = hdrs[n + 1] if n + 1 < len(hdrs) else end
        p = SEC[i][2]
        col, row, csp, rsp = struct.unpack_from('<HHHH', p, 8)
        w, = struct.unpack_from('<I', p, 16)
        bf, = struct.unpack_from('<H', p, 32)
        cells.append((row, col, rsp, csp, w, bf, children(i + 1, e, L + 1)))
    return cells, rows, cols, end


def lines_html(paras, join=False):
    """문단들 → 줄 html. join=True면 원본의 손 줄바꿈(한 문단을 여러 줄로 나눠 친 것)을 잇는다."""
    items = []
    for p in paras:
        pl = p.plain()
        items.append([p, pl, runs_html(p)])
    out = []
    MARK = re.compile(r'^\s*(?:[ㄱ-ㅎ]\.|[가-하]\.|[○□•◦◎▪※\-*]|\[[^\]]{1,8}\]|[①-⑤]|\([가-하ㄱ-ㅎ]\)|[가-힣]{1,4}\s*:|[가-힣]\s[가-힣]\s*:|-)')
    k = 0
    while k < len(items):
        p, pl, h = items[k]
        al = ps_align(p.ps)
        cls = {3: 'c', 2: 'r'}.get(al, '')
        if join and pl.strip():
            lead = pl.startswith('  ') and not MARK.match(pl)
            marked = bool(MARK.match(pl))
            while k + 1 < len(items):
                q, ql, qh = items[k + 1]
                cur = pl.rstrip()
                if not ql.strip() or '￼' in ql: break
                if len(cur.replace(' ', '')) < 22: break          # 짧은 줄 = 문단 끝
                if MARK.match(ql.lstrip()): break
                if ql.startswith('  ') and not marked: break        # 두 칸 들여쓴 줄 = 새 문단
                if ql.startswith(' ') and not pl.endswith(' '):
                    nxt = ql.lstrip()
                    glue = '' if re.match(r'^(이다|이며|이고|이므로|이나|이라|이란|을|를|은|는|이|가|의|에|에서|에게|와|과|로|으로|도|만|까지|부터|하다|한다|했다|하는|하고|하여|해|된다|되어|되는|된|할|함|하며|들|다\.|다,)', nxt) else ' '
                    JOINLOG.append(pl.rstrip()[-8:] + '|' + glue + '|' + nxt[:8])
                    h = h.rstrip() + glue + qh.lstrip()
                else:
                    h = h + qh.lstrip() if ql.startswith(' ') else h + qh
                pl = pl + ql.lstrip()
                k += 1
            ind = ' ind' if lead else (' hang' if marked else '')
        else:
            ind = ''
        if not pl.strip() and '￼' not in pl:
            out.append('<div class="ln e"></div>')
        else:
            out.append(f'<div class="ln{(" " + cls) if cls else ""}{ind}">{h.strip() if join else h}</div>')
        k += 1
    return ''.join(out)


def table_html(j, join=False):
    cells, rows, cols, end = table_cells(j)
    grid = {}
    trs = []
    by_row = {}
    for c in cells: by_row.setdefault(c[0], []).append(c)
    widths = {}
    for r, c, rs, cs, w, bf, ps in cells:
        if cs == 1: widths[c] = w
    tot = sum(widths.get(c, 0) for c in range(cols)) or 1
    cg = ''.join(f'<col style="width:{widths.get(c, tot / cols) / tot * 100:.1f}%">' for c in range(cols))
    for r in range(rows):
        tds = []
        for (_, c, rs, cs, w, bf, ps) in sorted(by_row.get(r, []), key=lambda x: x[1]):
            al = ps_align(ps[0].ps) if ps else 0
            st = bf_css(bf) + {3: ';text-align:center', 2: ';text-align:right'}.get(al, ';text-align:left')
            span = (f' rowspan="{rs}"' if rs > 1 else '') + (f' colspan="{cs}"' if cs > 1 else '')
            tds.append(f'<td{span} style="{st}">{lines_html(ps, join)}</td>')
        trs.append('<tr>' + ''.join(tds) + '</tr>')
    return f'<table class="ht"><colgroup>{cg}</colgroup>' + ''.join(trs) + '</table>'


def gso_html(j):
    L = SEC[j][1]; p = SEC[j][2]
    w, h = struct.unpack_from('<II', p, 16)
    end = j + 1
    while end < len(SEC) and SEC[end][1] > L: end += 1
    pics = [struct.unpack_from('<H', SEC[i][2], 71)[0] for i in range(j, end) if SEC[i][0] == 85]
    shapes_kind = [SEC[i][2][:4][::-1] for i in range(j, end) if SEC[i][0] == 76]
    if not (pics and len(shapes_kind) == 1):   # 그리기 개체(묶음·도형·글상자): 좌표대로 SVG
        import shapes
        return shapes.render(j)
    if pics:
        mm = w / 7200 * 25.4
        return ''.join(f'<img class="pic" src="IMG/BIN{BINS[b - 1]:04X}.png" style="width:{mm:.1f}mm">' for b in pics if 0 < b <= len(BINS))
    # 글상자가 든 그리기 개체: 안의 글만이라도
    txts = []
    for i in range(j, end):
        if SEC[i][0] == 72:
            ps = children(i + 1, end, SEC[i][1])
            txts.append(lines_html(ps))
    return f'<span class="draw" data-w="{w}" data-h="{h}">{"".join(txts)}</span>'


def tcps_html(j):
    p = SEC[j][2]
    n, = struct.unpack_from('<H', p, 4)
    chars = p[6:6 + 2 * n].decode('utf-16le', 'replace')
    return f'<span class="ovl">{html.escape(chars)}</span>'


def ctrl_html(j):
    cid = ctrl_id(j)
    if cid == 'tbl ': return table_html(j, join=False)
    if cid == 'gso ': return gso_html(j)
    if cid == 'tcps': return tcps_html(j)
    return ''


# ---------- 문항 나누기 ----------
TOP = children(0, len(SEC), 0)
SRC1 = re.compile(r'(\d{4})(년|학년도).*\d+번')
HDR2 = re.compile(r'^\d{1,3} (\d{4})(년|학년도)')
TITLE = re.compile(r'^Ⅰ-\((\d)\)\s*(.+?)\s*기출문제')


def single_table_text(p):
    """문단이 1×1 표 하나만 가졌으면 그 글"""
    tb = [c for c in p.ctrls if ctrl_id(c) == 'tbl ']
    if len(tb) != 1 or p.plain().replace('\ufffc', '').strip(): return None
    cells, rows, cols, end = table_cells(tb[0])
    if (rows, cols) != (1, 1): return None
    return ''.join(q.plain() for q in cells[0][6]).strip()


def expand(h):
    m = re.match(r'^\d+ (\d{4})년 (\d+)월 학평 (\d+)번', h)
    if m:
        y, mo, n = map(int, m.groups()); g = ' 고3' if (n >= 35 and y >= 2021) else ''
        return f'{y}년 {mo}월{g} 전국연합학력평가 국어영역 {n}번'
    m = re.match(r'^\d+ (\d{4})학년도 (\d+)월 모평 (\d+)번', h)
    if m: return f'{m.group(1)}학년도 {m.group(2)}월 모의평가 국어영역 {m.group(3)}번'
    m = re.match(r'^\d+ (\d{4})학년도 수능 (\d+)번', h)
    if m: return f'{m.group(1)}학년도 대학수학능력시험 국어영역 {m.group(2)}번'
    raise ValueError(h)


def bogi_box(p):
    """<보기> 상자 표(1~146: 3×3, 147~: 4×5)면 (제목, 본문 문단들)"""
    if len(p.ctrls) != 1 or ctrl_id(p.ctrls[0]) != 'tbl ': return None
    cells, rows, cols, end = table_cells(p.ctrls[0])
    if (rows, cols) not in ((3, 3), (4, 5)): return None
    lab = [c for c in cells if c[0] == 0 and c[1] == (1 if cols == 3 else 2)]
    if not lab: return None
    t = ''.join(q.plain() for q in lab[0][6]).strip()
    m = re.fullmatch(r'<\s*(.+?)\s*>', t)
    if not m: return None
    k = re.sub(r'\s', '', m.group(1))
    title = {'보기': '<보기>', '보기1': '<보기 1>', '보기2': '<보기 2>', '학습활동': '<학습 활동>'}.get(k, '<' + m.group(1) + '>')
    body = max(cells, key=lambda c: sum(len(q.plain().strip()) + 50 * len(q.ctrls) for q in c[6]))[6]   # 글이 가장 많은 칸 = 본문
    return title, body


def convert():
    parts = []; qs = []
    i = 0; part = None; cur = None; n = 0; region2 = False
    for p in TOP:
        pl = p.plain().strip()
        st = single_table_text(p)
        if st and TITLE.match(st):
            m = TITLE.match(st); part = f'Ⅰ-({m.group(1)}) {m.group(2)}'; parts.append(part); continue
        if st and SRC1.search(st) and len(st) < 60:
            cur = {'src': st, 'part': part, 'paras': []}; qs.append(cur); continue
        if HDR2.match(pl):
            if not region2:
                region2 = True; part = '추가 기출'; parts.append(part)
            cur = {'src': expand(pl), 'part': part, 'paras': [], 'new': True}; qs.append(cur); continue
        if cur is not None:
            cur['paras'].append(p)
    out = []
    for k, q in enumerate(qs, 1):
        ps = [p for p in q['paras']]
        # 발문
        si = next(x for x, p in enumerate(ps) if p.plain().strip())
        stem = runs_html(ps[si]).strip()
        rest = ps[si + 1:]
        blocks = []; choices = []; ctab = None
        new = q.get('new', False)
        tabrows = []
        def flush_tab():
            nonlocal tabrows
            if tabrows:
                rows = [[c.strip() for c in re.split(r'\t+', r) if c.strip() != ''] for r in tabrows]
                blocks.append({'type': 'tabrows', 'rows': rows}); tabrows = []
        for p in rest:
            pl = p.plain()
            if not pl.strip() and not p.ctrls: continue
            b = bogi_box(p)
            if b:
                flush_tab()
                title, body = b
                blocks.append({'type': 'bogi', 'title': title, 'html': lines_html(body, join=not new)}); continue
            if p.ctrls and not pl.replace('￼', '').strip():
                flush_tab()
                h = runs_html(p)
                if any(ctrl_id(c) == 'tbl ' for c in p.ctrls):
                    cells, rows, cols, end = table_cells(p.ctrls[0])
                    first = [''.join(x.plain() for x in c[6]).strip() for c in cells if c[1] == 0]
                    if sum(1 for f in first if f[:1] in CIRC) >= 5:
                        ctab = h; continue
                blocks.append({'type': 'html', 'html': h}); continue
            if '\t' in pl:
                tabrows.append(runs_html(p)); continue
            flush_tab()
            if pl.strip()[:1] in CIRC:
                choices.append(runs_html(p).strip()); continue
            if choices:   # 선지 아래 이어지는 줄(대화 둘째 줄 등)
                choices[-1] += '<br>' + runs_html(p).strip(); continue
            blocks.append({'type': 'line', 'html': runs_html(p)})
        flush_tab()
        # 괄호 그림(①~⑤가 그리기 개체 안 글상자)으로 두 문장씩 묶은 선지: 뒤의 줄을 둘씩 묶어 선지로
        for bi, b in enumerate(blocks):
            if b['type'] == 'line' and re.sub(r'<[^>]+>', '', b['html']).startswith('①②③④⑤'):
                tail = blocks[bi:]
                lines = [re.sub(r'^.*?⑤⑤', '', tail[0]['html'])] + [x['html'] for x in tail[1:] if x['type'] == 'line']
                lines = [l.strip() for l in lines]
                if len(lines) == 10 and not choices:
                    choices = [f'{CIRC[k]} ' + lines[2 * k] + '<br>' + lines[2 * k + 1] for k in range(5)]
                    del blocks[bi:]
                break
        # 선지 앞 괄호 도형(그리기 개체)은 빼고 글만
        choices = [re.sub(r'\s*(<br>)+\s*', '<br>', re.sub(r'<svg.*?</svg>', '', c, flags=re.S)).replace(' <br>', ' ') for c in choices]
        choices = [re.sub(r'^([①-⑤])\s*<br>', r'\1 ', c) for c in choices]
        if len(choices) == 1 and '<svg' in choices[0]:
            raw = '<br>'.join(re.sub(r'<svg.*?</svg>|<span class="draw".*?</span>', '', c, flags=re.S) for c in choices)
            raw = re.sub(r'<div[^>]*>|</div>', '', raw)
            ls = [x.strip() for x in raw.split('<br>') if re.sub(r'<[^>]+>', '', x).strip()]
            ls = [re.sub(r'^[①-⑤\s]+', '', x) for x in ls]
            ls = [x for x in ls if re.sub(r'<[^>]+>', '', x).strip()]
            if len(ls) == 10:
                choices = [f'{CIRC[k]} ' + ls[2 * k] + '<br>' + ls[2 * k + 1] for k in range(5)]
            else:
                print('괄호 선지 줄 수', k, len(ls))
        # 한 줄에 선지 여러 개(① … ② …): 나눔
        sp = []
        for c in choices:
            parts = re.split(r'\s*(?=[①-⑤])', c)
            sp += [x.strip() for x in parts if x.strip()]
        choices = sp
        if 0 < len(choices) < 5:   # 앞 선지는 탭으로 한 줄에, 마지막 선지만 따로 친 경우
            for b in list(blocks):
                if b['type'] == 'tabrows' and all(c[:1] in CIRC for r in b['rows'] for c in r):
                    choices = [c for r in b['rows'] for c in r] + choices; blocks.remove(b)
            choices.sort(key=lambda c: CIRC.index(re.sub(r'<[^>]+>', '', c).strip()[:1]))
        for b in list(blocks):
            if b['type'] == 'tabrows' and not choices and all(r and r[0][:1] in CIRC for r in b['rows']):
                cells = [c for r in b['rows'] for c in r]
                if len(cells) == 5:
                    choices = cells; blocks.remove(b)
        # 탭으로 줄 맞춘 선지 표(① 칸 …)
        if not choices and not ctab:
            for b in blocks:
                if b['type'] == 'tabrows' and sum(1 for r in b['rows'] if r and r[0][:1] in CIRC) >= 5:
                    b['choices'] = True
        out.append({'no': k, 'part': q['part'], 'src': q['src'], 'stem': stem, 'blocks': blocks,
                    'choices': choices, 'ctab': ctab})
    return parts, out


if __name__ == '__main__':
    parts, qs = convert()
    import overrides
    for q in qs:
        if q['no'] in overrides.FIX: overrides.FIX[q['no']](q)
    json.dump({'parts': parts, 'questions': qs}, open(os.path.join(H, 'qb.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(parts, len(qs))
    bad = [q['no'] for q in qs if len(q['choices']) not in (0, 5)]
    print('선지 수 이상:', bad)
    print('선지 없음:', [q['no'] for q in qs if not q['choices'] and not q['ctab'] and not any(b.get('choices') for b in q['blocks'])])
