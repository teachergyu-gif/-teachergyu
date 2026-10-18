"""전사 JSON 합치기 + 원본 오류 수정 → data.json. 수정 내역은 fixlog.txt."""
import json, re, os
D = os.path.dirname(os.path.abspath(__file__))
L = lambda f: json.load(open(os.path.join(D, f)))
pa, pb = L('pass_a.json'), L('pass_b.json')
qs = L('q01_15.json')['questions'] + L('q16_30.json')['questions']
ex = L('ex.json')['ex']
log = []


def rep(s, a, b, where, count_req=True):
    if a not in s:
        if count_req:
            raise SystemExit(f'not found [{where}]: {a}')
        return s
    log.append(f'{where}: {a} → {b}')
    return s.replace(a, b)


sets = pa['sets'] + pb['sets']
# 12번은 7쪽 묶음(10~11번)의 (가)(나)를 대상으로 함. 8쪽 왼쪽 아래 요약 지문 상자(13~15번용)는 전사 누락분 → 추가
[s for s in sets if str(s['id']) == '8'][0]['questions'].append(12)
sets.append({'id': '8L', 'questions': [13, 14, 15], 'head': '※ 다음 (가)와 (나)를 읽고 물음에 답하시오.', 'notes': [],
             'works': [{'label': '(가)', 'label_inline': True, 'prose': True,
                        'lines': '강호(江湖)에 가을이 드니 고기마다 살쪄 있다 / 소정(小艇)에 그물 실어 흘러가는 대로 띄워 던져두고 / 이 몸이 소일(消日)하옴도 역군은(亦君恩)이샷다'},
                       {'label': '(나)', 'label_inline': True, 'prose': True,
                        'lines': '논밭 갈아 김 매고 베잠방이 대님쳐 신들매고 / 낫 갈아 허리에 차고 도끼 벼려 둘러메고 무림산중(茂林山中) 들어가서 [...] / 석양이 재 넘어갈 제 어깨를 추스르며 긴 소리 짧은 소리 하며 어이 갈꼬 하더라.'}]})
sets.sort(key=lambda s: s['questions'][0])
S = {str(s['id']): s for s in sets}


def W(sid, label):
    return [w for w in S[sid]['works'] if w['label'] == label][0]


def wrep(sid, label, a, b):
    w = W(sid, label)
    w['lines'] = rep(w['lines'], a, b, f'지문[{sid}{label}]')


# --- 지문 ---
wrep('1', '(라)', '亦郡恩', '亦君恩')
wrep('1', '(라)', '역군은 이샷다', '역군은이샷다')
wrep('2', '(나)', '人ᄃᆞᆯ', 'ㅅᄃᆞᆯ')
wrep('2', '(다)', '白松鶻 )', '白松鶻)')
wrep('3', '(나)', '<<하사', '<하사')
wrep('3', '(나)', '天疊玉山', '千疊玉山')
for sid, lab in (('4', '(나)'), ('7', '(다)')):
    wrep(sid, lab, '흥(興이)', '흥(興)이')
    wrep(sid, lab, '銀鱗魚', '錦鱗魚')
    wrep(sid, lab, '亦君恩은)', '亦君恩)')
wrep('4', '(나)', '기픠자히', '기픠 자히')
wrep('4', '(나)', '안주로라', '안주로다')
wrep('5', '(라)', '보내는니', '보내느니')
for h in ('從容', '氣像', '闊遠', '境界'):
    wrep('6', '(다)', f'( {h})', f'({h})')
# 10쪽 상춘곡: 글꼴 문제로 빠진 옛한글 → 같은 작품 9쪽 판본으로 복원
W('10L', '(나)')['lines'] = W('9L', '(나)')['lines']
log.append('지문[10L(나)]: 옛한글 탈락(엇더고, 녯사 풍류 미가 미가 …) → 9쪽 판본으로 복원')
for sid in ('9L', '10L', '12L'):
    wrep(sid, '(나)', '錄樣芳草', '綠楊芳草')

# 출처 줄 형식 통일: - 작가, 「작품」
AUTH = {
    '<어부단가(漁父短歌)>, 이현보': '- 이현보, 「어부단가(漁父短歌)」',
    '<강호사시가(江湖四時歌)>, 맹사성': '- 맹사성, 「강호사시가(江湖四時歌)」',
    '- 윤선도, 『강호사시가』': '- 맹사성, 「강호사시가」',
    '황진이 -': '- 황진이',
    '- 박효관 -': '- 박효관',
    '- 작자미상 -': '- 작자 미상',
    '- 맹사성, 「강호사시가(江湖四時歌)」 -': '- 맹사성, 「강호사시가(江湖四時歌)」',
    '맹사성, 「강호사시사」': '- 맹사성, 「강호사시가」',
}


def fix_author(t):
    t = t.strip()
    if t in AUTH:
        return AUTH[t]
    m = re.match(r'^-?\s*(.*?),\s*[‘「](.*?)[’」]\s*(중에서)?$', t)
    if m:
        return f'- {m.group(1)}, 「{m.group(2)}」' + (' 중에서' if m.group(3) else '')
    return t if t.startswith('- ') else '- ' + t.lstrip('-').strip()


