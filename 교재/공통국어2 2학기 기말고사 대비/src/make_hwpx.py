"""2026년 2학기 공통국어2 기말고사 대비 교재 → HWPX 세 권(강의용·분석지·해설지).
PDF판(make_book.py)과 같은 데이터·순서. 양식: 국제고 교재 HWPX의 글꼴·스타일, A4 2단, 1쪽 표지·목차.
지문마다 강의용 → 지문 분석 → 정답 및 해설 순서의 한 파일. 사용: python3 make_hwpx.py"""
import os, re, sys, zipfile
from xml.sax.saxutils import escape

H0 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(H0 + '/../../..')
MB = REPO + '/문제 모음집/선운사에서·한 그리움이 다른 그리움에게'
sys.path.insert(0, MB + '/src')
sys.path.insert(0, H0 + '/pdf')
sys.path.insert(0, H0)
import render_book as RB
from hwpx_merge import Header
from make_book import SET_TITLES, NAME, BOOKS, sets_info

BASE = MB + '/국제고 1학년 기말고사 교과서 문학 교재 + 문제 은행.hwpx'
CIRC = '①②③④⑤'
PW, PH = 59528, 84188
ML = MR = 3402; MT = 3969; MBOT = 2268; MF = 2268
GAP = 1700
TW = PW - ML - MR
CW = (TW - GAP) // 2
SZ = 950
LINE_H = 1520


