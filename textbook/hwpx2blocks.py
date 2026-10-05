"""Extract an HWPX textbook into a flat list of semantic blocks (JSON).

Blocks, in document order:
  {"t": "heading", "text": ...}                         section title boxes (drawn rectangles)
  {"t": "label", "text": ...}                           small label boxes such as "정답"
  {"t": "para", "runs": [...], "num": "3.", "align": ..., "notes": [...]}
  {"t": "box", "paras": [...]}                          1x1 table placed inline (보기, passages, activity boxes)
  {"t": "table", "rows": [[{"paras": [...], "cs": n, "rs": n, "fill": "#..."}]]}
A run is {"text", "b", "u", "color", "shade"}; notes are floating 1x1 tables anchored to the paragraph.
Old Hangul stored in the Hanyang PUA range is converted to standard Unicode jamo.
"""
import json, re, sys, zipfile
from lxml import etree
import hypua2jamo

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
NS = {"hp": HP, "hh": HH}
SKIP_RECT = {"MEMO", "제1교시", "이재규T"}


def q(tag):
    return "{%s}%s" % (HP, tag)


class Doc:
    def __init__(self, path):
        z = zipfile.ZipFile(path)
        head = etree.fromstring(z.read("Contents/header.xml"))
        self.chars, self.paras, self.fills, self.numfmt = {}, {}, {}, {}
        for c in head.iter("{%s}charPr" % HH):
            ul = c.find("hh:underline", NS)
            self.chars[c.get("id")] = {
                "b": c.find("hh:bold", NS) is not None,
                "u": ul is not None and ul.get("type") not in (None, "NONE"),
                "color": (c.get("textColor") or "#000000").lower(),
                "shade": (c.get("shadeColor") or "none").lower(),
            }
        for p in head.iter("{%s}paraPr" % HH):
            hd = p.find("hh:heading", NS)
            al = p.find("hh:align", NS)
            self.paras[p.get("id")] = {
                "num": hd.get("idRef") if hd is not None and hd.get("type") == "NUMBER" else None,
                "align": al.get("horizontal") if al is not None else "JUSTIFY",
            }
        for n in head.iter("{%s}numbering" % HH):
            ph = n.find("hh:paraHead", NS)
            self.numfmt[n.get("id")] = (int(n.get("start") or 1), ph.text if ph is not None and ph.text else "^1.")
        for bf in head.iter("{%s}borderFill" % HH):
            wb = bf.find(".//{http://www.hancom.co.kr/hwpml/2011/core}winBrush")
            if wb is not None and wb.get("faceColor") not in (None, "none"):
                self.fills[bf.get("id")] = wb.get("faceColor").lower()
        self.counters = {}
        names = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n))
        self.sections = [etree.fromstring(z.read(n)) for n in names]

    # ---------- text ----------
    def runs_of(self, p):
        """Text runs of a paragraph, ignoring nested tables/rects (handled separately)."""
        out = []
        for run in p.findall("hp:run", NS):
            st = self.chars.get(run.get("charPrIDRef"), {})
            for t in run.findall("hp:t", NS):
                parts = [t.text or ""]
                for ch in t:
                    tag = etree.QName(ch).localname
                    if tag == "lineBreak":
                        parts.append("\n")
                    elif tag == "tab":
                        parts.append("  ")
                    elif tag in ("nbSpace", "fwSpace"):
                        parts.append(" ")
                    parts.append(ch.tail or "")
                text = hypua2jamo.translate("".join(parts))
                if text:
                    out.append({"text": text, **st})
        return out

    def number(self, p):
        pp = self.paras.get(p.get("paraPrIDRef"), {})
        nid = pp.get("num")
        if not nid:
            return None
        start, fmt = self.numfmt.get(nid, (1, "^1."))
        n = self.counters.get(nid, start - 1) + 1
        self.counters[nid] = n
        return re.sub(r"\^\d", str(n), fmt)

    def cell_paras(self, sub):
        out = []
        for p in sub.findall("hp:p", NS):
            runs = self.runs_of(p)
            inner = [self.table(t) for t in p.iter(q("tbl")) if t is not p]
            if runs or inner:
                out.append({"runs": runs, "align": self.paras.get(p.get("paraPrIDRef"), {}).get("align"), "tables": inner})
        return out

    def table(self, tbl):
        rows = []
        for tr in tbl.findall("hp:tr", NS):
            row = []
            for tc in tr.findall("hp:tc", NS):
                sp = tc.find("hp:cellSpan", NS)
                sub = tc.find("hp:subList", NS)
                row.append({
                    "paras": self.cell_paras(sub) if sub is not None else [],
                    "cs": int(sp.get("colSpan", 1)) if sp is not None else 1,
                    "rs": int(sp.get("rowSpan", 1)) if sp is not None else 1,
                    "fill": self.fills.get(tc.get("borderFillIDRef")),
                })
            rows.append(row)
        return rows

    # ---------- blocks ----------
    def blocks(self):
        out, pending_notes = [], []
        for sec in self.sections:
            for p in sec.findall("hp:p", NS):
                heads, inline, notes = [], [], []
                for run in p.findall("hp:run", NS):
                    for obj in run:
                        tag = etree.QName(obj).localname
                        if tag == "rect":
                            txt = hypua2jamo.translate("".join("".join(t.itertext()) for t in obj.iter(q("t")))).strip()
                            if txt and txt not in SKIP_RECT and not txt.isdigit():
                                heads.append(txt)
                        elif tag == "tbl":
                            pos = obj.find("hp:pos", NS)
                            floating = pos is not None and pos.get("treatAsChar") == "0"
                            rows = self.table(obj)
                            one = len(rows) == 1 and len(rows[0]) == 1
                            if floating and one:
                                notes.append({"paras": rows[0][0]["paras"], "x": int(pos.get("horzOffset", 0)), "y": int(pos.get("vertOffset", 0))})
                            elif one:
                                inline.append({"t": "box", "paras": rows[0][0]["paras"]})
                            else:
                                inline.append({"t": "table", "rows": rows})
                for h in heads:
                    out.append({"t": "label" if h == "정답" else "heading", "text": h})
                runs = self.runs_of(p)
                num = self.number(p)
                notes.sort(key=lambda n: (n["y"], n["x"]))
                if "".join(r["text"] for r in runs).strip() or num:
                    out.append({"t": "para", "runs": runs, "num": num,
                                "align": self.paras.get(p.get("paraPrIDRef"), {}).get("align"),
                                "notes": pending_notes + notes})
                    pending_notes = []
                else:
                    pending_notes += notes  # notes on an empty paragraph belong to the next line
                out.extend(inline)
        return out


if __name__ == "__main__":
    doc = Doc(sys.argv[1])
    blocks = doc.blocks()
    json.dump(blocks, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(b["t"] for b in blocks))
