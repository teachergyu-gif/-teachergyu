"""모의고사 데이터 만들기: 지문(교재 파일 원문) + raw.txt(문항·해설) → exam.json
사용: python3 build.py src
- src/f.txt: 부산외고 1학년 공통국어2 교과서 1-(3)단원 교재(hwpx) — 「흥보전」 강의용
- src/g.txt: 부산외고 1학년 「탄궁가」,「흰 바람벽이 있어」 교재(hwp) — 탄궁가·흰 바람벽 강의용, 「노신」(11-인수)
- 「누항사」(현대어 풀이)는 출제 원고에 실린 것"""
import json, re, sys, os

SRC = sys.argv[1]
H = os.path.dirname(os.path.abspath(__file__))
F = open(f'{SRC}/f.txt', encoding='utf8').read().split('\n')
G = open(f'{SRC}/g.txt', encoding='utf8').read().split('\n')
clean = lambda x: re.sub(r'\[OBJ\]', '', x).rstrip()


def mark(t, phrase, sym):
    assert t.count(phrase) == 1, (t.count(phrase), phrase)
    return t.replace(phrase, f'{sym} <u>{phrase}</u>')


def bracket(L2, i, j, lab):
    L2[i] = '{' + lab + '}' + L2[i]; L2[j] = L2[j] + '{/' + lab + '}'


issues = []

# ---- 1~3: 흥보전 (f 강의용: [앞부분 줄거리] ~ ‘뉘 아니 슬퍼하리.’) ----
i = next(k for k, x in enumerate(F) if x.strip() == '1-(3) 흥보전(강의용)') + 1
hb = []
while not F[i].startswith('- 정충권'):
    if F[i].strip():
        hb.append(clean(F[i]).strip())
    i += 1
k = next(k for k, x in enumerate(hb) if x.startswith('“그렇지. 볼기 구실 들어 보소.'))
assert hb[k].endswith('매품이나 팔아먹세.”'), hb[k][-20:]
bracket(hb, k, k, 'A')
a = next(k for k, x in enumerate(hb) if x.startswith('“그리 말고 서로 가난 자랑하여')) - 1
assert hb[a] == '흥보 이른 말이,'
b = next(k for k, x in enumerate(hb) if k > a and x.endswith('아무 목득의 아들놈도 못 팔아 갈 것이니.”'))
bracket(hb, a, b, 'B')
hb = '\n'.join(hb)
hb = mark(hb, '“천기누설이라, 말부터 앞세우면 이뤄질 일 없으니, 그 돈으로 양식 팔아 배불리 질끈 먹고.”', '㉠')
hb = mark(hb, '“네 아무것도 안 찾을 듯이 하더니 단계를 높여 하는구나. 너희 놈들이 내 마른 볼기를 대송방으로 아는 놈들이로구나.”', '㉡')
hb = mark(hb, '흥보 속마음에, ‘내가 분명 저승에 들어왔나 보다.’', '㉢')
hb = mark(hb, '“얼씨구나 즐겁도다. 우리 낭군 병영 내려갔다 매 아니 맞고 돌아오니, 이런 영화 또 있을까.”', '㉣')
hb = mark(hb, '“마음만 옳게 먹고 의롭지 않은 일 아니하면 장래 한때 볼 것이니 서러워 말고 살아나세.”', '㉤')
S1 = {'rng': '1～3', 'works': [{'label': '', 'lines': hb, 'author': '- 작자 미상, 「흥보전」 / 정충권 옮김 -'}]}

# ---- 4~6: (가) 탄궁가 (g 강의용) / (나) 누항사(현대어 풀이) ----
i = next(k for k, x in enumerate(G) if x.strip() == '｢탄궁가｣ 강의용 지문') + 3
tg = []
while not G[i].startswith('- 정훈'):
    x = clean(G[i]).strip()
    if x and not re.fullmatch(r'\[[A-E]\]', x):   # 교재의 [A]~[E] 표지는 문항에서 쓰지 않음
        tg.append(x)
    i += 1
notes_tg = []
i += 1
while G[i].startswith('*'):
    notes_tg.append(G[i].strip()); i += 1
