"""2차 N제(언어와 매체 N제/src/data/rNN.json)에서 '단어 파트'(품사, 형태소·단어의 형성) 문항만 골라
파트별 묶음(r01.json = Ⅰ 품사, r02.json = Ⅱ 형태소와 단어의 형성)으로 다시 번호를 매긴다.
지문 묶음은 통째로 옮기고, 문항 번호는 1번부터 이어 매긴다(해설 번호도 같이)."""
import json, os, copy

H = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(H, '..', '..', '..', '언어와 매체 N제', 'src', 'data')
OFFSET = 34
PARTS = [
    ('Ⅰ. 품사', [('r03', 38), ('r14', 39), ('r15', 39), ('r06', 39), ('r19', 35), ('r11', 38), ('r18', 39), ('r16', 39), ('r17', 35)]),
    ('Ⅱ. 형태소와 단어의 형성', [('r02', 38), ('r18', 38), ('r13', 35), ('r05', 38), ('r09', 37), ('r08', 38), ('r07', 38), ('r01', 35), ('r06', 37), ('r12', 37), ('r15', 37)]),
]
n = 0
for k, (title, picks) in enumerate(PARTS, 1):
    sets, ex, src = [], {}, []
    for r, q0 in picks:
        d = json.load(open(f'{SRC}/{r}.json'))
        s = next(s for s in d['sets'] if any(q['orig'] == q0 for q in s['questions']))
        s = copy.deepcopy(s)
        if not s['works']:   # 지문 없는 단독 문항 묶음: 고른 문항만
            s['questions'] = [q for q in s['questions'] if q['orig'] == q0]
        first = n + 1
        for q in s['questions']:
            n += 1
            old = q['orig']
            q['orig'] = n + OFFSET
            q.pop('colbrk', None)
            ex[str(q['orig'])] = dict(d['ex'][str(old)], src=f"2차 N제 {int(r[1:])}회 {old - OFFSET}번")
            src.append((n, f"2차 N제 {int(r[1:])}회 {old - OFFSET}번"))
        if s['works']:
            s['rng'] = f'{first + OFFSET}～{n + OFFSET}'
        sets.append(s)
    json.dump({'title': title, 'source': src, 'sets': sets, 'ex': ex}, open(f'{H}/r{k:02d}.json', 'w'), ensure_ascii=False, indent=1)
    print(title, len(src), src)
