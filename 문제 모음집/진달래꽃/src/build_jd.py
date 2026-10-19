"""진달래꽃 문제 모음집: work/s*/out.json → 양식 HWP."""
import json, re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwpbuild import Doc, T_PARA, T_TEXT, T_CS, table_records

D = os.path.dirname(os.path.abspath(__file__))
TPL = D + '/tpl/t.hwp'
CIRC = '①②③④⑤'


class Builder:
    def __init__(self):
        self.d = Doc(TPL)
        d = self.d
        self.U = {}  # charshape variants
        # 문단 모양
        self.ps_poem = d.ps(7, indent=0)                      # 지문(테두리 연결) 들여쓰기 없음
        self.ps_poem_r = d.ps(7, indent=0, align=2)           # 지문 안 출처(오른쪽)
        self.ps_poem_lab = d.ps(7, indent=0, top=600)         # 작품 표지 (가)(나) 앞 여백
        self.ps_box_c = d.ps(42, align=3)                     # <보기> 제목(가운데)
        self.ps_box = d.ps(42, indent=0)
        self.ps_box_i = d.ps(42, indent=-1700, left=1700)     # ㄱ. ㄴ. 항목
        self.ps_ex_t = d.ps(42, align=3)                      # '정답 및 해설' 제목
        self.ps_exn = d.ps(3, indent=0, top=1400)             # 해설 '1. ①'
        self.ps_exh = d.ps(8)                                 # 해설 ① 내어쓰기(선지 모양)
        self.ps_exl = d.ps(3, indent=0)
        self.ps_tc = d.ps(3, align=3, indent=0)
        self.ps_tbl = d.ps(3, align=3, indent=0, top=400, bottom=400)

    def cs(self, base, u=False, b=False, size=None):
        return self.d.cs(base, underline=u, bold=b, size=size)

    def runs(self, text, base):
        """<u>, <b>, <box> 표시 → (글자, 글자모양) 목록"""
        out, u, b = [], False, False
        for tok in re.split(r'(</?u>|</?b>|</?box>)', text):
            if tok in ('<u>', '</u>'): u = tok == '<u>'; continue
            if tok in ('<b>', '</b>'): b = tok == '<b>'; continue
            if tok == '<box>': out.append(('[', self.cs(base))); continue
            if tok == '</box>': out.append((']', self.cs(base))); continue
            if tok:
                out.append((tok, self.cs(base, u, b)))
        return out or [('', base)]

    def P(self, style, ps, text, cs, brk=0):
        return self.d.para(self.runs(text, cs), style, ps, brk=brk)

    # ---------- 지문 ----------
    def passage(self, s):
        out = []
        st, cs = 4, 3
        for wi, w in enumerate(s['works']):
            lines = w['lines'].split('\n')
            first = True
            open_lab = None
            for l in lines:
                m = re.match(r'^\{(\w+)\}', l)
                if m:
                    open_lab = m.group(1); l = l[m.end():]
                    l = f'<b>[{open_lab}]</b> ' + l
                elif open_lab:
                    l = '　  ' + l
                if re.search(r'\{/\w+\}$', l):
                    l = re.sub(r'\{/\w+\}$', '', l); open_lab = None
                if first and w.get('label'):
                    out += self.P(st, self.ps_poem_lab if wi else self.ps_poem, f'<b>{w["label"]}</b>', cs)
                first = False
                if l.strip() == '':
                    out += self.P(st, self.ps_poem, '', cs); continue
                out += self.P(st, self.ps_poem, l, cs)
            if w.get('author'):
                out += self.P(st, self.ps_poem_r, w['author'], cs)
        for n in s.get('notes') or []:
            out += self.P(st, self.ps_poem, n, cs)
        return out

    # ---------- 문항 ----------
    def question(self, q):
        out = self.P(1, 32, q['stem'], 4)   # '문제' 스타일: 번호 자동(1. 2. …)
        b = q.get('bogi')
        if b and b.get('table'):
            rows = [list(r) for r in b['table']]
            spans = {}
            # 빈 칸이 위 칸과 이어지는 경우(세로 병합)
            for r in range(1, len(rows)):
                for c in range(len(rows[r])):
                    if rows[r][c] == '' and c < 2 and rows[r - 1][c]:
                        k = r - 1
                        while rows[k][c] is None: k -= 1
                        rs, cs_ = spans.get((k, c), (1, 1)); spans[(k, c)] = (rs + 1, 1); rows[r][c] = None
            cs43 = 43
            def dp(t, last, lvl):
                return self.d.para(self.runs(t, cs43), 26, self.ps_tc, level=lvl, last=last)
            out += table_records(dp, rows, [4200, 12300, 15200], bf=6, ps=self.ps_tbl, cs=3)
            b = None
        if b:
            title = '<보기>' if b.get('title') is None else b['title']
            if title:
                out += self.P(26, self.ps_box_c, title, 43)
            for l in b['text'].split('\n'):
                ps = self.ps_box_i if re.match(r'^([ㄱ-ㅎ]\.|[㉠-㉭]|[ⓐ-ⓩ]|\(\S\))', l) else self.ps_box
                out += self.P(26, ps, l, 43)
        ex = q.get('extra')
        if isinstance(ex, dict):
            out += self.P(26, self.ps_box_c, ex.get('title') or '', 43)
            ex = ex.get('text')
        if ex:
            for l in ex.split('\n'):
                out += self.P(26, self.ps_box, l, 43)
        for i, c in enumerate(q.get('choices') or []):
            out += self.P(2, 8, f'{CIRC[i]} {c}', 3)
        return out

    # ---------- 해설 ----------
    def explanation(self, n, e):
        out = self.P(0, self.ps_exn, f'{n}. {e["answer"] if len(e["answer"]) < 12 else ""}'.rstrip(), 3)
        if len(e['answer']) >= 12:   # 서술형 모범 답안
            out += self.P(0, self.ps_exl, '<b>[모범 답안]</b> ' + e['answer'], 3)
        if e.get('plain'):
            for para in e['plain'].split('\n'):
                ps = self.ps_exh if para[:1] in CIRC else self.ps_exl
                out += self.P(0, ps, para, 3)
            return out
        if e.get('correct'):
            a = e['answer'][:1] if e['answer'][:1] in CIRC else ''
            out += self.P(0, self.ps_exh if a else self.ps_exl, (a + ' ' if a else '') + e['correct'], 3)
        if e.get('wrong'):
            out += self.P(0, self.ps_exl, '<b>[오답풀이]</b>', 3)
            for k, t in e['wrong']:
                out += self.P(0, self.ps_exh, f'{k} {t}'.strip(), 3)
        return out