tg = '\n'.join(tg).replace('㉠겨울을', '겨울을')   # 교재 문항용 ㉠ 표시는 지움
tg = mark(tg, '동편 이웃 쟁기 얻고 서편 이웃 호미 얻고', '㉠')
tg = mark(tg, '죽 웃물 상전 먹고 건더기 건져 종을 주니', '㉡')
tg = mark(tg, '네 혼자 신의 있어 나를 아니 버리거든', '㉢')
nh = '''가뭄이 몹시 심하여 농사철이 다 늦은 때에
서쪽 두둑 높은 논에 잠깐 갠 지나가는 비에
길 위에 흐르는 물을 반쯤 대어 두고
소 한 번 빌려주마 하고 엉성하게 하는 말씀
친절하다고 여긴 집에 달 없는 황혼에 허둥지둥 달려가서
굳게 닫은 문밖에 우두커니 혼자 서서
큰 기침 에헴이를 꽤 오래도록 한 후에
“어화, 거기 누구신고?” “염치없는 저옵니다.”
“초경도 거의 지났는데 그대 무슨 일로 와 계신고?”
“해마다 이러하기 구차한 줄 알건마는
소 없는 가난한 집에 걱정 많아 왔소이다.”
“공짜로나 값을 치나 빌려줄 만도 하다마는
다만 어젯밤에 건넛집 저 사람이
목 붉은 수꿩을 구슬 같은 기름에 구워 내고
갓 익은 삼해주를 취하도록 권하였는데
이러한 은혜를 어이 아니 갚을런고
내일 소 빌려주마 하고 굳게 약속하였으니
약속을 어기기가 편치 못하니 말씀하기 어렵구나.”
“사실이 그렇다면 설마 어찌할꼬.”
헌 멍덕*을 숙여 쓰고 축 없는 짚신에 맥없이 물러 나오니
풍채 작은 내 모습에 개가 짖을 뿐이로다
(중략)
빈이무원(貧而無怨)*을 어렵다 하건마는
내 생애 이러하되 서러운 뜻은 없노라
단사표음(簞食瓢飮)*을 이도 족히 여기노라
평생 한 뜻이 온포(溫飽)*에는 없노라
태평천하에 충효를 일 삼아
화형제(和兄弟) 신붕우(信朋友)* 그르다 할 이 누가 있으리
그 밖에 남은 일이야 생긴 대로 살겠노라'''
nh = mark(nh, '큰 기침 에헴이를 꽤 오래도록 한 후에', '㉣')
nh = mark(nh, '풍채 작은 내 모습에 개가 짖을 뿐이로다', '㉤')
S2 = {'rng': '4～6', 'works': [
    {'label': '(가)', 'lines': tg, 'author': '- 정훈, 「탄궁가」 -', 'notes': notes_tg},
    {'label': '(나)', 'lines': nh, 'author': '- 박인로, 「누항사」(현대어 풀이) -', 'notes': [
        '*멍덕: 짚으로 바구니 비슷하게 엮은 모자.', '*빈이무원: 가난하면서도 남을 원망하지 않음.',
        '*단사표음: 대나무로 만든 밥그릇에 담은 밥과 표주박에 든 물이라는 뜻으로, 소박한 시골 생활을 이르는 말.',
        '*온포: 따뜻하게 입고 배부르게 먹음.', '*화형제 신붕우: 형제간에 화목하고 벗 사이에 믿음이 있음.']}]}

# ---- 7~9: (가) 흰 바람벽이 있어 (g 강의용) / (나) 노신 (g 11-인수) ----
i = next(k for k, x in enumerate(G) if x.strip() == '｢흰 바람벽이 있어｣ 강의용 지문')
i = next(k for k in range(i, len(G)) if G[k].strip() == '(가)') + 1
hw = []
while not G[i].startswith('- 백석'):
    x = clean(G[i]).strip()
    if x and not re.fullmatch(r'\[[A-E]\]', x):
        hw.append(x)
    i += 1
notes_hw = [G[i + 1].strip()]
hw = '\n'.join(hw).replace('㉠오늘 저녁', '오늘 저녁')
hw = mark(hw, '희미한 십오촉(十五燭) 전등이 지치운 불빛을 내어던지고', '㉠')
hw = mark(hw, '차디찬 물에 손은 담그고 무이며 배추를 씻고 있다', '㉡')
hw = mark(hw, '그의 지아비와 마조 앉어 대구국을 끓여놓고 저녁을 먹는다', '㉢')
hw = mark(hw, '나는 이 세상에서 가난하고 외롭고 높고 쓸쓸하니 살어가도록 태어났다', '㉣')
hw = mark(hw, '초생달과 바구지꽃과 짝새와 당나귀가 그러하듯이', '㉤')
i = next(k for k, x in enumerate(G) if x.strip() == '시를 믿고 어떻게 살아가나')
ns = []
while not G[i].startswith('-김광균'):
    ns.append(clean(G[i]).strip()); i += 1
notes_ns = [G[i + 1].strip().replace('{1881~1936}', '(1881~1936)')]
ns = '\n'.join(ns).replace('㉢먼―', '먼―').replace('㉣지나는', '지나는')   # 문제 은행의 ㉢, ㉣ 표시는 지움
assert '㉢' not in ns and '㉣' not in ns
S3 = {'rng': '7～9', 'works': [
    {'label': '(가)', 'lines': hw, 'author': '- 백석, 「흰 바람벽이 있어」 -', 'notes': notes_hw},
    {'label': '(나)', 'lines': ns, 'author': '- 김광균, 「노신」 -', 'notes': notes_ns}]}
SETS = [S1, S2, S3]

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
        m = re.match(r'^(\d+)\. (.*?)(?: \[(\d(?:\.\d)?)점\])?$', s) if re.match(r'^\d+\. ', s) else None
        if m:
            q = {'no': m.group(1), 'stem': m.group(2), 'points': m.group(3), 'bogi': None, 'choices': [], 'extra': None}
            cur.append(q); box = None; continue
        if s in ('<보 기>', '<보기>'):
            q['bogi'] = {'title': '<보 기>', 'text': ''}; box = q['bogi']; continue
        if s[:1] in CIRC:
            q['choices'].append(s[1:].strip()); box = None; continue
        if s and box is not None:
            box['text'] += ('\n' if box['text'] else '') + s
    else:
        m = re.match(r'^(\d+)\. ([①-⑤])$', s)
        if m:
            e = {'no': m.group(1), 'answer': m.group(2), 'correct': '', 'wrong': [], 'plain': ''}
            exs.append(e); sub = 'c'; continue
        if not s:
            continue
        if s == '[오답풀이]':
            sub = 'w'; continue
        if sub == 'c':
            assert s[:1] == e['answer'], (e['no'], s[:20])
            e['correct'] = s[1:].strip()
        else:
            e['wrong'].append([s[:1], s[1:].strip()])

assert len(qsets) == len(SETS)
for st, qs in zip(SETS, qsets):
    st['questions'] = qs
for qs in qsets:
    for x in qs:
        assert len(x['choices']) == 5, x['no']
json.dump({'sets': SETS, 'ex': exs, 'issues': issues}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', sum(len(x) for x in qsets), '해설', len(exs), '정답', ''.join(x['answer'] for x in exs))
