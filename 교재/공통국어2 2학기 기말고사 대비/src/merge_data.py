"""작업 폴더(scratchpad/gk/work/A~E)의 answers.json·analysis.json을 data/로 합침."""
import json, os, sys
W = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/-home-user/cac8e88e-55f6-555b-a091-e2222438c3e6/scratchpad/gk/work'
D = os.path.dirname(os.path.abspath(__file__)) + '/data'
for f in ('answers', 'analysis'):
    m = {}
    for p in 'ABCDE':
        x = f'{W}/{p}/{f}.json'
        if os.path.exists(x):
            m.update(json.load(open(x)))
    json.dump(m, open(f'{D}/{f}.json', 'w'), ensure_ascii=False, indent=1)
    print(f, sorted(m, key=lambda k: (len(k), k)))
