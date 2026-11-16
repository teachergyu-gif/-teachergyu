"""원본 한글 파일의 해설(정답이 정답인 이유 / 오답이 오답인 이유) → ex/001-068.json.
원본은 줄마다 Enter로 끊겨 있어 이음매의 띄어쓰기를 판정한다(exjoins.json이 우선)."""
import re, json, os
H = os.path.dirname(os.path.abspath(__file__))
L = open('/tmp/claude-0/-home-user/cac8e88e-55f6-555b-a091-e2222438c3e6/scratchpad/hwp7/x.txt', encoding='utf8').read().split('\n')
try:
    J = json.load(open(os.path.join(H, 'exjoins.json'), encoding='utf8'))
except FileNotFoundError:
    J = {}
JL = []
st = next(i for i, l in enumerate(L) if '기출문제[263~330번] 해설' in l)
blocks = []; cur = None
for l in L[st:]:
    m = re.fullmatch(r'\s*(\d{3})번\s*', l)
    if m: cur = {'no': int(m.group(1)), 'lines': []}; blocks.append(cur); continue
    if cur: cur['lines'].append(l)


def glue(a, b):
    if a.endswith(' ') or b.startswith(' '): return ''
    key = a.rstrip()[-10:] + '|' + b.strip()[:10]
    if key in J: g = J[key]
    else:
        g = ' ' if re.search(r'([을를이가은는의에와과로도만며고면게서록기듯데니요다,.)’”]|에서|에게|까지|부터)$', a.rstrip()) else ''
        if re.match(r'^(도|이다|일까|이기|하지|하게|하다|한다|했다|하는|하고|하여|하며|해|되|된|됩|으로|로|를|을|는|은|의|에|와|과|이|가|들|씩|만)(\s|[.,?!’”]|$)', b.strip()): g = ''
        if re.match(r'^[.,)’”]', b.strip()): g = ''
    JL.append((key, g)); return g


def join(seg):
    out = []
    for x in seg:
        if re.match(r'^\s*([①-⑤]|[ㄱ-ㅎ]\.|-|→|•|◦|○|※|\[|<|\(\d\)|[가-하]\.)', x) or not out: out.append(x.strip())
        else: out[-1] = out[-1].rstrip() + glue(out[-1], x) + x.strip() if not out[-1].endswith(' ') else out[-1] + x.strip()
    return [re.sub(r'\s+', ' ', o).strip() for o in out]


ex = []
for b in blocks:
    raw = b['lines']
    cut = next((k for k, x in enumerate(raw) if x.strip() == '문항 번호'), len(raw))
    ls = [x for x in raw[:cut] if x.strip() and x.strip() != '[TABLE]']
    ans = ls[0].strip()
    i = next(k for k, x in enumerate(ls) if '정답이 정답인 이유' in x)
    j = next((k for k, x in enumerate(ls) if '오답이 오답인 이유' in x), len(ls))
    cor = join(ls[i + 1:j]); wr = join(ls[j + 1:])
    plain = cor + (['[오답풀이]'] + wr if wr else [])
    e = {'no': b['no'] - 262, 'answer': ans, 'plain': '\n'.join(plain), 'orig': b['no']}
    ex.append(e)
json.dump(ex, open(os.path.join(H, 'ex', '001-068.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(JL, open(os.path.join(H, '_exjoinlist.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
print(len(ex), 'joins', len(JL), 'bad', [e['no'] for e in ex if e['answer'] not in '①②③④⑤' or '[오답풀이]' not in e['plain']])
