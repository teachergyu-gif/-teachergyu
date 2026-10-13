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

# 한컴 private-use symbols that have a standard equivalent
PUA = {"\U000f0854": "『", "\U000f0855": "』", "\U000f02eb": "口"}


def fix_pua(t):
    for k, v in PUA.items():
        t = t.replace(k, v)
    return t


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
        self.lines = [None]  # thick borders / diagonals drawn on purpose (e.g. pitch contours over syllables)
        for bf in di.iter("BorderFill"):
            fc = bf.find("FillColorPattern")
            col = fc.get("background-color") if fc is not None else None
            self.fills.append(col.lower() if col and col.lower() not in ("#ffffff", "none") else None)
            sides = {}
            for bd in bf.findall("Border"):
                w = float((bd.get("width") or "0mm").replace("mm", "") or 0)
                sides[bd.get("attribute-name")] = bd.get("stroke-type") not in (None, "none") and w >= 0.3
            slash = bf.get("slash", "0") != "0" and sides.get("diagonal")
            bslash = bf.get("backslash", "0") != "0" and sides.get("diagonal")
            if any(sides.get(k) for k in ("left", "right", "top", "bottom")) or slash or bslash:
                self.lines.append({"l": sides.get("left", False), "r": sides.get("right", False), "t": sides.get("top", False),
                                   "b": sides.get("bottom", False), "slash": bool(slash), "bslash": bool(bslash)})
            else:
                self.lines.append(None)
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
                t = fix_pua(hypua2jamo.translate(node.text or ""))
            elif node.tag == "TCPSControl":  # 글자 겹치기 (circled letter)
                s = node.get("textlength") or ""
                if "◯" in s or "○" in s:
                    out.append({"text": s.replace("◯", "").replace("○", ""), "circle": True})
                elif set(s) == {"□", "V"}:
                    out.append({"text": "☑"})
                else:  # e.g. 'ㅗ' with a breve (반모음 ㅗ̆): base letter with a small mark above it
                    out.append({"text": s[0], "overlay": s[1:]})
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

    def textbox(self, g):
        """Text box drawn as a shape: returned as a one-cell table so it renders like a box."""
        tl = g.find(".//TextboxParagraphList")
        if tl is None:
            return None
        paras = self.cell_paras(tl)
        return [[{"paras": paras, "cs": 1, "rs": 1, "fill": None}]] if paras else None

    def cell_paras(self, cell):
        out = []
        for p in cell.findall("Paragraph"):
            r = self.runs(p)
            inner = [self.table(t) for t in self._objects(p, "TableControl") if self._inline_box_text(t) is None]
            imgs = []
            for g in p.iter("GShapeObjectControl"):
                if not self._direct(g, p):
                    continue
                for sp in g.iter("ShapePicture"):
                    fn = self.picture(sp)
                    if fn:
                        imgs.append({"src": fn, "w": self.shape_width(sp, g)})
                tb = self.textbox(g)
                if tb:
                    inner.append(tb)
            if "".join(x["text"] for x in r).strip() or inner or imgs:
                out.append({"runs": r, "align": self.paras.get(p.get("parashape-id"), "justify"), "tables": inner, "imgs": imgs})
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
                            "fill": self.fills[int(td.get("borderfill-id", 0))] if int(td.get("borderfill-id", 0)) < len(self.fills) else None,
                            "lines": self.lines[int(td.get("borderfill-id", 0))] if int(td.get("borderfill-id", 0)) < len(self.lines) else None})
            rows.append(row)
        return rows

    @staticmethod
    def shape_width(sp, ctrl):
        """Printed width in mm (HWPUNIT = 1/7200 inch); a picture inside a group uses its own component width."""
        comp = sp.getparent()
        w = int(comp.get("width", 0)) if comp is not None and comp.tag == "ShapeComponent" and comp.get("width") else 0
        if not w or len(list(ctrl.iter("ShapePicture"))) == 1:
            w = int(ctrl.get("width", 0)) or w
        return round(w * 25.4 / 7200, 1)

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
                        # a shape may be a picture, a text box, or a group holding several of both
                        pics = list(o.iter("ShapePicture"))
                        has_text = any("".join(t.text or "" for t in tl.iter("Text")).strip() for tl in o.iter("TextboxParagraphList"))
                        for sp in ([] if has_text else pics):  # a picture grouped under a text box is only its paper background
                            fn = self.picture(sp)
                            if fn:
                                inline.append({"t": "img", "src": fn, "w": self.shape_width(sp, o)})
                        if pics and len(list(o.iter("TextboxParagraphList"))) > 0:
                            for tl in o.iter("TextboxParagraphList"):
                                paras = self.cell_paras(tl)
                                if paras:
                                    inline.append({"t": "box", "paras": paras})
                            continue
                        if pics:
                            continue
                        txt = "".join(hypua2jamo.translate(t.text or "") for t in o.iter("Text")).strip()
                        if not txt or txt in SKIP or txt.isdigit():
                            continue
                        tb = self.textbox(o)
                        if len(txt) <= 30 and tb and len(tb[0][0]["paras"]) == 1:
                            inline.append({"t": "heading", "text": txt})
                        elif tb:
                            inline.append({"t": "box", "paras": tb[0][0]["paras"]})
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