def add_bf(H, sides, fill=None):
    def one(tag, v):
        t, w, c = v or ('NONE', '0.1 mm', '#000000')
        return '<hh:%s type="%s" width="%s" color="%s"/>' % (tag, t, w, c)
    n = H._count('borderFills')
    brush = '<hc:fillBrush><hc:winBrush faceColor="%s" hatchColor="#000000" alpha="0"/></hc:fillBrush>' % (fill or 'none')
    b = ('<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
         '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' % (n + 1)
         + ''.join(one(t, v) for t, v in zip(('leftBorder', 'rightBorder', 'topBorder', 'bottomBorder'), sides))
         + '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + brush + '</hh:borderFill>')
    H.x = H.x.replace('</hh:borderFills>', b + '</hh:borderFills>', 1)
    H.x = re.sub(r'<hh:borderFills itemCnt="\d+"', '<hh:borderFills itemCnt="%d"' % (n + 1), H.x, count=1)
    return n + 1


def add_para(H, base, align='JUSTIFY', intent=0, left=0, right=0, prev=0, nxt=0, line=160,
             border=None, offs=(0, 0, 0, 0), keep_next=False):
    b = re.search(r'<hh:paraPr id="%d" .*?</hh:paraPr>' % base, H.x, re.S).group(0)
    b = re.sub(r'<hh:align horizontal="\w+"', '<hh:align horizontal="%s"' % align, b, count=1)
    b = re.sub(r'<hh:heading [^>]*/>', '<hh:heading type="NONE" idRef="0" level="0"/>', b, count=1)
    b = re.sub(r'keepWithNext="\d"', 'keepWithNext="%d"' % keep_next, b, count=1)
    vals = {'intent': intent, 'left': left, 'right': right, 'prev': prev, 'next': nxt}

    def fix(seg, k):
        for name, v in vals.items():
            seg = re.sub(r'<hc:%s value="-?\d+"' % name, '<hc:%s value="%d"' % (name, v * k), seg)
        return re.sub(r'<hh:lineSpacing type="\w+" value="\d+"', '<hh:lineSpacing type="PERCENT" value="%d"' % line, seg)
    b = re.sub(r'<hp:case .*?</hp:case>', lambda m: fix(m.group(0), 1), b, flags=re.S)
    b = re.sub(r'<hp:default>.*?</hp:default>', lambda m: fix(m.group(0), 2), b, flags=re.S)
    bf, con = border if border else (2, 0)
    b = re.sub(r'<hh:border [^>]*/>',
               '<hh:border borderFillIDRef="%d" offsetLeft="%d" offsetRight="%d" offsetTop="%d" offsetBottom="%d" connect="%d" ignoreMargin="0"/>'
               % ((bf,) + tuple(offs) + (con,)), b, count=1)
    return H._add('paraProperties', 'paraPr', b)


class W:
    def __init__(self, H):
        self.H = H
        self.nid = 1800000000
        C = H.char
        self.c = {'n': C(20, size=SZ), 'b': C(20, bold=True, size=SZ), 'u': C(20, under=True, size=SZ),
                  'bu': C(20, bold=True, under=True, size=SZ), 'head': C(12, size=1050), 'sm': C(20, size=850),
                  'title': C(12, size=2000), 'sub': C(12, size=1300), 'toc': C(12, size=1100), 'pg': C(20, size=1000),
                  'tag': C(12, size=1000)}
        line = ('SOLID', '0.12 mm', '#000000')
        navy = ('SOLID', '0.4 mm', '#29334A')
        self.bf = {'box': add_bf(H, (line,) * 4), 'pass': add_bf(H, (line,) * 4),
                   'qa_n': add_bf(H, (line,) * 4, '#DCEBFA'), 'qa_v': add_bf(H, (line,) * 4),
                   'title': add_bf(H, (None, None, None, navy)), 'tagbox': add_bf(H, (line,) * 4, '#F7C9A9')}
        P = lambda **k: add_para(H, 5, **k)
        boxp = dict(border=(self.bf['pass'], 1), offs=(850, 850, 567, 567), left=1134, right=1134)
        self.p = {
            'title': P(align='LEFT', prev=8000, nxt=600, border=(self.bf['title'], 0), offs=(0, 0, 0, 400)),
            'sub': P(align='LEFT', nxt=2400),
            'toc': P(align='LEFT', nxt=500, left=600),
            'plain': P(), 'center': P(align='CENTER'),
            'head': P(align='LEFT', nxt=400, keep_next=True),
            'pass': P(intent=SZ, **boxp), 'pass0': P(intent=0, **boxp),
            'pass_item': P(intent=-1300, **dict(boxp, left=1134 + 1300)),
            'pass_c': P(align='CENTER', **boxp), 'pass_r': P(align='RIGHT', **boxp),
            'after': P(nxt=900),
            'q': P(intent=-1150, prev=1500, nxt=400, keep_next=True),
            'ch': P(intent=-1200, left=850 + 1200),
            'hold': P(align='CENTER', prev=200, nxt=400),
            'bt': P(align='CENTER', nxt=200), 'bx': P(intent=0), 'bx_i': P(intent=-1500, left=1500),
            'ans': P(),
            'eh': P(prev=1400, nxt=200, keep_next=True), 'ep': P(), 'ep_h': P(intent=-1100, left=1100),
            'foot_l': P(align='LEFT'), 'foot_r': P(align='RIGHT'),
            'qt': P(align='CENTER', nxt=600),
            'ansec': P(align='LEFT', prev=1300, nxt=350, keep_next=True),
            'anp': P(line=175, nxt=250), 'anp_h': P(intent=-1100, left=1100, line=175, nxt=250),
        }

    def id(self):
        self.nid += 1
        return self.nid

    def runs(self, text, base='n'):
        out, u, b = [], False, base == 'b'
        for tok in re.split(r'(</?u>|</?b>)', text):
            if tok in ('<u>', '</u>'): u = tok == '<u>'; continue
            if tok in ('<b>', '</b>'): b = tok == '<b>' or base == 'b'; continue
            if not tok: continue
            key = base if base not in ('n', 'b') else ('bu' if b and u else 'b' if b else 'u' if u else 'n')
            out.append('<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>' % (self.c[key], escape(tok)))
        return ''.join(out)

    def P(self, ps, text='', base='n', page=False, col=False, pre=''):
        body = pre + (self.runs(text, base) if text else '')
        if not body:
            body = '<hp:run charPrIDRef="%d"/>' % self.c['n']
        return ('<hp:p id="2147483648" paraPrIDRef="%d" styleIDRef="0" pageBreak="%d" columnBreak="%d" merged="0">%s</hp:p>'
                % (self.p[ps], int(page), int(col), body))

    def cols(self, n):
        line = '<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>' if n == 2 else ''
        return ('<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="%d" sameSz="1" sameGap="%d">%s</hp:colPr></hp:ctrl>'
                % (n, GAP, line))

    def table(self, rows, widths, height_row, margin=(425, 425, 283, 283), split=True):
        """rows = [[(문단 XML, borderFill), …], …]"""
        w = sum(widths)
        l, r, t, b = margin
        trs = ''
        for ri, row in enumerate(rows):
            tcs = ''.join(
                '<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="%d">'
                '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
                '<hp:cellAddr colAddr="%d" rowAddr="%d"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="%d" height="%d"/>'
                '<hp:cellMargin left="%d" right="%d" top="%d" bottom="%d"/></hp:tc>'
                % (bf, body, ci, ri, widths[ci], height_row, l, r, t, b) for ci, (body, bf) in enumerate(row))
            trs += '<hp:tr>%s</hp:tr>' % tcs
        return ('<hp:run charPrIDRef="%d"><hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="%s" repeatHeader="0" rowCnt="%d" colCnt="%d" cellSpacing="0" borderFillIDRef="%d" noAdjust="0">'
                '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
                '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
                '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="%d" right="%d" top="%d" bottom="%d"/>'
                '%s</hp:tbl><hp:t/></hp:run>'
                % (self.c['n'], self.id(), 'CELL' if split else 'NONE', len(rows), len(widths), rows[0][0][1], w,
                   height_row * len(rows), l, r, t, b, trs))

    def box(self, title, text):
        """<보기>·<조건>: 1칸 표"""
        cell = [self.P('bt', title)] if title else []
        n = 1
        for l in (text or '').split('\n'):
            cell.append(self.P('bx_i' if re.match(r'^([ㄱ-ㅎ]\.|[㉠-㉭ⓐ-ⓩ]|\(\d+\))', l) else 'bx', l))
            n += -(-len(re.sub(r'<[^>]+>', '', l)) // 30) or 1
        w = CW - 850
        return self.P('hold', pre=self.table([[(''.join(cell), self.bf['box'])]], [w], LINE_H * n + 1200, margin=(850, 850, 567, 567)))

    def footer(self, kind, para):
        return ('<hp:ctrl><hp:footer id="%d" applyPageType="%s"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="BOTTOM" linkListIDRef="0" linkListNextIDRef="0" textWidth="%d" textHeight="%d" hasTextRef="0" hasNumRef="0">'
                '<hp:p id="2147483648" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar="" supscript="0"/></hp:autoNum></hp:ctrl><hp:t/></hp:run></hp:p>'
                '</hp:subList></hp:footer></hp:ctrl>' % (self.id() % 100000, kind, TW, MF, self.p[para], self.c['pg']))

    # ---------- 내용 ----------
    def passage(self, s, numbered=False):
        out = [self.P('head', RB.set_head(s), base='head')]
        pn = 0
        first = True
        for wi, w in enumerate(s['works']):
            if w.get('label'):
                if not first:
                    out.append(self.P('pass0'))
                out.append(self.P('pass0', '<b>%s</b>' % w['label']))
            lines = w['lines'].split('\n')
            prose = max(len(re.sub(r'<[^>]+>', '', x)) for x in lines) > 60
            for l in lines:
                if not l.strip():
                    out.append(self.P('pass0')); continue
                if re.match(r'^<b>.*</b>$', l.strip()):
                    out.append(self.P('pass_c', l)); continue
                if re.match(r'^\(\d+\)', l.strip()):
                    out.append(self.P('pass_item', l)); continue
                if numbered and prose:
                    pn += 1
                    l = '<b>[%d]</b> ' % pn + l
                out.append(self.P('pass' if prose else 'pass0', l))
            if w.get('author'):
                out.append(self.P('pass_r', w['author']))
            first = False
        out.append(self.P('after'))
        return out

    def question(self, q):
        n = RB.qnum(q)
        lab = '[%s] ' % n if q.get('label') else '%s. ' % n
        out = [self.P('q', '<b>%s</b>%s' % (lab, q['stem']))]
        if q.get('bogi'):
            b = q['bogi']
            out.append(self.box(b.get('title') if b.get('title') is not None else '<보기>', b.get('text', '')))
        ex = q.get('extra')
        if isinstance(ex, dict):
            out.append(self.box(ex.get('title') or '', ex.get('text') or ''))
        elif ex:
            out.append(self.box('', ex))
        if q.get('pair_head'):
            out.append(self.P('ch', '　　%s' % '　/　'.join(q['pair_head'])))
        for i, c in enumerate(q.get('choices') or []):
            out.append(self.P('ch', '%s %s' % (CIRC[i], c.replace(' / ', '　/　'))))
        if not q.get('choices'):
            out += [self.P('ans') for _ in range(9)]
        return out

    def quick(self, sets, ans, note='서답형 1~4는 해설의 모범 답안 참고'):
        cells = [(RB.qnum(q), ' '.join(re.findall('[①-⑤]', (ans.get(RB.qkey(q)) or {}).get('answer', '')))) for s in sets for q in s['questions'] if q.get('choices')]
        rows = []
        for i in range(0, len(cells), 5):
            r = cells[i:i + 5] + [('', '')] * (5 - len(cells[i:i + 5]))
            row = []
            for n, v in r:
                row += [(self.P('center', n, base='b'), self.bf['qa_n']), (self.P('center', v), self.bf['qa_v'])]
            rows.append(row)
        w1 = CW * 9 // 100; w2 = (CW - 5 * w1) // 5
        out = [self.P('head', '<b>빠른 정답</b>', base='head'),
               self.P('plain', pre=self.table(rows, [w1, w2] * 5, 1700, margin=(141, 141, 141, 141))),
               self.P('plain', note, base='sm') if note else self.P('plain'), self.P('after')]
        return out

    def explanation(self, q, e):
        n = RB.qnum(q)
        out = []
        if q.get('choices'):
            out.append(self.P('eh', '<b>%s. %s</b>' % (n, e.get('answer', ''))))
            c = e.get('answer', '')[:1]
            if e.get('plain'):
                out += [self.P('ep_h' if p[:1] in CIRC else 'ep', '<b>%s</b>' % p if p.startswith('[') else p) for p in e['plain'].split('\n') if p.strip()]
            else:
                if e.get('correct'):
                    out.append(self.P('ep_h', '%s %s' % (c, e['correct'])))
                if e.get('wrong'):
                    out.append(self.P('ep', '<b>[오답풀이]</b>'))
                    out += [self.P('ep_h', ('%s %s' % (k, t)).strip()) for k, t in e['wrong']]
        else:
            out.append(self.P('eh', '<b>[%s]</b>' % n))
            out.append(self.P('ep', '<b>[모범 답안]</b>'))
            out += [self.P('ep_h', '· ' + x) for x in e.get('answer', '').split('\n') if x.strip()]
            if e.get('points'):
                out.append(self.P('ep', '<b>[채점 기준]</b>'))
                out += [self.P('ep_h', '· ' + x) for x in e['points']]
            if e.get('plain'):
                out.append(self.P('ep', '<b>[해설]</b>'))
                out += [self.P('ep', x) for x in e['plain'].split('\n') if x.strip()]
        return out

    def analysis(self, a):
        """주제·글의 구조 / 문단 요약 / 핵심 어휘 / 출제 포인트: 묶음마다 띄워서"""
        out = []
        sec = lambda t: self.P('ansec', '<b>[%s]</b>' % t)
        for part in a.get('works', [a]):
            if part.get('label'):
                out.append(self.P('eh', '<b>%s %s</b>' % (part['label'], part.get('title', ''))))
            if part.get('topic'):
                out += [sec('주제'), self.P('anp', part['topic'])]
            if part.get('structure'):
                out += [sec('글의 구조'), self.P('anp', part['structure'])]
            if part.get('paras'):
                out.append(sec('문단 요약'))
                out += [self.P('anp_h', '<b>[%s]</b> %s' % (p['n'], p['summary'])) for p in part['paras']]
            if part.get('vocab'):
                out.append(sec('핵심 어휘'))
                out += [self.P('anp_h', '· <b>%s</b>: %s' % (w, m)) for w, m in part['vocab']]
            if part.get('points'):
                out.append(sec('출제 포인트'))
                out += [self.P('anp_h', '✔ ' + x) for x in part['points']]
            out.append(self.P('after'))
        return out


def build(Wr, secpr):
    """지문마다 강의용 → 지문 분석 → 정답 및 해설"""
    sets, ans, ana = RB.load(H0 + '/data')
    info = sets_info()
    out = [('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            '<hp:run charPrIDRef="%d">%s%s</hp:run><hp:run charPrIDRef="%d">%s%s<hp:t/></hp:run>%s</hp:p>'
            % (Wr.p['title'], Wr.c['n'], secpr, Wr.cols(1), Wr.c['n'], Wr.footer('EVEN', 'foot_l'), Wr.footer('ODD', 'foot_r'),
               Wr.runs(NAME, 'title')))]
    for k, s in enumerate(info, 1):
        out.append(Wr.P('sub', 'PART %02d　%s　(%s)' % (k, s['title'], s['rng']), base='toc'))
        out.append(Wr.P('toc', '강의용 교재　·　지문 분석지　·　정답 및 해설', base='sm'))
    two = '<hp:run charPrIDRef="%d">%s</hp:run>' % (Wr.c['n'], Wr.cols(2))
    for i, s in enumerate(sets):
        no = '%02d' % (i + 1)
        # 강의용
        out.append(Wr.P('qt', '<b>%s 강의용</b>' % no, base='sub', page=True, pre=two))
        out += Wr.passage(s)
        for q in s['questions']:
            out += Wr.question(q)
        # 지문 분석
        out.append(Wr.P('qt', '<b>%s 지문 분석</b>' % no, base='sub', page=True))
        out += Wr.passage(s, numbered=True)
        a = ana.get(str(s['no']))
        if a:
            x = Wr.analysis(a)
            x[0] = x[0].replace('columnBreak="0"', 'columnBreak="1"', 1)
            out += x
        # 정답 및 해설
        out.append(Wr.P('qt', '<b>%s 정답 및 해설</b>' % no, base='sub', page=True))
        sd = any(q.get('label') for q in s['questions'])
        out += Wr.quick([s], ans, note='서답형은 해설의 모범 답안 참고' if sd else '')
        for q in s['questions']:
            e = ans.get(RB.qkey(q))
            if e:
                out += Wr.explanation(q, e)
    return ''.join(out)


def make():
    out = os.path.join(H0, '..', NAME + '.hwpx')
    zin = zipfile.ZipFile(BASE)
    files = {k: zin.read(k) for k in zin.namelist()}
    H = Header(files['Contents/header.xml'].decode('utf-8'))
    Wr = W(H)
    sec = files['Contents/section0.xml'].decode('utf-8')
    root = re.match(r'(.*?<hs:sec [^>]*>)', sec, re.S).group(1)
    secpr = re.search(r'<hp:secPr .*?</hp:secPr>', sec, re.S).group(0)
    secpr = re.sub(r'<hp:pagePr [^>]*>', '<hp:pagePr landscape="WIDELY" width="%d" height="%d" gutterType="LEFT_ONLY">' % (PW, PH), secpr)
    secpr = re.sub(r'<hp:margin [^>]*/>', '<hp:margin header="0" footer="%d" gutter="0" left="%d" right="%d" top="%d" bottom="%d"/>' % (MF, ML, MR, MT, MBOT), secpr)
    secpr = re.sub(r'masterPageCnt="\d+"', 'masterPageCnt="0"', secpr)
    secpr = re.sub(r'<hp:masterPage [^>]*/>', '', secpr)
    secpr = re.sub(r'hideFirstFooter="\d"', 'hideFirstFooter="1"', secpr)
    secpr = re.sub(r'hideFirstPageNum="\d"', 'hideFirstPageNum="1"', secpr)
    secpr = re.sub(r'<hp:pageBorderFill type="BOTH" borderFillIDRef="\d+"', '<hp:pageBorderFill type="BOTH" borderFillIDRef="1"', secpr)
    body = build(Wr, secpr)
    files['Contents/section0.xml'] = (root + body + '</hs:sec>').encode('utf-8')
    files['Contents/header.xml'] = H.x.encode('utf-8')
    hpf = files['Contents/content.hpf'].decode('utf-8')
    hpf = re.sub(r'<opf:item id="(masterpage\d+|image\d+)"[^>]*/>', '', hpf)
    hpf = re.sub(r'<opf:title>.*?</opf:title>', '<opf:title>%s</opf:title>' % escape(NAME), hpf)
    files['Contents/content.hpf'] = hpf.encode('utf-8')
    for k in [k for k in files if k.startswith('Contents/masterpage') or k.startswith('BinData/')]:
        del files[k]
    files['settings.xml'] = re.sub(rb'<ha:CaretPosition [^>]*/>', b'<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>', files['settings.xml'])
    files['Preview/PrvText.txt'] = NAME.encode('utf-8')
    files.pop('Preview/PrvImage.png', None)
    order = [k for k in zin.namelist() if k in files] + [k for k in files if k not in zin.namelist()]
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), files['mimetype'], compress_type=zipfile.ZIP_STORED)
        for k in order:
            if k != 'mimetype':
                z.writestr(k, files[k], compress_type=zipfile.ZIP_DEFLATED)
    print('ok', out)


if __name__ == '__main__':
    make()
