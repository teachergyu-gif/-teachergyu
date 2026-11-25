"""모의고사 3회 데이터 만들기: 지문(교재 파일 원문, 2회와 같은 본문) + raw.txt(문항·해설) → exam.json
사용: python3 build.py 원본폴더(c.txt·d.txt·e.txt = 교재 hwpx/hwp에서 뽑은 글) 공통국어2데이터폴더
- c.txt: 국제고 1학년 2학기 기말고사 진달래꽃, 무화과 교재(hwpx)
- d.txt: 국제고 1학년 2학기 기말고사 춘향전 교재(hwpx)
- e.txt: 국제고 1학년 「타는 목마름으로」,「두꺼비」 교재(hwp)
- 비문학 01·02·06·07: 김T 비문학 프린트물(교재/공통국어2 2학기 기말고사 대비/src/data A·D·E)
- 15~17 기부 지문: 원본폴더의 gibu.txt(3-(2)단원 교재 본문 강의용, 한 줄에 한 문단)와
  ../img/gibu1.*·gibu2.*·gibu3.*(교과서 [자료 1]~[자료 3])가 있으면 넣고, 없으면 자리 표시만 둔다.
※ 2회에 쓰인 기호는 모두 지우고, 편집 안내(3회)의 기호만 새로 넣음."""
import json, re, sys, os, glob

SRC, GK = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(os.path.dirname(H), 'img')
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


def blank(t, word, sym, ctx):
    """ctx(앞뒤 말 포함) 안의 word를 빈칸 ( sym )으로"""
    assert t.count(ctx) == 1, ctx
    return t.replace(ctx, ctx.replace(word, f'(\u00a0\u00a0{sym}\u00a0\u00a0)', 1))


def bracket(t, first, last, lab):
    """[A] 묶음: first로 시작하는 줄 ~ last로 끝나는 줄"""
    L2 = t.split('\n')
    i = next(k for k, x in enumerate(L2) if x.startswith(first))
    j = next(k for k, x in enumerate(L2) if k >= i and x.rstrip().endswith(last))
    L2[i] = '{' + lab + '}' + L2[i]; L2[j] = L2[j] + '{/' + lab + '}'
    return '\n'.join(L2)


issues = []

# ---- 1~3: (가) 진달래꽃 / (나) 선운사에서(㉠~㉤) / (다) 한 그리움이 다른 그리움에게 — 2회 10~13번 본문, 순서만 바꿈 ----
jd = block(C, '진달래꽃(강의용)', r'^- 김소월')
i = next(k for k, x in enumerate(C) if k > 2200 and x.strip() == '어느 날 당신과 내가')
hg = []
while not C[i].startswith('- 정희성'):
    hg.append(C[i].rstrip()); i += 1
hg = '\n'.join(hg)
i = next(k for k, x in enumerate(C) if k > 2700 and x.strip() == '꽃이')
sw = []
while not C[i].startswith('- 최영미'):
    sw.append(C[i].rstrip()); i += 1
sw = '\n'.join(sw).strip('\n')
sw = mark(sw, '피는 건 힘들어도', '㉠')
sw = mark(sw, '님 한번 생각할 틈 없이', '㉡')
sw = mark(sw, '잊는 것 또한 그렇게 / 순간이면 좋겠네', '㉢')
sw = mark(sw, '멀리서 웃는 그대여', '㉣')
sw = mark(sw, '영영 한참이더군', '㉤')
S1 = {'rng': '1～3', 'works': [
    {'label': '(가)', 'lines': jd, 'author': '- 김소월, 「진달래꽃」 -'},
    {'label': '(나)', 'lines': sw, 'author': '- 최영미, 「선운사에서」 -'},
    {'label': '(다)', 'lines': hg, 'author': '- 정희성, 「한 그리움이 다른 그리움에게」 -'}]}

