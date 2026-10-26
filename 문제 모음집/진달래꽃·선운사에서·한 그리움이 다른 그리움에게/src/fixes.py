"""원본 오류 수정(작품, 문항 orig 또는 'P'+orig=지문, 바꿀 글, 새 글). 문항은 그 문항(발문·보기·선지)과 해설 모두에서 찾는다.
진달래꽃 교재의 fixes_jd.py와 같은 방식."""
import re

JD = '진달래꽃'
HG = '한 그리움이 다른 그리움에게'
SW = '선운사에서'
FIX = [
    (JD, 'P22', '<box>달</box>', '달'),   # 「황계사」 ‘달’ 네모: 문항에서 쓰지 않음
    (SW, 'P13', '<box>산</box>에는', '산에는'),   # 「산유화」 ‘산’ 네모: 13번에서 쓰지 않음
]
# 검수·해설 보충 결과(review/*.json: fix = 원본 오류 수정, ex_add = 원본에 없는 해설)
import json as _json, os as _os
_R = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'review')
_REV = {}
for _k, _w in (('jd', JD), ('sw', SW), ('hg', HG)):
    _p = _os.path.join(_R, f'{_k}.json')
    if _os.path.exists(_p):
        _REV[_w] = _json.load(open(_p))
        for _f in _REV[_w].get('fix', []):
            FIX.append((_w, _f['orig'], _f['old'], _f['new']))


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
        for e in src['ex']:   # 정답 선지가 [오답풀이]에 또 들어간 것 삭제
            if e.get('wrong') and e['answer'][:1] in '①②③④⑤':
                e['wrong'] = [w for w in e['wrong'] if w[0].strip() != e['answer'][:1]]
            c = e['answer'][:1]
            if e.get('correct') and c in '①②③④⑤' and e['correct'].startswith(c):   # 정답 기호가 해설 앞에 또 붙은 것
                e['correct'] = e['correct'][1:].lstrip()
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
        # 해설 문장 끝 마침표 보완(원본에 빠진 곳)
        END = (r'(?:하다|않다|있다|이다|한다|된다|없다|같다|는다|진다|난다|낸다|렵다|준다|친다|린다|춘다|였다|었다|았다|했다|'
               r'보인다|든다|운다|룬다|간다|온다|본다|싶다|아니다|가깝다|멀다|띤다|맞다|틀리다)')
        def dot(t):
            out = []
            for para in t.split('\n'):
                p2 = re.sub(END + r'(?=\s+\S)', lambda m: m.group(0) + '.', para)
                if re.search(r'[가-힣ᄀ-ᇿ0-9)\]]$', p2.rstrip()):
                    p2 = p2.rstrip() + '.'
                out.append(p2)
            return '\n'.join(out)
        nd = 0
        for e in src['ex']:
            for k in ('correct', 'plain'):
                if e.get(k):
                    t = dot(e[k]); nd += t != e[k]; e[k] = t
            for w in e.get('wrong') or []:
                t = dot(w[1]); nd += t != w[1]; w[1] = t
            if len(e['answer']) >= 12:
                t = dot(e['answer']); nd += t != e['answer']; e['answer'] = t
        if nd:
            log.append(f'{name} 해설: 문장 끝 마침표 보완 {nd}곳')
        # 원본 오류 수정은 표기를 맞춘 뒤에
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

    drop_works(data, log)
    drop_marks(data, log)
    add_ex(data, log)

def straight(s):
    """곧은 따옴표 쌍 → 둥근 따옴표"""
    s = re.sub(r"'([^'\n]{1,80}?)'", r'‘\1’', s)
    return re.sub(r'"([^"\n]{1,80}?)"', r'“\1”', s)


AUTHORS = {'어느 날 당신과 내가': '- 정희성, 「한 그리움이 다른 그리움에게」',
           '나 보기가 역겨워': '- 김소월, 「진달래꽃」',
           '가시리 가시리잇고': '- 작자 미상, 「가시리」',
           '당신이 맑은 새벽에': '- 한용운, 「나의 꿈」',
           '피는 건 힘들어도': '- 최영미, 「선운사에서」'}
PLAIN = lambda l: re.sub(r' +', ' ', re.sub(r'</?\w+>|[㉠-㉭㉮-㉻ⓐ-ⓩ]', '', l)).strip()


