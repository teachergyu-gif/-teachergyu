"""독서 기출_고2 교육청(7) 1~9번 → HWPX(한글 파일).
양식: 문제 은행 HWPX(국제고 교재)의 글꼴·스타일을 그대로 쓰고, 쪽은 원본 PDF처럼 A4 2단·표지 1쪽.
사용: python3 make_hwpx.py 출력.hwpx"""
import sys, os, re, zipfile, io
from xml.sax.saxutils import escape
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(D + '/../../..')
MB = REPO + '/문제 모음집/선운사에서·한 그리움이 다른 그리움에게'
sys.path.insert(0, MB + '/src')
from hwpx_merge import Header
import data

BASE = MB + '/국제고 1학년 기말고사 교과서 문학 교재 + 문제 은행.hwpx'
CIRC = '①②③④⑤'

# A4, 원본 PDF와 비슷한 여백(HWPUNIT: 1mm = 283.46)
PW, PH = 59528, 84188
ML = MR = 3402; MT = 3685; MBOT = 2268; MF = 2268
GAP = 1700
TW = PW - ML - MR
CW = (TW - GAP) // 2
BODY_H = PH - MT - MBOT - MF
SZ = 900                      # 본문 9pt(원본과 같은 밀도: 한 줄 약 30자)
LINE_H = 1440                 # 9pt × 160%
Q_GAP = 4500                  # 같은 단 안에서 다음 문항 앞 간격


