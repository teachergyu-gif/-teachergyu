"""청운고 1학년 2학기 중간고사 대비 모의고사 1회 해설지: a.txt(정답·해설) → exam.json
문제지는 사용자가 한글로 만든 파일이므로, 여기서는 해설지만 만든다(문항은 번호·선지 수만 채운 빈 자리)."""
import json, os, re

H = os.path.dirname(os.path.abspath(__file__))


def curly(s):
    s = re.sub(r'"([^"\n]*)"', r'“\1”', s)
    return re.sub(r"'([^'\n]*)'", r'‘\1’', s)


def parse_a(path):
    exs = []
    for blk in re.split(r'\n(?=(?:\d+\. [①-⑤]|\[서술형 \d+\])\n)', '\n' + curly(open(path, encoding='utf8').read()).strip()):
        blk = blk.strip()
        if not blk:
            continue
        head, *rest = blk.split('\n')
        m = re.match(r'^(\d+)\. ([①-⑤])$', head)
        if m:
            exs.append({'no': m.group(1), 'answer': m.group(2), 'plain': '\n'.join(x for x in rest if x.strip())}); continue
        no = re.match(r'^\[(서술형 \d+)\]$', head).group(1)
        exs.append({'no': no, 'answer': '', 'plain': '\n'.join(x.strip() for x in rest if x.strip())})
    return exs


EX = parse_a(f'{H}/a.txt')
assert [e['no'] for e in EX if e['answer']] == [str(i) for i in range(1, sum(1 for e in EX if e['answer']) + 1)]
SETS = [{'rng': '', 'works': [], 'questions': [{'no': e['no'], 'stem': '', 'choices': ['-'] * 5 if e['answer'] else []} for e in EX]}]
json.dump({'sets': SETS, 'ex': EX, 'issues': []}, open(f'{H}/exam.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('문항', len(EX), '정답', ''.join(e['answer'] for e in EX))
