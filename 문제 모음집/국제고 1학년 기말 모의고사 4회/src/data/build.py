"""모의고사 4회 데이터 만들기: 지문(교재 파일 원문, 2회·3회와 같은 본문) + raw.txt(문항·해설) → exam.json
사용: python3 build.py 원본폴더(c.txt·d.txt·e.txt = 교재 hwpx/hwp에서 뽑은 글) 공통국어2데이터폴더
- c.txt: 국제고 1학년 2학기 기말고사 진달래꽃, 무화과 교재(hwpx)
- d.txt: 국제고 1학년 2학기 기말고사 춘향전 교재(hwpx)
- e.txt: 국제고 1학년 「타는 목마름으로」,「두꺼비」 교재(hwp)
- 비문학 03(사랑천 산책로 협상)·04(금융 이해력)·05(마녀사냥)·07(제정신이라는 착각): 김T 비문학 프린트물(교재/공통국어2 2학기 기말고사 대비/src/data B·C·E)
- 15~17 기부 지문: 원본폴더의 gibu.txt(3-(2)단원 교재 본문 강의용, 한 줄에 한 문단)와
  ../img/gibu1.*·gibu2.*·gibu3.*(교과서 [자료 1]~[자료 3])가 있으면 넣고, 없으면 자리 표시만 둔다.
※ 2회·3회에 쓰인 기호는 모두 지우고, 편집 안내(4회)의 기호·빈칸·묶음만 새로 넣음."""
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
SYM = r'[㉠-㉭ⓐ-ⓩ]'


def nosym(t):
    """교재·2회·3회 기호 지우기(기호+밑줄/굵게 → 말만)"""
    t = re.sub(SYM + r'\s?<u>(?:<b>)?(.*?)(?:</b>)?</u>', r'\1', t)
    assert not re.search(SYM + '|<u>|<b>', t), t[:80]
    return t


# ---- 1~3: (가) 한 그리움이 다른 그리움에게 / (나) 진달래꽃 / (다) 선운사에서 — 세 편 모두 전문, 기호 없음 ----
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
for t in (jd, hg, sw):
    assert not re.search(SYM + '|<u>', t)
S1 = {'rng': '1～3', 'works': [
    {'label': '(가)', 'lines': hg, 'author': '- 정희성, 「한 그리움이 다른 그리움에게」 -'},
    {'label': '(나)', 'lines': jd, 'author': '- 김소월, 「진달래꽃」 -'},
    {'label': '(다)', 'lines': sw, 'author': '- 최영미, 「선운사에서」 -'}]}

# ---- 4~7, 서답형 1: (가) 무화과(기호 없음) / (나) 타는 목마름으로(ⓐ~ⓔ) / (다) 김소월, 「바라건대는 …」 ----
mu = block(C, '무화과(강의용)', r'^- 김지하')
ta = block(E, '김지하, ｢타는 목마름으로｣(강의용 지문)', r'^- 김지하')
ta = ta.replace('발자국 소리', '발자욱 소리')   # 교과서 판본(1회·2회·3회와 같음)
assert not re.search(SYM + '|<u>', mu + ta)
ta = mark(ta, '목마름의 기억', 'ⓐ')
ta = mark(ta, '남 몰래', 'ⓑ')                 # 첫 번째 것(‘네 이름을 남 몰래 쓴다 민주주의여’)
assert '네 이름을 ⓑ <u>남 몰래</u> 쓴다 민주주의여' in ta
ta = mark(ta, '푸르른 자유의 추억', 'ⓒ')
ta = mark(ta, '끌려가던 벗들의 피 묻은 얼굴', 'ⓓ')
ta = mark(ta, '만세', 'ⓔ')
# (다) 김소월 — 편집 안내(4회)의 본문·주석 그대로(원문 대조 결과는 issues에 적음)
bo = """나는 꿈꾸었노라, 동무들과 내가 가지런히
벌가의 하루 일을 다 마치고
석양에 마을로 돌아오는 꿈을,
즐거이, 꿈 가운데.

그러나 집 잃은 내 몸이여,
바라건대는 우리에게 우리의 보습 대일 땅이 있었더면!
이처럼 떠돌으랴, 아침에 저물손에
새라새로운 탄식을 얻으면서.

동이랴, 남북이랴,
내 몸은 떠가나니, 볼지어다,
희망의 반짝임은, 별빛이 아득임은.
물결뿐 떠올라라, 가슴에 팔다리에.

그러나 어쩌면 황송한 이 심정을! 날로 나날이 내 앞에는
자칫 가늘은 길이 이어가라. 나는 나아가리라
한 걸음, 또 한 걸음. 보이는 산비탈엔
온새벽 동무들 저 저 혼자…… 산경(山耕)을 김매이는."""
issues.append('4~7 (다) 김소월: 편집 안내 본문 그대로 넣음. 널리 쓰이는 현대어 표기본과 다른 곳(원문 대조는 기억에 의존, 원본 확인 필요): 8행 ‘새라새로운’(대개 ‘새라 새로운’으로 띄어 씀), 16행 ‘온새벽’(원문 표기, 현대어본에 따라 ‘온 새벽’). 원문 제목은 ‘보섭’.')
S2 = {'rng': '4～7, 서답형 1', 'works': [
    {'label': '(가)', 'lines': mu, 'author': '- 김지하, 「무화과」 -'},
    {'label': '(나)', 'lines': ta, 'author': '- 김지하, 「타는 목마름으로」 -'},
    {'label': '(다)', 'lines': bo, 'author': '- 김소월, 「바라건대는 우리에게 우리의 보습 대일 땅이 있었더면」 -',
     'notes': ['*보습: 쟁기 끝에 끼워 땅을 가는 쇳조각.\u2003*저물손: 저물녘.', '*산경: 산에 있는 밭을 가는 일.']}]}

