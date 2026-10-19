"""원본 오류 수정(작품, 문항 orig 또는 'P'+orig=지문, 바꿀 글, 새 글). 문항은 그 문항(발문·보기·선지)과 해설 모두에서 찾는다.
진달래꽃 교재의 fixes_jd.py와 같은 방식."""
import re

HG = '한 그리움이 다른 그리움에게'
SW = '선운사에서'
FIX = [
    # 한 그리움이 다른 그리움에게
    (HG, 1, '배려의 태도로 , 표면적으로는', '배려의 태도로, 표면적으로는'),
    (HG, 8, '수미 상관의 구조를 통해', '수미상관의 구조를 통해'),
    (HG, 12, '13행에서 ‘어느 날’', '14행에서 ‘어느 날’'),           # 15행 중 ‘어느 날’은 1·14행
    (HG, 18, '종결 어미 ‘-리’를 사용하여 시상을 마무리하고 있다.', '종결 어미 ‘-리’를 사용하여 화자의 의지를 드러내고 있다.'),   # 시는 ‘있다면’으로 끝남 → 정답 둘
    (HG, 18, '종결 어미 ‘-리’를 사용하여 시상을 마무리하는 부분 ‘어느 겨울인들/우리들의 사랑을 춥게 하리’ 부분에서 확인할 수 있다.', '종결 어미 ‘-리’를 사용하여 화자의 의지를 드러내는 부분은 ‘나는 기다리리’, ‘어느 겨울인들/우리들의 사랑을 춥게 하리’에서 확인할 수 있다.'),
    (HG, 32, '마지막 부분인 13~15행에', '마지막 부분인 14~15행에'),
    (HG, 36, '추위도 이겨낼 수 있다는', '추위도 이겨 낼 수 있다는'),
    # 창작 시기: 1991년 시집 수록작 — 다른 문항(25번)과 같이 1980년대로 통일
    (HG, 16, '1970년대', '1980년대'),
    (HG, 20, '1970년대', '1980년대'),
    (HG, 28, '1970년대', '1980년대'),
    (HG, 43, '1970년대', '1980년대'),
    # 선운사에서
    (SW, 1, '생성과 순환이라는 자연의 순환', '생성과 소멸이라는 자연의 순환'),
    (SW, 2, '자연현상을 통해', '자연 현상을 통해'),
    (SW, 4, '주제의식을 강조한다', '주제 의식을 강조한다'),
    (SW, 4, '(나)의 시적화자는', '(나)의 시적 화자는'),
    (SW, 6, '특정 종결어미의', '특정 종결 어미의'),
    (SW, 'P8', '산에는 꽃이 피네', '산에는 꽃 피네'),
    (SW, 8, '따라서 (나) ㉠은', '따라서 (가)의 ㉠은'),
    (SW, 8, '(나)의 ㉡ 화자와', '(나)의 ㉡은 화자와'),
    (SW, 8, '공감이라는 해석은', '공간이라는 해석은'),
    (SW, 9, '‘꽃‘은 자연의 세계인 ’산에서', '‘꽃’은 자연의 세계인 ‘산’에서'),
    (SW, 9, '2연의 산에 지는 꽃은', '4연의 산에 지는 꽃은'),
    (SW, 10, '피어 있네’와 ‘멀리서 웃는', '피어 있네’와 (나)의 ‘멀리서 웃는'),
    (SW, 10, '(가)는 꽃의 피고 짐을 통해 사랑과', '(나)는 꽃의 피고 짐을 통해 사랑과'),
    # 20번 ③·31번 ②: 해설이 선지 내용을 인정하면서 오답 처리 → 정답 둘. 선지를 분명히 틀린 내용으로
    (SW, 20, '(나)는 문답의 방식을 통해 화자의 마음을', '(나)는 계절의 변화를 통해 화자의 마음을'),
    (SW, 20, '(나)는 문답의 방식을 통해 님과의 대화를 상상하며 화자의 마음을 표현하고 있으므로 적절하지 않다.', '(나)에는 계절의 변화가 나타나지 않으므로 적절하지 않다.'),
    (SW, 22, '모두 감정이입을 통해', '모두 감정 이입을 통해'),
    (SW, 22, '감정이입의 표현 방식이', '감정 이입의 표현 방식이'),
    (SW, 24, '공통점으로 볼 수 없다', '적절하지 않다'),
    (SW, 30, '(가)와 (나)에 대한 공통점으로', '(가)와 (나)의 공통점으로'),
    (SW, 31, '(나)는 3음보의 율격을 통해', '(나)는 4음보의 율격을 통해'),
    (SW, 31, '(나)는 3음보의 율격이 나타나므로 (나)의 설명이 적절하지 않다.', '(나)는 4음보가 아니라 3음보의 율격이 나타나므로 적절하지 않다.'),
    (SW, 40, '1연과 4연이 유사한 구조(형식)는', '1연과 4연의 유사한 구조(형식)는'),
    (SW, 40, '‘꽃‘이라는 자연물(형식)은 지는 속성(’잠깐‘)', '‘꽃’이라는 자연물(형식)은 지는 속성(‘잠깐’)'),
    (SW, 45, '먼 후일 당신이 찾으시면그때에 내 말이 ‘잊었노라‘당신이 속으로 나무라면’무척 그리다가 잊었노라’오늘도 어제도 아니 잊고먼 후일 그때에 ‘잊었노라’김소월, <먼 후일> -', '먼 후일 당신이 찾으시면\n그때에 내 말이 ‘잊었노라’\n\n당신이 속으로 나무라면\n‘무척 그리다가 잊었노라’\n\n오늘도 어제도 아니 잊고\n먼 후일 그때에 ‘잊었노라’\n- 김소월, 「먼 후일」'),
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
        for e in src['ex']:   # 정답 선지가 [오답풀이]에 또 들어간 것 삭제
            if e.get('wrong') and e['answer'][:1] in '①②③④⑤':
                e['wrong'] = [w for w in e['wrong'] if w[0].strip() != e['answer'][:1]]
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

def straight(s):
    """곧은 따옴표 쌍 → 둥근 따옴표"""
    s = re.sub(r"'([^'\n]{1,80}?)'", r'‘\1’', s)
    return re.sub(r'"([^"\n]{1,80}?)"', r'“\1”', s)


AUTHORS = {'어느 날 당신과 내가': '- 정희성, 「한 그리움이 다른 그리움에게」',
           '당신이 맑은 새벽에': '- 한용운, 「나의 꿈」',
           '피는 건 힘들어도': '- 최영미, 「선운사에서」'}
PLAIN = lambda l: re.sub(r' +', ' ', re.sub(r'</?\w+>|[㉠-㉭㉮-㉻ⓐ-ⓩ]', '', l)).strip()


def poem(w, log):
    """원본이 묶음마다 다르게 찍은 시 모양을 시의 원래 모양으로 맞춘다."""
    t = w['lines']
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
                        while k < len(L) and re.match(r'^<u>[^<]*</u>$', L[k]):
                            L[k] = L[k][3:-4]; k += 1
                    L[i] = new
                    i += 1
                if gone:
                    w['lines'] = '\n'.join(L)
                    log.append(f'{src["source"]} 지문(문항 {[q["orig"] for q in s["questions"]]}): 문항에 없는 기호 삭제 {"".join(dict.fromkeys(gone))}')


# ---- 문항에서 쓰지 않는 지문(작품) 삭제: (작품, 묶음 첫 문항 원번호) → 지울 표지 ----
# 표지 (가)(나)(다)는 문항이 그대로 가리키므로 바꾸지 않는다.
DROP_WORKS = {
    (SW, 6): ['(가)'],    # 황인숙 「봄눈 오는 밤」 — 6번은 (나)·(다)만 물음
    (SW, 7): ['(다)'],    # 서정주 「추천사」 — 7번은 (가)·(나)만 물음
    (HG, 16): ['(나)'],   # 한용운 「나의 꿈」 — 16번은 (가)만 물음
    (HG, 19): ['(나)'],   # 한용운 「나의 꿈」 — 19번은 (가)만 물음
}


def drop_works(data, log):
    for src in data:
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
            log.append(f'{src["source"]} 지문(문항 {[q["orig"] for q in qs]}): 문항에 쓰지 않는 지문 삭제 ' + ', '.join(f'{w["label"]} {(w.get("author") or "").lstrip("- ")}' for w in gone))