# ---- 4~7, 서답형 1: (가) 무화과([A][B]) / (나) 타는 목마름으로(기호 없음) / (다) 빼앗긴 들에도 봄은 오는가 ----
mu = block(C, '무화과(강의용)', r'^- 김지하')
mu = bracket(mu, '이봐', '어떤가', 'A')
mu = bracket(mu, '이것 봐', '어떤가', 'B')
ta = block(E, '김지하, ｢타는 목마름으로｣(강의용 지문)', r'^- 김지하')
ta = ta.replace('발자국 소리', '발자욱 소리')   # 교과서 판본(1회·2회와 같음)
# (다) 이상화, 「빼앗긴 들에도 봄은 오는가」 — 편집 안내(3회)의 본문 그대로(『개벽』(1926) 현대어 표기본과 대조: '살진'은 판본에 따라 '살찐')
ppa = """지금은 남의 땅 ― 빼앗긴 들에도 봄은 오는가?

나는 온몸에 햇살을 받고
푸른 하늘 푸른 들이 맞붙은 곳으로
가르마 같은 논길을 따라 꿈속을 가듯 걸어만 간다.

입술을 다문 하늘아 들아
내 맘에는 내 혼자 온 것 같지를 않구나
네가 끌었느냐 누가 부르더냐 답답워라 말을 해 다오.

(중략)

내 손에 호미를 쥐어 다오
살진 젖가슴과 같은 부드러운 이 흙을
발목이 시도록 밟아도 보고 좋은 땀조차 흘리고 싶다.

강가에 나온 아이와 같이
짬도 모르고 끝도 없이 닫는 내 혼아
무엇을 찾느냐 어디로 가느냐 웃어웁다 답을 하려무나.

나는 온몸에 풋내를 띠고
푸른 웃음 푸른 설움이 어우러진 사이로
다리를 절며 하루를 걷는다 아마도 봄 신령이 지폈나 보다.

그러나 지금은 ― 들을 빼앗겨 봄조차 빼앗기겠네."""
S2 = {'rng': '4～7, 서답형 1', 'works': [
    {'label': '(가)', 'lines': mu, 'author': '- 김지하, 「무화과」 -'},
    {'label': '(나)', 'lines': ta, 'author': '- 김지하, 「타는 목마름으로」 -'},
    {'label': '(다)', 'lines': ppa, 'author': '- 이상화, 「빼앗긴 들에도 봄은 오는가」 -'}]}

# ---- 8~11: 춘향전 (2회 14~17번 본문, [A][B]·㉠~㉤ 새로) ----
i = next(k for k, x in enumerate(Dd) if x.strip() == '2-(3) 춘향전(강의용)') + 1
ch = []
while True:
    ch.append(Dd[i].rstrip())
    if Dd[i].rstrip().endswith('길이 전하더라.'):
        break
    i += 1
ch = '\n'.join(x for x in ch).strip('\n')
ch = re.sub(r'\n{2,}', '\n\n', ch)
ch = ch.replace('장수원님이', '장수 원님이').replace('저 사령의 거동 보소\n', '저 사령의 거동 보소.\n')
if '높았더라.이렇듯이' in ch:
    ch = ch.replace('높았더라.이렇듯이', '높았더라.\n이렇듯이')
ch = re.sub(r'옥소반의 아름다운 안주는 ?\n일만 백성의 기름이라\.', '옥소반의 아름다운 안주는 일만 백성의 기름이라.', ch)   # 풀이 4행(편집 안내): 2회에서는 이 줄이 둘로 나뉘어 있었음
assert '안주는 일만 백성의 기름이라.' in ch
ch = bracket(ch, '금준미주(金樽美酒)', '원망 소리 높았더라.', 'A')
ch = bracket(ch, '좌수(座首), 별감(別監) 넋을 잃고', '물 마르다 목 들여라.”', 'B')
ch = mark(ch, '저 사령의 거동 보소.', '㉠')
ch = mark(ch, '‘마는’ 하는 끝말을 내뱉고는 입맛이 사납겠다.', '㉡')
ch = mark(ch, '달 같은 마패를 햇빛같이 번쩍 들어', '㉢')
ch = mark(ch, '춘향의 높은 절개 광채 있게 되었으니 어찌 아니 좋을쏜가.', '㉣')
ch = mark(ch, '봄풀은 해마다 푸르건만 / 떠난 객은 돌아오지 않는다고 이른 시(詩)는 / 나를 두고 이름이라.', '㉤')
S3 = {'rng': '8～11', 'works': [{'label': '', 'lines': ch, 'author': '- 작자 미상, 「춘향전」 -'}]}

