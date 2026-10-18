"""샘플: 강호사시가 + 말 업슨 청산이오 (부산외고 2학기 기말고사) — 원본 그대로(A) / 한글 재작성(B)."""
import sys, os
S = os.path.dirname(os.path.abspath(__file__)) + '/..'
SMP = S + '/smp'
LOGO = '/home/user/-teachergyu/brand/logo_navy.png'
HEAD = '부산외고 2학기 기말고사'
SUB = '〔강호사시가 · 말 업슨 청산이오 작품별 문제〕'
TOTAL = 60  # 전체 페이지 수 자리(샘플이라 임시)

CSS = r"""
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#111;font-family:"Noto Serif CJK KR",serif;font-size:9.6pt;line-height:1.62}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;page-break-after:always;padding:11mm 13mm 0}
.top1{position:relative;height:9mm;text-align:center;font-family:"Noto Sans CJK KR",sans-serif;font-size:13pt;color:#29334A;letter-spacing:-.01em;padding-top:1mm}
.top1 .pn{position:absolute;right:0;top:-2mm;font-family:"Noto Serif CJK KR",serif;font-weight:900;font-size:24pt;color:#111}
.row1{display:flex;align-items:center;justify-content:space-between;height:15mm}
.kyo{border:1.4px solid #111;border-radius:50%/50%;padding:.6mm 4.2mm;font-family:"Noto Serif CJK KR",serif;font-weight:700;font-size:12pt}
.kyo b{font-size:15pt}
.sub{font-family:"Noto Sans CJK KR",sans-serif;font-weight:900;font-size:27pt;letter-spacing:-.01em;margin-left:9mm}
.logo{height:11.5mm}
.rule{border-top:2.6px solid #111;border-bottom:.8px solid #111;height:4px;margin:1mm 0 0}
.topn{display:flex;align-items:flex-end;justify-content:space-between;height:15mm;padding-bottom:1.2mm}
.topn .pn{font-family:"Noto Serif CJK KR",serif;font-weight:900;font-size:24pt;line-height:1;width:30mm}
.topn .ra{font-family:"Playfair Display","Noto Serif CJK KR",serif;font-size:18pt;letter-spacing:.04em;color:#29334A}
.topn .lg{width:30mm;display:flex}
.topn .lg img{height:9mm}
.even .topn .lg{justify-content:flex-end}
.odd .topn{flex-direction:row-reverse}
.odd .topn .pn{text-align:right}
.cols{position:absolute;left:13mm;right:13mm;top:var(--top);bottom:20mm;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:minmax(0,1fr);column-gap:8mm}
.cols:before{content:"";position:absolute;left:50%;top:0;bottom:0;border-left:1.2px solid #111}
.col{position:relative;overflow:hidden}
.foot{position:absolute;bottom:8mm;left:0;right:0;text-align:center}
.fr{display:inline-block;position:relative;width:15mm;height:9mm;border:1px solid #111;font-family:"Noto Serif CJK KR",serif;font-weight:700;font-size:8pt;line-height:1}
.fr:after{content:"";position:absolute;left:0;top:0;width:100%;height:100%;background:linear-gradient(to bottom right,transparent calc(50% - .5px),#111 calc(50% - .5px),#111 calc(50% + .5px),transparent calc(50% + .5px))}
.fr i{position:absolute;left:1.6mm;top:.9mm;font-size:9pt;font-style:normal}
.fr s{position:absolute;right:1.2mm;bottom:.8mm;text-decoration:none}
.set{font-family:"Noto Sans CJK KR",sans-serif;font-weight:700;font-size:9.4pt;margin:0 0 2mm}
.box{border:1px solid #111;padding:3mm 3.6mm;margin-bottom:5mm}
.box.cont{border-top:none}
.box.open{border-bottom:none;margin-bottom:0;padding-bottom:0}
.box img{display:block;width:100%}
.q{margin-bottom:9mm}
.q img{display:block;width:100%}
.qh{display:flex;gap:1.6mm;font-weight:700;margin-bottom:1.6mm;line-height:1.55}
.qh .n{flex:none;font-family:"Noto Sans CJK KR",sans-serif;font-weight:900}
.qi{display:flex;gap:1.4mm;align-items:flex-start}
.qi .n{flex:none;font-family:"Noto Sans CJK KR",sans-serif;font-weight:900;font-size:10pt;line-height:1.5}
.qi img{flex:1;min-width:0;width:auto;max-width:calc(100% - 5mm)}
.ch{display:flex;gap:1.2mm;margin:.5mm 0 .5mm 1mm;text-align:justify}
.ch .c{flex:none}
.p{margin:0;line-height:1.6;font-size:9.2pt}
.p>span{display:block}
.p .sp{height:1.9mm}
.p .tag{font-family:"Noto Sans CJK KR",sans-serif;font-weight:700}
.p .au{display:block;text-align:right}
.p .ind{padding-left:1em;text-indent:-1em;display:block}
.note{font-size:8.6pt;line-height:1.55;margin-top:1.2mm}
u{text-underline-offset:2px}
.nan{text-align:center;line-height:1.45;font-size:9pt;letter-spacing:-.03em}
"""

