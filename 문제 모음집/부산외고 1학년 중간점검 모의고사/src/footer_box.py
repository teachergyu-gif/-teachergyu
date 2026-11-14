"""합본 PDF의 모든 쪽 꼬리말 쪽 상자를 개념 교재 모양(대각선, 왼쪽 위 쪽 번호·오른쪽 아래 전체 쪽수)으로 다시 그린다.
기존 상자(개념 교재 쪽·문제 은행 쪽 두 자리)는 흰색으로 덮고, 꼬리말이 없던 쪽(MEMO)은 그대로 둔다.
사용: python3 footer_box.py 입력.pdf 출력.pdf 전체쪽수 앞문서쪽수 [건너뛸 쪽,…]
앞 문서 쪽(1~앞문서쪽수)은 원래 상자 자리, 문제 은행 쪽은 문제 은행 상자 자리(단 구분선 아래)에 그린다."""
import sys, io, subprocess, tempfile, os
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from PIL import Image

src, out, total, n0 = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
SKIP = {int(x) for x in (sys.argv[5] if len(sys.argv) > 5 else '').split(',') if x}   # 꼬리말 없는 쪽(MEMO)
r = PdfReader(src)
W, H = float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)
# 개념 교재 쪽 상자 위치(pt, 위에서부터): x 265~301, y 749.5~765.4
BW, BH = 36.5, 16.0
POS = [(265.0, 749.5), (297.6 - BW / 2, 808.0 - BH / 2)]   # 상자 왼쪽 위(개념 교재, 문제 은행)
OLD = [(262, 746, 305, 769), (277, 786, 319, 830)]   # 지울 자리(개념 교재, 문제 은행)


def has_footer(i):
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(['pdftoppm', '-r', '50', '-png', '-f', str(i + 1), '-l', str(i + 1), src, t + '/p'], check=True)
        im = Image.open([os.path.join(t, f) for f in os.listdir(t)][0]).convert('L')
    k = 50 / 72
    for x0, y0, x1, y1 in OLD:
        box = im.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)))
        if min(box.get_flattened_data() if hasattr(box, 'get_flattened_data') else box.getdata()) < 128:
            return True
    return False


w = PdfWriter()
for i, p in enumerate(r.pages):
    if i + 1 not in SKIP and has_footer(i):
        k = 0 if i < n0 else 1
        BX, BTOP = POS[k]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(W, H))
        c.setFillColorRGB(1, 1, 1); c.setStrokeColorRGB(1, 1, 1)
        for x0, y0, x1, y1 in OLD[k:k + 1]:
            c.rect(x0, H - y1, x1 - x0, y1 - y0, stroke=0, fill=1)
        y = H - BTOP - BH
        c.setStrokeColorRGB(0, 0, 0); c.setFillColorRGB(0, 0, 0); c.setLineWidth(0.6)
        c.rect(BX, y, BW, BH, stroke=1, fill=0)
        c.setLineWidth(0.4); c.line(BX, y, BX + BW, y + BH)          # 왼쪽 아래 → 오른쪽 위
        c.setFont('Times-Roman', 8.6)
        c.drawString(BX + 3.2, y + BH - 7.6, str(i + 1))           # 쪽 번호(왼쪽 위)
        c.drawRightString(BX + BW - 3.2, y + 2.0, str(total))      # 전체 쪽수(오른쪽 아래)
        c.save(); buf.seek(0)
        p.merge_page(PdfReader(buf).pages[0])
    w.add_page(p)
w.write(out)
print('ok', len(r.pages))
