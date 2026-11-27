"""1차 N제(data1/n1_rNN.json, 한글 파일 PDF에서 옮김)와 2차 N제(언어와 매체 N제/src/data/rNN.json)에서
'단어 파트'(품사, 형태소·단어의 형성) 문항만 골라 파트별 묶음으로 다시 번호를 매긴다.
r01.json = Ⅰ 품사, r02.json = Ⅱ 형태소와 단어의 형성. 지문 묶음은 통째로 옮기고, 문항 번호는 1번부터 이어 매긴다."""
import json, os, copy

H = os.path.dirname(os.path.abspath(__file__))
SRC = {'1차': os.path.join(H, '..', 'data1') + '/n1_r{:02d}.json',
       '2차': os.path.join(H, '..', '..', '..', '언어와 매체 N제', 'src', 'data') + '/r{:02d}.json'}
OFFSET = 34
PARTS = [
    ('Ⅰ. 품사', [
        # 품사 분류·품사 통용
        ('1차', 18, 37), ('2차', 15, 39), ('1차', 6, 37), ('1차', 24, 39),
        # 체언
        ('1차', 15, 35), ('1차', 4, 38), ('2차', 3, 38), ('1차', 10, 37), ('2차', 14, 39),
        # 관계언
        ('1차', 7, 38), ('1차', 13, 35), ('1차', 16, 35),
        # 수식언
        ('1차', 14, 38),
        # 용언: 자동사·타동사, 활용, 사전, 어미, 보조 용언
        ('1차', 3, 39), ('2차', 6, 39), ('2차', 19, 35),
        ('1차', 12, 35), ('2차', 11, 38), ('1차', 4, 39), ('1차', 8, 38), ('1차', 10, 39), ('2차', 18, 39), ('1차', 24, 37),
        ('1차', 18, 38), ('2차', 16, 39), ('1차', 9, 35), ('2차', 17, 35),
    ]),
    ('Ⅱ. 형태소와 단어의 형성', [
        # 형태소, 어근과 어간
        ('1차', 17, 35), ('2차', 2, 38), ('2차', 18, 38), ('1차', 3, 37), ('2차', 13, 35), ('1차', 5, 35),
        # 파생어
        ('1차', 4, 37), ('2차', 5, 38), ('2차', 9, 37), ('1차', 20, 35), ('2차', 8, 38), ('1차', 9, 39), ('1차', 11, 37),
        # 합성어
        ('1차', 1, 35), ('2차', 1, 35), ('2차', 7, 38), ('2차', 6, 37), ('2차', 12, 37), ('2차', 15, 37), ('1차', 21, 38),
    ]),
]
n = 0
seen = set()
for k, (title, picks) in enumerate(PARTS, 1):
    sets, ex, src = [], {}, []
    for which, r, q0 in picks:
        d = json.load(open(SRC[which].format(r)))
        s = next(s for s in d['sets'] if any(q['orig'] == q0 for q in s['questions']))
        s = copy.deepcopy(s)
        if not s['works']:   # 지문 없는 단독 문항 묶음: 고른 문항만
            s['questions'] = [q for q in s['questions'] if q['orig'] == q0]
        first = n + 1
        for q in s['questions']:
            key = (which, r, q['orig'])
            assert key not in seen, key
            seen.add(key)
            n += 1
            old = q['orig']
            q['orig'] = n + OFFSET
            q.pop('colbrk', None)
            label = f"{which} N제 {r}회 {old - OFFSET}번"
            ex[str(q['orig'])] = dict(d['ex'][str(old)], src=label)
            src.append((n, label))
        if s['works']:
            s['rng'] = f'{first + OFFSET}～{n + OFFSET}'
        sets.append(s)
    json.dump({'title': title, 'source': src, 'sets': sets, 'ex': ex}, open(f'{H}/r{k:02d}.json', 'w'), ensure_ascii=False, indent=1)
    print(title, len(src), ''.join(ex[str(i + OFFSET)]['answer'] for i, _ in src))
