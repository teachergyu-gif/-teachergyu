"""모의고사 데이터 만들기: 지문(교재 파일 원문) + raw.txt(문항·해설) → exam.json
사용: python3 build.py 원본폴더(c.txt·d.txt·e.txt = 교재 hwpx/hwp에서 뽑은 글) 공통국어2데이터폴더
- c.txt: 국제고 1학년 2학기 기말고사 진달래꽃, 무화과 교재(hwpx)
- d.txt: 국제고 1학년 2학기 기말고사 춘향전 교재(hwpx)
- e.txt: 국제고 1학년 「타는 목마름으로」,「두꺼비」 교재(hwp)
- 비문학 01·04·07: 김T 비문학 프린트물(교재/공통국어2 2학기 기말고사 대비/src/data A·B·E)"""
import json, re, sys, os

SRC, GK = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__))
L = lambda f: open(f'{SRC}/{f}.txt', encoding='utf8').read().split('\n')
C, Dd, E = L('c'), L('d'), L('e')


def block(lines, start, end_pat):
    """start 줄 다음부터 end_pat(작가 줄)까지"""
    i = next(k for k, x in enumerate(lines) if x.strip() == start) + 1
    out = []
    while not re.search(end_pat, lines[i]):
        out.append(lines[i].rstrip()); i += 1
    return '\n'.join(out).strip('\n')


def mark(t, phrase, sym, count=1):
    """phrase에 기호와 밑줄. ' / '로 나눈 여러 행은 행마다 밑줄"""
    parts = phrase.split(' / ')
    if len(parts) > 1:
        src = '\n'.join(parts)
        assert src in t, phrase
        new = f'{sym} ' + '\n'.join(f'<u>{p}</u>' for p in parts)
        return t.replace(src, new, count)
    assert phrase in t, phrase
    return t.replace(phrase, f'{sym} <u>{phrase}</u>', count)


def bracket(t, first, last, lab):
    """[A] 묶음: first로 시작하는 줄 ~ last로 끝나는 줄"""
    L2 = t.split('\n')
    i = next(k for k, x in enumerate(L2) if x.startswith(first))
    j = next(k for k, x in enumerate(L2) if k >= i and x.rstrip().endswith(last))
    L2[i] = '{' + lab + '}' + L2[i]; L2[j] = L2[j] + '{/' + lab + '}'
    return '\n'.join(L2)


issues = []

# ---- 1~4: (가) 무화과 (c 강의용) / (나) 타는 목마름으로 (e 강의용) ----
mu = block(C, '무화과(강의용)', r'^- 김지하')
mu = mark(mu, '우러른 잿빛 하늘', '㉠')
mu = mark(mu, '꽃 없이 바로 열매 맺는 게', '㉡')
mu = mark(mu, '열매 속에서 속 꽃 피는 게', '㉢')
mu = mark(mu, '검은 도둑괭이 하나가 날쌔게 / 개굴창을 가로지른다.', '㉣')
ta = block(E, '김지하, ｢타는 목마름으로｣(강의용 지문)', r'^- 김지하')
ta = mark(ta, '신새벽 뒷골목에', 'ⓐ')
ta = mark(ta, '발자국 소리 호르락 소리 문 두드리는 소리', 'ⓑ')
ta = mark(ta, '네 이름의 외로운 눈부심', 'ⓒ')
ta = ta.replace('떨리는 손 떨리는 가슴\n떨리는 치떨리는 노여움으로', 'ⓓ <u>떨리는 손 떨리는 가슴</u>\n<u>떨리는 치떨리는 노여움</u>으로')
assert 'ⓓ' in ta
ta = mark(ta, '백묵으로 서툰 솜씨로', 'ⓔ')
S1 = {'rng': '1～4, 서답형 1', 'works': [
    {'label': '(가)', 'lines': mu, 'author': '- 김지하, 「무화과」 -'},
    {'label': '(나)', 'lines': ta, 'author': '- 김지하, 「타는 목마름으로」 -'}]}