def header(n, first):
    if first:
        return f'''<div class="top1">{HEAD} {SUB}<span class="pn">{n}</span></div>
<div class="row1"><span class="kyo"><b>제 1 교시</b></span><span class="sub">국어 영역</span><img class="logo" src="file://{LOGO}"></div>
<div class="rule"></div>'''
    return f'''<div class="topn"><span class="pn">{n}</span><span class="ra">RICH ACADEMY</span><span class="lg"><img src="file://{LOGO}"></span></div><div class="rule"></div>'''

def page(n, left, right):
    first = n == 1
    cls = 'odd' if n % 2 else 'even'
    top = '42mm' if first else '33mm'
    return f'''<div class="page {cls}">{header(n, first)}
<div class="cols" style="--top:{top}"><div class="col">{left}</div><div class="col">{right}</div></div>
<div class="foot"><span class="fr"><i>{n}</i><s>{TOTAL}</s></span></div></div>'''

def img(name): return f'<img src="file://{SMP}/{name}">'

# ---------- A: 원본 그대로 ----------
def version_a():
    p1 = page(1,
        f'<div class="set">[1] 다음 글을 읽고 물음에 답하시오.</div><div class="box open">{img("s1L.png")}</div>',
        f'<div class="box cont">{img("s1R.png")}</div>'
        f'<div class="q qi"><span class="n">1.</span>{img("img-000.png")}</div>')
    p2 = page(2,
        f'<div class="set">[2] 다음 글을 읽고 물음에 답하시오.</div><div class="box">{img("s2L.png")}</div>',
        f'<div class="q qi"><span class="n">2.</span>{img("img-004.png")}</div>')
    return p1 + p2

# ---------- B: 한글 재작성 ----------
def poem(lines):
    out = []
    for l in lines:
        if l == '': out.append('<span class="sp"></span>')
        elif l.startswith('@'): out.append(f'<span class="au">{l[1:]}</span>')
        elif l.startswith('#'): out.append(f'<span class="tag">{l[1:]}</span>')
        elif l.startswith('>'): out.append(f'<span class="ind">{l[1:]}</span>')
        else: out.append(f'<span>{l}</span>')
    return '<div class="p">' + ''.join(out) + '</div>'

def q(n, stem, chs):
    c = ''.join(f'<div class="ch"><span class="c">{"①②③④⑤"[i]}</span><span>{t}</span></div>' for i, t in enumerate(chs))
    return f'<div class="q"><div class="qh"><span class="n">{n}.</span><span>{stem}</span></div>{c}</div>'

