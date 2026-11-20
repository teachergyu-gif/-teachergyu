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

def parse_q(path):
    qs = []; q = None; box = None
    for line in open(path, encoding='utf8').read().split('\n') + ['']:
        s = line.rstrip()
        m = re.match(r'^(\d+)\. (.+)$', s) or re.match(r'^\[(서답형 \d+)\] (.+)$', s)
        if m and not s[:1] in CIRC and not (box is not None and '조' in box['title'] and re.match(r'^\d+\. ', s)):
            q = {'no': m.group(1), 'stem': m.group(2), 'bogi': [], 'choices': [], 'extra': None}
            qs.append(q); box = None; continue
        if not s:
            continue
        if s[:1] in CIRC:
            q['choices'].append(s[1:].strip()); box = None; continue
        if re.fullmatch(r'<[^<>]{1,12}>', s) or s == '[상자]':
            box = {'title': '' if s == '[상자]' else s, 'parts': []}
            q['bogi'].append(box); continue
        mi = re.match(r'^@I (\S+)$', s)   # 그림
        if mi:
            box['parts'].append(('T', f'<img src="file://{os.path.dirname(H)}/img/{mi.group(1)}" style="display:block;width:100%;margin:1mm 0">')); continue
        mt = re.match(r'^@T (\w+)$', s)
        if mt:
            if box is not None:
                box['parts'].append(('T', TABLES[mt.group(1)]))
            else:
                q['bogi'].append({'title': '', 'html': TABLES[mt.group(1)]})
            continue
        assert box is not None, (q['no'], s)
        box['parts'].append(('L', s))
    for q in qs:   # 상자 정리: 글만 있으면 text, 표가 섞이면 html
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


def parse_a(path):
    exs = []
    for blk in re.split(r'\n(?=(?:\d+\. [①-⑤]|\[서답형 \d+\])\n)', '\n' + open(path, encoding='utf8').read().strip()):
        blk = blk.strip()
        if not blk:
            continue
        head, *rest = blk.split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        if m:
            exs.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(rest)}); continue
        no = re.match(r'^\[(서답형 \d+)\]$', head).group(1)
        e = {'no': no, 'answer': '', 'plain': ''}
        lines = []
        for x in rest:
            k = re.match(r'^\[(모범 답안|예시 답안)\] (.*)$', x)
            if k:
                e['answer'], e['tag'] = k.group(2), k.group(1)
            elif x.strip():
                lines.append(re.sub(r'^\*\s*', '· ', x.strip()))
        e['plain'] = '\n'.join(lines)
        exs.append(e)
    return exs


# 묶음: (이름, 문항 파일, 해설 파일, 지문)
LIT = json.load(open(f'{H}/lit.json', encoding='utf8'))   # 「흥보전」·「춘향전」
NL = open(f'{H}/nonlit.txt', encoding='utf8').read().strip()   # 2024년 7월 고3 더프리미엄 모의고사 [4~7] 지문(4~6번 문항만 수록)
gq, ga = parse_q(f'{H}/questions.txt'), parse_a(f'{H}/answers.txt')
k = next(i for i, x in enumerate(gq) if x['no'] == '32')
DEL = {13, 14, 15, 17, 19, 23, 24}   # 10~19번 삭제 뒤 번호 기준(그때 번호 N = gq[N])
KEEP = [i for i in range(10, k) if i not in DEL]
GROUPS = [(parse_q(f'{H}/lit_q.txt'), parse_a(f'{H}/lit_a.txt'), LIT),
          (parse_q(f'{H}/lit2_q.txt'), parse_a(f'{H}/lit2_a.txt'), json.load(open(f'{H}/lit2.json', encoding='utf8'))),   # 「흰 바람벽이 있어」·「논두렁에 서서」·「수경당기」(원 세트 1~5번 중 1~4번)
          (parse_q(f'{H}/hw_q.txt'), parse_a(f'{H}/hw_a.txt'), json.load(open(f'{H}/hw.json', encoding='utf8'))),   # 2027학년도 3월 고3 더프리미엄 화법과 작문 43~45
          ([gq[i] for i in KEEP], [ga[i] for i in KEEP], []),   # 중세 문법: 앞 10문항 삭제, 이어 당시 13·14·15·17·19·23·24번 삭제(사용자 지정)
          (gq[k:], ga[k:], [{'label': '', 'lines': NL, 'author': ''}])]
SETS, exs, n = [], [], 0
for qs, ea, works in GROUPS:
    assert [e['no'] for e in ea] == [q['no'] for q in qs], 'answers mismatch'
    for q, e in zip(qs, ea):   # 객관식 번호는 앞에서부터 이어서 다시 매김
        if not q['no'].startswith('서답형'):
            n += 1; q['no'] = e['no'] = str(n)
    mc = [q['no'] for q in qs if q['no'].isdigit()]
    sd = [q['no'] for q in qs if not q['no'].isdigit()]
    rng = (f'{mc[0]}～{mc[-1]}' if len(mc) > 1 else mc[0]) + (', ' + ', '.join(sd) if sd else '')
    SETS.append({'rng': rng, 'works': works, 'questions': qs}); exs += ea
json.dump({'sets': SETS, 'ex': exs, 'issues': []}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', len(exs), '정답', ''.join(e['answer'] for e in exs if not e['no'].startswith('서답형')))
