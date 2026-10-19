"""양식 HWP(바탕쪽·1쪽 머리·목차 틀 유지)에 본문 문단을 채워 새 HWP를 만든다."""
import struct, copy
from hwplib import parse_records, dump_records, inflate, deflate, read_hwp, write_cfb

T_PARA, T_TEXT, T_CS, T_SEG = 66, 67, 68, 69
DI_IDMAP, DI_CS, DI_PS = 17, 21, 25

# 양식 스타일 번호 → (style id, parashape, charshape)
ST = {
    'normal': (0, 3, 5), 'q': (1, 32, 4), 'ch': (2, 8, 3), 'bogi': (3, 2, 3), 'pass': (4, 7, 3),
    'head': (5, 33, 17), 'author': (11, 0, 33), 'box': (26, 42, 43),
}
LINESEG = bytes.fromhex('00000000be0b00007e0400007e040000d2030000b002000000000000ac7d000000000600')


class Doc:
    def __init__(self, tpl):
        self.s = read_hwp(tpl)
        self.di = parse_records(inflate(self.s['DocInfo']))
        self.sec = parse_records(inflate(self.s['BodyText/Section0']))
        self._csmap = {}
        self._psmap = {}

    # ---- DocInfo: 글자 모양/문단 모양 복제 추가 ----
    def _idmap(self):
        return [r for r in self.di if r[0] == DI_IDMAP][0]

    def _clone(self, tag, idx, mod, slot):
        recs = [i for i, r in enumerate(self.di) if r[0] == tag]
        p = bytearray(self.di[recs[idx]][2])
        mod(p)
        lvl = self.di[recs[idx]][1]
        self.di.insert(recs[-1] + 1, [tag, lvl, bytes(p)])
        im = self._idmap()
        cnt = list(struct.unpack('<%di' % (len(im[2]) // 4), im[2]))
        new = cnt[slot]; cnt[slot] += 1
        im[2] = struct.pack('<%di' % len(cnt), *cnt)
        return new

    def cs(self, base, underline=False, bold=False, size=None):
        key = (base, underline, bold, size)
        if key == (base, False, False, None):
            return base
        if key not in self._csmap:
            def mod(p):
                off = 7 * 2 + 7 * 4  # fonts(7*u16) ratios/spacings/relsizes/offsets(7*u8 each)
                if size:
                    struct.pack_into('<i', p, off, size)
                a, = struct.unpack_from('<I', p, off + 4)
                if underline:
                    a = (a & ~0xC) | 0x4
                if bold:
                    a |= 0x2
                struct.pack_into('<I', p, off + 4, a)
            self._csmap[key] = self._clone(DI_CS, base, mod, 9)
        return self._csmap[key]

    def ps_word(self, base):
        """같은 문단 모양에 한글 줄 나눔을 '어절' 단위로(글자 단위 끊김 방지)."""
        key = ('word', base)
        if key not in self._psmap:
            def mod(p):
                a, = struct.unpack_from('<I', p, 0)
                struct.pack_into('<I', p, 0, a & ~0x80)
            self._psmap[key] = self._clone(DI_PS, base, mod, 13)
        return self._psmap[key]

    def ps(self, base, indent=None, left=None, align=None, top=None, bottom=None, right=None):
        key = (base, indent, left, align, top, bottom, right)
        if key not in self._psmap:
            def mod(p):
                a, = struct.unpack_from('<I', p, 0)
                if align is not None:  # 0 both,1 left,2 right,3 center
                    a = (a & ~(0x7 << 2)) | (align << 2); struct.pack_into('<I', p, 0, a)
                if left is not None: struct.pack_into('<i', p, 4, left)
                if right is not None: struct.pack_into('<i', p, 8, right)
                if indent is not None: struct.pack_into('<i', p, 12, indent)
                if top is not None: struct.pack_into('<i', p, 16, top)
                if bottom is not None: struct.pack_into('<i', p, 20, bottom)
            self._psmap[key] = self._clone(DI_PS, base, mod, 13)
        return self._psmap[key]

    # ---- 본문 문단 ----
    @staticmethod
    def para(runs, style, ps, level=0, brk=0, last=False):
        """runs: [(text, charshape)]"""
        text = ''.join(t for t, _ in runs) + '\r'
        n = len(text)
        css, pos = [], 0
        for t, c in runs:
            if not t:
                continue
            if not css or css[-1][1] != c:
                css.append((pos, c))
            pos += len(t)
        if not css:
            css = [(0, runs[0][1] if runs else 3)]
        hdr = struct.pack('<IIHBBHHHIH', n | (0x80000000 if last else 0), 0, ps, style, brk, len(css), 0, 1, 0, 0)
        recs = [[T_PARA, level, hdr]]
        if n > 1:
            recs.append([T_TEXT, level + 1, text.encode('utf-16le')])
        recs.append([T_CS, level + 1, b''.join(struct.pack('<II', a, b) for a, b in css)])
        recs.append([T_SEG, level + 1, LINESEG])
        return recs

    def p(self, kind, runs, brk=0, **psmod):
        st, ps, cs = ST[kind]
        if isinstance(runs, str):
            runs = [(runs, cs)]
        runs = [(t, cs if c is None else c) for t, c in runs]
        if psmod:
            ps = self.ps(ps, **psmod)
        return self.para(runs, st, ps, brk=brk)

    # ---- 양식 안 글자 바꾸기 (문단 텍스트 치환, 글자모양 위치 보정) ----
    def replace_text(self, old, new):
        for i, (t, l, p) in enumerate(self.sec):
            if t != T_TEXT:
                continue
            s = p.decode('utf-16le', 'surrogatepass')
            k = s.find(old)
            if k < 0:
                continue
            s2 = s[:k] + new + s[k + len(old):]
            d = len(new) - len(old)
            self.sec[i][2] = s2.encode('utf-16le', 'surrogatepass')
            # header
            j = i - 1
            while self.sec[j][0] != T_PARA:
                j -= 1
            h = bytearray(self.sec[j][2]); n, = struct.unpack_from('<I', h, 0)
            struct.pack_into('<I', h, 0, (n & 0x80000000) | ((n & 0x7FFFFFFF) + d)); self.sec[j][2] = bytes(h)
            # char shape positions
            c = i + 1
            if self.sec[c][0] == T_CS:
                arr = list(struct.unpack('<%dI' % (len(self.sec[c][2]) // 4), self.sec[c][2]))
                for q in range(0, len(arr), 2):
                    if arr[q] > k:
                        arr[q] += d
                self.sec[c][2] = struct.pack('<%dI' % len(arr), *arr)
            return True
        raise KeyError(old)

    def save(self, out, body, prvtext='', first_brk=4):
        """body: 문단 레코드 목록. 양식의 '다음 글을 읽고…' 문단 자리에 넣고, 마지막 MEMO 쪽은 유지."""
        tops = [i for i, r in enumerate(self.sec) if r[0] == T_PARA and r[1] == 0]
        # 양식: [0]=구역·바탕쪽·1쪽 머리·목차, [1]=빈 문단, [2]=쪽 나눔+제목 상자, [3]='다음 글을 읽고…', [4]=MEMO
        head = self.sec[:tops[2]]   # 2쪽 제목 상자(｢｣ 문제 은행)는 넣지 않음
        h = bytearray(body[0][2]); h[11] = first_brk; body[0][2] = bytes(h)   # 첫 문단에서 쪽 나눔(0이면 1쪽에서 바로 시작)
        memo = self.sec[tops[4]:]
        sec = head + body + memo
        self.s['BodyText/Section0'] = deflate(dump_records(sec))
        self.s['DocInfo'] = deflate(dump_records(self.di))
        if prvtext:
            self.s['PrvText'] = prvtext[:1000].encode('utf-16le')
        write_cfb(out, self.s)


def table_records(d_para, rows, widths, level=0, bf=6, cs=3, ps=3, spans=None, inst=0x13572468):
    """간단한 표(글자처럼 취급). rows: [[셀 글자, …]], spans: {(r,c):(rowspan,colspan)}, 생략 셀은 None."""
    spans = spans or {}
    nrows, ncols = len(rows), len(widths)
    W = sum(widths)
    H = 1400 * nrows
    text = '\x0b' + b' lbt'.decode('utf-16le') + '\0' * 4 + '\x0b' + '\r'
    hdr = struct.pack('<IIHBBHHHIH', len(text), 0x800, ps, 0, 0, 1, 0, 1, 0, 0)
    recs = [[T_PARA, level, hdr], [T_TEXT, level + 1, text.encode('utf-16le')],
            [T_CS, level + 1, struct.pack('<II', 0, cs)], [T_SEG, level + 1, LINESEG]]
    ch = struct.pack('<4sIiiIIi4hI8x', b' lbt', 0x082A2211, 0, 0, W, H, 0, 0, 0, 0, 0, inst)
    recs.append([71, level + 1, ch])
    cells = []
    per_row = []
    for r in range(nrows):
        k = 0
        for c in range(ncols):
            if rows[r][c] is None:
                continue
            rs, cspan = spans.get((r, c), (1, 1))
            cells.append((r, c, rs, cspan, rows[r][c])); k += 1
        per_row.append(k)
    tb = struct.pack('<IHHH4H', 0x04000004, nrows, ncols, 0, 141, 141, 141, 141)
    tb += b''.join(struct.pack('<H', k) for k in per_row) + struct.pack('<HH', bf, 0)
    recs.append([77, level + 2, tb])
    for r, c, rs, cspan, txt in cells:
        w = sum(widths[c:c + cspan])
        lines = txt.split('\n') if txt else ['']
        lh = struct.pack('<HHI', len(lines), 0, 0x01000020)
        lh += struct.pack('<HHHHII4HHI9x', c, r, cspan, rs, w, 1400 * rs, 141, 141, 141, 141, bf, w)
        recs.append([72, level + 2, lh])
        for i, l in enumerate(lines):
            recs += d_para(l, i == len(lines) - 1, level + 2)
    return recs


def cold_para(runs, ncols, style, ps, brk, level=0, spacing=2268):
    """다단 설정을 바꾸는 문단: 문단 앞에 '단 정의'(cold) 조판 부호를 넣는다(brk에 0x02 포함)."""
    ctrl = '\x02' + b'dloc'.decode('utf-16le') + '\0' * 4 + '\x02'
    body = ''.join(t for t, _ in runs)
    text = ctrl + body + '\r'
    css, pos = [(0, runs[0][1] if runs else 3)], len(ctrl)
    for t, c in runs:
        if not t: continue
        if css[-1][1] != c:
            css.append((pos, c))
        pos += len(t)
    hdr = struct.pack('<IIHBBHHHIH', len(text), 0x4, ps, style, brk, len(css), 0, 1, 0, 0)
    attr = (ncols << 2) | 0x1000   # 단 너비 동일
    cold = b'dloc' + struct.pack('<HH', attr, spacing if ncols > 1 else 0) + b'\0' * 8
    return [[T_PARA, level, hdr], [T_TEXT, level + 1, text.encode('utf-16le')],
            [T_CS, level + 1, b''.join(struct.pack('<II', a, b) for a, b in css)],
            [T_SEG, level + 1, LINESEG], [71, level + 1, cold]]


def remove_toc(d):
    """1쪽 목차 표(구역 첫 문단의 마지막 표 조판 부호)를 지운다: 표 레코드, 문단 글자 속 부호 8자, 글자 수·글자 모양 위치."""
    sec = d.sec
    tops = [i for i, r in enumerate(sec) if r[0] == T_PARA and r[1] == 0]
    a, b = tops[0], tops[1]
    k = max(i for i in range(a, b) if sec[i][0] == 71 and sec[i][1] == 1 and sec[i][2][:4] == b' lbt')
    assert any(r[0] == T_TEXT and '[문제 은행]' in r[2].decode('utf-16le', 'ignore') for r in sec[k:b]), '목차 표가 아님'
    del sec[k:b]
    ti = a + 1
    t = sec[ti][2].decode('utf-16le', 'surrogatepass')
    mark = '\x0b' + b' lbt'.decode('utf-16le')
    pos = t.rfind(mark)
    assert pos >= 0 and t[pos + 7] == '\x0b'
    sec[ti][2] = (t[:pos] + t[pos + 8:]).encode('utf-16le', 'surrogatepass')
    h = bytearray(sec[a][2]); n, = struct.unpack_from('<I', h, 0)
    struct.pack_into('<I', h, 0, (n & 0x80000000) | ((n & 0x7FFFFFFF) - 8)); sec[a][2] = bytes(h)
    c = ti + 1
    if sec[c][0] == T_CS:
        arr = list(struct.unpack('<%dI' % (len(sec[c][2]) // 4), sec[c][2]))
        for q in range(0, len(arr), 2):
            if arr[q] > pos:
                arr[q] = max(pos, arr[q] - 8)
        sec[c][2] = struct.pack('<%dI' % len(arr), *arr)


def remove_page1(d, keep=(b'secd', b'cold', b'foot')):
    """구역 첫 문단의 1쪽 전용 개체(1쪽 머리 표·국어 영역 그림·1쪽 쪽 상자·쪽 감추기·목차)를 모두 지운다.
    구역·단·꼬리말 정의(keep)만 남긴다. 레코드, 문단 글자 속 부호(8자), 글자 수, 글자 모양 위치를 함께 고친다."""
    sec = d.sec
    tops = [i for i, r in enumerate(sec) if r[0] == T_PARA and r[1] == 0]
    a, b = tops[0], tops[1]
    ctl = [i for i in range(a, b) if sec[i][0] == 71 and sec[i][1] == 1]
    spans = [(k, (ctl[j + 1] if j + 1 < len(ctl) else b), sec[k][2][:4][::-1]) for j, k in enumerate(ctl)]
    ti = a + 1
    t = sec[ti][2].decode('utf-16le', 'surrogatepass')
    # 글자 속 확장 조판 부호(8자) 위치, 레코드 순서와 같음
    pos, i = [], 0
    while i < len(t):
        if ord(t[i]) < 32 and ord(t[i]) not in (0, 10, 13) and ord(t[i]) < 24:
            pos.append(i); i += 8
        else:
            i += 1
    assert len(pos) == len(spans), (len(pos), len(spans))
    drop = [j for j, (_, _, cid) in enumerate(spans) if cid not in keep]
    for j in reversed(drop):
        k, e, _ = spans[j]
        del sec[k:e]
    cut = sorted(pos[j] for j in drop)
    t2 = ''.join(ch for q, ch in enumerate(t) if not any(c <= q < c + 8 for c in cut))
    sec[ti][2] = t2.encode('utf-16le', 'surrogatepass')
    h = bytearray(sec[a][2]); n, = struct.unpack_from('<I', h, 0)
    struct.pack_into('<I', h, 0, (n & 0x80000000) | ((n & 0x7FFFFFFF) - 8 * len(cut))); sec[a][2] = bytes(h)
    c = ti + 1
    if sec[c][0] == T_CS:
        arr = list(struct.unpack('<%dI' % (len(sec[c][2]) // 4), sec[c][2]))
        for q in range(0, len(arr), 2):
            arr[q] -= 8 * sum(1 for x in cut if x < arr[q])
        sec[c][2] = struct.pack('<%dI' % len(arr), *arr)
    return [spans[j][2] for j in drop]
