"""원본 문제 PDF(raw/)의 오탈자·발문 오류를 고쳐 raw/fixed/에 저장(사용자 지정, 2026-11).
고칠 글자만 흰색으로 덮고 같은 글꼴(나눔명조, 원본에 쓰인 글꼴)로 다시 쓴다. 단어 16번은 발문이 두 줄이 되어 그 아래 단 내용을 한 줄 내린다.
사용: python3 fix_raw.py"""
import os, statistics
import pymupdf

H = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = f'{H}/raw', f'{H}/raw/fixed'
FONTS = {'NanumMyeongjo': '/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf',
         'NanumMyeongjoBold': '/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf'}
SEEN = {}
FOBJ = {k: pymupdf.Font(fontfile=v) for k, v in FONTS.items()}
PITCH = 15.2   # 줄 간격(pt)


def find_span(page, start):
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = ''.join(c['c'] for c in s['chars'])
                if start in t:
                    return s, t
    raise ValueError(start)


def metrics(s):
    """원본 줄의 글자 폭: 한글 한 자 폭, 띄어쓰기 폭, 가로 비율"""
    cs = s['chars']
    adv = [(cs[i]['c'], cs[i + 1]['origin'][0] - cs[i]['origin'][0]) for i in range(len(cs) - 1)]
    han = statistics.median([a for c, a in adv if '가' <= c <= '힣'])
    sp = [a for c, a in adv if c == ' ']
    nat = FOBJ[s['font']].text_length('가', s['size'])
    global SEEN   # 원본 줄에 있던 글자는 그 글자의 원래 폭을 그대로 씀
    SEEN = {}
    for c, a in adv:
        SEEN.setdefault(c, []).append(a)
    SEEN = {c: statistics.median(v) for c, v in SEEN.items() if c != ' '}
    return han, (statistics.median(sp) if sp else han * .45), han / nat


def font_key(page, s):
    name = 'B' if 'Bold' in s['font'] else 'R'
    page.insert_font(fontname='nm' + name, fontfile=FONTS[s['font']])
    return 'nm' + name


def draw(page, s, x, y, text, han, sp, k, fit_to=None):
    """text를 x부터 원본과 같은 글자 폭으로 쓴다. fit_to가 있으면 띄어쓰기 폭을 조정해 그 자리에서 끝나게(양쪽 맞춤)."""
    fk = font_key(page, s)
    f = FOBJ[s['font']]
    def adv(c):
        if c == ' ':
            return sp
        if c in SEEN and not ('가' <= c <= '힣'):
            return SEEN[c]
        if '가' <= c <= '힣' or c in '㉠㉡①②③④⑤〈〉':
            return han
        return f.text_length(c, s['size']) * k
    widths = [adv(c) for c in text]
    if fit_to is not None:
        n = text.count(' ')
        extra = (fit_to - x - sum(widths) + (sp if text.endswith(' ') else 0)) / max(n - (1 if text.endswith(' ') else 0), 1)
        widths = [w + extra if c == ' ' else w for c, w in zip(text, widths)]
    for c, w in zip(text, widths):
        if c != ' ':
            page.insert_text((x, y), c, fontname=fk, fontsize=s['size'], color=(0, 0, 0))
        x += w
    return x


def white(page, r):
    page.draw_rect(pymupdf.Rect(*r), color=None, fill=(1, 1, 1), overlay=True)


def replace_chars(page, start, old, new):
    """같은 글자 수로 바꿈: 바뀌는 글자 자리만 덮고 다시 씀"""
    s, t = find_span(page, start)
    i = t.index(old)
    han, sp, k = metrics(s)
    for j, (a, b) in enumerate(zip(old, new)):
        if a != b:
            c = s['chars'][i + j]
            x0, y0, x1, y1 = c['bbox']
            white(page, (x0 - .2, y0, x1 + .2, y1))
            draw(page, s, c['origin'][0], c['origin'][1], b, han, sp, k)


def redraw_tail(page, start, frm, new_tail, justify=False):
    """frm 글자부터 줄 끝까지를 new_tail로 다시 씀(justify면 원래 줄 끝에 맞춤)"""
    s, t = find_span(page, start)
    i = t.index(frm)
    han, sp, k = metrics(s)
    c0 = s['chars'][i]
    right = max(c['bbox'][2] for c in s['chars'] if c['c'] != ' ')
    white(page, (c0['bbox'][0] - .3, s['bbox'][1] - .5, s['bbox'][2] + 1, s['bbox'][3] + .8))
    return s, draw(page, s, c0['origin'][0], c0['origin'][1], new_tail, han, sp, k, fit_to=right if justify else None)


os.makedirs(OUT, exist_ok=True)

# ───── 품사 ─────
d = pymupdf.open(f'{RAW}/1_품사.pdf')
replace_chars(d[4], '내일가지는', '내일가지는', '내일까지는')                       # 6번 <보기>
replace_chars(d[17], '눈길의 걸어', '눈길의', '눈길을')                              # 28번 [예문] ㉢ⓑ
redraw_tail(d[17], "결합 유형에는 '격 조사격", '결', "결합 유형에는 '격 조사-격 조사', '격 조사-보조사', '보조사-격 조사', ", justify=True)   # 29번
redraw_tail(d[17], "'보조사-보조사'가 있다.", "'", "'보조사-보조사'가 있다. 예컨대 '형에게조차도'의 '에게조차'는 ", justify=True)
redraw_tail(d[18], '‘덥고’는어간', '②', '② ‘더운’과 ‘덥고’는 어간의 의미가 같지만 형태를 하나로 고정하여 ', justify=True)   # 31번 ②
d.save(f'{OUT}/1_품사.pdf', garbage=3, deflate=True)

# ───── 단어 ─────
d = pymupdf.open(f'{RAW}/2_단어.pdf')
replace_chars(d[3], '연관 지어 <자료>', '자료', '보기')                            # 5번 발문
redraw_tail(d[8], '14. <보기>의 ㉠, ㉡', '㉠', '㉠에 해당하는 예로 적절하지 않은 것은?')   # 14번 발문
# 16번 발문: 두 줄 → 그 아래 오른쪽 단 내용을 한 줄 내림
src = pymupdf.open(f'{RAW}/2_단어.pdf')
pg = d[9]
s, t = find_span(pg, '16. <보기>에 따라')
TOP, BOT = s['bbox'][3] + 1.5, 380
white(pg, (299.5, TOP, 572, BOT + PITCH))
pg.show_pdf_page(pymupdf.Rect(299.5, TOP + PITCH, 572, BOT + PITCH), src, 9, clip=pymupdf.Rect(299.5, TOP, 572, BOT))
s, x = redraw_tail(pg, '16. <보기>에 따라', '>', ' 1>의 ㉠에 해당하는 것만을 <보기 2>에서')
han, sp, k = metrics(s)
lt = next(c for c in s['chars'] if c['c'] == '<')
draw(pg, s, lt['origin'][0], s['origin'][1] + PITCH, '있는 대로 고른 것은?', han, sp, k)
d.save(f'{OUT}/2_단어.pdf', garbage=3, deflate=True)
print('ok')