def unslash(t, extra=()):
    """빗금(/)·겹빗금(//)·두 칸 띄움으로 줄여 찍은 시를 행·연으로 편다. 행을 넘는 밑줄·굵게는 행마다 닫고 다시 연다.
    extra: 한 행에 붙어 찍힌 것을 더 나눌 자리(정규식, 그 자리에서 줄바꿈)"""
    t = re.sub(r'\s*//\s*(?=\n|$)', '\n', t)                 # 행 끝 // → 연 구분(뒤 줄바꿈과 합쳐 빈 줄)
    t = re.sub(r'(?<=\S)\s*//\s*', '\n\n', t)
    t = re.sub(r'\s*//\s*', '\n\n', t)
    t = re.sub(r'\s+/\s*|(?<=[가-힣.])  +(?=\S)', '\x00', t)
    for rx in extra:
        t = re.sub(rx, '\x00', t)
    out = []
    for line in t.split('\n'):
        opened = []
        pieces = []
        for pc in line.split('\x00'):
            pre = ''.join(f'<{x}>' for x in opened)
            for tag in re.findall(r'<(/?)(u|b)>', pc):
                if tag[0]:
                    if tag[1] in opened: opened.remove(tag[1])
                else:
                    opened.append(tag[1])
            pieces.append(pre + pc.strip() + ''.join(f'</{x}>' for x in reversed(opened)))
        out.append('\n'.join(re.sub(r'<(u|b)></\1>', '', p) for p in pieces))
    t = '\n'.join(out)
    return re.sub(r'\n{3,}', '\n\n', t).strip('\n')


def poem(w, log):
    """원본이 묶음마다 다르게 찍은 시 모양을 시의 원래 모양으로 맞춘다."""
    t = w['lines']
    if re.search(r' / |//|[가-힣]  [가-힣]', t) and ('피는 건 힘들어도' in PLAIN(t) or '갈 봄 여름 없이' in t):
        # 「산유화」: 한 행에 붙어 찍힌 곳도 나눔
        ex = (r'(?<=피네\.) (?=꽃이)', r'(?<=지네\.) (?=꽃이)', r'(?<=없이) (?=꽃이)', r'(?<=산에) (?=산에)', r'(?<=산에) (?=피는)', r'(?<=좋아) (?=산에서)', r'(?<=산에서) (?=사노라네)') if '갈 봄 여름 없이' in t else ()
        t = unslash(t, ex)
    if PLAIN(t).startswith('어느 날') and '그윽한 눈' in t:
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
        # 교과서 수록본(PART 01 작품 분석)으로 통일: 4연, 1연·4연 첫 행 ‘꽃이’ 따로, ‘님 한 번’, 마침표 없음
        t = re.sub(r'(꽃이(?:</u>)?) (?=(?:<u>)?(?:피는 건 힘들어도|지는 건 쉬워도))', r'\1\n', t)
        t = re.sub(r'\n\n(?=[^\n]*골고루)', '\n', t)
        t = re.sub(r'[임님] 한 ?번', '님 한 번', t).replace('쳐다 볼', '쳐다볼').replace('산 넘어 가는', '산 넘어가는')
        t = re.sub(r'(꽃이(?:</u>)?\n(?:<u>)?)피는 건 쉬워도', r'\1지는 건 쉬워도', t)   # 4연 첫머리를 1연으로 잘못 옮긴 것
        t = re.sub(r'\.(?=(?:</u>)?(?:\{/[^}]+\})?(?:\n|$))', '', t)
    if '갈 봄 여름 없이' in t:   # 김소월 「산유화」: 두 행이 한 줄로 붙은 것, 묶음마다 다른 마침표(없는 쪽으로 통일)
        t = t.replace('꽃이 지네. 갈 봄', '꽃이 지네.\n갈 봄')
        t = re.sub(r'\.(?=(?:</u>)?(?:\{/[^}]+\})?(?:\n|$))', '', t)
    if '당신이 맑은 새벽에' in t:   # 한용운 「나의 꿈」: 묶음마다 다른 문장 끝 마침표를 통일
        t = re.sub(r'습니다$', '습니다.', t, flags=re.M)
    if '잊었노라' in t:   # 김소월 「먼 후일」: 따옴표가 앞 행 끝에 잘못 붙은 것
        t = re.sub(r'나무라면’\n([^\n‘]*잊었노라)’', r'나무라면\n‘\1’', t)
    if t != w['lines']:
        log.append('지문 모양: ' + PLAIN(t.split('\n')[0]))
        w['lines'] = t
    a = (w.get('author') or '').strip()
    if a or w.get('label') != '(나)' or not t.startswith('이 작품'):
        a = re.sub(r'^-\s*|\s*-$', '', a)
        a = re.sub(r'<(?!/?[ub]>)([^<>]+)>|‘([^’]+)’', lambda m: '「' + (m.group(1) or m.group(2)) + '」', a)
        if not a:
            a = next((v[2:] for k, v in AUTHORS.items() if k in t), '')
        w['author'] = ('- ' + a) if a else None


