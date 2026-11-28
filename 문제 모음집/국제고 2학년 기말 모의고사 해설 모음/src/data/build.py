"""부산외고 2학년 2학기 기말고사 모의고사 해설: sN.txt(사용자 해설 원고) → exam.json
원고 형식: 첫 줄 제목 / [빠른 정답] / 해설(‘N. ③’ 객관식, ‘서답형 N.’ 서답형). 사용: python3 data/build.py 1"""
import json, os, re, sys

H = os.path.dirname(os.path.abspath(__file__))
CIRC = '①②③④⑤'
rounds = []
for k in sys.argv[1:]:
    t = open(f'{H}/s{k}.txt', encoding='utf8').read().strip()
    title = t.split('\n', 1)[0].strip()
    qs = t.index('[빠른 정답]'); b0 = re.search(r'\n1\. [①-⑤]\n', t).start()
    quick = dict(re.findall(r'(\d+)\s+([①-⑤])', t[qs:b0]))
    body = t[b0:].strip()
    ex = []
    for blk in re.split(r'\n\s*\n(?=(?:\d+\. [①-⑤]|서답형 \d+\.)\n)', body):
        head, *rest = blk.strip().split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        if m:
            ex.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(x.strip() for x in rest if x.strip())})
            continue
        no = re.match(r'^(서답형 \d+)\.$', head).group(1)
        lines = []; sec = None
        for x in rest:
            if not x.strip():
                continue
            s = x.strip()
            if re.fullmatch(r'\[.+\]', s):
                sec = s; lines.append(s); continue
            if sec == '[채점 기준]' and not s.startswith('('):
                lines += ['*' + y.strip() for y in s.split(' / ')]      # 채점 항목: 글머리 •
            elif s.startswith('- '):
                lines.append('*' + s[2:].strip())
            elif x.startswith('  '):
                lines.append('　　' + s)                                  # 하위 줄(들여쓰기)
            else:
                lines.append(s)
        ex.append({'no': no, 'answer': '', 'plain': '\n'.join(lines)})
    mc = [e for e in ex if e['answer']]
    assert [e['no'] for e in mc] == [str(i) for i in range(1, len(mc) + 1)], title
    assert quick == {e['no']: e['answer'] for e in mc}, (title, [(e['no'], quick.get(e['no']), e['answer']) for e in mc if quick.get(e['no']) != e['answer']])
    for e in mc:
        labs = [l[0] for l in e['plain'].split('\n') if l[:1] in CIRC]
        if labs:     # 정답 선지 + 오답풀이 선지 = ①~⑤ 한 번씩(ⓐ~ⓔ형은 정답 선지 문단 없이 오답풀이만)
            full = labs if labs[0] == e['answer'] else [e['answer']] + labs
            assert full[0] == e['answer'] and sorted(full) == sorted(CIRC), (title, e['no'], labs)
        if labs: assert '[오답풀이]' in e['plain'].split('\n'), (title, e['no'])   # ㄱ~ㅁ 연결형은 오답풀이 없이 항목별 해설
    rounds.append({'title': title, 'ex': ex})
    print(title, len(mc), ''.join(e['answer'] for e in mc), [e['no'] for e in ex if not e['answer']])
json.dump({'rounds': rounds}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
