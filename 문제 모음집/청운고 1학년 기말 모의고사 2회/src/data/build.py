"""청운고 1학년 2학기 기말고사 대비 모의고사 2회: passages.py(지문) + q.txt(문항) + a.txt(정답·해설) → exam.json
문항 형식(부산외고 실전모의고사와 같음)
  N. 발문 / [서답형 n] 발문      문항 시작
  <보 기>, <자 료>, <조 건> …    상자 시작(이어지는 줄이 상자 글),  [상자] = 제목 없는 상자
  @T 이름                        표,  @L 글                       상자 밖 줄(서답형의 (1)·(2) 물음 등)
  @C ㉠|㉡|㉢                     선지 표 머리(뒤 ①~⑤ 줄은 '|'로 칸 나눔)
  ① ⟦묶음 제목⟧선지              선지 위에 묶음 제목(‘(가)와 관련하여,’)
해설 형식: N. ③ 다음 줄부터 해설([오답풀이] 포함). 서답형: [서답형 n] → [모범 답안]/[예시 답안] → 답 줄 → [채점 요소] → * 항목 → ※ 유의"""
import html, json, os, re, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
from passages import SETS as PSETS
CIRC = '①②③④⑤'


def curly(s):
    """곧은따옴표 → 둥근따옴표(태그 속은 건드리지 않음)"""
    def f(t):
        t = re.sub(r'"([^"\n]*)"', r'“\1”', t)
        return re.sub(r"'([^'\n]*)'", r'‘\1’', t)
    return re.sub(r'(<[^>]*>)|([^<]+)', lambda m: m.group(1) or f(m.group(2)), s)


def tbl(rows, cls='in', left=True):
    out = []
    for i, r in enumerate(rows):
        out.append('<tr>' + ''.join(f'<{"th" if (i == 0 or j == 0) else "td"} style="{"text-align:left" if (left and i and j) else ""}">{c}</{"th" if (i == 0 or j == 0) else "td"}>' for j, c in enumerate(r)) + '</tr>')
    return f'<table class="{cls}">' + ''.join(out) + '</table>'


