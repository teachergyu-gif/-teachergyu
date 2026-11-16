"""한글 그리기 개체(gso) → SVG. 묶음·사각형·직선·다각형·타원·그림·글상자를 좌표대로 다시 그린다(회전은 무시)."""
import struct, html
import hwp2json as H
SEC = H.SEC


def sc_info(p, top):
    off = 8 if top else 4
    x, y, gl, lv, iw, ih, cw, ch, fl = struct.unpack_from('<iiHHIIIII', p, off)
    o = off + 32 + 2 + 8    # flag 다음 회전각(2)·중심(8)
    n, = struct.unpack_from('<H', p, o); o += 2
    tx = struct.unpack_from('<6d', p, o); o += 48
    mats = []
    for k in range(n):
        sm = struct.unpack_from('<6d', p, o); o += 48
        rm = struct.unpack_from('<6d', p, o); o += 48
        mats.append((sm, rm))
    line = None
    if len(p) >= o + 13:
        col, w, attr = struct.unpack_from('<IiI', p, o)
        line = (col, w, attr & 0x3F)
        o += 13
        ft, = struct.unpack_from('<I', p, o) if len(p) >= o + 4 else (0,)
        fill = None
        if ft & 1 and len(p) >= o + 8:
            fill, = struct.unpack_from('<I', p, o + 4)
    else:
        fill = None
    return dict(x=x, y=y, iw=iw or 1, ih=ih or 1, cw=cw, ch=ch, tx=tx, mats=mats, line=line, fill=fill)


def col(c):
    return '#%02x%02x%02x' % (c & 255, (c >> 8) & 255, (c >> 16) & 255)


def render(g):
    """g = gso 컨트롤 레코드 번호 → svg 문자열"""
    L = SEC[g][1]; cp = SEC[g][2]
    W, Hh = struct.unpack_from('<II', cp, 16)
    end = g + 1
    while end < len(SEC) and SEC[end][1] > L: end += 1
    out = []

    def apply(m, x, y):
        a, b, c, d, e, f = m
        return a * x + b * y + c, d * x + e * y + f

    def walk(i, mats_parent, top):
        t, l, p = SEC[i]
        cid = p[:4][::-1]
        info = sc_info(p, top)
        # 이 개체 좌표계 → 위쪽 좌표계: 자기 행렬(이동·크기·회전) 다음 부모 행렬
        own = [info['tx']] + [m for pair in info['mats'] for m in pair]
        def T(x, y):
            for m in reversed(own[1:]):
                pass
            # 크기·회전 행렬 먼저, 이동 행렬 마지막
            for sm, rm in info['mats']:
                x, y = apply(sm, x, y); x, y = apply(rm, x, y)
            x, y = apply(info['tx'], x, y)
            for f in mats_parent:
                x, y = f(x, y)
            return x, y
        chain = [T]
        # 자식 범위
        j = i + 1; kids = []; spec = None; lst = None
        while j < end and SEC[j][1] > l:
            if SEC[j][1] == l + 1:
                if SEC[j][0] == 76: kids.append(j)
                elif SEC[j][0] in (78, 79, 80, 82, 83, 85): spec = j
                elif SEC[j][0] == 72: lst = j
            j += 1
        ln = info['line']
        stroke = 'none' if (ln is None or ln[2] == 0 and False) else col(ln[0])
        sw = max(20, abs(ln[1])) if ln else 20
        if ln and ln[1] == 0: stroke = 'none'
        fill = col(info['fill']) if info['fill'] not in (None, 0xFFFFFFFF) and cid != b'$lin' else 'none'
        iw, ih = info['iw'], info['ih']
        if cid == b'$con':
            for k in kids: walk(k, [T] + mats_parent if False else [T], False) if False else walk(k, [lambda x, y, T=T: T(x, y)], False)
            return
        pts = None
        if cid == b'$rec' or cid == b'$pic':
            pts = [(0, 0), (iw, 0), (iw, ih), (0, ih)]
        elif cid == b'$lin' and spec is not None:
            x1, y1, x2, y2 = struct.unpack_from('<iiii', SEC[spec][2], 0)
            a, b = T(x1, y1), T(x2, y2)
            out.append(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}" stroke="{col(ln[0]) if ln else "#000"}" stroke-width="{sw}"/>')
        elif cid in (b'$pol', b'$cur') and spec is not None:
            q = SEC[spec][2]
            n, = struct.unpack_from('<i', q, 0) if cid == b'$pol' else struct.unpack_from('<i', q, 0)
            ps = [struct.unpack_from('<ii', q, 4 + 8 * k) for k in range(n)]
            P = [T(*xy) for xy in ps]
            out.append('<polyline points="' + ' '.join(f'{a:.0f},{b:.0f}' for a, b in P) + f'" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        elif cid == b'$ell':
            P = [T(0, 0), T(iw, ih)]
            cx, cy = (P[0][0] + P[1][0]) / 2, (P[0][1] + P[1][1]) / 2
            out.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{abs(P[1][0] - P[0][0]) / 2:.0f}" ry="{abs(P[1][1] - P[0][1]) / 2:.0f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if pts:
            P = [T(*xy) for xy in pts]
            x0 = min(a for a, b in P); y0 = min(b for a, b in P); x1 = max(a for a, b in P); y1 = max(b for a, b in P)
            if cid == b'$pic' and spec is not None:
                bid, = struct.unpack_from('<H', SEC[spec][2], 71)
                if 0 < bid <= len(H.BINS) and H.BINS[bid - 1]:
                    out.append(f'<image href="IMG/BIN{H.BINS[bid - 1]:04X}.png" x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" preserveAspectRatio="none"/>')
            elif stroke != 'none' or fill != 'none':
                out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            if lst is not None:
                ps = H.children(lst + 1, j, SEC[lst][1])
                inner = H.lines_html(ps)
                lh = SEC[lst][2]
                va = (struct.unpack_from('<I', lh, 4)[0] >> 5) & 3
                jc = {0: 'flex-start', 1: 'center', 2: 'flex-end'}.get(va, 'center')
                out.append(f'<foreignObject x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"><div xmlns="http://www.w3.org/1999/xhtml" class="svgtx" style="height:100%;display:flex;flex-direction:column;justify-content:{jc}">{inner}</div></foreignObject>')

    tops = [k for k in range(g + 1, end) if SEC[k][0] == 76 and SEC[k][1] == L + 1]
    for k in tops: walk(k, [], True)
    mm = W / 7200 * 25.4
    inl = ' inl' if Hh < 2600 else ''
    return (f'<svg class="gso{inl}" viewBox="0 0 {W} {Hh}" style="width:{mm:.1f}mm;max-width:100%;overflow:visible" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(out)}</svg>')
