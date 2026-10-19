"""진달래꽃 문제 모음집: work/s*/out.json → 양식 HWP."""
import json, re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwpbuild import Doc, T_PARA, T_TEXT, T_CS, table_records, cold_para, insert_text, add_para_after

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


def main(out_path):
    B = Builder(); d = B.d
    data = [json.load(open(f'{D}/work/s{i}/out.json')) for i in range(1, 5)]
    import fixes_jd
    from layout_overrides import Q_BREAK, SET_BREAK, ANSWER_LINES
    log = []
    fixes_jd.apply(data, log)
    open(f'{D}/fixlog.txt', 'w').write('\n'.join(log) + '\n')
    body, exs, toc = [], [], []
    dp = f'{D}/pdf/decisions.json'
    DEC = json.load(open(dp)) if os.path.exists(dp) else []
    si = 0
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
            dec = DEC[si] if si < len(DEC) else {'top': True}
            si += 1
            if not body or dec.get('top') or not dec.get('mid'):
                hps, hbrk = B.d.ps(33, bottom=400), (8 if body else 0)       # 새 단 첫머리
            else:   # PDF판과 같이: 단에 남은 공간의 절반을 띄우고 시작
                hps, hbrk = B.d.ps(33, bottom=400, top=int(dec['gap'] * 150)), 0
            if SET_BREAK.get(a) == 'page': hps, hbrk = B.d.ps(33, bottom=400), 4
            elif SET_BREAK.get(a) == 'col': hps, hbrk = B.d.ps(33, bottom=400), 8
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
        if n >= first_n:
            toc.append(f'{src["source"]} ············ {first_n}～{n}번')
    # 정답 및 해설
    # '정답 및 해설' 제목은 1단 영역에 두고, 그 아래부터 다시 2단 → 왼쪽·오른쪽 단의 첫 해설이 같은 높이에서 시작
    body += cold_para(B.runs('<b>정답 및 해설</b>', B.cs(3, size=1400)), 1, 0, B.ps_exl, brk=4 | 2)
    body += cold_para([('', 3)], 2, 0, B.ps_exl, brk=2)
    for k, e in exs:
        body += B.explanation(k, e)
    # 1쪽 머리·목차·제목 상자
    d.replace_text('문제 은행', 'RICH ACADEMY')    # 1쪽 머리 위 문구
    d.replace_text(' , ｢｣', ' 김소월, ｢진달래꽃｣')
    # 목차 칸 맨 위 빈 문단 삭제 → '[문제 은행]'이 칸 첫 줄부터
    sec = d.sec
    k = [i for i, r in enumerate(sec) if r[0] == T_TEXT and r[2].decode('utf-16le', 'ignore').startswith('[문제 은행]')][0]
    h = k - 1; lvl = sec[h][1]
    prev = h - 1
    while not (sec[prev][0] == T_PARA and sec[prev][1] == lvl) and sec[prev][0] != 72:
        prev -= 1
    if sec[prev][0] == T_PARA:   # 바로 앞 빈 문단
        j = prev
        while sec[j][0] != 72: j -= 1
        del sec[prev:h]
        p = bytearray(sec[j][2]); struct.pack_into('<h', p, 0, struct.unpack_from('<h', p, 0)[0] - 1); sec[j][2] = bytes(p)
    # 1쪽 목차 표 삭제(문제가 1쪽부터 바로 시작)
    sec = d.sec
    top1 = [i for i, r in enumerate(sec) if r[0] == T_PARA and r[1] == 0][1]
    tbls = [i for i in range(top1) if sec[i][0] == 71 and sec[i][1] == 1 and sec[i][2][:4] == b' lbt']
    toc = [i for i in tbls if any(r[0] == T_TEXT and '목 차' in r[2].decode('utf-16le', 'ignore')
                                  for r in sec[i:next((j for j in range(i + 1, top1) if sec[j][1] <= 1), top1)])][0]
    end = next((j for j in range(toc + 1, top1) if sec[j][1] <= 1), top1)
    nth = tbls.index(toc)
    del sec[toc:end]
    t = sec[1][2].decode('utf-16le', 'surrogatepass')
    pos, seen, i_ = None, -1, 0
    while i_ < len(t):
        if ord(t[i_]) in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
            if t[i_ + 1:i_ + 3].encode('utf-16le') == b' lbt':
                seen += 1
                if seen == nth: pos = i_; break
            i_ += 8
        else:
            i_ += 1
    sec[1][2] = (t[:pos] + t[pos + 8:]).encode('utf-16le', 'surrogatepass')
    h = bytearray(sec[0][2]); nc, = struct.unpack_from('<I', h, 0); struct.pack_into('<I', h, 0, nc - 8); sec[0][2] = bytes(h)
    arr = list(struct.unpack('<%dI' % (len(sec[2][2]) // 4), sec[2][2]))
    sec[2][2] = struct.pack('<%dI' % len(arr), *[(v - 8 if (k % 2 == 0 and v > pos) else v) for k, v in enumerate(arr)])
    # 1쪽 머리의 '제1교시' 상자 감춤(글자 지우고 테두리 없앰)
    sec = d.sec
    ki = [i for i, r in enumerate(sec) if r[0] == T_TEXT and '교시' in r[2].decode('utf-16le', 'ignore')][0]
    t = sec[ki][2].decode('utf-16le', 'surrogatepass')
    sec[ki][2] = (' ' * (len(t) - 1) + '\r').encode('utf-16le')
    si = max(i for i in range(ki) if sec[i][0] == 76 and sec[i][2][:4] == b'cer$')
    p = bytearray(sec[si][2]); cnt = struct.unpack_from('<H', p, 46)[0]; off = 48 + 48 + cnt * 96
    struct.pack_into('<I', p, off + 4, 0); a_ = struct.unpack_from('<I', p, off + 8)[0]
    struct.pack_into('<I', p, off + 8, a_ & ~0x3F); sec[si][2] = bytes(p)
    # 바탕쪽 머리말에 학원 이름·학교 학년, 꼬리말에 교재 이름
    from layout_overrides import HEAD_INFO, FOOT_TEXT
    small = d.cs(16, size=1000, color=0x4A3329)        # 남색 #29334A (BGR)
    gray = d.cs(14, size=850, color=0x777777)
    sec = d.sec
    atno = [i for i, r in enumerate(sec) if r[0] == 71 and r[2][:4] == b'onta' and r[1] == 5]   # 바탕쪽 쪽 번호
    for k in atno:
        hi = k - 4
        assert sec[hi][0] == T_PARA
        right = struct.unpack_from('<H', sec[hi][2], 8)[0] == 26    # 홀수쪽(오른쪽 정렬)
        if right:
            insert_text(sec, hi, 0, HEAD_INFO + '   ', small)
        else:
            insert_text(sec, hi, 9, '   ' + HEAD_INFO, small)
    foot = [i for i, r in enumerate(sec) if r[0] == 71 and r[2][:4] == b'toof'][0]
    add_para_after(sec, foot + 2, FOOT_TEXT, gray, d.ps(20, align=1, top=0, bottom=0))
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
    d.s['BinData/BIN0001.jpg'] = deflate(open(f'{D}/logo3.jpg', 'rb').read())
    # 본문 전체 한글 줄 나눔을 어절 단위로(<보기>·선지·해설 낱말이 줄 끝에서 끊기지 않게)
    for r in body:
        if r[0] == T_PARA:
            h = bytearray(r[2]); ps = struct.unpack_from('<H', h, 8)[0]
            struct.pack_into('<H', h, 8, d.ps_word(ps)); r[2] = bytes(h)
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
