"""교정용 텍스트: 완성본 번호와 원본(작품·원번호)을 함께 보인다. 사용: python3 preview.py 데이터폴더 > preview.txt"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/pdf')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render, fixes
data = render.load(sys.argv[1]); fixes.apply(data, [])
n = 0
exs = []
for src in data:
    exm = {e['orig']: e for e in src['ex']}
    for s in src['sets']:
        qs = s.get('questions') or []
        print(f'\n##### 지문 묶음 [{n+1}~{n+len(qs)}] ({src["source"]} 원번호 {[q["orig"] for q in qs]})')
        for w in s['works']:
            print(w.get('label') or '', '\n' + w['lines'], '\n', w.get('author'))
        for nt in s.get('notes') or []: print(nt)
        for q in qs:
            n += 1
            print(f'\n{n}. [{src["source"]} {q["orig"]}번] {q["stem"]}')
            if q.get('bogi'): print('[보기]', q['bogi'])
            if q.get('extra'): print('[extra]', q['extra'])
            for i, c in enumerate(q.get('choices') or []): print('①②③④⑤'[i], c)
            exs.append((n, src['source'], exm[q['orig']]))
print('\n\n##### 정답 및 해설')
for k, sname, e in exs:
    print(f'\n{k}. [{sname} {e["orig"]}번] 정답 {e["answer"]}')
    for f in ('correct', 'plain'):
        if e.get(f): print(f'({f})', e[f])
    for w in e.get('wrong') or []: print('  오답', w[0], w[1])