def main(out_path):
    B = Builder(); d = B.d
    data = [json.load(open(f'{D}/work/s{i}/out.json')) for i in range(1, 5)]
    import fixes_jd
    log = []
    fixes_jd.apply(data, log)
    open(f'{D}/fixlog.txt', 'w').write('\n'.join(log) + '\n')
    body, exs, toc = [], [], []
    n = 0
    for src in data:
        exmap = {e['orig']: e for e in src['ex']}
        first_n = n + 1
        for s in src['sets']:
            qs = s['questions']
            if not qs:
                continue
            a, b = n + 1, n + len(qs)
            rng = f'{a}' if a == b else f'{a}～{b}'
            body += B.P(5, 33, '<b>다음 글을 읽고 물음에 답하시오.</b>', 17)
            body += B.passage(s)
            for q in qs:
                n += 1
                body += B.question(q)
                exs.append((n, exmap[q['orig']]))
        if n >= first_n:
            toc.append(f'{src["source"]} ············ {first_n}～{n}번')
    # 정답 및 해설
    body += d.para(B.runs('<b>정답 및 해설</b>', B.cs(3, size=1400)), 26, B.ps_ex_t, brk=4)
    for k, e in exs:
        body += B.explanation(k, e)
    # 1쪽 머리·목차·제목 상자
    d.replace_text('문제 은행', '진달래꽃 문제 은행')          # 1쪽 머리 표
    d.replace_text('[문제 은행]', '[진달래꽃 문제 은행]')        # 목차 제목 (먼저 나오는 '[' 포함 문단)
    d.replace_text(' , ｢｣', ' 김소월, ｢진달래꽃｣')
    d.replace_text('｢｣ 문제 은행', '｢진달래꽃｣ 문제 은행')
    add_toc(d, toc)
    d.save(out_path, body, prvtext='진달래꽃 문제 은행')
    print('questions', n)


def add_toc(d, lines):
    """목차 표 마지막 칸(‘김소월, ｢진달래꽃｣’ 문단 뒤)에 목차 줄을 넣는다."""
    sec = d.sec
    k = [i for i, r in enumerate(sec) if r[0] == T_TEXT and '김소월' in r[2].decode('utf-16le', 'ignore')][0]
    h = k - 1
    lvl = sec[h][1]
    # 이 문단이 속한 셀의 LIST_HEADER 찾기
    j = h
    while not (sec[j][0] == 72 and sec[j][1] == lvl):
        j -= 1
    st, ps = sec[h][2][10], struct.unpack_from('<H', sec[h][2], 8)[0]
    cs = struct.unpack_from('<I', sec[k + 1][2], 4)[0]
    # 끼울 위치: 그 문단 레코드 묶음 끝
    e = k + 1
    while e < len(sec) and not (sec[e][0] == T_PARA and sec[e][1] <= lvl):
        e += 1
    new = []
    for t in [''] + lines:
        new += Doc.para([(t, cs)], st, ps, level=lvl)
    sec[e:e] = new
    cnt = struct.unpack_from('<h', sec[j][2], 0)[0] + len(lines) + 1
    p = bytearray(sec[j][2]); struct.pack_into('<h', p, 0, cnt); sec[j][2] = bytes(p)


if __name__ == '__main__':
    main(sys.argv[1])