S1_L = ['#(가)', '산은', '구강산(九江山)', '보랏빛 석산(石山)', '', '산도화', '두어 송이', '송이 버는데', '',
        '봄눈 녹아 흐르는', '옥 같은', '물에', '', '사슴은', '암사슴', '발을 씻는다.', '@- 박목월, ‘산도화’', '', '#(나)']
NANUM = ['山', '절망의산,', '대가리를밀어버', '린, 민둥산, 벌거숭이산', '분노의산, 사랑의산, 침묵의',
         '산, 함성의산, 증인의산, 죽음의산,', '부활의산, 영생하는산, 생의산, 희생의',
         '산, 숨가쁜산, 치밀어오르는산, 갈망하는', '산, 꿈꾸는산, 꿈의산, 그러나 현실의산, 피의산,',
         '피투성이산, 종교적인산, 아아너무나너무나 폭발적인', '산, 힘든산, 힘센산, 일어나는산, 눈뜬산, 눈뜨는산, 새벽',
         '의산, 희망의산, 모두모두절정을이루는평등의산, 평등한산, 대', '지의산, 우리를감싸주는, 격하게, 넉넉하게, 우리를감싸주는', '어머니']
S1_L2 = ['@- 황지우, ‘무등’', '', '#(다)', '산이 날 에워싸고', '씨나 뿌리며 살아라 한다.', '밭이며 갈며 살아라 한다.', '',
         '어느 짧은 산자락에 집을 모아', '아들 낳고 딸을 낳고', '흙담 안팎에 호박 심고', '들찔레처럼 살아라 한다.',
         '쑥대밭처럼 살아라 한다.', '', '산이 날 에워싸고', '그믐달처럼 사위어지는 목숨']
S1_R = ['그믐달처럼 살아라 한다.', '@- 박목월, ‘산이 날 에워싸고’', '', '#(라)',
        '江湖(강호)에 봄이 드니 미친 興(흥)이 절로 난다.', '濁醪溪邊(탁료계변)에 錦鱗魚(금린어)ㅣ 안주로다.',
        '이 몸이 閑暇(한가)해 옴도 亦君恩(역군은)이샷다.', '',
        '江湖(강호)에 녀름이 드니 草堂(초당)에 일이 업다.', '有信(유신)한 江波(강파)는 보내나니 바람이다.', '이 몸이 서늘해 옴도 역군은이샷다.', '',
        '강호에 가을이 드니 고기마다 살져 잇다.', '㉠<u>小艇(소정)에 그물 시러 흘리 띄여 더뎌 주고,</u>', '이 몸이 消日(소일)해 옴도 역군은이샷다.', '',
        '강호에 겨울이 드니 눈 기픠 자히 남다.', '삿갓 빗기 쓰고 누역으로 오슬 삼아,', '이 몸이 칩지 아니해 옴도 역군은이샷다.',
        '@- 맹사성, ‘강호사시가(江湖四時歌)’']
Q1 = q(1, '(가) ~ (라)에 대한 이해로 가장 적절한 것은?', [
    '(가)와 (나) 모두 화자가 작품에 직접적으로 드러나지 않으며 대상을 묘사하고 있다.',
    '(나)는 (다)와 달리 시적 대상을 의인화하여 시상을 전개하고 있다.',
    '(다)는 (라)와 달리 유사한 통사 구조를 반복하여 리듬감을 형성하고 있다.',
    '(나)와 달리 (다)는 시련을 환기하는 시어로 주제를 형상화하고 있다.',
    '(가)와 달리 (라)는 자연 속에서의 소박한 화자의 태도가 나타나 있다.'])