# ---- 5~7: 두꺼비 (e 강의용) ----
du = block(E, '황순원, ｢두꺼비｣(강의용 지문)', r'^- 황순원')
du = bracket(du, '“선생님두 다 아시다시피', '이런 거 다 생각해 주셔야 헙죠.”', 'A')
du = bracket(du, '두꺼비 같은 것, 두꺼비 같은 것', '영 견딜 수 없더군.', 'B')
du = mark(du, '현세는 이 일을 어서 끝내고만 싶었다.', '㉠')
du = mark(du, '현세는 문득 자기네도 미역 이파리나 사 놔야 하지 않나 하는 생각이 들었다.', '㉡')
du = mark(du, '그것은 뱀같이 독이 오른 대가리였다.', '㉢')
du = mark(du, '그것은 벌써 이미 다 죽어 가는 실뱀의 악에 지나지 못하는 것이었다.', '㉣')
du = mark(du, '저도 모르는 새 돈 묶음만은 집어 쥔 채.', '㉤')
if '정말……\n' in du:
    issues.append('두꺼비: 두갑이의 대사 “글쎄 첨엔 … 서울깍쟁이라더니 정말……”에 닫는 따옴표가 없음(교재 원문 그대로 둠)')
S2 = {'rng': '5～7', 'works': [{'label': '', 'lines': du, 'author': '- 황순원, 「두꺼비」 -'}]}

# ---- 8~11: (가) 진달래꽃 (c 강의용) / (나) 한 그리움이 다른 그리움에게 / (다) 선운사에서 (c 문제 은행에 실린 교재 원문) ----
jd = block(C, '진달래꽃(강의용)', r'^- 김소월')
i = next(k for k, x in enumerate(C) if k > 2200 and x.strip() == '어느 날 당신과 내가')
hg = []
while not C[i].startswith('- 정희성'):
    hg.append(C[i].rstrip()); i += 1
hg = '\n'.join(hg)
hg = mark(hg, '날과 씨로 만나서', '㉠')
hg = mark(hg, '한 폭의 비단이 된다면', '㉡')
hg = mark(hg, '추운 길목에서', '㉢')
hg = mark(hg, '한 슬픔이 다른 슬픔에게 손을 주고', '㉣')
hg = mark(hg, '어느 겨울인들 / 우리들의 사랑을 춥게 하리', '㉤')
i = next(k for k, x in enumerate(C) if k > 2700 and x.strip() == '꽃이')
sw = []
while not C[i].startswith('- 최영미'):
    sw.append(C[i].rstrip()); i += 1
sw = '\n'.join(sw).strip('\n')
S3 = {'rng': '8～11', 'works': [
    {'label': '(가)', 'lines': jd, 'author': '- 김소월, 「진달래꽃」 -'},
    {'label': '(나)', 'lines': hg, 'author': '- 정희성, 「한 그리움이 다른 그리움에게」 -'},
    {'label': '(다)', 'lines': sw, 'author': '- 최영미, 「선운사에서」 -'}]}

# ---- 12~15: 춘향전 (d 강의용: [앞부분 줄거리] ~ 길이 전하더라.) ----
i = next(k for k, x in enumerate(Dd) if x.strip() == '2-(3) 춘향전(강의용)') + 1
ch = []
while True:
    ch.append(Dd[i].rstrip())
    if Dd[i].rstrip().endswith('길이 전하더라.'):
        break
    i += 1
ch = '\n'.join(x for x in ch).strip('\n')
ch = re.sub(r'\n{2,}', '\n\n', ch)
# 교재 원문에서 한 문단에 붙어 버린 곳(줄 바꿈 빠짐)
if '높았더라.이렇듯이' in ch:
    ch = ch.replace('높았더라.이렇듯이', '높았더라.\n이렇듯이')
    issues.append('춘향전: 교재 원문 ‘노랫소리 높은 곳에 원망 소리 높았더라.이렇듯이 지었으되 …’가 한 줄로 붙어 있어 ‘높았더라.’ 뒤에서 줄을 나눔')