# ---- 12~14: 두꺼비 (2회 6~9번 본문, 앞부분 줄거리 포함, ⓐ~ⓔ 새로) ----
du = block(E, '황순원, ｢두꺼비｣(강의용 지문)', r'^- 황순원')
du = du.replace('일인지두몰라', '일인지두 몰라')
du = du.replace('서울깍쟁이라더니 정말……\n', '서울깍쟁이라더니 정말……”\n')   # 닫는 따옴표 보충(2회와 같음)
du = mark(du, '수표', 'ⓐ')                         # 첫 번째 ‘수표’(“하고 수표를 도로 돌려주기라도 할 것 같은 기세”)
assert 'ⓐ <u>수표</u>를 도로 돌려주기라도' in du
du = mark(du, '찰거머리', 'ⓑ')
du = mark(du, '십 원짜리 한 묶음', 'ⓒ')
du = mark(du, '가짜 돈', 'ⓓ')
du = mark(du, '불고기와 소주와 마늘을 먹은 뒤에 나는 냄새', 'ⓔ')
S4 = {'rng': '12～14', 'works': [{'label': '', 'lines': du, 'author': '- 황순원, 「두꺼비」 -'}]}

# ---- 15~17, 서답형 2: 3-(2)단원 교재 본문(강의용) + 교과서 [자료 1]~[자료 3] ----
def gimg(n, cap):
    f = sorted(glob.glob(f'{IMG}/gibu{n}.*'))
    if f:
        return f'@I {os.path.basename(f[0])} {cap}'
    issues.append(f'15~17: [자료 {n}] 그림 파일(img/gibu{n}.*) 없음 → 자리 표시')
    return f'@I gibu{n}_slot.svg {cap}'
CAP = {1: '[자료 1]', 2: '[자료 2]', 3: '[자료 3]'}
gp = f'{SRC}/gibu.txt'
if os.path.exists(gp):
    paras = [x.strip() for x in open(gp, encoding='utf8').read().split('\n') if x.strip()]
    gb = '\n'.join(paras)
    gb = mark(gb, '‘경제적 여유가 없어서’', '㉠')
    gb = mark(gb, '‘기부에 관심이 없어서’', '㉡')           # 2문단 첫 번째 것
    gb = mark(gb, '‘기부 단체 등에 대한 불신’', '㉢')
    P = gb.split('\n')
    P.insert(1, gimg(1, CAP[1])); P.insert(2, gimg(2, CAP[2]))   # [자료 1]·[자료 2]: 1문단 뒤
    k = [i for i, x in enumerate(P) if not x.startswith('@I ')][4]
    P.insert(k + 1, gimg(3, CAP[3]))                              # [자료 3]: 5문단 뒤
    gb = '\n'.join(P)
else:
    issues.append('15~17: 기부 지문 원문(gibu.txt) 없음 → 지문 자리 표시만 넣음')
    gb = '\n'.join([
        '※ [지문 자리] 3-(2)단원 교재 본문(강의용) 전체가 들어갈 자리입니다. 원문을 받으면 그대로 넣고, 기호 ㉠ ‘경제적 여유가 없어서’, ㉡ ‘기부에 관심이 없어서’(2문단 첫 번째 것), ㉢ ‘기부 단체 등에 대한 불신’을 표시합니다. 교과서 자료는 [자료 1](1문단 옆)·[자료 2](1문단 뒤)·[자료 3](5문단 옆) 자리에 넣습니다.',
        gimg(1, CAP[1]), gimg(2, CAP[2]), gimg(3, CAP[3])])