for s in sets:
    for w in s['works']:
        out = []
        for l in w['lines'].split('\n'):
            if l.startswith('@'):
                nl = '@' + fix_author(l[1:])
                if nl != l:
                    if l[1:].strip() == '- 윤선도, 『강호사시가』':
                        log.append(f'지문[{s["id"]}] 출처: {l[1:]} → {nl[1:]} (작가 오기)')
                l = nl
            out.append(l)
        w['lines'] = '\n'.join(out)

# --- 문항 ---
Q = {q['n']: q for q in qs}
Q[2]['stem'] = rep(Q[2]['stem'], '않은</u> 것은', '않은</u> 것은?', '2번 발문')
Q[7]['bogi']['text'] = rep(Q[7]['bogi']['text'], '각 연 마다', '각 연마다', '7번 <보기>')
Q[8]['bogi']['text'] = rep(Q[8]['bogi']['text'], '져그덧', '져근덧', '8번 <보기>')
Q[10]['choices'][2] = rep(Q[10]['choices'][2], '사물화 하는', '사물화하는', '10번 ③')
Q[12]['choices'][1] = rep(Q[12]['choices'][1], '정(精)', '정(情)', '12번 ②')
Q[12]['choices'][3] = rep(Q[12]['choices'][3], '도션', '됴션', '12번 ④')
Q[29]['bogi']['text'] = rep(Q[29]['bogi']['text'], '비욱', '비우고', '29번 <보기>')

# --- 해설 ---
E = {e['n']: e for e in ex}
E[27]['answer'] = '③'
log.append('27번 정답: ② → ③ (해설이 ㄱ, ㄴ, ㅁ 세 개를 적절하지 않다고 설명 = 3개)')
E[12]['body'] = rep(E[12]['body'], '‘밤믈과 낟믈’ ‘곶’', '‘밤믈과 낟믈’, ‘곶’', '12번 해설')
E[29]['body'] = rep(E[29]['body'], '있닫', '있다는', '29번 해설')
E[11]['body'] = rep(E[11]['body'], '‘역군은이샷다‘', '‘역군은이샷다’', '11번 해설', False)
b = E[26]['body']
b = rep(b, '’삿갓을 빗기 쓰고~’ 부분에서 (나)는 ‘산림‘', '‘삿갓을 빗기 쓰고~’ 부분에서, (나)는 ‘산림’', '26번 해설')
b = re.sub(r'([①②③④⑤])(?=\S)', r'\1 ', b)
E[26]['body'] = b
E[25]['body'] = re.sub(r'([①②③④⑤])(?=\S)', r'\1 ', E[25]['body'])
E[28]['body'] = rep(E[28]['body'], '’이 몸이 ~하옴도 역군은(亦君恩)이샷다‘', '‘이 몸이 ~하옴도 역군은(亦君恩)이샷다’', '28번 해설')
b = E[30]['body'].replace("(' 미친 흥'", "('미친 흥'")
E[30]['body'] = re.sub(r"'([^']*)'", r'‘\1’', b)
log.append('30번 해설: 곧은 따옴표 → ‘ ’, "(\' 미친 흥\'" 공백 삭제')
# 원본에 해설이 없는 8번: 새로 작성
E[8]['body'] = ('<보기>는 밤이 되어 바람과 물결이 잦아들자 부상(해 뜨는 곳) 가까이에서 달을 기다리는 장면이다. '
                '(라)는 망양정에서 본 거센 파도를 ‘은산’, ‘ᄇᆡᆨ셜’에 빗대어 표현하는 낮 장면으로 끝나고, '
                '(마)는 ‘쥬렴을 고텨 것고, 옥계ᄅᆞᆯ 다시 쓸며, 계명셩 돗도록 곳초 안자 ᄇᆞ라보니’로 시작하여 밤에 달이 떠오르기를 기다리는 장면이 이어진다. '
                '따라서 <보기>는 (라)와 (마) 사이, 즉 (마)의 앞에 들어가야 자연스럽다.')
log.append('8번 해설: 원본에 없음 → 새로 작성')

for n, e in E.items():
    for k in ('answer', 'body'):
        e[k] = e[k].replace(' / ', '\n') if n == 27 and k == 'body' else e[k]

E[1]['body'] = rep(E[1]['body'], '반면, (나)는 ‘탁료계변’', '반면, (라)는 ‘탁료계변’', '1번 해설(지문 표지 오류)')
E[2]['body'] = rep(E[2]['body'], '시적화자', '시적 화자', '2번 해설')
# --- 2차 교정(검토 결과) ---
wrep('8', '(다)', 'ᄯᅮᆨ닥', 'ᄯᅮᆼ닥')
wrep('8', '(나)', '浮說', '浮世')
for s in sets:
    for w in s['works']:
        for a, b2 in (('安酒', '按酒'), ('삭정이마른', '삭정이 마른'), ('헌ᄉᆞᄅᆞᆸ다', '헌ᄉᆞ롭다')):
            if a in w['lines']:
                w['lines'] = rep(w['lines'], a, b2, f'지문[{s["id"]}{w["label"]}]')
