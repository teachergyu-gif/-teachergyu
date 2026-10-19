"""「선운사에서」·「한 그리움이 다른 그리움에게」 문제 은행: work/*/out.json → 양식 HWP (Builder는 진달래꽃 build_jd.py와 같음).
사용: TOTAL_PAGES=<PDF 쪽수-MEMO> python3 build.py 데이터폴더 출력.hwp"""
import json, re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwpbuild import Doc, T_PARA, T_TEXT, T_CS, table_records, cold_para, remove_toc

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
        M = 2268   # <보기>·조건 상자 좌우 여백 4mm(값은 2배 단위)
        self.ps_box_c = d.ps(42, align=3, left=M, right=M)    # <보기> 제목(가운데)
        self.ps_box = d.ps(42, indent=0, left=M, right=M)
        self.ps_box_i = d.ps(42, indent=-1700, left=1700 + M, right=M)     # ㄱ. ㄴ. 항목
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
            # [A] 묶음: 표지는 묶음 가운데 줄 앞에, 나머지 줄은 같은 폭만큼 들여 씀
            i = 0
            while i < len(lines):
                m = re.match(r'^\{(\w+)\}', lines[i])
                if not m:
                    i += 1; continue
                lab = m.group(1); lines[i] = lines[i][m.end():]
                j = i
                while not re.search(r'\{/\w+\}$', lines[j]):
                    j += 1
                lines[j] = re.sub(r'\{/\w+\}$', '', lines[j])
                mid = i + (j - i) // 2
                for k in range(i, j + 1):
                    lines[k] = (f'<b>[{lab}]</b> ' if k == mid else '\u3000\u2002 ') + lines[k]
                i = j + 1
            first = True
            for l in lines:
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
            out += table_records(dp, rows, [3900, 11420, 14112], bf=6, ps=self.ps_tbl, cs=3)
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


def main(work_dir, out_path):
    sys.path.insert(0, D + '/pdf')
    import render, fixes
    from layout_overrides import Q_BREAK, SET_BREAK, ANSWER_LINES
    B = Builder(); d = B.d
    data = render.load(work_dir)
    fixes.apply(data, [])
    body = []
    dp = f'{D}/pdf/decisions.json'
    DEC = json.load(open(dp)) if os.path.exists(dp) else []
    si = 0
    n = 0
    # 작품마다: 문제 모음 → 정답 및 해설
    for wi, ((name, label, _), src) in enumerate(zip(render.WORKS, data)):
        exmap = {e['orig']: e for e in src['ex']}
        exs = []
        first = True
        for s in src['sets']:
            qs = s['questions']
            if not qs:
                continue
            a, b = n + 1, n + len(qs)
            rng = f'{a}' if a == b else f'{a}～{b}'
            dec = DEC[si] if si < len(DEC) else {'top': True}
            si += 1
            if first and wi:
                hps, hbrk = B.d.ps(33, bottom=400), 4                      # 둘째 작품: 새 쪽
            elif not body or dec.get('top') or not dec.get('mid'):
                hps, hbrk = B.d.ps(33, bottom=400), (8 if body else 0)       # 새 단 첫머리
            else:   # PDF판과 같이: 단에 남은 공간의 절반을 띄우고 시작
                hps, hbrk = B.d.ps(33, bottom=400, top=int(dec['gap'] * 150)), 0
            if SET_BREAK.get(a) == 'page': hps, hbrk = B.d.ps(33, bottom=400), 4
            elif SET_BREAK.get(a) == 'col': hps, hbrk = B.d.ps(33, bottom=400), 8
            first = False
            body += B.P(5, hps, f'<b>【{rng}】 다음 글을 읽고 물음에 답하시오.</b>', 17, brk=hbrk)
            body += B.passage(s)
            for q in qs:
                n += 1
                qr = B.question(q)
                if not q.get('choices'):   # 서술형: 답안 쓸 여백
                    for _ in range(ANSWER_LINES):
                        qr += B.P(0, B.ps_exl, '', 3)
                if Q_BREAK.get(n):
                    h = bytearray(qr[0][2]); h[11] = 8 if Q_BREAK[n] == 'col' else 4; qr[0][2] = bytes(h)
                body += qr
                exs.append((n, exmap[q['orig']]))
        # 정답 및 해설: 제목은 1단 영역, 그 아래부터 다시 2단
        body += cold_para(B.runs('<b>정답 및 해설</b>', B.cs(3, size=1400)), 1, 0, B.ps_exl, brk=4 | 2)
        body += cold_para([('', 3)], 2, 0, B.ps_exl, brk=2)
        for k, e in exs:
            body += B.explanation(k, e)
    # 1쪽 머리(목차 없음: 머리 아래부터 바로 문제)
    d.replace_text('문제 은행', render.HEAD)    # 1쪽 머리 표
    remove_toc(d)
    # MEMO 쪽: 바탕쪽·머리말·꼬리말·쪽 번호·테두리를 모두 감춤(MEMO 상자만 보이게)
    for r in d.sec:
        if r[0] == 71 and r[2][:4] == b'dhgp' and r[2][4:8] == b'\x02\0\0\0':
            r[2] = b'dhgp' + struct.pack('<I', 0x3F)
    # 바닥쪽 쪽 상자 전체 쪽수(양식 '33') → PDF판 쪽수
    tot = os.environ.get('TOTAL_PAGES')
    if tot:
        d.replace_text('33\r', tot + '\r')
    # 1쪽 '국어 영역(A형)' 그림 → '국어 영역'
    from hwplib import deflate
    d.s['BinData/BIN0001.jpg'] = deflate(open(f'{D}/logo2.jpg', 'rb').read())
    # 본문 전체 한글 줄 나눔을 어절 단위로
    for r in body:
        if r[0] == T_PARA:
            h = bytearray(r[2]); ps = struct.unpack_from('<H', h, 8)[0]
            struct.pack_into('<H', h, 8, d.ps_word(ps)); r[2] = bytes(h)
    d.save(out_path, body, prvtext=render.HEAD, first_brk=0)
    print('questions', n)



if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
