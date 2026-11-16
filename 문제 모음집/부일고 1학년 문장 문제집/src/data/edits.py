"""문항 표기 수정(검토 반영). apply(q) — 발문·<보기>·선지·출처 글에 적용."""
import re, json

SRC = {}
GRADE = {n: '고3' for n in range(85, 118)}   # 원본 세 자리 번호(고3 문제집) 문항
REP = {}


def fix_text(s, no):
    for a, b in REP.get(no, []):
        s = s.replace(a, b)
    s = re.sub(r'([가-힣]) (니다|시다)(?=[^가-힣]|$)', r'\1\2', s)          # ‘가능합 니다’ → ‘가능합니다’
    s = s.replace('￮', '◦')
    s = re.sub(r'(○○[가-힣]+)', r'<span class="nb">\1</span>', s)   # ‘○○미술관’이 ○ 사이에서 갈라지지 않게
    s = re.sub(r'([㉠-㉭ⓐ-ⓩㄱ-ㅎ])\s*[~〜～∼]\s*([㉠-㉭ⓐ-ⓩㄱ-ㅎ])', r'\1~\2', s)   # 범위 기호 ‘~’로 붙여
    s = re.sub(r'([㉠-㉭ⓐ-ⓩ])(</u>)? (과|와|의|에서|에|을|를|은|는|이|가|도|만|로|으로)(?=[\s.,’”)<]|$)', r'\1\2\3', s)   # ‘㉢ 의’ → ‘㉢의’
    for a, b in REP.get(no, []):
        s = s.replace(a, b)
    return s


def apply(q):
    no = q['no']
    q['stem'] = fix_text(q['stem'], no)
    for b in q['blocks']:
        if 'html' in b:
            b['html'] = fix_text(b['html'], no)
            if b['type'] == 'bogi':   # 원본이 띄어쓰기 여러 칸으로 자리를 맞춘 곳(‘어간     이나’)은 한 칸으로
                b['html'] = re.sub(r'(?<=[가-힣)’])\s{3,}(?=[가-힣(‘])', ' ', b['html'])
        if 'rows' in b: b['rows'] = [[fix_text(c, no) for c in r] for r in b['rows']]
    q['choices'] = [fix_text(c, no) for c in q['choices']]
    if q.get('ctab'): q['ctab'] = fix_text(q['ctab'], no)
    s = q['src']
    s = re.sub(r'국어 ([AB](?:/[AB])?형)', r'국어영역 \1', s)
    if no in SRC: s = s.replace(*SRC[no])
    if no in GRADE and '학력평가' in s and not re.search(r'고[123]', s): s = re.sub(r'(\d+월) ', r'\1 ' + GRADE[no] + ' ', s, 1)
    q['src'] = s
