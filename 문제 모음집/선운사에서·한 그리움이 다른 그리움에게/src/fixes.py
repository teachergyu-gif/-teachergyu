"""원본 오류 수정(작품, 문항 orig 또는 'P'+orig=지문, 바꿀 글, 새 글). 문항은 그 문항(발문·보기·선지)과 해설 모두에서 찾는다.
진달래꽃 교재의 fixes_jd.py와 같은 방식."""
import re

FIX = [
]


def quotes(s):
    s = re.sub(r'’(\S[^‘’,\n]{0,30}?\S|\S)‘', r'‘\1’', s)
    s = re.sub(r'‘([^‘’\n]{1,40})‘', r'‘\1’', s)
    s = re.sub(r'’([^‘’\n]{1,40})’', r'‘\1’', s)
    return s


def walk(o, f):
    if isinstance(o, str):
        return f(o)
    if isinstance(o, list):
        return [walk(x, f) for x in o]
    if isinstance(o, dict):
        return {k: (walk(v, f) if k not in ('orig', 'why') else v) for k, v in o.items()}
    return o


def apply(data, log):
    for src in data:
        name = src['source']
        for work, key, a, b in FIX:
            if work != name:
                continue
            hit = False
            for s in src['sets']:
                ids = [q['orig'] for q in s.get('questions', [])]
                if isinstance(key, str):  # 지문: 그 문항이 든 묶음
                    if int(key[1:]) in ids:
                        for w in s['works']:
                            if a in w['lines']:
                                w['lines'] = w['lines'].replace(a, b); hit = True
                    continue
                for qi, q in enumerate(s.get('questions', [])):
                    if q['orig'] == key:
                        nq = walk(q, lambda t: t.replace(a, b))
                        if nq != q: hit = True
                        s['questions'][qi] = nq
            for ei, e in enumerate(src['ex']):
                if e['orig'] == key:
                    ne = walk(e, lambda t: t.replace(a, b))
                    if ne != e: hit = True
                    src['ex'][ei] = ne
            if not hit:
                raise SystemExit(f'수정 대상 없음: {name} {key} {a}')
            log.append(f'{name} {key}번: {a} → {b}')
        for e in src['ex']:
            for w in e.get('wrong') or []:
                if w[1].startswith(w[0]):
                    w[0] = ''
        # 지문 속 밑줄 앞 기호(㉠ ⓐ Ⓐ ㉮ 등)와 밑줄 사이 한 칸
        SYM = r'([㉠-㉭㉮-㉻ⓐ-ⓩⒶ-Ⓩ])'
        for s in src['sets']:
            for w in s.get('works', []):
                t = re.sub(r'<u>' + SYM + r'\s*', r'\1 <u>', w['lines'])
                t = re.sub(SYM + r'(<b>)?<u>', r'\1 \2<u>', t).replace(' None<u>', ' <u>')
                w['lines'] = t
        for s in src['sets']:
            for w in s.get('works', []):
                poem(w, log)
        src['sets'] = walk(src['sets'], straight); src['ex'] = walk(src['ex'], straight)
        src['sets'] = walk(src['sets'], quotes); src['ex'] = walk(src['ex'], quotes)


def straight(s):
    """곧은 따옴표 쌍 → 둥근 따옴표"""
    s = re.sub(r"'([^'\n]{1,80}?)'", r'‘\1’', s)
    return re.sub(r'"([^"\n]{1,80}?)"', r'“\1”', s)


AUTHORS = {'어느 날 당신과 내가': '- 정희성, 「한 그리움이 다른 그리움에게」',
           '당신이 맑은 새벽에': '- 한용운, 「나의 꿈」',
           '피는 건 힘들어도': '- 최영미, 「선운사에서」'}
PLAIN = lambda l: re.sub(r'</?\w+>|[㉠-㉭㉮-㉻ⓐ-ⓩ]', '', l).strip()


def poem(w, log):
    """원본이 묶음마다 다르게 찍은 시 모양을 시의 원래 모양으로 맞춘다."""
    t = w['lines']
    if t.startswith('어느 날') and '그윽한 눈' in t:
        # 정희성 시: 4연 15행(문항·해설이 '1연·4연', '마지막 연'을 전제함)
        t = t.replace('춥게하리', '춥게 하리').replace('춥게 하리 외롭고', '춥게 하리\n외롭고')
        L = [l for l in t.split('\n') if l.strip()]
        out = []
        for i, l in enumerate(L):
            out.append(l)
            if i < len(L) - 1 and re.search(r'(비단이 된다면|들여다볼 때|기다림 끝에)$', PLAIN(l)):
                out.append('')
        t = '\n'.join(out)
    if '피는 건 힘들어도' in t:
        t = t.replace('그대가 처음 내 속에', '그대가 처음\n내 속에').replace('꽃이지는', '꽃이 지는')
    if '갈 봄 여름 없이' in t:   # 김소월 「산유화」: 두 행이 한 줄로 붙은 것
        t = t.replace('꽃이 지네. 갈 봄', '꽃이 지네.\n갈 봄')
    if '잊었노라' in t:   # 김소월 「먼 후일」: 따옴표가 앞 행 끝에 잘못 붙은 것
        t = re.sub(r'나무라면’\n([^\n‘]*잊었노라)’', r'나무라면\n‘\1’', t)
    if t != w['lines']:
        log.append('지문 모양: ' + PLAIN(t.split('\n')[0]))
        w['lines'] = t
    a = (w.get('author') or '').strip()
    if a or w.get('label') != '(나)' or not t.startswith('이 작품'):
        a = re.sub(r'^-\s*|\s*-$', '', a)
        a = re.sub(r'<([^<>]+)>|‘([^’]+)’', lambda m: '「' + (m.group(1) or m.group(2)) + '」', a)
        if not a:
            a = next((v[2:] for k, v in AUTHORS.items() if k in t), '')
        w['author'] = ('- ' + a) if a else None