S5 = {'rng': '15～17, 서답형 2', 'works': [{'label': '', 'lines': gb, 'author': ''}]}

# ---- 18~20: 나룻배와 행인 / 님의 침묵 (2회 18~20번 본문, ㉠~㉧ 새로) ----
na = """나는 나룻배
당신은 행인(行人)
당신은 흙발로 나를 짓밟습니다.
나는 당신을 안고 물을 건너갑니다.
나는 당신을 안으면 깊으나 옅으나 급한 여울이나 건너갑니다.
만일 당신이 아니 오시면 나는 바람을 쐬고 눈비를 맞으며 밤에서 낮까지 당신을 기다리고 있습니다.
당신은 물만 건너면 나를 돌아보지도 않고 가십니다그려.
그러나 당신이 언제든지 오실 줄만은 알아요.
나는 당신을 기다리면서 날마다 날마다 낡아 갑니다.
나는 나룻배
당신은 행인"""
nm = """님은 갔습니다. 아아, 사랑하는 나의 님은 갔습니다.
푸른 산빛을 깨치고 단풍나무 숲을 향하여 난 작은 길을 걸어서, 차마 떨치고 갔습니다.
황금의 꽃같이 굳고 빛나던 옛 맹서는 차디찬 티끌이 되어서 한숨의 미풍에 날아갔습니다.
날카로운 첫 키스의 추억은 나의 운명의 지침을 돌려놓고, 뒷걸음쳐서 사라졌습니다.
나는 향기로운 님의 말소리에 귀먹고, 꽃다운 님의 얼굴에 눈멀었습니다.
사랑도 사람의 일이라, 만날 때에 미리 떠날 것을 염려하고 경계하지 아니한 것은 아니지만, 이별은 뜻밖의 일이 되고, 놀란 가슴은 새로운 슬픔에 터집니다.
그러나 이별을 쓸데없는 눈물의 원천을 만들고 마는 것은 스스로 사랑을 깨치는 것인 줄 아는 까닭에, 걷잡을 수 없는 슬픔의 힘을 옮겨서 새 희망의 정수박이에 들어부었습니다.
우리는 만날 때에 떠날 것을 염려하는 것과 같이, 떠날 때에 다시 만날 것을 믿습니다.
아아, 님은 갔지마는 나는 님을 보내지 아니하였습니다.
제 곡조를 못 이기는 사랑의 노래는 님의 침묵을 휩싸고 돕니다."""
na = na.replace('당신은 행인(行人)', '당신은 ㉠ <u>행인</u>(行人)', 1)
for sym, ph in [('㉡', '안고 물을 건너갑니다'), ('㉢', '바람을 쐬고 눈비를 맞으며'), ('㉣', '돌아보지도 않고 가십니다그려')]:
    na = mark(na, ph, sym)
for sym, ph in [('㉤', '날카로운 첫 키스의 추억'), ('㉥', '새로운 슬픔'), ('㉦', '새 희망의 정수박이'), ('㉧', '사랑의 노래')]:
    nm = mark(nm, ph, sym)
S6 = {'rng': '18～20', 'works': [
    {'label': '(가)', 'lines': na, 'author': '- 한용운, 「나룻배와 행인」 -'},
    {'label': '(나)', 'lines': nm, 'author': '- 한용운, 「님의 침묵」 -'}]}

# ---- 비문학: 김T 프린트 01(매체)·02(가짜 정보 댓글)·07(제정신이라는 착각)·06(매카시즘) ----
gk = lambda f, i: json.load(open(f'{GK}/{f}/out.json'))['sets'][i]
def nonlit(s, rng):
    return {'rng': rng, 'works': [{'label': w.get('label', ''), 'lines': w['lines'], 'author': w.get('author', '')} for w in s['works']],
            'notes': s.get('notes') or []}
