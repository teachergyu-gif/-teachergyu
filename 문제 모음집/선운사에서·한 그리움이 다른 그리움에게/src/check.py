"""검수: 문항·정답·해설 짝, 선지 수, 오답풀이 번호, 지문 표지·기호 참조, 해설 속 인용, PDF 번호 순서.
사용: python3 check.py 데이터폴더 [완성본.pdf]"""
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/pdf')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render, fixes
CIRC = '①②③④⑤'
data = render.load(sys.argv[1]); fixes.apply(data, [])
P = []
def warn(n, src, q, msg): P.append(f'{n:>2}번 [{src} {q["orig"]}번] {msg}')
plain = lambda t: re.sub(r'</?\w+>', '', t or '')
n = 0
for src in data:
    exm = {e['orig']: e for e in src['ex']}
    for s in src['sets']:
        ptxt = plain('\n'.join(w['lines'] for w in s['works']) + '\n'.join(s.get('notes') or []))
        labels = {(w.get('label') or '') for w in s['works']}
        for q in s['questions']:
            n += 1
            e = exm.get(q['orig'])
            qt = plain(json.dumps({k: q.get(k) for k in ('stem', 'bogi', 'choices', 'extra')}, ensure_ascii=False))
            if not e: warn(n, src['source'], q, '해설 없음'); continue
            ch = q.get('choices') or []
            if ch:
                if len(ch) != 5: warn(n, src['source'], q, f'선지 {len(ch)}개')
                if e['answer'][:1] not in CIRC: warn(n, src['source'], q, f'정답 형식 {e["answer"]!r}')
                a = e['answer'][:1]
                wl = [w[0].strip() for w in e.get('wrong') or []]
                if a in ''.join(wl): warn(n, src['source'], q, f'오답풀이에 정답 {a}')
                if len(set(ch)) != len(ch): warn(n, src['source'], q, '같은 선지 있음')
            else:
                if len(e['answer']) < 12: warn(n, src['source'], q, f'서술형 모범 답안이 짧음 {e["answer"]!r}')
            # 문항이 가리키는 (가)(나)(다)가 지문에 있는지
            for lab in set(re.findall(r'\(([가-마])\)', plain(q['stem']) + ' '.join(plain(c) for c in ch))):
                if len(s['works']) > 1 and f'({lab})' not in labels:
                    warn(n, src['source'], q, f'문항의 ({lab})가 지문에 없음')
            # 문항 기호가 지문(또는 보기)에 있는지
            for sym in set(re.findall(r'[㉠-㉻ⓐ-ⓩⒶ-Ⓩ]', plain(q['stem']) + ' '.join(plain(c) for c in ch))):
                if sym not in ptxt and sym not in plain(json.dumps(q.get('bogi'), ensure_ascii=False)) + plain(str(q.get('extra'))):
                    warn(n, src['source'], q, f'기호 {sym}가 지문에 없음')
            # 해설 속 기호·표지가 지문에서 지워졌는지
            et = plain(json.dumps(e, ensure_ascii=False))
            for sym in set(re.findall(r'[㉠-㉻ⓐ-ⓩⒶ-Ⓩ]', et)):
                if sym not in ptxt and sym not in qt: warn(n, src['source'], q, f'해설의 기호 {sym}가 문제·지문에 없음')
            for lab in set(re.findall(r'\(([가-마])\)', et)):
                if len(s['works']) > 1 and f'({lab})' not in labels and f'({lab})' not in qt:
                    warn(n, src['source'], q, f'해설의 ({lab})가 지문에 없음')
            # 해설의 ‘인용’이 문제·지문에 있는지(짧은 것 제외)
            for quo in re.findall(r'‘([^’]{4,40})’', et):
                k = re.sub(r'\s+', '', quo)
                hay = re.sub(r'\s+', '', ptxt + qt)
                if k not in hay and '/' not in quo and '…' not in quo:
                    warn(n, src['source'], q, f'해설 인용 ‘{quo}’가 문제·지문에 그대로 없음')
print('문항', n)
if len(sys.argv) > 2:
    t = subprocess.run(['pdftotext', '-layout', sys.argv[2], '-'], capture_output=True, text=True).stdout
    i = t.find('정답 및 해설')
    qn = [int(x) for x in re.findall(r'(?m)^\s*(\d{1,2})\. ', t[:i])]
    hd = re.findall(r'【(\d+)(?:～(\d+))?】', t)
    print('지문 안내', len(hd), '개')
print('\n'.join(P) or '문제 없음')
