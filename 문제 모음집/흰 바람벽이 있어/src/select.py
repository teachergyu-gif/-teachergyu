"""난이도별 20문항 고르기 결과(selection.json)로 data/L1·L2·L3/out.json을 만든다. 탄궁가(t01·t02)는 data/TG로 합친다.
selection.json = {"기본": [["s01", 4], ...], "실전": [...], "고난도": [...]}  — 목록 순서 = 교재에 실리는 순서
(최근 연도부터: s01·s02 2025 → s03 2024(01) → s04 2024(02) → s05·s06 2022, 같은 파일은 원래 순서)
사용: python3 select.py 작업폴더(work) 데이터폴더(data)"""
import json, os, sys

W, D = sys.argv[1], sys.argv[2]
sel = json.load(open(f'{D}/selection.json'))


def load(part):
    return json.load(open(f'{W}/{part}/out.json'))


cache = {}
for key, folder in (('기본', 'L1'), ('실전', 'L2'), ('고난도', 'L3')):
    out = {'source': folder, 'sets': [], 'ex': [], 'issues': []}
    for part, orig in sel[key]:
        d = cache.setdefault(part, load(part))
        # 이 문항이 든 묶음
        s = next(s for s in d['sets'] if any(q['orig'] == orig for q in s.get('questions') or []))
        q = next(q for q in s['questions'] if q['orig'] == orig)
        q = dict(q, orig=f'{part}-{orig}')
        if out['sets'] and out['sets'][-1]['_key'] == json.dumps(s['works'], ensure_ascii=False):   # 바로 앞 문항과 같은 지문이면 한 묶음으로
            out['sets'][-1]['questions'].append(q)
        else:
            out['sets'].append({k: v for k, v in s.items() if k not in ('questions', 'skipped')} | {'questions': [q], '_key': json.dumps(s['works'], ensure_ascii=False)})
        e = next(e for e in d['ex'] if e['orig'] == orig)
        out['ex'].append(dict(e, orig=f'{part}-{orig}'))
    for s in out['sets']:
        s.pop('_key')
    os.makedirs(f'{D}/{folder}', exist_ok=True)
    json.dump(out, open(f'{D}/{folder}/out.json', 'w'), ensure_ascii=False, indent=1)
    print(folder, len(sel[key]), '문항', len(out['sets']), '묶음')

# 탄궁가: 두 파트를 이어 붙임(경계에서 같은 지문이면 한 묶음)
tg = {'source': 'TG', 'sets': [], 'ex': [], 'issues': []}
for part in ('t01', 't02'):
    d = load(part)
    for s in d['sets']:
        qs = s.get('questions') or []
        if not qs:
            continue
        s = dict(s, questions=[dict(q, orig=f'{part}-{q["orig"]}') for q in qs])
        if tg['sets'] and tg['sets'][-1]['works'] == s['works']:
            tg['sets'][-1]['questions'] += s['questions']
        else:
            tg['sets'].append(s)
os.makedirs(f'{D}/TG', exist_ok=True)
json.dump(tg, open(f'{D}/TG/out.json', 'w'), ensure_ascii=False, indent=1)
print('TG', sum(len(s['questions']) for s in tg['sets']), '문항', len(tg['sets']), '묶음')
