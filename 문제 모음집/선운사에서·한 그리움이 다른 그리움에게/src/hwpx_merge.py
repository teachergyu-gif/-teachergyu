"""사용자가 보낸 HWPX(개념 교재) 뒤에 이 문제 은행을 이어 붙인다(쪽 번호는 그대로 이어짐).
- 붙일 곳: 보낸 파일 마지막의 빈 '쪽 나눔' 문단 자리(= 12쪽 첫머리).
- 양식: 보낸 파일 안의 같은 계열 스타일([∼]·문제·①·지문)을 그대로 쓰고, 굵게·밑줄·내어쓰기 등은 그 모양을 복제해 추가.
- 배치: PDF판과 같은 단 나눔(pdf/decisions.json, layout_overrides, pdf/balanced.json).
사용: python3 hwpx_merge.py 보낸파일.hwpx 출력.hwpx [데이터폴더] [--toc 정희성쪽,선운사문제쪽,한그리움문제쪽] [--total 전체쪽수]"""
import sys, os, re, json, zipfile, argparse
from xml.sax.saxutils import escape

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D + '/pdf')
sys.path.insert(0, D)
import render, fixes
from layout_overrides import Q_BREAK, SET_BREAK, ANSWER_LINES

CIRC = '①②③④⑤'
COL_W = (84188 - 8787 * 2 - 2268) // 2   # 보낸 파일의 쪽 너비·여백·단 간격 기준 한 단 너비


class Header:
    """header.xml에 글자 모양·문단 모양을 복제해 추가."""

    def __init__(self, xml):
        self.x = xml
        self.memo = {}

    def _count(self, tag):
        return int(re.search(r'<hh:%s itemCnt="(\d+)"' % tag, self.x).group(1))

    def _add(self, tag, item, block):
        n = self._count(tag)
        block = re.sub(r'^<hh:%s id="\d+"' % item, '<hh:%s id="%d"' % (item, n), block)
        self.x = self.x.replace('</hh:%s>' % tag, block + '</hh:%s>' % tag, 1)
        self.x = re.sub(r'<hh:%s itemCnt="\d+"' % tag, '<hh:%s itemCnt="%d"' % (tag, n + 1), self.x, count=1)
        return n

    def char(self, base, bold=False, under=False, size=None):
        key = ('c', base, bold, under, size)
        if key in self.memo:
            return self.memo[key]
        if not (bold or under or size):
            return base
        b = re.search(r'<hh:charPr id="%d" .*?</hh:charPr>' % base, self.x, re.S).group(0)
        if size:
            b = re.sub(r'height="\d+"', 'height="%d"' % size, b, count=1)
        if bold and '<hh:bold/>' not in b:
            b = b.replace('<hh:underline', '<hh:bold/><hh:underline', 1)
        if under:
            b = re.sub(r'<hh:underline type="\w+"', '<hh:underline type="BOTTOM"', b, count=1)
        self.memo[key] = self._add('charProperties', 'charPr', b)
        return self.memo[key]

    def para(self, base, align=None, heading_none=False, border=None, **m):
        key = ('p', base, align, heading_none, border, tuple(sorted(m.items())))
        if key in self.memo:
            return self.memo[key]
        b = re.search(r'<hh:paraPr id="%d" .*?</hh:paraPr>' % base, self.x, re.S).group(0)
        if align:
            b = re.sub(r'<hh:align horizontal="\w+"', '<hh:align horizontal="%s"' % align, b, count=1)
        if heading_none:
            b = re.sub(r'<hh:heading [^>]*/>', '<hh:heading type="NONE" idRef="0" level="0"/>', b, count=1)
        for k, v in m.items():   # intent·left·right·prev·next (case·default 둘 다)
            b = re.sub(r'<hc:%s value="-?\d+"' % k, '<hc:%s value="%d"' % (k, v), b)
        if border is not None:
            bf, con = border
            b = re.sub(r'<hh:border borderFillIDRef="\d+"([^>]*?)connect="\d"', r'<hh:border borderFillIDRef="%d"\1connect="%d"' % (bf, con), b, count=1)
        self.memo[key] = self._add('paraProperties', 'paraPr', b)
        return self.memo[key]