def add_bf(H, sides, fill=None):
    """borderFill 추가(id는 1부터라 개수+1). sides = (left, right, top, bottom), 각 (종류, 굵기, 색) 또는 None."""
    def one(tag, v):
        t, w, c = v or ('NONE', '0.1 mm', '#000000')
        return '<hh:%s type="%s" width="%s" color="%s"/>' % (tag, t, w, c)
    n = H._count('borderFills')
    brush = '<hc:fillBrush><hc:winBrush faceColor="%s" hatchColor="#000000" alpha="0"/></hc:fillBrush>' % (fill or 'none')
    b = ('<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
         '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
         % (n + 1)
         + ''.join(one(t, v) for t, v in zip(('leftBorder', 'rightBorder', 'topBorder', 'bottomBorder'), sides))
         + '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + brush + '</hh:borderFill>')
    H.x = H.x.replace('</hh:borderFills>', b + '</hh:borderFills>', 1)
    H.x = re.sub(r'<hh:borderFills itemCnt="\d+"', '<hh:borderFills itemCnt="%d"' % (n + 1), H.x, count=1)
    return n + 1


def add_para(H, base, align='JUSTIFY', intent=0, left=0, right=0, prev=0, nxt=0, line=160,
             border=None, offs=(0, 0, 0, 0), keep_next=False):
    """문단 모양 추가. 여백은 HwpUnitChar 쪽(case)이 실제 값, default는 그 2배(보낸 파일과 같은 방식)."""
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
        self.nid = 1700000000
        self.bins = []                      # (id, 파일 이름)
        C = H.char
        self.c = {'n': C(20, size=SZ), 'b': C(20, bold=True, size=SZ), 'u': C(20, under=True, size=SZ),
                  'bu': C(20, bold=True, under=True, size=SZ),
                  'head': C(12, size=1050), 'tbl': C(12, size=850), 'ana': C(12, size=950),
                  'cover': C(12, size=1800), 'pg': C(20, size=1000)}
        line = ('SOLID', '0.12 mm', '#000000')
        thick = ('SOLID', '0.4 mm', '#000000')
        blue = ('SOLID', '0.5 mm', '#4472C4')
        self.bf = {'box': add_bf(H, (line,) * 4),
                   'pass': add_bf(H, (blue,) * 4),
                   'src0': add_bf(H, (None, line, thick, line)),
                   'src1': add_bf(H, (line, line, thick, line)),
                   'src2': add_bf(H, (line, None, thick, line))}
        P = lambda **k: add_para(H, 5, **k)
        self.p = {
            'cover': P(align='LEFT', prev=21000),
            'plain': P(),
            'src': P(align='CENTER', line=130),
            'srchold': P(align='LEFT', nxt=500),
            'head': P(align='LEFT', nxt=500, keep_next=True),
            'pass': P(intent=SZ, left=1134, right=1134, border=(self.bf['pass'], 1), offs=(850, 850, 567, 567)),
            'pass_a': P(intent=0, left=1134, right=1134, border=(self.bf['pass'], 1), offs=(850, 850, 567, 567)),
            'after': P(nxt=600),
            'q': P(intent=-1150, nxt=500, keep_next=True),
            'q_gap': P(intent=-1150, prev=Q_GAP, nxt=500, keep_next=True),
            'ch': P(intent=-1200, left=850 + 1200),
            'hold': P(align='CENTER', prev=200, nxt=400),
            'bt': P(align='CENTER', nxt=200),
            'bx': P(intent=SZ),
            'bx_i': P(intent=-1500, left=1500),
            'bx_c': P(align='CENTER', nxt=200),
            'ana': P(align='CENTER'),
            'foot_l': P(align='LEFT'),
            'foot_r': P(align='RIGHT'),
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

    # ---------- 표·그림 ----------
    def table(self, cells, height, margin=(567, 567, 567, 567), valign='TOP', split=False):
        """1행 표. cells = [(너비, 칸 안 문단 XML, borderFill)]"""
        w = sum(c[0] for c in cells)
        l, r, t, b = margin
        tcs = ''.join(
            '<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="%d">'
            '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="%s" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
            '<hp:cellAddr colAddr="%d" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="%d" height="%d"/>'
            '<hp:cellMargin left="%d" right="%d" top="%d" bottom="%d"/></hp:tc>'
            % (bf, valign, body, i, cw, height, l, r, t, b) for i, (cw, body, bf) in enumerate(cells))
        return ('<hp:run charPrIDRef="%d"><hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="%s" repeatHeader="0" rowCnt="1" colCnt="%d" cellSpacing="0" borderFillIDRef="%d" noAdjust="0">'
                '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
                '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
                '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="%d" right="%d" top="%d" bottom="%d"/>'
                '<hp:tr>%s</hp:tr></hp:tbl><hp:t/></hp:run>'
                % (self.c['n'], self.id(), 'CELL' if split else 'NONE', len(cells), cells[0][2], w, height, l, r, t, b, tcs))

    def pic(self, name, width):
        k = len(self.bins) + 1
        self.bins.append(('image%d' % k, name))
        pw, ph = Image.open(D + '/img/' + name).size
        W0, H0 = pw * 75, ph * 75           # 원본 크기(1px = 75 HWPUNIT)
        w, h = width, round(width * ph / pw)
        return ('<hp:run charPrIDRef="%d"><hp:pic id="%d" zOrder="%d" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="%d" reverse="0">'
                '<hp:offset x="0" y="0"/><hp:orgSz width="%d" height="%d"/><hp:curSz width="%d" height="%d"/><hp:flip horizontal="0" vertical="0"/>'
                '<hp:rotationInfo angle="0" centerX="%d" centerY="%d" rotateimage="1"/>'
                '<hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:scaMatrix e1="%.6f" e2="0" e3="0" e4="0" e5="%.6f" e6="0"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
                '<hc:img binaryItemIDRef="image%d" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
                '<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="%d" y="0"/><hc:pt2 x="%d" y="%d"/><hc:pt3 x="0" y="%d"/></hp:imgRect>'
                '<hp:imgClip left="0" right="%d" top="0" bottom="%d"/><hp:inMargin left="0" right="0" top="0" bottom="0"/>'
                '<hp:imgDim dimwidth="%d" dimheight="%d"/><hp:effects/>'
                '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
                '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
                '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:shapeComment>그림입니다.</hp:shapeComment></hp:pic><hp:t/></hp:run>'
                % (self.c['n'], self.id(), k, self.id(), W0, H0, w, h, w // 2, h // 2, w / W0, h / H0,
                   k, W0, W0, H0, H0, W0, H0, W0, H0, w, h)), h

    # ---------- 부분 ----------
    def src_table(self, vals):
        ws = [int(CW * f) for f in (0.26, 0.26, 0.22)]
        ws.append(CW - sum(ws))
        bfs = [self.bf['src0'], self.bf['src1'], self.bf['src1'], self.bf['src2']]
        cells = [(w, self.P('src', v, base='tbl'), bf) for w, v, bf in zip(ws, vals, bfs)]
        return self.table(cells, 1500, margin=(141, 141, 283, 283), valign='CENTER')

    def analysis(self, height):
        body = self.P('ana', '〈지문분석〉', base='ana')
        return self.table([(CW, body, self.bf['box'])], height, margin=(850, 850, 425, 425))

    def bogi(self, lines, img=None):
        w = CW - 850
        cell = [self.P('bt', '〈 보 기 〉')]
        h = 2 * 567 + LINE_H + 200          # 칸 여백 + 제목 줄(높이는 한글이 내용에 맞춰 다시 늘림)
        if img:
            pr, ph = self.pic(img, w - 2 * 850 - 1000)
            cell.append(self.P('bx_c', pre=pr)); h += ph + 200
        for l in lines:
            cell.append(self.P('bx_i' if re.match(r'^[ⓐ-ⓩ㉠-㉭]', l) else 'bx', l))
            h += LINE_H * -(-len(l) // 30)
        return self.P('hold', pre=self.table([(w, ''.join(cell), self.bf['box'])], h, margin=(850, 850, 567, 567)))

    def question(self, n, q, first):
        brk = q.get('brk')
        out = [self.P('q' if first or brk else 'q_gap', '%d. %s' % (n, q['stem']), base='b',
                      page=brk == 'page', col=brk == 'col')]
        if q.get('bogi'):
            out.append(self.bogi(q['bogi'], q.get('bogi_img')))
        if q.get('img'):
            name, how = q['img']
            if how == 'frame':     # 그림 둘레에 원본처럼 테두리
                pr, h = self.pic(name, CW - 4000)
                out.append(self.P('hold', pre=self.table([(CW - 850, self.P('bx_c', pre=pr), self.bf['box'])], h + 600,
                                                          margin=(600, 600, 300, 300))))
            else:
                pr, h = self.pic(name, CW - 850)
                out.append(self.P('hold', pre=pr))
        for i, c in enumerate(q.get('choices') or []):
            out.append(self.P('ch', '%s %s' % (CIRC[i], c)))
        return out

    def footer(self, kind, para):
        return ('<hp:ctrl><hp:footer id="%d" applyPageType="%s"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="BOTTOM" linkListIDRef="0" linkListNextIDRef="0" textWidth="%d" textHeight="%d" hasTextRef="0" hasNumRef="0">'
                '<hp:p id="2147483648" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar="" supscript="0"/></hp:autoNum></hp:ctrl><hp:t/></hp:run></hp:p>'
                '</hp:subList></hp:footer></hp:ctrl>' % (self.id() % 100000, kind, TW, MF, self.p[para], self.c['pg']))


def build(Wr, secpr):
    out = []
    # 1쪽 표지(1단, 쪽 번호 없음)
    first = ('<hp:p id="0" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
             '<hp:run charPrIDRef="%d">%s%s</hp:run><hp:run charPrIDRef="%d">%s%s<hp:t/></hp:run>%s</hp:p>'
             % (Wr.p['cover'], Wr.c['n'], secpr, Wr.cols(1), Wr.c['n'],
                Wr.footer('EVEN', 'foot_l'), Wr.footer('ODD', 'foot_r'), Wr.runs(data.TITLE, 'cover')))
    out.append(first)
    n = 0
    for si, s in enumerate(data.SETS):
        pre = ('<hp:run charPrIDRef="%d">%s</hp:run>' % (Wr.c['n'], Wr.cols(2))) if si == 0 else ''
        out.append(Wr.P('srchold', page=True, pre=pre + Wr.src_table(s['src'])))
        out.append(Wr.P('head', s['head'], base='head'))
        for p in s['paras']:
            if isinstance(p, tuple):
                out.append(Wr.P('pass_a', '<b>%s</b>  %s' % p))
            else:
                out.append(Wr.P('pass', p))
        if s['analysis'] == 'page':
            out.append(Wr.P('plain', page=True, pre=Wr.analysis(BODY_H - 1500)))
        else:
            out.append(Wr.P('after'))
            out.append(Wr.P('plain', pre=Wr.analysis(int(BODY_H * 0.78))))
        for qi, q in enumerate(s['questions']):
            n += 1
            out += Wr.question(n, q, qi == 0)
    return ''.join(out)


def plain_text():
    t = [data.TITLE]
    n = 0
    for s in data.SETS:
        t.append(s['head'])
        t += [re.sub(r'</?\w>', '', p if isinstance(p, str) else p[1]) for p in s['paras']]
        for q in s['questions']:
            n += 1
            t.append('%d. %s' % (n, re.sub(r'</?\w>', '', q['stem'])))
    return '\r\n'.join(t)[:1000]


def main(out):
    zin = zipfile.ZipFile(BASE)
    files = {k: zin.read(k) for k in zin.namelist()}
    H = Header(files['Contents/header.xml'].decode('utf-8'))
    Wr = W(H)
    sec = files['Contents/section0.xml'].decode('utf-8')
    root = re.match(r'(.*?<hs:sec [^>]*>)', sec, re.S).group(1)
    secpr = re.search(r'<hp:secPr .*?</hp:secPr>', sec, re.S).group(0)
    secpr = re.sub(r'<hp:pagePr [^>]*>', '<hp:pagePr landscape="WIDELY" width="%d" height="%d" gutterType="LEFT_ONLY">' % (PW, PH), secpr)
    secpr = re.sub(r'<hp:margin [^>]*/>', '<hp:margin header="0" footer="%d" gutter="0" left="%d" right="%d" top="%d" bottom="%d"/>'
                   % (MF, ML, MR, MT, MBOT), secpr)
    secpr = re.sub(r'masterPageCnt="\d+"', 'masterPageCnt="0"', secpr)
    secpr = re.sub(r'<hp:masterPage [^>]*/>', '', secpr)
    secpr = re.sub(r'hideFirstFooter="\d"', 'hideFirstFooter="1"', secpr)
    secpr = re.sub(r'hideFirstPageNum="\d"', 'hideFirstPageNum="1"', secpr)
    secpr = re.sub(r'<hp:pageBorderFill type="BOTH" borderFillIDRef="\d+"', '<hp:pageBorderFill type="BOTH" borderFillIDRef="1"', secpr)
    body = build(Wr, secpr)
    files['Contents/section0.xml'] = (root + body + '</hs:sec>').encode('utf-8')
    files['Contents/header.xml'] = H.x.encode('utf-8')
    # 패키지 목록: 바탕쪽·기존 그림 빼고 새 그림 넣기
    hpf = files['Contents/content.hpf'].decode('utf-8')
    hpf = re.sub(r'<opf:item id="(masterpage\d+|image\d+)"[^>]*/>', '', hpf)
    hpf = re.sub(r'<opf:title>.*?</opf:title>', '<opf:title>%s</opf:title>' % escape(data.TITLE), hpf)
    items = ''.join('<opf:item id="%s" href="BinData/%s.jpg" media-type="image/jpeg" isEmbeded="1"/>' % (i, i) for i, _ in Wr.bins)
    hpf = hpf.replace('<opf:item id="section0"', items + '<opf:item id="section0"', 1)
    files['Contents/content.hpf'] = hpf.encode('utf-8')
    for k in [k for k in files if k.startswith('Contents/masterpage') or k.startswith('BinData/')]:
        del files[k]
    for i, name in Wr.bins:
        files['BinData/%s.jpg' % i] = open(D + '/img/' + name, 'rb').read()
    files['settings.xml'] = re.sub(rb'<ha:CaretPosition [^>]*/>', b'<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>', files['settings.xml'])
    files['Preview/PrvText.txt'] = plain_text().encode('utf-8')
    if os.path.exists(D + '/preview.png'):
        files['Preview/PrvImage.png'] = open(D + '/preview.png', 'rb').read()
    order = [k for k in zin.namelist() if k in files] + [k for k in files if k not in zin.namelist()]
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), files['mimetype'], compress_type=zipfile.ZIP_STORED)
        for k in order:
            if k != 'mimetype':
                z.writestr(k, files[k], compress_type=zipfile.ZIP_DEFLATED)
    print('ok', out, 'images', len(Wr.bins))


if __name__ == '__main__':
    main(sys.argv[1])
