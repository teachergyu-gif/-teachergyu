"""원본 오류 수정(회차, 문항 orig 또는 'P'=지문, 바꿀 글, 새 글). 문항은 그 문항(발문·보기·선지)과 해설 모두에서 찾는다."""
import re, json
SYMS = r'[㉠-㉭㉮-㉻ⓐ-ⓩⒶ-Ⓩ]'

FIX = [
    # 1회
    (1, 9, '각 행이 3연으로', '각 연이 3행으로'),
    (1, 10, '자신이 떠나는 길에', '임이 떠나는 길에'),
    (1, 3, '유격', '율격'),
    (1, 7, '임과의 이별하고', '임과 이별하고'),
    (1, 7, '공덕을기리는', '공덕을 기리는'),
    (1, 18, '㉠~㉤중', '㉠~㉤ 중'),
    (1, 19, '大平盛大', '大平盛代'),
    (1, 5, '점입가경', '설상가상'),
    (1, 11, '윗글의 ‘(가)와 (나)', '윗글의 (가)와 (나)'),
    (1, 'P3', 'ᄌᆞᆷ은 엇디 자시ᄂᆞᆫ고.', 'ᄌᆞᆷ은 엇디 자시ᄂᆞᆫ고'),
    (1, 'P3', '츄일동쳔', '츄일동텬'),
    (1, 'P7', '가시옵소서.\n나 보기가', '가시옵소서.\n\n나 보기가'),
    (1, 14, '민속적 전통을 배경으로', '민족적 전통을 배경으로'),
    (1, 8, '① 에서도', '①에서도'),
    (1, 17, '화자는 체념적 태도가 드러난다', '화자의 체념적 태도가 드러난다'),
    # 2회
    (2, 'P2', 'ᄒᆞ돗쎤디', 'ᄒᆞ돗ᄯᅥᆫ디'),
    (2, 'P2', 'ᄆᆞ음', 'ᄆᆞᄋᆞᆷ'),
    (2, 'P2', 'ᄇᆞᆰ갓ᄂᆞᆫ고', 'ᄇᆞᆯ갓ᄂᆞᆫ고'),
    (2, 'P20', 'ᄒᆞ돗쎤디', 'ᄒᆞ돗ᄯᅥᆫ디'),
    (2, 'P20', 'ᄆᆞ음', 'ᄆᆞᄋᆞᆷ'),
    (2, 'P20', 'ᄇᆞᆰ갓ᄂᆞᆫ고', 'ᄇᆞᆯ갓ᄂᆞᆫ고'),
    (2, 'P6', '<u>진달래꽃</u>', '㉮<u>진달래꽃</u>'),
    (2, 3, '‘믈가’', '‘믈ᄀᆞ’'),
    (2, 5, '슬픔으로 드러내지', '슬픔을 드러내지'),
    (2, 13, '(나)는 가시리/', '(나)는 ‘가시리/'),
    (2, 21, '대한 대한', '대한'),
    (2, 21, '<보기>엣는', '<보기>에서는'),
    (2, 21, '(나),<보기>', '(나), <보기>'),
    # 3회
    (3, 'P12', 'ⓐ<u>안개</u>', 'ⓑ<u>안개</u>'),
    (3, 12, '㉤ : 도치과 반어적 표현으로', '㉤ : 반어적 표현으로'),
    (3, 12, '반어법과, 목적어와 서술어의 순서를 바꾼 도치법을 사용하여', '반어법을 사용하여'),
    (3, 3, '3자에서 13자까지', '4자에서 13자까지'),
    (3, 9, '견뎌 내려하고', '견뎌 내려 하고'),
    (3, 9, '(가)에서 ‘진달래꽃’은', '(나)에서 ‘진달래꽃’은'),
    # 4회
    (4, 2, '발아들이겠다는', '받아들이겠다는'),
    (4, 8, '슬픔과 충격과 깔려', '슬픔과 충격이 깔려'),
    (4, 6, '태도로 ,', '태도로,'),
    (4, 14, '太平盛大(태평셩대)', '大平盛代(대평셩ᄃᆡ)'),
    (4, 2, '임에 또한 강렬한', '임에 대한 강렬한'),
    (4, 'P4', 'ᄒᆞ돗ᄯᅧᆫ디', 'ᄒᆞ돗ᄯᅥᆫ디'),
    (4, 'P4', 'ᄂᆞᆽ비치', 'ᄂᆞᆺ비치'),
    (4, 'P4', 'ᄀᆞᆽ티', 'ᄀᆞᆺ티'),
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
    for i, src in enumerate(data, 1):
        for rnd, key, a, b in FIX:
            if rnd != i:
                continue
            hit = False
            for s in src['sets']:
                ids = [q['orig'] for q in s.get('questions', [])]
                if isinstance(key, str):  # 지문: 그 문항이 든 묶음
                    if int(key[1:]) in ids:
                        for w in s['works']:
                            if a in w['lines']:
                                w['lines'] = w['lines'].replace(a, b, 1 if 'ⓐ' in a else -1); hit = True
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
                raise SystemExit(f'수정 대상 없음: {rnd}회 {key} {a}')
            log.append(f'{rnd}회 {key}번: {a} → {b}')
        for e in src['ex']:
            for w in e.get('wrong') or []:
                if w[1].startswith(w[0]):
                    w[0] = ''
        # 쓰이지 않는 밑줄(속미인곡 ‘보오’) 제거, 따옴표 방향
        for s in src['sets']:
            for w in s.get('works', []):
                if '<u>보오</u>' in w['lines']:
                    w['lines'] = w['lines'].replace('<u>보오</u>', '보오'); log.append(f'{i}회 지문: 문항에서 쓰지 않는 ‘보오’ 밑줄 삭제')
        # 문항(넣은 문항·해설)에서 쓰지 않는 지문 속 기호·[A] 묶음·밑줄은 삭제(풀이 때 헷갈리지 않게)
        exm = {e['orig']: e for e in src['ex']}
        for s in src['sets']:
            qs = s.get('questions') or []
            if not qs:
                continue
            used_txt = json.dumps([qs, [exm.get(q['orig']) for q in qs]], ensure_ascii=False)
            used = set(re.findall(SYMS, used_txt))
            for a_, b_ in re.findall('(' + SYMS + r')\s*[~～∼\-]\s*(' + SYMS + ')', used_txt):
                used |= {chr(c) for c in range(ord(a_), ord(b_) + 1)}
            labs = set(re.findall(r'\[([A-Z])\]', used_txt))
            for a_, b_ in re.findall(r'\[([A-Z])\]\s*[~～∼\-]\s*\[([A-Z])\]', used_txt):
                labs |= {chr(c) for c in range(ord(a_), ord(b_) + 1)}
            plain_txt = re.sub(r'\(.*?\)|[^가-힣ᄀ-ᇿ]', '', used_txt)
            tag = f'{i}회 지문({qs[0]["orig"]}번 묶음)'
            for w in s.get('works', []):
                out_lines, carry = [], None   # carry: 앞 줄 끝에서 이어지는 밑줄을 남길지(True)/지울지(False)
                for line in w['lines'].split('\n'):
                    pos, res, last_keep = 0, '', None
                    pat = re.compile('(' + SYMS + r')?\s*((?:<b>)?<u>.*?</u>(?:</b>)?|<b>.*?</b>)|(' + SYMS + ')')
                    for m in pat.finditer(line):
                        res += line[pos:m.start()]; pos = m.end()
                        sym = m.group(1) or m.group(3); seg = m.group(2)
                        if seg is None:          # 밑줄 없는 기호
                            if sym in used: res += m.group(0)
                            else: log.append(f'{tag}: 문항에 없는 기호 {sym} 삭제')
                            continue
                        if sym:
                            keep = sym in used
                        elif m.start() == 0 and carry is not None:
                            keep = carry         # 앞 줄에서 이어진 밑줄
                        else:
                            inner = re.sub(r'</?[bu]>', '', seg)
                            key = re.sub(r'\(.*?\)|[^가-힣ᄀ-ᇿ]', '', inner)[:4]
                            keep = bool(key) and key in plain_txt
                        if keep:
                            res += m.group(0)
                        else:
                            res += re.sub(r'</?[bu]>', '', seg)
                            log.append(f'{tag}: 문항에 없는 ' + (f'기호 {sym}와 밑줄' if sym else f'밑줄·굵게 ‘{re.sub(r"</?[bu]>", "", seg)[:10]}’') + ' 삭제')
                        last_keep = keep if m.end() >= len(line.rstrip()) - len(re.search(r'\{/\w+\}$', line).group(0) if re.search(r'\{/\w+\}$', line) else '') else None
                    res += line[pos:]
                    carry = last_keep if re.search(r'</u>(</b>)?(\{/\w+\})?\s*[.,]?$', line) else None
                    out_lines.append(res)
                t = '\n'.join(out_lines)
                for lab in set(re.findall(r'\{([A-Z])\}', t)) - labs:
                    t = t.replace('{' + lab + '}', '').replace('{/' + lab + '}', '')
                    log.append(f'{tag}: 문항에 없는 [{lab}] 묶음 표시 삭제')
                w['lines'] = t
        # 지문 속 밑줄 앞 기호(㉠ ⓐ Ⓐ ㉮ 등)와 밑줄 사이 한 칸
        SYM = r'([㉠-㉭㉮-㉻ⓐ-ⓩⒶ-Ⓩ])'
        for s in src['sets']:
            for w in s.get('works', []):
                t = re.sub(r'<u>' + SYM + r'\s*', r'\1 <u>', w['lines'])
                t = re.sub(SYM + r'(<b>)?<u>', r'\1 \2<u>', t).replace(' None<u>', ' <u>')
                if t != w['lines']:
                    w['lines'] = t
        log.append(f'{i}회 지문: 밑줄 앞 기호 뒤 한 칸 띄움')
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
            log.append(f'{i}회 해설: 문장 끝 마침표 보완 {nd}곳')
        before = repr(src)
        src['sets'] = walk(src['sets'], quotes); src['ex'] = walk(src['ex'], quotes)
        if repr(src) != before:
            log.append(f'{i}회: 방향이 뒤집힌 작은따옴표 바로잡음')