class Writer:
    def __init__(self, H):
        self.H = H
        self.nid = 1500000000
        C = H.char
        P = H.para
        # 글자 모양: 20 = 본문(신명 중명조 11.48pt), 12 = 신명 태고딕(지문 안내)
        self.c = {'n': 20, 'b': C(20, bold=True), 'u': C(20, under=True), 'bu': C(20, bold=True, under=True),
                  'head': C(12, bold=True), 'title': C(12, bold=True, size=1500)}
        # 문단 모양
        self.p = {
            'head': P(21, intent=0, next=400),                       # 【1～2】 다음 글을 읽고…
            'pass': P(25, intent=0),                                  # 지문 상자(문단 테두리 이어짐)
            'pass_r': P(25, intent=0, align='RIGHT'),
            'q': P(27, heading_none=True),                            # 발문(번호는 글자로, 내어쓰기)
            'ch': 24,                                                 # 선지
            'box_hold': P(5, align='CENTER', prev=300, next=300),   # <보기> 표를 담는 문단
            'box': P(5, intent=0),                                    # <보기> 칸 안
            'box_c': P(5, intent=0, align='CENTER'),
            'box_i': P(5, intent=-1700, left=1700),
            'exn': P(5, prev=1400),                                   # 해설 'N. ①'
            'exl': 5,
            'exh': 24,
            'blank': 5,
        }

    def id(self):
        self.nid += 1
        return self.nid

    def runs(self, text, base='n'):
        out, u, b = [], False, False
        for tok in re.split(r'(</?u>|</?b>|</?box>)', text):
            if tok in ('<u>', '</u>'): u = tok == '<u>'; continue
            if tok in ('<b>', '</b>'): b = tok == '<b>'; continue
            if tok in ('<box>', '</box>'): tok = '[' if tok == '<box>' else ']'
            if not tok: continue
            key = base if base != 'n' else ('bu' if b and u else 'b' if b else 'u' if u else 'n')
            out.append('<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>' % (self.c[key], escape(tok)))
        return ''.join(out)

    def P(self, ps, text='', base='n', style=0, page=False, col=False, pre=''):
        body = pre + (self.runs(text, base) if text else '')
        if not body:
            body = '<hp:run charPrIDRef="%d"/>' % self.c['n']
        return ('<hp:p id="2147483648" paraPrIDRef="%d" styleIDRef="%d" pageBreak="%d" columnBreak="%d" merged="0">%s</hp:p>'
                % (ps, style, int(page), int(col), body))

    def cols(self, n):
        line = '<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>' if n == 2 else ''
        return ('<hp:run charPrIDRef="%d"><hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="%d" sameSz="1" sameGap="2268">%s</hp:colPr></hp:ctrl></hp:run>'
                % (self.c['n'], n, line))

    def title(self, text, page):
        """주황 상자 제목(1단) → 그 아래부터 다시 2단."""
        w = int(len(text) * 1500 * 0.95) + 2 * 1700
        h = 1500 + 2 * 700
        cell = self.P(self.p['exl'], text, base='title')
        tbl = ('<hp:run charPrIDRef="%d"><hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="0" rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="31" noAdjust="0">'
               '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
               '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="1700" right="1700" top="700" bottom="700"/>'
               '<hp:tr><hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="31">'
               '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
               '<hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="%d" height="%d"/><hp:cellMargin left="1700" right="1700" top="700" bottom="700"/></hp:tc></hp:tr></hp:tbl><hp:t/></hp:run>'
               % (self.c['n'], self.id(), w, h, cell, w, h))
        return self.P(self.p['exn'], pre=self.cols(1) + tbl, page=page) + self.P(self.p['blank'], pre=self.cols(2))

    # ---------- 지문 ----------
    def passage(self, s):
        out = []
        for wi, w in enumerate(s['works']):
            if wi:
                out.append(self.P(self.p['pass']))
            if w.get('label'):
                out.append(self.P(self.p['pass'], '<b>%s</b>' % w['label']))
            lab = None
            for l in w['lines'].split('\n'):
                m = re.match(r'^\{([^{}/]+)\}', l)
                if m:
                    lab = m.group(1); l = '<b>[%s]</b> ' % lab + l[m.end():]
                elif lab:
                    l = '　  ' + l
                if re.search(r'\{/[^{}]+\}$', l):
                    l = re.sub(r'\{/[^{}]+\}$', '', l); lab = None
                out.append(self.P(self.p['pass'], l))
            if w.get('author'):
                out.append(self.P(self.p['pass_r'], w['author']))
        for n in s.get('notes') or []:
            out.append(self.P(self.p['pass'], n))
        return out

    # ---------- 문항 ----------
    def bogi(self, title, text):
        """<보기>·조건: 단 너비보다 좌우 4mm씩 좁은 1칸 표(실선)."""
        cell = []
        if title:
            cell.append(self.P(self.p['box_c'], title))
        for l in text.split('\n'):
            ps = self.p['box_i'] if re.match(r'^([ㄱ-ㅎ]\.|[㉠-㉭]|[ⓐ-ⓩ]|\(\S\))', l) else self.p['box']
            cell.append(self.P(ps, l))
        w = COL_W - 2 * 1134
        h = 1600 * len(cell) + 1000
        tbl = ('<hp:run charPrIDRef="%d"><hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="0" rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="10" noAdjust="0">'
               '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
               '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="1134" right="1134" top="567" bottom="567"/>'
               '<hp:tr><hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="10">'
               '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
               '<hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="%d" height="%d"/><hp:cellMargin left="1134" right="1134" top="567" bottom="567"/></hp:tc></hp:tr></hp:tbl><hp:t/></hp:run>'
               % (self.c['n'], self.id(), w, h, ''.join(cell), w, h))
        return [self.P(self.p['box_hold'], pre=tbl)]

    def question(self, n, q, col=False):
        out = [self.P(self.p['q'], '<b>%d.</b> %s' % (n, q['stem']), style=1, col=col)]
        b = q.get('bogi')
        if b:
            out += self.bogi('<보기>' if b.get('title') is None else b['title'], b['text'])
        ex = q.get('extra')
        if isinstance(ex, dict):
            out += self.bogi(ex.get('title') or '', ex.get('text') or '')
        elif ex:
            out += self.bogi('', ex)
        for i, c in enumerate(q.get('choices') or []):
            out.append(self.P(self.p['ch'], '%s %s' % (CIRC[i], c), style=2))
        if not q.get('choices'):
            out += [self.P(self.p['blank']) for _ in range(ANSWER_LINES)]
        return out

    # ---------- 해설 ----------
    def explanation(self, n, e):
        a = e['answer']
        out = [self.P(self.p['exn'], ('%d. %s' % (n, a if len(a) < 12 else '')).rstrip())]
        if len(a) >= 12:
            out.append(self.P(self.p['exl'], '<b>[모범 답안]</b> ' + a))
        if e.get('plain'):
            for para in e['plain'].split('\n'):
                out.append(self.P(self.p['exh'] if para[:1] in CIRC else self.p['exl'], para))
            return out
        if e.get('correct'):
            c = a[:1] if a[:1] in CIRC else ''
            out.append(self.P(self.p['exh'] if c else self.p['exl'], (c + ' ' if c else '') + e['correct']))
        if e.get('wrong'):
            out.append(self.P(self.p['exl'], '<b>[오답풀이]</b>'))
            for k, t in e['wrong']:
                out.append(self.P(self.p['exh'], ('%s %s' % (k, t)).strip()))
        return out