ch = ch.replace('옥소반의 아름다운 안주는 \n일만 백성의 기름이라.', '옥소반의 아름다운 안주는 일만 백성의 기름이라.')
ch = ch.replace('[앞부분 줄거리] ', '[앞부분 줄거리] ')
ch = mark(ch, '등을 밀쳐 내니 어찌 아니 명관(名官)인가.', '㉠')
ch = mark(ch, '‘마는’ 하는 끝말을 내뱉고는 입맛이 사납겠다.', '㉡')
ch = mark(ch, '‘오냐. 도적질은 내가 하마. 오라는 네가 받아라.’', '㉢')
ch = mark(ch, '‘아뿔싸. 일이 났다.’', '㉣')
ch = mark(ch, '인궤 잃고 강정 들고, 병부(兵符) 잃고 송편 들고, 탕건 잃고 용수 쓰고, 갓 잃고 소반 쓰고.', '㉤')
S4 = {'rng': '12～15, 서답형 2', 'works': [{'label': '', 'lines': ch, 'author': '- 작자 미상, 「춘향전」 -'}]}

# ---- 16~18: 나룻배와 행인 / 님의 침묵 ----
na = '''나는 나룻배
당신은 행인(行人)
당신은 ⓐ흙발로 나를 짓밟습니다.
나는 당신을 안고 물을 건너갑니다.
나는 당신을 안으면 깊으나 얕으나 급한 여울이나 건너갑니다.
만약 당신이 아니 오시면 나는 ⓑ바람을 쐬고 눈비를 맞으며 밤에서 낮까지 당신을 기다리고 있습니다.
당신은 물만 건너면 나를 ⓒ돌아보지도 않고 가십니다그려.
그러나 당신이 ⓓ언제든지 오실 줄만 알아요.
나는 당신을 기다리면서 날마다 날마다 낡아 갑니다.
나는 나룻배
당신은 행인'''
nm = '''님은 갔습니다. 아아, 사랑하는 나의 님은 갔습니다.
ⓔ푸른 산빛을 깨치고 단풍나무 숲을 향하여 난 작은 길을 걸어서, 차마 떨치고 갔습니다.
황금의 꽃같이 굳고 빛나던 옛 맹서는 차디찬 티끌이 되어서 ⓕ한숨의 미풍에 날아갔습니다.
날카로운 첫 키스의 추억은 나의 운명의 지침을 돌려놓고, 뒷걸음쳐서 사라졌습니다.
나는 향기로운 님의 말소리에 귀먹고, 꽃다운 님의 얼굴에 눈멀었습니다.
사랑도 사람의 일이라, 만날 때에 미리 떠날 것을 염려하고 경계하지 아니한 것은 아니지만, 이별은 뜻밖의 일이 되고, 놀란 가슴은 새로운 슬픔에 터집니다.
그러나 이별을 ⓖ쓸데없는 눈물의 원천을 만들고 마는 것은 스스로 사랑을 깨치는 것인 줄 아는 까닭에, 걷잡을 수 없는 슬픔의 힘을 옮겨서 ⓗ새 희망의 정수박이에 들어부었습니다.
우리는 만날 때에 떠날 것을 염려하는 것과 같이, 떠날 때에 다시 만날 것을 믿습니다.
아아, 님은 갔지마는 나는 님을 보내지 아니하였습니다.
제 곡조를 못 이기는 사랑의 노래는 님의 침묵을 휩싸고 돕니다.'''
for sym, ph in [('ⓐ', '흙발로 나를 짓밟습니다'), ('ⓑ', '바람을 쐬고 눈비를 맞으며'), ('ⓒ', '돌아보지도 않고 가십니다그려'), ('ⓓ', '언제든지 오실 줄만 알아요')]:
    na = na.replace(sym + ph, f'{sym} <u>{ph}</u>')
for sym, ph in [('ⓔ', '푸른 산빛을 깨치고'), ('ⓕ', '한숨의 미풍에 날아갔습니다'), ('ⓖ', '쓸데없는 눈물의 원천'), ('ⓗ', '새 희망의 정수박이에 들어부었습니다')]:
    nm = nm.replace(sym + ph, f'{sym} <u>{ph}</u>')
assert all(x in na + nm for x in ('ⓐ <u>', 'ⓑ <u>', 'ⓒ <u>', 'ⓓ <u>', 'ⓔ <u>', 'ⓕ <u>', 'ⓖ <u>', 'ⓗ <u>'))
S5 = {'rng': '16～18', 'works': [
    {'label': '(가)', 'lines': na, 'author': '- 한용운, 「나룻배와 행인」 -'},
    {'label': '(나)', 'lines': nm, 'author': '- 한용운, 「님의 침묵」 -'}]}

