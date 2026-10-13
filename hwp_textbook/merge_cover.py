"""Replace page 1 of a PDF with a separately printed cover page (no running footer), keeping shared fonts."""
import sys
from pypdf import PdfReader, PdfWriter

main, cover = sys.argv[1], sys.argv[2]
r, c = PdfReader(main), PdfReader(cover)
w = PdfWriter()
w.add_page(c.pages[0])
for p in r.pages[1:]:
    w.add_page(p)
w.compress_identical_objects()
with open(main, "wb") as f:
    w.write(f)