def body(W, data):
    dp = f'{D}/pdf/decisions.json'
    DEC = json.load(open(dp)) if os.path.exists(dp) else []
    bp = f'{D}/pdf/balanced.json'
    BAL = {(k.split('|')[0], int(k.split('|')[1])) for k in json.load(open(bp))} if os.path.exists(bp) else set()
    out, si = [], 0
    for (name, label, _), src in zip(render.WORKS, data):
        exm = {e['orig']: e for e in src['ex']}
        exs, n, first = [], 0, True
        out.append(W.title(label.split(', ')[1] + ' 문제 은행', page=True))
        for s in src['sets']:
            qs = s.get('questions') or []
            if not qs:
                continue
            a, b = n + 1, n + len(qs)
            rng = f'{a}' if a == b else f'{a}～{b}'
            dec = DEC[si] if si < len(DEC) else {'top': True}
            si += 1
            ps, col = W.p['head'], False
            if first:
                pass
            elif dec.get('top') or not dec.get('mid'):
                col = True                                                     # 새 단 첫머리
            else:   # PDF판처럼 단에 남은 공간의 절반을 띄우고 시작(1px = 75 HWPUNIT)
                ps = W.H.para(21, intent=0, next=400, prev=int(dec['gap'] * 75))
            if SET_BREAK.get((name, a)):
                ps, col = W.p['head'], True
            first = False
            out.append(W.P(ps, f'【{rng}】 다음 글을 읽고 물음에 답하시오.', base='head', style=6, col=col))
            out += W.passage(s)
            for q in qs:
                n += 1
                out += W.question(n, q, col=bool(Q_BREAK.get((name, n))) or (name, n) in BAL)
                exs.append((n, exm[q['orig']]))
        out.append(W.title('정답 및 해설', page=True))
        for k, e in exs:
            out += W.explanation(k, e)
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out'); ap.add_argument('data', nargs='?', default=D + '/data')
    ap.add_argument('--toc', default='')       # 목차 빈 쪽 번호(앞에서부터 차례로)
    ap.add_argument('--total', default='')     # 쪽 상자 전체 쪽수
    a = ap.parse_args()
    data = render.load(a.data)
    fixes.apply(data, [])
    zin = zipfile.ZipFile(a.src)
    files = {n: zin.read(n) for n in zin.namelist()}
    H = Header(files['Contents/header.xml'].decode('utf-8'))
    W = Writer(H)
    xml = body(W, data)
    sec = files['Contents/section0.xml'].decode('utf-8')
    # 마지막 빈 쪽 나눔 문단(= 12쪽 첫머리)을 이 교재로 바꿈
    m = re.search(r'<hp:p [^>]*pageBreak="1"[^>]*><hp:run charPrIDRef="\d+"/>(?:<hp:linesegarray>.*?</hp:linesegarray>)?</hp:p></hs:sec>$', sec, re.S)
    assert m, '마지막 빈 쪽 나눔 문단이 없음'
    sec = sec[:m.start()] + xml + '</hs:sec>'
    # 목차의 빈 쪽 번호 채우기: '…p. </hp:t>'(숫자 없음) 자리를 앞에서부터
    for v in [x for x in a.toc.split(',') if x]:
        sec, k = re.subn(r'p\. </hp:t>', 'p. %s</hp:t>' % v, sec, count=1)
        assert k, '목차 빈칸 부족'
    # 쪽 상자 전체 쪽수(꼬리말)
    if a.total:
        i = sec.find('<hp:footer'); j = sec.find('</hp:footer>', i)
        foot = re.sub(r'<hp:t>\d+</hp:t>', '<hp:t>%s</hp:t>' % a.total, sec[i:j], count=1)
        sec = sec[:i] + foot + sec[j:]
    files['Contents/section0.xml'] = sec.encode('utf-8')
    files['Contents/header.xml'] = H.x.encode('utf-8')
    # 미리보기 글자는 그대로 둠
    with zipfile.ZipFile(a.out, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), files.pop('mimetype'), compress_type=zipfile.ZIP_STORED)
        for n in zin.namelist():
            if n in files:
                z.writestr(n, files[n], compress_type=zipfile.ZIP_DEFLATED)
    print('ok', a.out)


if __name__ == '__main__':
    main()