# ---- 8~11: 춘향전 (2회 14~17번 본문, ㉠~㉤·[C] 새로) ----
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
ch = re.sub(r'옥소반의 아름다운 안주는 ?\n일만 백성의 기름이라\.', '옥소반의 아름다운 안주는 일만 백성의 기름이라.', ch)
assert not re.search(SYM + '|<u>', ch)
ch = mark(ch, '“여봐라 사령들아. 너의 사또에게 여쭈어라. 먼 데 있는 걸인이 좋은 잔치에 왔으니 술과 안주나 좀 얻어먹자고 여쭈어라.”', '㉠')
ch = mark(ch, '‘오냐. 도적질은 내가 하마. 오라는 네가 받아라.’', '㉡')
ch = mark(ch, '“걸인이 어려서 한시(漢詩)깨나 읽었더니 좋은 잔치 당하여서 술과 안주를 포식하고 그냥 가기 민망하니 차운 한 수 하사이다.”', '㉢')
ch = mark(ch, '“내려오는 관장마다 모두 명관(名官)이로구나. 어사또 들으시오. 층암절벽 높은 바위가 바람 분들 무너지며, 청송녹죽 푸른 나무가 눈이 온들 변하리까. 그런 분부 마옵시고 어서 바삐 죽여 주오.”', '㉣')
ch = mark(ch, '“얼씨구나 좋을시고 어사 낭군 좋을시고. 남원 읍내 가을이 들어 떨어지게 되었더니, 객사에 봄이 들어 이화춘풍(李花春風) 날 살린다. 꿈이냐 생시냐? 꿈을 깰까 염려로다.”', '㉤')
ch = bracket(ch, '이때 어사또는 좌도와 우도의 읍들을 순찰하여', '길이 전하더라.', 'C')
S3 = {'rng': '8～11', 'works': [{'label': '', 'lines': ch, 'author': '- 작자 미상, 「춘향전」 -'}]}

# ---- 12~14: 두꺼비 (2회 6~9번 본문, 앞부분 줄거리 포함, ㉠~㉤ 새로) ----
du = block(E, '황순원, ｢두꺼비｣(강의용 지문)', r'^- 황순원')
du = du.replace('일인지두몰라', '일인지두 몰라')
du = du.replace('서울깍쟁이라더니 정말……\n', '서울깍쟁이라더니 정말……”\n')   # 닫는 따옴표 보충(2회·3회와 같음)
assert not re.search(SYM + '|<u>', du)
du = mark(du, '“우린 전재민이 아니웨까?”', '㉠')
du = mark(du, '그러는 늙은 집주름의 얼굴은 온통 땀투성이가 되고 눈도 충혈이 돼 있었다.', '㉡')
du = mark(du, '현세는 왜 그런지 가슴이 섬뜩함을 느꼈다.', '㉢')
du = mark(du, '서울깍쟁이라더니 정말……”', '㉣')
du = mark(du, '먼 메아리처럼 등 뒤로 들으면서', '㉤')
S4 = {'rng': '12～14', 'works': [{'label': '', 'lines': du, 'author': '- 황순원, 「두꺼비」 -'}]}

