"""부산외고 1학년 실전모의고사 1회: questions.txt(문항) + answers.txt(정답·해설) → exam.json
문항 형식
  N. 발문                       문항 시작
  <…>                           상자 시작(줄 전체가 <보 기>, <탐 구> 같은 제목). 이어지는 줄이 상자 글
  [상자]                        제목 없는 상자 시작
  @T 이름                       표(상자 안이면 상자 속, 밖이면 따로)
  ①~⑤                          선지
해설 형식
  N. ③                          정답, 다음 줄부터 해설(‘[오답풀이]’ 포함)"""
import json, os, re
H = os.path.dirname(os.path.abspath(__file__))
CIRC = '①②③④⑤'
COLS = ['아음', '설음', '순음', '치음', '후음', '반설음', '반치음']


def tbl(rows, head=True, cls=''):
    out = []
    for i, r in enumerate(rows):
        tag = 'th' if (head and i == 0) else 'td'
        out.append('<tr>' + ''.join(f'<{"th" if (tag == "th" or j == 0) else "td"}>{c}</{"th" if (tag == "th" or j == 0) else "td"}>' for j, c in enumerate(r)) + '</tr>')
    return f'<table class="{cls}">' + ''.join(out) + '</table>'


def mo_empty(title):
    return (f'<div style="text-align:center;font-weight:700;margin:1mm 0">{title}</div>'
            + tbl([['', '전설 평순', '전설 원순', '후설 평순', '후설 원순'], ['고모음', '', '', '', ''], ['중모음', '', '', '', ''], ['저모음', '', '', '', '']]))


TABLES = {
    'JA': tbl([[''] + COLS] + [[r] + [''] * 7 for r in ('전청', '차청', '전탁', '불청불탁')]),
    'JE': tbl([['구분'] + COLS] + [[r] + [''] * 7 for r in ('기본자', '가획자', '이체자')]),
    'MO': mo_empty('&lt;중세국어 단모음&gt;') + mo_empty('&lt;현대국어 단모음&gt;'),
    'SY': tbl([['', '허용되는 자음의 개수', '허용되는 자음의 종류'], ['초성 제약', '최대 1개', '‘ㅇ’을 제외한 18종류'], ['종성 제약', '최대 1개', '‘ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅇ’']], cls='in'),
    'DM': tbl([['', '전설 모음', '후설 평순 모음', '후설 원순 모음'], ['고모음', 'ㅣ', 'ㅡ', 'ㅜ'], ['중모음', '', 'ㅓ', 'ㅗ'], ['저모음', '', 'ㅏ', 'ㆍ']]),
}

qs = []; q = None; box = None
for line in open(f'{H}/questions.txt', encoding='utf8').read().split('\n') + ['']:
    s = line.rstrip()
    m = re.match(r'^(\d+)\. (.+)$', s)
    if m and not s[:1] in CIRC:
        q = {'no': m.group(1), 'stem': m.group(2), 'bogi': [], 'choices': [], 'extra': None}
        qs.append(q); box = None; continue
    if not s:
        continue
    if s[:1] in CIRC:
        q['choices'].append(s[1:].strip()); box = None; continue
    if re.fullmatch(r'<[^<>]{1,12}>', s) or s == '[상자]':
        box = {'title': '' if s == '[상자]' else s, 'parts': []}
        q['bogi'].append(box); continue
    mt = re.match(r'^@T (\w+)$', s)
    if mt:
        if box is not None:
            box['parts'].append(('T', TABLES[mt.group(1)]))
        else:
            q['bogi'].append({'title': '', 'html': TABLES[mt.group(1)]})
        continue
    assert box is not None, (q['no'], s)
    box['parts'].append(('L', s))

# 상자 정리: 글만 있으면 text, 표가 섞이면 html
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
    assert len(q['choices']) == 5, q['no']

exs = []
for blk in re.split(r'\n(?=\d+\. [①-⑤]\n)', '\n' + open(f'{H}/answers.txt', encoding='utf8').read().strip()):
    blk = blk.strip()
    if not blk:
        continue
    head, *rest = blk.split('\n')
    m = re.match(r'^(\d+)\. ([①-⑤])$', head)
    exs.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(rest)})
assert [e['no'] for e in exs] == [q['no'] for q in qs], 'answers mismatch'
NL = open(f'{H}/nonlit.txt', encoding='utf8').read().strip()   # 2024년 7월 고3 더프리미엄 모의고사 [4~7] 지문(4~6번 문항만 수록)
k = next(i for i, x in enumerate(qs) if x['no'] == '32')
SETS = [{'rng': '', 'works': [], 'questions': qs[:k]},
        {'rng': '32～34', 'works': [{'label': '', 'lines': NL, 'author': ''}], 'questions': qs[k:]}]
json.dump({'sets': SETS, 'ex': exs, 'issues': []}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', len(qs), '정답', ''.join(e['answer'] for e in exs))
