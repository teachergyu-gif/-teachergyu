# 수업용 교재 HWPX → PDF

1. `python3 hwpx2blocks.py <교재.hwpx> data/<이름>.blocks.json`
   — 본문·표·주석 상자·자동 번호·옛한글(한양 PUA → 유니코드)을 블록으로 추출 (`pip install lxml hypua2jamo`)
2. `FONT_DIR=<node_modules> NODE_PATH=<node_modules> python3 render.py data/<이름>.blocks.json <출력.pdf> "<표지 1행>" "<표지 2행>" "<부제>"`
   — RICH ACADEMY 디자인(brand/)으로 렌더링, 목차 쪽 번호는 2회 렌더링으로 채움
