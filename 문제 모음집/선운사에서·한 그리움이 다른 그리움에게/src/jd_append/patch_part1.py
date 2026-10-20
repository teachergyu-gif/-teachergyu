"""합본 PDF의 PART 01(작품 분석, 한글에서 만든 쪽) 오탈자를 PDF에서 바로 고친다.
고칠 줄의 글자를 지우고(배경·괘선·형광 표시는 그대로), 같은 쪽에 박힌 글꼴의 글리프로 같은 자리·간격에 다시 쓴다
(가운데 맞춘 칸은 가운데를 유지). 글꼴에 없는 글자(p.8 HY헤드라인의 '길')가 든 줄은 비슷한 굵은 고딕(Noto Sans CJK KR Bold,
장평을 원래 글자 폭에 맞춤)으로 다시 쓴다.
사용: python3 patch_part1.py 입력.pdf 출력.pdf"""
import re, sys
import pymupdf

src, out = sys.argv[1], sys.argv[2]
d = pymupdf.open(src)
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

# (쪽, 고칠 줄의 원래 글, 새 글, 가운데 맞춤)
FIX = [
    (2, '이별로 인한 슬프모가 고통의 순간성에 대한 소망', '이별로 인한 슬픔과 고통의 순간성에 대한 소망', False),
    (2, '꽃은 힘들게 피지만, 지는건 한참이더군.', '꽃은 힘들게 피지만, 지는 건 잠깐이더군.', True),   # 시 1연은 ‘지는 건 잠깐이더군’
    (2, '꽃이 지는건 쉬워도, 잊는 건', '꽃이 지는 건 쉬워도, 잊는 건', True),
    (3, '골고루 쳐다 볼 틈 없이', '골고루 쳐다볼 틈 없이', False),
    (3, '잊는 것또한 그렇게', '잊는 것 또한 그렇게', False),
    (4, '골고루 쳐다 볼틈 없이', '골고루 쳐다볼 틈 없이', False),   # 글자 자리로만 띄어 있던 ‘볼 틈’
    (8, '추운 골목, 어느 겨울', '추운 길목, 어느 겨울', False),
]


def tounicode(xref):
    m = re.search(r'/ToUnicode (\d+) 0 R', d.xref_object(xref))
    s = d.xref_stream(int(m.group(1))).decode('latin1')
    mp = {}
    for blk in re.findall(r'beginbfchar(.*?)endbfchar', s, re.S):
        for a, b in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            mp[chr(int(b, 16))] = a.upper().zfill(4)
    for blk in re.findall(r'beginbfrange(.*?)endbfrange', s, re.S):
        for a, b, c in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            for k in range(int(a, 16), int(b, 16) + 1):
                mp[chr(int(c, 16) + k - int(a, 16))] = '%04X' % k
    return mp


def find(pg, text):
    for b in pg.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            ch = [c for s in l['spans'] for c in s['chars']]
            while ch and ch[-1]['c'] == ' ':
                ch = ch[:-1]
            if ''.join(c['c'] for c in ch) == text:
                for sp in l['spans']:
                    for c in sp['chars']:
                        c['font'] = sp['font']
                return l['spans'][0], ch
    raise SystemExit(f'못 찾음: {text}')


def kind(c):
    return 'sp' if c == ' ' else (c if c in ',.' else 'h')