SYM = r'[㉠-㉭ⓐ-ⓩ]'
# 21~23: 01 지문 — 기호 모두 삭제, 빈칸 ㉮~㉰
S7 = nonlit(gk('A', 0), '21～23')
w = S7['works'][0]
w['lines'] = re.sub(SYM + r'<u><b>(.*?)</b></u>', r'\1', w['lines'])
assert not re.search(SYM + '|<u>|<b>', w['lines'])
w['lines'] = blank(w['lines'], '시간', '㉮', '다른 시간이나 공간으로 옮길 수 없다.')
w['lines'] = blank(w['lines'], '시민 사회', '㉯', '지식을 널리 보급하여 시민 사회가 성장하는 발판이 되었다.')
w['lines'] = blank(w['lines'], '생산자와 수용자', '㉰', '정보 생산자와 수용자의 경계가 허물어졌다.')
# 24~26: 02 지문 — ㉠~㉤ 삭제, ⓐ·ⓑ·ⓒ 유지
S8 = nonlit(gk('A', 1), '24～26')
w = S8['works'][0]
w['lines'] = re.sub(r'[㉠-㉤]<u><b>(.*?)</b></u>', r'\1', w['lines'])
assert not re.search('[㉠-㉤]', w['lines']) and all(x in w['lines'] for x in 'ⓐⓑⓒ')
w['author'] = '- ' + w['author'].strip() + ' -' if not w['author'].startswith('-') else w['author']
# 27~29, 서답형 3: 07 지문 — ⓐ·ⓑ 유지, (가)에 빈칸 ㉮~㉰ (1회와 같은 오탈자 바로잡기)
S9 = nonlit(gk('E', 0), '27～29, 서답형 3')
for w in S9['works']:
    w['lines'] = w['lines'].replace('비교하는데 필요한', '비교하는 데 필요한').replace('국립과학수사연구소에 필적 감정을 증거로', '국립과학수사연구소의 필적 감정을 증거로').replace('국립과학수사연수소', '국립과학수사연구소').replace('잘 이해할 수 있었어.\n', '잘 이해할 수 있었어.”\n')
    if w['author']:
        w['author'] = '- 필리프 슈테르처, 『제정신이라는 착각』 - (출제를 위해 일부 수정)' if '슈테르처' in w['author'] else '- ' + w['author']
issues.append('비문학 07: (가) ‘비교하는데’ → ‘비교하는 데’, (나) ‘연구소에 필적 감정을’ → ‘연구소의’, ⓑ(2) ‘국립과학수사연수소’ → ‘연구소’, (3) 인용문 닫는 따옴표(”) 보충 — 1회와 같음')
w = S9['works'][0]
w['lines'] = blank(w['lines'], '환상', '㉮', '‘현실과 부합하는 환상’이다.')
w['lines'] = blank(w['lines'], '감각 데이터', '㉯', '머릿속 예측 기계가 감각 데이터에 더 많은 비중을 둘수록')
w['lines'] = blank(w['lines'], '통제감', '㉰', '통제감을 되찾게 하는 것이다.')
# 30~32, 서답형 4: 06 지문 — 2회 28~30번 본문, [A] 없음, ⓐ·ⓑ 유지, 어휘 ㉠~㉤ 새로
S10 = nonlit(gk('D', 0), '30～32, 서답형 4')
w0 = S10['works'][0]
w0['lines'] = re.sub(r'[㉠-㉤]<u>([^<]*)</u>', r'\1', w0['lines'])
for w in S10['works']:
    w['lines'] = w['lines'].replace('갑첩', '간첩')
assert not re.search('[㉠-㉤]', w0['lines'])
w0['lines'] = mark(w0['lines'], '부상한', '㉠')
w0['lines'] = mark(w0['lines'], '일축했지만', '㉡')
w0['lines'] = mark(w0['lines'], '색출', '㉢')
w0['lines'] = mark(w0['lines'], '풍미했던', '㉣')
w0['lines'] = mark(w0['lines'], '기승', '㉤')
SETS = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10]
for s in SETS:
    for w in s['works']:
        assert '{' not in w['lines'] or s['rng'] in ('4～7, 서답형 1', '8～11'), s['rng']

