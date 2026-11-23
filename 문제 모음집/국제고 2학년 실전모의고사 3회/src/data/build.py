"""국제고 2학년 실전모의고사 3회: passages.py(지문) + q.txt(문항) + a.txt(정답·해설) → exam.json
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
    'FALL': tbl([['물체', '중력', '부력', '특징'], ['A', '0.5N', '0.1N', '-'], ['B', '0.5N', '0.3N', 'A와 질량은 같지만 부피가 훨씬 큼'],
                 ['C', '2N', '0.1N', '낙하 방향에서 본 단면적이 크고 빠르게 떨어짐']], left=False),
    'STR': tbl([['', '압축 강도', '인장 강도'], ['X', '30', '3'], ['Y', '250', '250']], left=False),
    'YOUTH': tbl([['항목', '내용'], ['취업자', '1년 전보다 14만 3천 명 감소 (46개월 연속 감소)'],
                  ['고용률', '44.1% (1년 전보다 1.0%p 하락, 28개월째 하락)'],
                  ['실업률', '5.4% (1년 전보다 0.5%p 상승, 4년 만에 최고)'],
                  ['경제활동<br>참가율', '46.6% (1년 전보다 0.8%p 하락, 2020년 8월 이후 최저)']]),
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
                h = ''.join(f'<div class="bl">{v}</div>' if k == 'L' else v for k, v in b['parts'])
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
    if b == 20:
        qs.append(byno['서답형 1'])
    for w in works:
        w['lines'] = curly(w['lines'])
    sd = [q['no'] for q in qs if not q['no'].isdigit()]
    rng = f'{a}～{b}' + (', ' + ', '.join(sd) if sd else '')
    SETS.append({'rng': rng, 'works': works, 'questions': qs, **({'head': head} if head else {})})
    used |= {q['no'] for q in qs}
rest = [q for q in QS if q['no'] not in used]   # 서답형 2·3: 지문 없는 단독 문항
SETS.append({'rng': ', '.join(q['no'] for q in rest), 'works': [], 'questions': rest})
json.dump({'sets': SETS, 'ex': EX, 'issues': []}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', len(EX), '정답', ''.join(e['answer'] for e in EX if e['answer']))
