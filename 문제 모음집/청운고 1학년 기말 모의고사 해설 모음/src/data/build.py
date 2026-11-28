"""청운고 1학년 2학기 기말고사 대비 모의고사 1~3회 해설 모음: s1~s3.txt(사용자 최종 해설 원고) → exam.json
원고 형식: [제목] / ■ 빠른 정답(번호 답 …) / ■ 해설(‘N. ③’ → 정답 풀이 → [오답풀이] → 나머지)."""
import json, os, re

H = os.path.dirname(os.path.abspath(__file__))
CIRC = '①②③④⑤'
rounds = []
for k in (1, 2, 3):
    t = open(f'{H}/s{k}.txt', encoding='utf8').read().strip()
    title = re.match(r'^\[(.+?)\]', t).group(1)
    qa_txt = t[t.index('■ 빠른 정답'):t.index('■ 해설')]
    quick = dict(re.findall(r'(\d+)\s+([①-⑤])', qa_txt))
    body = t[t.index('■ 해설') + len('■ 해설'):].strip()
    ex = []
    for blk in re.split(r'\n\s*\n(?=\d+\. [①-⑤]\n)', body):
        head, *rest = blk.strip().split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        ex.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(x.strip() for x in rest if x.strip())})
    # 검토: 빠른 정답 = 해설 머리, 번호 연속, 객관식 해설은 정답 풀이 1개 + 오답 4개(번호 겹침·빠짐 없음)
    assert [e['no'] for e in ex] == [str(i) for i in range(1, len(ex) + 1)], title
    assert quick == {e['no']: e['answer'] for e in ex}, (title, [(e['no'], quick.get(e['no']), e['answer']) for e in ex if quick.get(e['no']) != e['answer']])
    for e in ex:
        lines = e['plain'].split('\n')
        labs = [l[0] for l in lines if l[:1] in CIRC]
        if labs:
            assert labs[0] == e['answer'] and sorted(labs) == sorted(CIRC), (title, e['no'], labs)
        assert '[오답풀이]' in lines, (title, e['no'])
    rounds.append({'title': title, 'ex': ex})
    print(title, len(ex), ''.join(e['answer'] for e in ex))
json.dump({'rounds': rounds}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