# ---- 문항에서 쓰지 않는 지문 기호 삭제 ----
SYMS = '㉠㉡㉢㉣㉤㉥㉦㉧㉨㉩㉪㉫㉬㉭' + '㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻' + ''.join(chr(c) for c in range(0x24D0, 0x24EA)) + ''.join(chr(c) for c in range(0x24B6, 0x24D0))
SERIES = ['㉠㉡㉢㉣㉤㉥㉦㉧㉨㉩㉪㉫㉬㉭', '㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻',
          ''.join(chr(c) for c in range(0x24D0, 0x24EA)), ''.join(chr(c) for c in range(0x24B6, 0x24D0))]


def used_marks(qs):
    """문항(발문·<보기>·선지·조건)에 나오는 기호. ‘㉠~㉤’ 같은 범위는 펼친다."""
    t = json_text(qs)
    used = set(ch for ch in t if ch in SYMS)
    for a, b in re.findall(r'([' + SYMS + r'])\s*[~～∼\-]\s*([' + SYMS + r'])', t):
        for ser in SERIES:
            if a in ser and b in ser and ser.index(a) <= ser.index(b):
                used |= set(ser[ser.index(a):ser.index(b) + 1])
    used |= set(re.findall(r'\[([A-Z])\]', t))
    return used


def json_text(qs):
    import json
    return json.dumps([{k: q.get(k) for k in ('stem', 'bogi', 'choices', 'extra')} for q in qs], ensure_ascii=False)


def drop_marks(data, log):
    S = '[' + SYMS + ']'
    for src in data:
        for s in src['sets']:
            used = used_marks(s.get('questions') or [])
            for w in s.get('works', []):
                L = w['lines'].split('\n')
                gone = []
                i = 0
                while i < len(L):
                    l = L[i]
                    # [A]·{Ⓐ} 묶음 표시
                    m = re.match(r'^\{([^{}/]+)\}', l)
                    if m and m.group(1) not in used:
                        lab = m.group(1); gone.append(lab)
                        L[i] = l = l[m.end():]
                        for j in range(i, len(L)):
                            if re.search(r'\{/' + re.escape(lab) + r'\}$', L[j]):
                                L[j] = re.sub(r'\{/' + re.escape(lab) + r'\}$', '', L[j]); break
                    # 기호(+ 그 기호의 밑줄)
                    def sub(mm):
                        if mm.group(1) in used:
                            return mm.group(0)
                        gone.append(mm.group(1))
                        return (mm.group(2) or '') + (mm.group(3) if mm.group(3) is not None else '') + (mm.group(4) or '')
                    new = re.sub(r'(' + S + r') ?(<b>)?(?:<u>(.*?)</u>)?(</b>)?', lambda mm: sub(mm) if mm.group(3) is not None else (mm.group(0) if mm.group(1) in used else (gone.append(mm.group(1)) or (mm.group(2) or '') + (mm.group(4) or ''))), l)
                    # 지운 기호의 밑줄이 줄 끝까지 가면 다음 줄들의 이어진 밑줄도 지움
                    if new != l and re.search(r'</u>$', l) and not re.search(r'</u>$', new):
                        k = i + 1
                        while k < len(L) and re.match(r'^<u>[^<]*</u>', L[k]):   # 이어진 밑줄(줄 앞부분까지만 이어진 것 포함)
                            whole = re.match(r'^<u>[^<]*</u>$', L[k])
                            L[k] = re.sub(r'^<u>([^<]*)</u>', r'\1', L[k]); k += 1
                            if not whole:
                                break
                    L[i] = new
                    i += 1
                if gone:
                    w['lines'] = '\n'.join(L)
                    log.append(f'{src["source"]} 지문(문항 {[q["orig"] for q in s["questions"]]}): 문항에 없는 기호 삭제 {"".join(dict.fromkeys(gone))}')