# ---- 15~17, 서답형 2: 3-(2)단원 교재 본문(강의용) + 교과서 [자료 1]~[자료 3] — 기호 없음 ----
def gimg(n, cap):
    f = sorted(x for x in glob.glob(f'{IMG}/gibu{n}.*'))
    if f:
        return f'@I {os.path.basename(f[0])} {cap}'
    issues.append(f'15~17: [자료 {n}] 그림 파일(img/gibu{n}.*) 없음 → 자리 표시')
    return f'@I gibu{n}_slot.svg {cap}'
CAP = {1: '[자료 1]', 2: '[자료 2]', 3: '[자료 3]'}
gp = f'{SRC}/gibu.txt'
if os.path.exists(gp):
    paras = [x.strip() for x in open(gp, encoding='utf8').read().split('\n') if x.strip()]
    P = paras[:]
    P.insert(1, gimg(1, CAP[1])); P.insert(2, gimg(2, CAP[2]))   # [자료 1]·[자료 2]: 1문단 뒤
    k = [i for i, x in enumerate(P) if not x.startswith('@I ')][4]
    P.insert(k + 1, gimg(3, CAP[3]))                              # [자료 3]: 5문단 뒤
    gb = '\n'.join(P)
else:
    issues.append('15~17: 기부 지문 원문(gibu.txt) 없음 → 지문 자리 표시만 넣음')
    gb = '\n'.join([
        '※ [지문 자리] 3-(2)단원 교재 본문(강의용) 전체(7문단)가 들어갈 자리입니다. 원문을 받으면 기호 없이 그대로 넣습니다. 교과서 자료는 [자료 1]·[자료 2](1문단 뒤)·[자료 3](5문단 뒤) 자리에 넣습니다.',
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
for sym, ph in [('㉠', '짓밟습니다'), ('㉡', '깊으나 옅으나'), ('㉢', '기다리고 있습니다'), ('㉣', '언제든지 오실 줄만은 알아요')]:
    assert na.count(ph) == 1, ph
    na = mark(na, ph, sym)
for sym, ph in [('㉤', '차마 떨치고 갔습니다'), ('㉥', '귀먹고'), ('㉦', '뜻밖의 일'), ('㉧', '다시 만날 것을 믿습니다')]:
    assert nm.count(ph) == 1, ph
    nm = mark(nm, ph, sym)
S6 = {'rng': '18～20', 'works': [
    {'label': '(가)', 'lines': na, 'author': '- 한용운, 「나룻배와 행인」 -'},
    {'label': '(나)', 'lines': nm, 'author': '- 한용운, 「님의 침묵」 -'}]}

# ---- 비문학: 김T 프린트 03(사랑천 협상)·04(금융 이해력)·05(마녀사냥)·07(제정신이라는 착각) ----
gk = lambda f, i: json.load(open(f'{GK}/{f}/out.json'))['sets'][i]
def nonlit(s, rng):
    return {'rng': rng, 'works': [{'label': w.get('label', ''), 'lines': w['lines'], 'author': w.get('author', '')} for w in s['works']],
            'notes': s.get('notes') or []}
# 21~23: 03 지문(2회 21~23번) — ㉠·㉡·ⓐ 삭제, 빈칸 ㉮~㉰, 묶음 [A]~[C]
S7 = nonlit(gk('B', 0), '21～23')
w = S7['works'][0]
w['lines'] = nosym(w['lines'])
w['lines'] = blank(w['lines'], '서식지', '㉮', '수달의 서식지와 사람들의 이동 경로를 분리해야 합니다.')
w['lines'] = blank(w['lines'], '캠페인', '㉯', '미래시 차원에서 수달 보호 캠페인을 벌일 것을 제안합니다.')
w['lines'] = blank(w['lines'], '생태 복합 시설', '㉰', '그 대신 희망구에 사랑천 생태 복합 시설을 만드는 것을 제안드리려 합니다.')
w['lines'] = bracket(w['lines'], '미래시 공무원 : 안녕하십니까?', '협의가 이루어지길 바랍니다.', 'A')
w['lines'] = bracket(w['lines'], '미래시 공무원 : 깨끗하고 조용한 자연에서', '수달에게 미치는 영향도 비교적 적을 것 같습니다.', 'B')
w['lines'] = bracket(w['lines'], '희망구 주민 대표 : 음…….', '합의안을 만들어 볼까요?', 'C')
L7 = w['lines'].split('\n')
assert L7[0].startswith('{A}') and L7[1].endswith('{/A}') and L7[2].startswith('{B}') and L7[-1].endswith('{/C}') and L7[-4].startswith('{C}'), L7[-4][:20]
# 24~26: 04 지문(금융 이해력) — 기호 없음
S8 = nonlit(gk('B', 1), '24～26')
assert not re.search(SYM + '|<u>', S8['works'][0]['lines'])
# 27~29, 서답형 3: 05 지문(2회 24~27번) — ⓐ 삭제, (나)의 ⓑ만 유지, (가)에 빈칸 ㉮~㉰
S9 = nonlit(gk('C', 0), '27～29, 서답형 3')
for w in S9['works']:
    w['lines'] = w['lines'].replace('(Afred Dreyfus)', '(Alfred Dreyfus)')   # 원문 오타
wa, wb = S9['works'][0], S9['works'][1]
wa['lines'] = nosym(wa['lines'])
assert 'ⓑ<u>사람들</u>' in wb['lines']
wb['lines'] = wb['lines'].replace('ⓑ<u>사람들</u>', 'ⓑ <u>사람들</u>')
assert not re.search(SYM, S9['works'][2]['lines'])
wa['lines'] = blank(wa['lines'], '정적 제거', '㉮', '두 번째 공통점은 정적 제거이다.')
wa['lines'] = blank(wa['lines'], '시선 돌리기', '㉯', '세 번째 공통점은 시선 돌리기다.')
wa['lines'] = blank(wa['lines'], '정서', '㉰', '먼저 개인의 정서 수준을 하락시킨다.')
wa['author'] = '- 홍성남, 「마녀 사냥은 사라졌나」 - (출제를 위해 일부 수정)'
# 30~32, 서답형 4: 07 지문 — ⓐ·ⓑ 유지, 빈칸 없음(3회의 빈칸은 원래 말로), 1회·3회와 같은 오탈자 바로잡기
S10 = nonlit(gk('E', 0), '30～32, 서답형 4')
for w in S10['works']:
    w['lines'] = w['lines'].replace('비교하는데 필요한', '비교하는 데 필요한').replace('국립과학수사연구소에 필적 감정을 증거로', '국립과학수사연구소의 필적 감정을 증거로').replace('국립과학수사연수소', '국립과학수사연구소').replace('잘 이해할 수 있었어.\n', '잘 이해할 수 있었어.”\n')
    w['lines'] = re.sub(r'(ⓐ|ⓑ)<u>', r'\1 <u>', w['lines'])
    if w['author']:
        w['author'] = '- 필리프 슈테르처, 『제정신이라는 착각』 - (출제를 위해 일부 수정)' if '슈테르처' in w['author'] else '- ' + w['author']
assert 'ⓐ' in S10['works'][1]['lines'] and 'ⓑ' in S10['works'][1]['lines'] and '( ' not in S10['works'][0]['lines']
issues.append('비문학 07: (가) ‘비교하는데’ → ‘비교하는 데’, (나) ‘연구소에 필적 감정을’ → ‘연구소의’, ⓑ(2) ‘국립과학수사연수소’ → ‘연구소’, (3) 인용문 닫는 따옴표(”) 보충 — 1회·3회와 같음')
SETS = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10]
for s in SETS:
    for w in s['works']:
        assert '{' not in w['lines'] or s['rng'] in ('8～11', '21～23'), s['rng']

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
        m = re.match(r'^(\d+)\. ([①-⑤](?: \(잠정\))?|미정)$', s)   # ‘② (잠정)’: 지문 확인 전 잠정 정답
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
            assert s[:1] == e['answer'][:1], (e['no'], s[:20])
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
print('정답', ''.join((x['answer'][:1] if x['answer'][:1] in CIRC else '?') for x in exs if x['no'].isdigit()))
print('잠정', [x['no'] for x in exs if '잠정' in x['answer']])
print('\n'.join(issues))
