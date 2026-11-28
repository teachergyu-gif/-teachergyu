"""국제고 1학년 2학기 기말고사 대비 모의고사 3·4회 해설 모음: s3·s4.txt(사용자 최종 해설 원고) → exam.json
원고 형식: [제목] / ■ 빠른 정답 / ■ 해설(‘N. ③’ 객관식, ‘[서답형 N]’ 서답형)."""
import json, os, re

H = os.path.dirname(os.path.abspath(__file__))
CIRC = '①②③④⑤'
rounds = []
for k in (3, 4):
    t = open(f'{H}/s{k}.txt', encoding='utf8').read().strip()
    title = re.match(r'^\[(.+?)\]', t).group(1)
    quick = dict(re.findall(r'(\d+)\s+([①-⑤])', t[t.index('■ 빠른 정답'):t.index('■ 해설')]))
    body = t[t.index('■ 해설') + len('■ 해설'):].strip()
    ex = []
    for blk in re.split(r'\n\s*\n(?=(?:\d+\. [①-⑤]|\[서답형 \d+\])\n)', body):
        head, *rest = blk.strip().split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        if m:
            ex.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(x.strip() for x in rest if x.strip())})
            continue
        no = re.match(r'^\[(서답형 \d+)\]$', head).group(1)
        lines = []
        for x in rest:
            if not x.strip():
                continue
            s = x.strip()
            m2 = re.match(r'^(\[예시 답안\])\s*(.+)$', s)
            if m2:                       # ‘[예시 답안] …’ → 제목 줄 + 본문
                lines += [m2.group(1), m2.group(2)]
            elif s.startswith('•'):      # 채점 항목: 글머리 •
                lines.append('*' + s[1:].strip())
            elif s.startswith('- '):     # 하위 항목
                lines.append('　- ' + s[2:].strip())
            else:
                lines.append(s)
        ex.append({'no': no, 'answer': '', 'plain': '\n'.join(lines)})
    mc = [e for e in ex if e['answer']]
    assert [e['no'] for e in mc] == [str(i) for i in range(1, len(mc) + 1)], title
    assert quick == {e['no']: e['answer'] for e in mc}, (title, [(e['no'], quick.get(e['no']), e['answer']) for e in mc if quick.get(e['no']) != e['answer']])
    for e in mc:
        labs = [l[0] for l in e['plain'].split('\n') if l[:1] in CIRC]
        if labs:
            assert labs[0] == e['answer'] and sorted(labs) == sorted(CIRC), (title, e['no'], labs)
        assert '[오답풀이]' in e['plain'].split('\n'), (title, e['no'])
    rounds.append({'title': title, 'ex': ex})
    print(title, len(mc), ''.join(e['answer'] for e in mc), [e['no'] for e in ex if not e['answer']])
json.dump({'rounds': rounds}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