# ---- 문항·해설: raw.txt ----
raw = open(f'{H}/raw.txt', encoding='utf8').read().split('\n')
CIRC = '①②③④⑤'
qsets, exs = [], []
cur = None; mode = 'q'; q = None; e = None; box = None; nxt = 1
for line in raw + ['']:
    s = line.rstrip()
    if s.startswith('#'):
        continue
    if s.startswith('【'):
        cur = []; qsets.append(cur); mode = 'q'; continue
    if s == '@EX':
        mode = 'ex'; e = None; continue
    if mode == 'q':
        m = re.match(r'^(\d+)\. (.*)$', s) or re.match(r'^\[(서답형 \d)\] (.*)$', s)
        if m and (m.group(1).startswith('서답형') or int(m.group(1)) == nxt):
            nxt += m.group(1).isdigit()
            q = {'no': m.group(1), 'stem': m.group(2), 'bogi': None, 'choices': [], 'extra': None}
            cur.append(q); box = None; continue
        if s in ('<보 기>', '<보기>'):
            q['bogi'] = {'title': '<보 기>', 'text': ''}; box = q['bogi']; continue
        if s in ('<조 건>', '<조건>'):
            q['extra'] = {'title': '<조 건>', 'text': ''}; box = q['extra']; continue
        if s.startswith('@C '):
            q['chead'] = s[3:].split('|'); box = None; continue
        if s[:1] in CIRC:
            q['choices'].append(s[1:].strip()); box = None; continue
        if s and box is not None:
            box['text'] += ('\n' if box['text'] else '') + s
            continue
    else:
        m = re.match(r'^(\d+)\. ([①-⑤]|미정)$', s)
        m2 = re.match(r'^\[(서답형 \d)\]$', s)
        if m or m2:
            e = {'no': m.group(1) if m else m2.group(1), 'answer': m.group(2) if m else '', 'correct': '', 'wrong': [], 'plain': ''}
            exs.append(e); sub = 'c'; continue
        if not s:
            continue
        if e['no'].startswith('서답형') or e['answer'] == '미정':
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
            e['wrong'].append([s[:1], s[1:].strip()] if s[:1] in CIRC else ['', s])   # ㄱ~ㄹ 항목은 그대로

# 선지 표(㉮~㉰ 짝 짓기)
for qs in qsets:
    for x in qs:
        h = x.pop('chead', None)
        if h:
            rows = '<tr><td></td>' + ''.join(f'<td>{c}</td>' for c in h) + '</tr>'
            rows += ''.join(f'<tr><td>{CIRC[i]}</td>' + ''.join(f'<td>{c.strip()}</td>' for c in t.split('|')) + '</tr>' for i, t in enumerate(x['choices']))
            x['ctab'] = f'<div class="ctabq"><table>{rows}</table></div>'

assert len(qsets) == len(SETS), (len(qsets), len(SETS))
for st, qs in zip(SETS, qsets):
    st['questions'] = qs
nq = sum(1 for qs in qsets for x in qs if x['no'].isdigit())
ns = sum(1 for qs in qsets for x in qs if not x['no'].isdigit())
for qs in qsets:
    for x in qs:
        if x['no'].isdigit():
            assert len(x['choices']) == 5, x['no']
            assert len(set(x['choices'])) == 5, ('선지 중복', x['no'])
assert [x['no'] for qs in qsets for x in qs if x['no'].isdigit()] == [str(k) for k in range(1, nq + 1)]
assert [x['no'] for x in exs] == [x['no'] for qs in qsets for x in qs], '문항·해설 번호 순서'
json.dump({'sets': SETS, 'ex': exs, 'issues': issues}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('객관식', nq, '서답형', ns)
print('정답', ''.join((x['answer'] if x['answer'] in CIRC else '?') for x in exs if x['no'].isdigit()))
print('\n'.join(issues))