Q[29]['bogi']['text'] = rep(Q[29]['bogi']['text'], '콧노래 조올다가', '콧노래에 조올다가', '29번 <보기>(지문과 통일)')
# 7번: ㄷ '중장'은 '종장'의 오류 → 정답이 성립하지 않음. ㄷ을 바로잡고 정답 ④(ㄱ, ㄴ, ㄷ)
Q[7]['bogi']['text'] = rep(Q[7]['bogi']['text'], 'ㄷ. 각 연마다 중장의 첫 음보는', 'ㄷ. 각 수마다 종장의 첫 음보는', '7번 <보기> ㄷ')
E[7]['answer'] = '④'
log.append('7번 정답: ⑤ → ④ (원본 정답 ㄱ,ㄴ,ㄹ은 ㄹ이 (라) 사대부 작품에 맞지 않아 불성립)')
E[7]['body'] = ('(가)~(라)는 모두 시조이다. ㄱ. 시조는 4음보의 율격을 기본으로 한다. '
                'ㄴ. 시조는 초장과 중장에서 상황을 제시하고, 종장에서 화자의 정서를 드러내는 경우가 많다. '
                'ㄷ. 시조는 종장의 첫 음보가 세 글자로 고정되어 있다. (가) ‘어론 님’, (나) ‘날 잇고’, (다) ‘쉰밥이’, (라) ‘이 몸이’가 모두 세 글자이다. '
                'ㄹ. 작가층이 평민으로 확대되고 민요적 특성을 지니는 것은 조선 후기 사설시조인 (다)에 해당하는 특징이다. (라)는 사대부인 맹사성의 작품이므로 공통점이 될 수 없다.')
log.append('7번 해설: 원본에 없음 → 새로 작성')
# 19번: (가)에는 설의적 표현이 없음 → ④도 틀린 진술이 되어 복수 정답. 선택지 ④를 (나)만으로 한정
Q[19]['choices'][3] = rep(Q[19]['choices'][3], '(가)와 (나)는 모두 설의적 표현을', '(나)는 설의적 표현을', '19번 ④')
E[19]['body'] = rep(E[19]['body'], '④ (가)의 “이 몸이 한가하옴도 역군은이샷다”나 (나)의 “지락을 모를 것인가”는',
                    '④ (나)의 ‘지락(至樂)을 ᄆᆞᄅᆞᆯ 것가’는', '19번 해설 ④')
E[26]['body'] = rep(E[26]['body'], '‘삿갓을 빗기 쓰고~’', '‘삿갓 빗기 쓰고~’', '26번 해설(지문 인용 형태)')
for n in E:
    if '수풀에 우는 새' in E[n]['body']:
        E[n]['body'] = rep(E[n]['body'], '수풀에 우는 새', '수풀에 우ᄂᆞᆫ 새', f'{n}번 해설(지문 인용 형태)')
E[23]['body'] = rep(E[23]['body'], '(가)는 춘사, 하사, 추사, 동사로 구성되어', '(가)는 제1수~제4수가 봄, 여름, 가을, 겨울로 구성되어', '23번 해설(지문 표지)')
E[27]['body'] = '적절하지 않은 것은 ㄱ, ㄴ, ㅁ의 3개이다.\n' + E[27]['body']
E[3]['body'] = rep(E[3]['body'], '나눠져 있다', '나뉘어 있다', '3번 해설')
E[10]['body'] = rep(E[10]['body'], '사설 시조로', '사설시조로', '10번 해설')
E[10]['body'] = rep(E[10]['body'], '현대 시조이다', '현대시조이다', '10번 해설')
E[25]['body'] = rep(E[25]['body'], '안분지족 삶의', '안분지족의 삶의', '25번 해설')
wrep('8', '(나)', '천지 폐색(天地 閉塞) 호되 바다흔', '천지 폐색(天地閉塞)ᄒᆞ되 바다ᄒᆞᆫ')
wrep('3', '(나)', '듸희ᄂᆞᆫ', '뒤희ᄂᆞᆫ')
wrep('1', '(라)', '더뎌 주고', '더뎌 두고')
Q[12]['stem'] = rep(Q[12]['stem'], '(정답 2개)', '<u>(정답 2개)</u>', '12번 발문 밑줄(원본 표기)')
log.append('지문[9] 출처: 「강호사시사」 → 「강호사시가」 (같은 작품의 다른 이름, 시험지 안 표기 통일)')
for e in E.values():
    b = e['body'].replace(' / ', '\n')
    b = re.sub(r'(?<=[.다])\s+(?=[①②③④⑤]\s)', '\n', b)
    b = re.sub(r'(?<=[.다])\s+(?=[ㄱ-ㅎ]\.\s)', '\n', b)
    e['body'] = b
data = {'sets': sets, 'questions': [Q[n] for n in sorted(Q)], 'ex': [E[n] for n in sorted(E)]}
json.dump(data, open(os.path.join(D, 'data.json'), 'w'), ensure_ascii=False, indent=1)
open(os.path.join(D, 'fixlog.txt'), 'w').write('\n'.join(log) + '\n')
print(len(log), 'fixes')