TABLES = {
    'PETT': tbl([['구분', '검출기에 도달한 두 감마선', '도달 시간의 차'],
                 ['㉮', '한 지점에서 방출된 한 쌍으로, 진행 방향의 변화가 없음', '3ns'],
                 ['㉯', '한 지점에서 방출된 한 쌍으로, 그중 하나의 진행 방향이 바뀜', '6ns'],
                 ['㉰', '서로 다른 지점에서 방출된 감마선이 하나씩 도달함', '9ns'],
                 ['㉱', '한 지점에서 방출된 한 쌍으로, 진행 방향의 변화가 없음', '14ns']], cls='in pett', left=False),
    'TRUTH': '<table class="in truth"><tr><th>p</th><th>q</th><th>A</th><th>B</th><th>C</th></tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{x}</td>' for x in r) + '</tr>' for r in ('TTFTF', 'FTFTF', 'TFTTF', 'FFFTF')) + '</table>',
    'G13A': '<table class="in" style="font-size:inherit"><tr><td style="text-align:left;padding:1.4mm 4mm;line-height:1.6">ㄱ. 아무것도 <u>아닌</u> 일에 화내지 마라.<br>ㄴ. <u>아니</u> 땐 굴뚝에 연기 날까.<br>ㄷ. <u>아니</u>, 벌써 도착했어?</td></tr></table>',
    'G13B': '<table class="in" style="width:auto;margin:1.2mm auto"><tr><th style="border:none;background:none;padding:.3mm 1.4mm">품사 분류</th><th style="border:none;background:none;padding:.3mm 1.4mm"></th><th style="border:none;background:none;padding:.3mm 1.4mm">의미</th><th style="border:none;background:none;padding:.3mm 1.4mm"></th><th style="border:none;background:none;padding:.3mm 1.4mm">기능</th><th style="border:none;background:none;padding:.3mm 1.4mm"></th><th style="border:none;background:none;padding:.3mm 1.4mm">형태</th></tr><tr><td style="border:none;background:none;padding:.3mm 1.4mm">ㄱ의 ‘아닌’</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">(\u3000ⓐ\u3000)</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 용언 )</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 가변어 )</td></tr><tr><td style="border:none;background:none;padding:.3mm 1.4mm">ㄴ의 ‘아니’</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 부사 )</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">(\u3000ⓑ\u3000)</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 불변어 )</td></tr><tr><td style="border:none;background:none;padding:.3mm 1.4mm">ㄷ의 ‘아니’</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 감탄사 )</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">( 독립언 )</td><td style="border:none;background:none;padding:.3mm 1.4mm">⊂</td><td style="border:none;background:none;padding:.3mm 1.4mm">(\u3000ⓒ\u3000)</td></tr></table>',
    'G15A': '<table class="in" style="width:auto;margin:1.6mm auto 0;font-size:inherit"><tr><td style="padding:1mm 6mm">동생은 학교에서의 일들을 나한테만 털어놓았다.</td></tr></table>',
    'G16A': '<div class="bogi" style="margin:0"><div class="bl" style="text-align:center"><b>학습 자료</b></div><div class="bl">1. 명사와 명사가 결합한 합성어</div><div class="bl" style="padding-left:1em">㉮ <u>종속적으로 결합한 합성어</u></div><table style="border-collapse:collapse;width:88%;margin:0 0 0 2.2em;font-size:inherit;line-height:1.6"><tr><td style="border:none;padding:0;height:auto;text-align:left;width:25%">거짓말</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">물새</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">산나물</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">안팎</td></tr></table><div class="bl" style="padding-left:1em">㉯ <u>대등하게 결합한 합성어</u></div><table style="border-collapse:collapse;width:88%;margin:0 0 0 2.2em;font-size:inherit;line-height:1.6"><tr><td style="border:none;padding:0;height:auto;text-align:left;width:25%">팔다리</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">마소</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">손발</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">논밭</td></tr></table><div class="bl">2. 관형사와 명사가 결합한 합성어</div><div class="bl" style="padding-left:1em">㉰ <u>종속적으로 결합한 합성어</u></div><table style="border-collapse:collapse;width:88%;margin:0 0 0 2.2em;font-size:inherit;line-height:1.6"><tr><td style="border:none;padding:0;height:auto;text-align:left;width:25%">온종일</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">그이</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">딴소리</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">된장</td></tr></table><div class="bl" style="text-align:center">⋮</div><div class="bl">3. 용언의 관형사형과 명사가 결합한 합성어</div><div class="bl" style="padding-left:1em">㉱ <u>종속적으로 결합한 합성어</u></div><table style="border-collapse:collapse;width:88%;margin:0 0 0 2.2em;font-size:inherit;line-height:1.6"><tr><td style="border:none;padding:0;height:auto;text-align:left;width:25%">건널목</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">볼일</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">젊은이</td><td style="border:none;padding:0;height:auto;text-align:left;width:25%">큰집</td></tr></table><div class="bl" style="text-align:center">⋮</div></div>',
}