# ---- 문항에서 쓰지 않는 지문(작품) 삭제: (작품, 묶음 첫 문항 원번호) → 지울 표지 ----
# 한 작품만 남으면 표지를 지우고 문항·해설의 표지를 '윗글'로(조사 맞춤), 여러 작품이 남으면 (가)(나)… 순서로 다시 매긴다.
DROP_WORKS = {
    (JD, 7): ['(가)', '(나)'],                 # 「가시리」·이조년 — 7번은 (다) 「진달래꽃」과 <보기>만
    (JD, 8): ['(나)'],                         # 「가시리」 — 8번은 (가)의 ⓑ만
    (JD, 13): ['(가)'],                        # 「가시리」 — 13번은 (나)의 ⓐ만
    (JD, 14): ['(가)'],                        # 「가시리」 — 14·15번은 (나)와 그 ㉠~㉤만
    (JD, 26): ['(가)', '(나)', '(다)', '(라)', '(마)', '(사)'],   # 26번은 (바) 「진달래꽃」만
    (JD, 29): ['(나)'],                        # 「제망매가」 — 29번은 (가)·(다)만
    (SW, 12): ['(가)'],                        # 윤동주 「쉽게 씌어진 시」 — 12번 ㉠~㉤은 (나)~(라)에만
    (SW, 13): ['(다)'],                        # 김관식 「거산호·II」 — 13번은 (가)·(나)만
}
LABS = '가나다라마바사아'
JOSA = {'와': '과', '는': '은', '가': '이', '를': '을'}   # 받침 없는 표지 → '윗글'(받침 ㄹ)


def relabel(t, m):
    """t 안의 표지 (가)(나)…를 m에 따라 한 번에 바꾼다. '윗글'로 바뀌면 뒤 조사도 맞춘다."""
    def sub(mm):
        lab, josa = mm.group(1), mm.group(2) or ''
        new = m.get(lab)
        if new is None:
            return mm.group(0)
        if new == '윗글':
            return '윗글' + JOSA.get(josa, josa)
        return new + josa
    return re.sub(r'(\([가-아]\))(와|는|가|를)?', sub, t)


def drop_works(data, log):
    for src in data:
        exm = {e['orig']: e for e in src['ex']}
        for s in src['sets']:
            qs = s.get('questions') or []
            if not qs:
                continue
            labs = DROP_WORKS.get((src['source'], qs[0]['orig']))
            if not labs:
                continue
            before = len(s['works'])
            gone = [w for w in s['works'] if w.get('label') in labs]
            s['works'] = [w for w in s['works'] if w.get('label') not in labs]
            assert len(s['works']) == before - len(labs), (src['source'], qs[0]['orig'])
            if len(s['works']) == 1:
                m = {s['works'][0]['label']: '윗글'}
                s['works'][0]['label'] = ''
            else:
                m = {}
                for k, w in enumerate(s['works']):
                    m[w['label']] = f'({LABS[k]})'; w['label'] = f'({LABS[k]})'
            m = {a: b for a, b in m.items() if a != b}
            for q in qs:
                for k in ('stem', 'bogi', 'choices', 'extra'):
                    if q.get(k):
                        q[k] = walk(q[k], lambda t: relabel(t, m))
                e = exm.get(q['orig'])
                if e:
                    for k in ('answer', 'correct', 'wrong', 'plain'):
                        if e.get(k):
                            e[k] = walk(e[k], lambda t: relabel(t, m))
            log.append(f'{src["source"]} 지문(문항 {[q["orig"] for q in qs]}): 문항에 쓰지 않는 지문 삭제 ' + ', '.join(f'{w["label"]} {(w.get("author") or "").lstrip("- ")}' for w in gone) + (f' / 표지 {m}' if m else ''))


# ---- 원본에 해설이 없는 문항: 새로 쓴 해설(정답 선지 해설 + 오답풀이) ----
EX_ADD = {(w, a['orig']): {k: v for k, v in a.items() if k != 'orig'} for w, r in _REV.items() for a in r.get('ex_add', [])}


def add_ex(data, log):
    for src in data:
        for e in src['ex']:
            add = EX_ADD.get((src['source'], e['orig']))
            if add:
                for k, v in add.items():
                    assert not e.get(k), ('원본에 해설이 있음', src['source'], e['orig'], k)
                    e[k] = v
                log.append(f'{src["source"]} {e["orig"]}번: 원본에 없는 해설 새로 씀')
