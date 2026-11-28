"""납품 전 확인: 데이터의 모든 문장이 PDF에 그대로 있는지, 지운 항목이 남지 않았는지, 목차 쪽 번호가 맞는지"""
import re, sys, json, os
from pypdf import PdfReader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
norm = lambda t: re.sub(r'[\s\x01•–]+', '', t)
for src in ('data/busanwoe.txt', 'data/kukje.txt'):
    meta, items = build.parse(src)
    pdf = os.path.join(build.OUT, meta['file'] + '.pdf')
    pages = [norm(p.extract_text() or '') for p in PdfReader(pdf).pages]
    allt = ''.join(pages)
    miss = []
    for line in open(src, encoding='utf8'):
        t = line.strip()
        if not t or t.startswith('@meta'): continue
        t = re.sub(r'^@(section|sum|info|part|h|box) ', '', t)
        if t.startswith('@passage '): t = t[9:].split('|')[0]
        if t == '@endbox': continue
        t = re.sub(r'^(- |1\. )', '', t.lstrip())
        cells = [c for c in t.strip('|').split('|')] if t.startswith('|') else [t]
        for c in cells:
            c = norm(c)
            if c and c not in allt: miss.append(c[:40])
    bad = [w for w in ('출제포인트', '함정포인트', '설명하시면', '짚을수있습니다', '연결됩니다', '권합니다') if w in allt]
    pj = json.load(open(src + '.pages.json'))
    toc_ok = all(norm(it['title'])[:18] in pages[int(p) - 1] for it, p in zip(items, pj['pages'].values()))
    mixed = ('김T' in allt) if 'busanwoe' in src else any(w in allt for w in ('모의평가', '수능'))
    print(meta['file'], '누락', len(miss), miss[:5], '/ 지운 말 남음', bad, '/ 목차 쪽', toc_ok, '/ 섞임', mixed)