def parse_q(path):
    qs = []; q = None; box = None; chead = None
    for line in curly(open(path, encoding='utf8').read()).split('\n') + ['']:
        s = line.rstrip()
        m = re.match(r'^(\d+)\. (.+)$', s) or re.match(r'^\[(서답형 \d+)\] (.+)$', s)
        if m and not (box is not None and '조' in box['title'] and re.match(r'^\d+\. ', s)):
            q = {'no': m.group(1), 'stem': m.group(2), 'bogi': [], 'choices': [], 'extra': None}
            qs.append(q); box = None; chead = None; continue
        if not s:
            continue
        if s.startswith('@C '):
            chead = s[3:].split('|'); box = None; continue
        if s[:1] in CIRC:
            q['choices'].append(s[1:].strip()); box = None; continue
        if re.fullmatch(r'<[^<>]{1,12}>', s) or s == '[상자]':
            box = {'title': '' if s == '[상자]' else s, 'parts': []}
            q['bogi'].append(box); continue
        if s.startswith('@L '):   # 상자 밖 줄
            t = html.escape(s[3:], quote=False).replace('&lt;u&gt;', '<u>').replace('&lt;/u&gt;', '</u>')
            q['bogi'].append({'title': '', 'html': f'<div class="subq">{t}</div>'}); box = None; continue
        mt = re.match(r'^@T (\w+)$', s)
        if mt:
            if box is not None:
                box['parts'].append(('T', TABLES[mt.group(1)]))
            else:
                q['bogi'].append({'title': '', 'html': TABLES[mt.group(1)]})
            continue
        assert box is not None, (q['no'], s)
        box['parts'].append(('L', s))
        q['_chead'] = chead
    for q in qs:
        out = []
        for b in q['bogi']:
            if 'html' in b:
                out.append(b); continue
            if any(k == 'T' for k, _ in b['parts']):
                h = ''.join((f'<div class="bl{" bi" if re.match(r"^([ㄱ-ㅎ]\.|○)", v) else ""}">{v}</div>') if k == 'L' else v for k, v in b['parts'])
                out.append({'title': b['title'] or '<보 기>', 'html': h})
            else:
                out.append({'title': b['title'], 'text': '\n'.join(v for _, v in b['parts'])})
        q['bogi'] = out or None
        assert len(q['choices']) == (0 if q['no'].startswith('서답형') else 5), q['no']
    return qs


def add_ctab(path, qs):
    """@C 머리가 있는 문항: 선지를 표로"""
    cur = None; heads = {}
    for line in curly(open(path, encoding='utf8').read()).split('\n'):
        m = re.match(r'^(\d+)\. ', line)
        if m: cur = m.group(1)
        if line.startswith('@C '): heads[cur] = line[3:].split('|')
    for q in qs:
        h = heads.get(q['no'])
        if not h:
            continue
        rows = '<tr><td></td>' + ''.join(f'<td>{x}</td>' for x in h) + '</tr>'
        rows += ''.join(f'<tr><td>{CIRC[i]}</td>' + ''.join(f'<td>{x.strip()}</td>' for x in c.split('|')) + '</tr>' for i, c in enumerate(q['choices']))
        q['ctab'] = f'<div class="ctabq"><table>{rows}</table></div>'
    for q in qs:
        q.pop('_chead', None)


def parse_a(path):
    exs = []
    for blk in re.split(r'\n(?=(?:\d+\. [①-⑤]|\[서답형 \d+\])\n)', '\n' + curly(open(path, encoding='utf8').read()).strip()):
        blk = blk.strip()
        if not blk:
            continue
        head, *rest = blk.split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        if m:
            exs.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(x for x in rest if x.strip())}); continue
        no = re.match(r'^\[(서답형 \d+)\]$', head).group(1)
        exs.append({'no': no, 'answer': '', 'plain': '\n'.join(x.strip() for x in rest if x.strip())})
    return exs


QS = parse_q(f'{H}/q.txt'); add_ctab(f'{H}/q.txt', QS)
EX = parse_a(f'{H}/a.txt')
assert [e['no'] for e in EX] == [q['no'] for q in QS], 'answers mismatch'
byno = {q['no']: q for q in QS}
SETS = []
used = set()
for a, b, works, head in PSETS:
    qs = [byno[str(n)] for n in range(a, b + 1)]
    for w in works:
        w['lines'] = curly(w['lines'])
    sd = [q['no'] for q in qs if not q['no'].isdigit()]
    rng = f'{a}～{b}' + (', ' + ', '.join(sd) if sd else '')
    SETS.append({'rng': rng, 'works': works, 'questions': qs, **({'head': head} if head else {})})
    used |= {q['no'] for q in qs}
run = []   # 지문 없는 단독 문항: 이어지는 번호끼리 묶어 문항 순서대로 끼워 넣음
for q in QS + [None]:
    if q is not None and q['no'] not in used:
        run.append(q); continue
    if run:
        SETS.append({'rng': ', '.join(x['no'] for x in run), 'works': [], 'questions': run}); run = []
SETS.sort(key=lambda s: int(s['questions'][0]['no']) if s['questions'][0]['no'].isdigit() else 999)
json.dump({'sets': SETS, 'ex': EX, 'issues': []}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', len(EX), '정답', ''.join(e['answer'] for e in EX if e['answer']))