A = 'ᄋᆞ'
S2 = ['#(가)', '눈 마ᄌᆞ 휘여진 ᄃᆡ를 뉘라셔 굽다턴고', '구블 절(節)이면 눈 속에 프를소냐', '아마도 세한 고절(歲寒孤節)은 너뿐인가 ᄒᆞ노라', '',
      '#(나)', '동지(冬至)ㅅᄃᆞᆯ 기나긴 밤을 한 허리를 버혀 내어', '춘풍(春風) 니불 아래 서리서리 너헛다가', '어론 님 오신 날 밤이여든 구뷔구뷔 펴리라', '',
      '#(다)', '두터비 파리를 물고 두엄 우희 치다라 안자', '>것넌산 바라보니 백송골(白松鶻)이 떠 잇거늘 가슴이 금즉하여 풀덕 뛰여 내닷다가 두험 아래 쟛바지거고',
      '모쳐라 날낸 낼싀만졍 에헐질 번 하괘라', '',
      '#(라)', '생사(生死) 길은', '예 있으매 머뭇거리고,', '나는 간다는 말도', '몯다 이르고 어찌 갑니까.', '어느 가을 이른 바람에',
      '이에 저에 떨어질 잎처럼,', '한 가지에 나고', '가는 곳 모르온저.', '아아, 미타찰(彌陀刹)에서 만날 나', '도(道) 닦아 기다리겠노라.', '@- 월명사, ‘제망매가’', '',
      '#(마)', '강호(江湖)에 봄이 드니 미친 흥(興)이 절로 난다', '탁료계변(濁醪溪邊)에 금린어(錦鱗魚) 안주로다', '이 몸이 한가하옴도 역군은(亦君恩)이샷다', '',
      '강호에 여름이 드니 초당(草堂)에 일이 없다', '유신(有信)한 강파(江波)는 보내느니 바람이로다', '이 몸이 서늘하옴도 역군은(亦君恩)이샷다', '',
      '강호에 가을이 드니 고기마다 살져 있다', '소정(小艇)에 그믈 실어 흘리 띄워 던져 두고', '이 몸이 소일하옴도 역군은(亦君恩)이샷다.', '',
      '강호에 겨울이 드니 눈 깊이 자히 남다.', '삿갓 비껴 쓰고 누역으로 옷을 삼아', '이 몸이 춥지 아니하옴도 역군은(亦君恩)이샷다.', '@- 맹사성, ‘강호사시가(江湖四時歌)’']
Q2 = q(2, '(마)를 읽고 난 후의 반응으로 적절하지 <u>않은</u> 것은?', [
    '자연에서 봄을 맞는 화자의 즐거움이 생생하게 느껴져.',
    '이 작품을 통해 계절의 변화와 그에 따른 화자의 생활상을 짐작할 수 있어.',
    '추운 겨울에도 삿갓과 누역으로 만족하는 화자의 모습을 보니 ‘안분지족’이라는 말이 떠올라.',
    '사계절의 풍류를 즐기면서도 임금에 대한 은혜를 잊지 않는 걸 보니 화자는 사대부일 거야.',
    '가을에 살이 오른 물고기를 잡아 넉넉한 생활을 할 수 있다는 것에 감사하고 있군.'])

def version_b():
    nan = '<div class="nan">' + '<br>'.join(NANUM) + '</div>'
    left = ('<div class="set">[1] 다음 글을 읽고 물음에 답하시오.</div><div class="box open">'
            + poem(S1_L) + nan + poem(S1_L2) + '</div>')
    right = ('<div class="box cont">' + poem(S1_R)
             + '<div class="note">*탁료계변 : 시냇가에 앉아 막걸리를 마심.<br>*누역 : 도롱이, 띠풀로 엮은 비옷.</div></div>' + Q1)
    p1 = page(1, left, right)
    p2 = page(2, '<div class="set">[2] 다음 글을 읽고 물음에 답하시오.</div><div class="box">' + poem(S2) + '</div>', Q2)
    return p1 + p2

def html(body):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'

if __name__ == '__main__':
    d = os.path.dirname(os.path.abspath(__file__))
    open(d + '/a.html', 'w').write(html(version_a()))
    open(d + '/b.html', 'w').write(html(version_b()))
