"""선생님이 보낸 91쪽 합본(base.pdf)에서 바뀐 쪽만 새 빌드 쪽으로 교체. 실행: cd src && python3 user91/patch.py user91/base.pdf <출력.pdf>"""
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
from make_book import run, a4, H, DATA, PHRASE, FOOT
from pypdf import PdfReader, PdfWriter
T, OUT = sys.argv[1:3]
MAP = {8: 8, 25: 25, 34: 34, 41: 40, 42: 41, 50: 48, 51: 49}   # 보내준 파일 쪽 → 새 빌드 쪽
TOTAL = str(len(PdfReader(T).pages))
new = {}
with tempfile.TemporaryDirectory() as t:
    for off in sorted({k - v for k, v in MAP.items()}):
        start = 4 + off          # 원래 본문 첫 쪽 4 → 번호를 off만큼 밀어 렌더
        env = dict(os.environ, START_PAGE=str(start), MODE='perset')
        run('python3', '-I', f'{H}/pdf/render_book.py', DATA, f'{t}/b.html', env=env)
        run('node', f'{H}/pdf/print.js', f'{t}/b.html', f'{t}/b{off}.pdf')
        w = PdfWriter()
        for _ in range(start - 1):
            w.add_blank_page(595, 841)
        for p in PdfReader(f'{t}/b{off}.pdf').pages:
            w.add_page(a4(p))
        w.write(f'{t}/m0.pdf')
        skip = ','.join(str(i) for i in range(1, start))
        run('python3', '-I', f'{H}/header_phrase.py', f'{t}/m0.pdf', f'{t}/m1.pdf', PHRASE, '1', skip)
        run('python3', '-I', f'{H}/footer_text.py', f'{t}/m1.pdf', f'{t}/m2.pdf', FOOT, '1', skip)
        run('python3', '-I', f'{H}/footer_box.py', f'{t}/m2.pdf', f'{t}/m{off}.pdf', TOTAL, '1', skip)
        pages = PdfReader(f'{t}/m{off}.pdf').pages
        for tp, op in MAP.items():
            if tp - op == off:
                new[tp] = pages[tp - 1]
    out = PdfWriter()
    for i, p in enumerate(PdfReader(T).pages, 1):
        out.add_page(new.get(i, p))
    out.write(OUT)
print('ok', sorted(new))
