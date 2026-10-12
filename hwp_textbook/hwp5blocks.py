"""HWP 5.0 textbook → flat list of semantic blocks (JSON), via `hwp5proc xml` (pyhwp).

Usage: hwp5proc xml in.hwp > in.xml;  python3 hwp5blocks.py in.xml in.hwp out.blocks.json img_dir/
Blocks, in reading order (same vocabulary as textbook/hwpx2blocks.py):
  {"t": "heading", "text"}              text inside drawn rectangles / text boxes
  {"t": "para", "runs": [...], "align"} runs: {"text", "b", "u", "color", "shade", "circle"}
  {"t": "box", "paras": [...]}          1x1 table
  {"t": "table", "rows": [[{"paras", "cs", "rs", "fill"}]]}
  {"t": "img", "src"}                   embedded picture (written to img_dir/)
  {"t": "pagebreak"}                    hard page break in the source
"""
import json, os, sys
import olefile, zlib
from lxml import etree
import hypua2jamo

SKIP = {"MEMO", "제1교시", "이재규T", "RICH ACADEMY"}


class Doc:
    def __init__(self, xml_path, hwp_path, img_dir):
        self.root = etree.parse(xml_path).getroot()
        di = self.root.find("DocInfo")
        self.chars = []
        for c in di.iter("CharShape"):
            self.chars.append({
                "b": c.get("bold") == "1",
                "u": c.get("underline") == "underline",  # pyhwp reports a bogus line_through (style 15) on plain text
                "color": (c.get("text-color") or "#000000").lower(),
                "shade": (c.get("shade-color") or "#ffffff").lower(),
            })
        self.fills = [None]  # borderfill ids are 1-based
        for bf in di.iter("BorderFill"):
            fc = bf.find("FillColorPattern")
            col = fc.get("background-color") if fc is not None else None
            self.fills.append(col.lower() if col and col.lower() not in ("#ffffff", "none") else None)
        self.paras, self.heads = {}, {}
        for i, p in enumerate(di.iter("ParaShape")):
            self.paras[str(i)] = p.get("align") or "justify"
            self.heads[str(i)] = (p.get("head-shape"), p.get("numbering-bullet-id"))
        self.counters = {}
        self.img_dir = img_dir
        os.makedirs(img_dir, exist_ok=True)
        self.bins = {}
        ole = olefile.OleFileIO(hwp_path)
        for e in ole.listdir():
            if e[0] == "BinData":
                name = e[1]
                data = ole.openstream(e).read()
                try:
                    data = zlib.decompress(data, -15)
                except zlib.error:
                    pass
                idx = int(name[3:7], 16)
                self.bins[idx] = (name, data)

    # ---------- text ----------
    def runs(self, p):
        out = []
        for node in p.iter("Text", "ControlChar", "TCPSControl", "TableControl"):
            if node.tag == "TableControl":
                if self._direct(node, p) and self._inline_box_text(node) is not None:
                    out.append({"text": self._inline_box_text(node), "boxed": True})
                continue
            if self._inside_object(node, p):
                continue
            cs = self.chars[int(node.get("charshape-id", 0))] if node.get("charshape-id") else {}
            if node.tag == "Text":
                t = hypua2jamo.translate(node.text or "")
            elif node.tag == "TCPSControl":  # 글자 겹치기 (circled letter)
                s = node.get("textlength") or ""
                out.append({"text": s.replace("◯", "").replace("○", ""), "circle": True})
                continue
            else:
                name = node.get("name")
                t = {"LINE_BREAK": "\n", "FIXWIDTH_SPACE": " ", "NONBREAK_SPACE": " ", "TAB": "  "}.get(name, "")
            if t:
                if out and all(out[-1].get(k) == cs.get(k) for k in ("b", "u", "color", "shade")) and not out[-1].get("circle"):
                    out[-1]["text"] += t
                else:
                    out.append({"text": t, **cs})
        return out

    @staticmethod
    def _inside_object(node, p):
        """True when node belongs to a nested table/textbox, not to paragraph p itself."""
        a = node.getparent()
        while a is not None and a is not p:
            if a.tag in ("TableControl", "GShapeObjectControl", "TextboxParagraphList"):
                return True
            a = a.getparent()
        return False

    def _inline_box_text(self, tc):
        """A one-cell table that sits inside a line of text (e.g. a boxed phrase in a question stem)."""
        if tc.get("inline") != "1":
            return None
        rows = tc.find("TableBody").findall("TableRow")
        if len(rows) != 1 or len(rows[0].findall("TableCell")) != 1:
            return None
        cell = rows[0].find("TableCell")
        ps = cell.findall("Paragraph")
        txt = "".join(hypua2jamo.translate(t.text or "") for t in cell.iter("Text")).strip()
        if len(ps) != 1 or not txt or len(txt) > 20 or cell.find(".//TableControl") is not None:
            return None
        # only when the paragraph also has its own text (otherwise it is a stand-alone box)
        par = tc
        while par is not None and par.tag != "Paragraph":
            par = par.getparent()
        own = "".join(t.text or "" for t in par.iter("Text") if not self._inside_object(t, par)).strip()
        return txt if own else None

    def cell_paras(self, cell):
        out = []
        for p in cell.findall("Paragraph"):
            r = self.runs(p)
            inner = [self.table(t) for t in self._objects(p, "TableControl")]
            if "".join(x["text"] for x in r).strip() or inner:
                out.append({"runs": r, "align": self.paras.get(p.get("parashape-id"), "justify"), "tables": inner})
        return out

    def _objects(self, p, tag):
        return [o for o in p.iter(tag) if not self._inside_object(o, p) or o.getparent() is not None and self._direct(o, p)]

    @staticmethod
    def _direct(o, p):
        a = o.getparent()
        while a is not None and a is not p:
            if a.tag in ("TableControl", "GShapeObjectControl", "TextboxParagraphList") and a is not o:
                return False
            a = a.getparent()
        return True

    def table(self, tc):
        rows = []
        for tr in tc.find("TableBody").findall("TableRow"):
            row = []
            for td in tr.findall("TableCell"):
                row.append({"paras": self.cell_paras(td), "cs": int(td.get("colspan", 1)), "rs": int(td.get("rowspan", 1)),
                            "fill": self.fills[int(td.get("borderfill-id", 0))] if int(td.get("borderfill-id", 0)) < len(self.fills) else None})
            rows.append(row)
        return rows

    def picture(self, sp):
        pi = sp.find(".//PictureInfo")
        idx = int(pi.get("bindata-id"))
        if idx not in self.bins:
            return None
        name, data = self.bins[idx]
        ext = name.split(".")[-1].lower()
        fn = f"img{idx:02d}.{ 'png' if ext == 'bmp' else ext }"
        path = os.path.join(self.img_dir, fn)
        if ext == "bmp":
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
                f.write(data)
            subprocess.run(["convert", f.name, path], check=True)
            os.unlink(f.name)
        else:
            open(path, "wb").write(data)
        return fn

    # ---------- blocks ----------
    def blocks(self):
        out = []
        sec = self.root.find("BodyText/SectionDef")
        for cs in sec.findall("ColumnSet"):
            for p in cs.findall("Paragraph"):
                if p.get("new-page") == "1" and out:
                    out.append({"t": "pagebreak"})
                inline = []
                for o in p.iter("TableControl", "GShapeObjectControl"):
                    if not self._direct(o, p):
                        continue
                    if o.tag == "TableControl":
                        if self._inline_box_text(o) is not None:
                            continue  # rendered inside the paragraph text
                        rows = self.table(o)
                        if len(rows) == 1 and len(rows[0]) == 1:
                            inline.append({"t": "box", "paras": rows[0][0]["paras"]})
                        else:
                            inline.append({"t": "table", "rows": rows})
                    else:
                        sp = o.find(".//ShapePicture")
                        if sp is not None:
                            fn = self.picture(sp)
                            if fn:
                                inline.append({"t": "img", "src": fn, "w": int(o.get("width", 0))})
                            continue
                        txt = "".join(hypua2jamo.translate(t.text or "") for t in o.iter("Text")).strip()
                        if txt and txt not in SKIP and not txt.isdigit():
                            inline.append({"t": "heading", "text": txt})
                r = self.runs(p)
                shape, nid = self.heads.get(p.get("parashape-id"), (None, None))
                num = None
                if shape == "number":  # 문단 번호 (auto-numbered questions): one running counter per numbering id
                    self.counters[nid] = self.counters.get(nid, 0) + 1
                    num = f"{self.counters[nid]}."
                elif shape == "bullet":
                    num = "•"
                if "".join(x["text"] for x in r).strip() or num:
                    out.append({"t": "para", "runs": r, "num": num, "align": self.paras.get(p.get("parashape-id"), "justify")})
                out.extend(inline)
        return out


if __name__ == "__main__":
    d = Doc(sys.argv[1], sys.argv[2], sys.argv[4])
    b = d.blocks()
    json.dump(b, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(x["t"] for x in b))