for pn, old, new, center in FIX:
    pg = d[pn - 1]
    s, ch = find(pg, old)
    x0, y = ch[0]['origin']
    adv = {}
    for a, b in zip(ch, ch[1:]):
        adv.setdefault(kind(a['c']), []).append(b['origin'][0] - a['origin'][0])
    adv = {k: sum(v) / len(v) for k, v in adv.items()}
    H = adv['h']
    adv.setdefault('sp', 4.2); adv.setdefault(',', H / 3); adv.setdefault('.', H / 3)
    if pn == 4:   # ‘볼틈’은 글자 자리로 띄어 있었음 → 띄어쓰기 간격은 3쪽과 같게
        adv['sp'] = 4.2
    width = lambda t: sum(adv[kind(c)] for c in t[:-1]) + H
    if center:
        x0 += (width(old) - width(new)) / 2
    xs, x = [], x0
    for c in new:
        xs.append(x); x += adv[kind(c)]
    font = next(f for f in pg.get_fonts(full=True) if f[3].endswith(s['font']))
    cmap = tounicode(font[0])
    r = pymupdf.Rect(ch[0]['bbox']) | pymupdf.Rect(ch[-1]['bbox'])
    # 4쪽 ‘틈 없이’ 형광 표시: 글자와 함께 옮김
    shift = xs[new.index('틈')] - ch[old.index('틈')]['origin'][0] if pn == 4 else 0
    pg.add_redact_annot(pymupdf.Rect(r.x0 - 0.5, r.y0 + 0.8, r.x1 + 0.5, r.y1 - 0.8), fill=False)
    pg.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    if shift:
        for dr in pg.get_drawings():
            q = dr['rect']
            if dr.get('fill') and abs(q.y0 - r.y0) < 3 and q.x0 > r.x0 and q.x1 <= r.x1 + 2:
                # 왼쪽으로 옮김(shift < 0): 앞쪽에 같은 색을 늘이고 뒤쪽 남는 부분은 흰색으로 덮음(글자는 그 뒤에 씀)
                pg.draw_rect(pymupdf.Rect(q.x0 + shift, q.y0, q.x0 + 0.2, q.y1), color=None, fill=dr['fill'], width=0)
                pg.draw_rect(pymupdf.Rect(q.x1 + shift, q.y0, q.x1 + 0.2, q.y1), color=None, fill=(1, 1, 1), width=0)
    # 문장 부호처럼 원래 다른 글꼴(한글 파일의 Times 등, WinAnsi)로 찍힌 글자는 그 글꼴 그대로
    other = {c['c']: c['font'] for c in ch if c['c'] not in cmap and c['c'] != ' '}
    res = {f[3].split('+')[-1]: f for f in pg.get_fonts(full=True)}
    if all(c in cmap or c in other or c == ' ' for c in new):
        Hh = pg.rect.height
        ops = ['q 0 g BT']
        for c, xx in zip(new, xs):
            if c == ' ':
                continue
            if c in cmap:
                ops.append(f'/{font[4]} {s["size"]:.4f} Tf 1 0 0 1 {xx:.3f} {Hh - y:.3f} Tm <{cmap[c]}> Tj')
            else:
                f2 = res[other[c]]
                code = f'<{tounicode(f2[0])[c]}>' if f2[2] == 'Type0' else f'({c})'
                ops.append(f'/{f2[4]} {s["size"]:.4f} Tf 1 0 0 1 {xx:.3f} {Hh - y:.3f} Tm {code} Tj')
        ops.append('ET Q')
        xref = d.get_new_xref()
        d.update_object(xref, '<<>>')
        d.update_stream(xref, '\n'.join(ops).encode())
        c = d.xref_get_key(pg.xref, 'Contents')
        arr = c[1] if c[0] == 'array' else f'[{c[1]}]'
        d.xref_set_key(pg.xref, 'Contents', arr[:-1] + f' {xref} 0 R]')
    else:   # 박힌 글꼴에 없는 글자 → 굵은 고딕, 원래 글자 폭(H)에 맞춰 장평을 줄임
        fz = s['size'] * 0.97
        for c, xx in zip(new, xs):
            if c != ' ':
                p = pymupdf.Point(xx, y)
                pg.insert_text(p, c, fontsize=fz, fontname='nsb', fontfile=BOLD, color=(0, 0, 0), morph=(p, pymupdf.Matrix(H / fz, 1)))
    print(pn, old, '→', new)
d.save(out, garbage=3, deflate=True)