# ---- 비문학: 김T 프린트 01(매체의 발달)·04(금융 이해력)·07(제정신이라는 착각) ----
gk = lambda f, i: json.load(open(f'{GK}/{f}/out.json'))['sets'][i]
def nonlit(s, rng):
    return {'rng': rng, 'works': [{'label': w.get('label', ''), 'lines': w['lines'], 'author': w.get('author', '')} for w in s['works']],
            'notes': s.get('notes') or []}
S6 = nonlit(gk('A', 0), '19～22')
S7 = nonlit(gk('B', 1), '23～26')
S8 = nonlit(gk('E', 0), '27～30, 서답형 3')
for w in S8['works']:
    w['lines'] = w['lines'].replace('국립과학수사연수소', '국립과학수사연구소').replace('잘 이해할 수 있었어.\n', '잘 이해할 수 있었어.”\n')
    if w['author']:
        w['author'] = '- ' + w['author']
issues += ['비문학 07: ⓑ(2) ‘국립과학수사연수소’ → ‘연구소’, (3) 인용문 닫는 따옴표(”) 보충']
SETS = [S1, S2, S3, S4, S5, S6, S7, S8]

# ---- 문항·해설: raw.txt ----
raw = open(f'{H}/raw.txt', encoding='utf8').read().split('\n')
CIRC = '①②③④⑤'
qsets, exs = [], []
cur = None; mode = 'q'; q = None; e = None; box = None
for line in raw + ['']:
    s = line.rstrip()
    if s.startswith('【'):
        cur = []; qsets.append(cur); mode = 'q'; continue
    if s == '@EX':
        mode = 'ex'; e = None; continue
    if mode == 'q':
        m = re.match(r'^(\d+)\. (.*) \[(\d\.\d)점\]$', s) or re.match(r'^\[(서답형 \d)\] (.*) \[(\d)점\]$', s)
        if m:
            q = {'no': m.group(1), 'stem': m.group(2), 'points': m.group(3), 'bogi': None, 'choices': [], 'extra': None}
            cur.append(q); box = None; continue
        if s in ('<보 기>', '<보기>'):
            q['bogi'] = {'title': '<보 기>', 'text': ''}; box = q['bogi']; continue
        if s in ('<조 건>', '<조건>'):
            q['extra'] = {'title': '<조 건>', 'text': ''}; box = q['extra']; continue
        if s[:1] in CIRC:
            q['choices'].append(s[1:].strip()); box = None; continue
        if s and box is not None:
            box['text'] += ('\n' if box['text'] else '') + s
            continue
    else:
        m = re.match(r'^(\d+)\. ([①-⑤])$', s)
        m2 = re.match(r'^\[(서답형 \d)\]$', s)
        if m or m2:
            e = {'no': m.group(1) if m else m2.group(1), 'answer': m.group(2) if m else '', 'correct': '', 'wrong': [], 'plain': ''}
            exs.append(e); sub = 'c'; continue
        if not s:
            continue
        if e['no'].startswith('서답형'):
            m = re.match(r'^\[(모범 답안|예시 답안)\] (.*)$', s)
            if m:
                e['answer'] = m.group(2); e['tag'] = m.group(1); continue
            e['plain'] += ('\n' if e['plain'] else '') + s
            continue
        if s == '[오답풀이]':
            sub = 'w'; continue
        if sub == 'c':
            assert s[:1] == e['answer'], (e['no'], s[:20])
            e['correct'] = s[1:].strip()
        else:
            e['wrong'].append([s[:1], s[1:].strip()])

assert len(qsets) == len(SETS), (len(qsets), len(SETS))
for st, qs in zip(SETS, qsets):
    st['questions'] = qs
nq = sum(1 for qs in qsets for x in qs if x['no'].isdigit())
ns = sum(1 for qs in qsets for x in qs if not x['no'].isdigit())
for qs in qsets:
    for x in qs:
        if x['no'].isdigit():
            assert len(x['choices']) == 5, x['no']
assert len(exs) == nq + ns, (len(exs), nq, ns)
pts = sum(float(x['points']) for qs in qsets for x in qs)
json.dump({'sets': SETS, 'ex': exs, 'issues': issues}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('객관식', nq, '서답형', ns, '배점 합', round(pts, 1))
print('\n'.join(issues))
