"""Fill the official Apart template (template/apart_template.docx) with report_own_words.md.
Keeps the template's title block, author table, abstract box, footnote and styles."""
import re, io, sys, copy
import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches

SRC = io.open("report_own_words.md", encoding="utf-8").read()
OUT = sys.argv[1] if len(sys.argv) > 1 else "Detect-or-Degrade-Apart.docx"
d = docx.Document("template/apart_template.docx")
W = qn("w:t")

title = re.search(r"^# (.+)$", SRC, re.M).group(1)
author_line = re.search(r"^\*\*(.+?)\*\* — (.+)$", SRC, re.M)
author, affil = author_line.group(1), author_line.group(2)
abstract = SRC.split("## Abstract", 1)[1].split("\n## ", 1)[0].strip()

# --- title block ---------------------------------------------------------------
head = d.tables[0]
for p in head.rows[0].cells[0].paragraphs:
    if "PROJECT TITLE" in p.text:
        done = False
        for r in p.runs:
            if r.text.strip() and not done:
                r.text = title; done = True
            elif r.text.strip() and "PROJECT" in "".join(x.text for x in p.runs) and r._r.find(qn("w:footnoteReference")) is None:
                r.text = ""
cell = head.rows[1].cells[0]
authors_tbl, abstract_tbl = cell.tables
# author cells: empty all six placeholder cells; put the author above "With Apart Research"
inner = [tc for tc in authors_tbl._tbl.iter(qn("w:tc")) if tc.find(".//" + qn("w:tbl")) is None]
for tc in inner:
    txt = "".join(t.text or "" for t in tc.iter(W))
    if txt.startswith("Author name"):
        for t in tc.iter(W): t.text = ""
        for b in list(tc.iter(qn("w:br"))): b.getparent().remove(b)
# the "With / Apart Research" paragraph sits in the outer cell; put the author line above it
for pel in authors_tbl._tbl.iter(qn("w:p")):
    ptxt = "".join(t.text or "" for t in pel.iter(W))
    if ptxt.startswith("With") and "Apart" in ptxt:
        newp = copy.deepcopy(pel)
        for r in list(newp.iter(qn("w:r"))): r.getparent().remove(r)
        pel.addprevious(newp)
        np_ = docx.text.paragraph.Paragraph(newp, None)
        r = np_.add_run(author); r.bold = True
        r.add_break(); np_.add_run(affil); np_.add_run().add_break()
        break
# abstract box
ab_cell = abstract_tbl.rows[0].cells[0]
ps = ab_cell.paragraphs
ps[0].runs[0].text = abstract
for r in ps[0].runs[1:]: r.text = ""
for r in ps[0].runs: r.italic = False
for p in ps[1:]:
    for r in p.runs: r.text = ""

# --- drop the guidance body (everything after the title table, except sectPr) ----
body = d.element.body
kids = list(body.iterchildren())
start = kids.index(head._tbl) + 1
for el in kids[start:]:
    if el.tag != qn("w:sectPr"):
        body.remove(el)

# --- content -------------------------------------------------------------------
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
def add_runs(par, text, size=None, bold=False, italic=False):
    for part in INLINE.split(text):
        if not part: continue
        if part.startswith("**") and part.endswith("**"): r = par.add_run(part[2:-2]); r.bold = True
        elif part.startswith("*") and part.endswith("*"): r = par.add_run(part[1:-1]); r.italic = True
        elif part.startswith("`") and part.endswith("`"): r = par.add_run(part[1:-1]); r.font.name = "Consolas"
        else: r = par.add_run(part)
        if bold: r.bold = True
        if italic: r.italic = True
        if size: r.font.size = Pt(size)

def shade(c, fill):
    tcPr = c._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), fill); tcPr.append(s)

def set_borders(t):
    tblPr = t._tbl.tblPr; b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "999999")
        b.append(e)
    tblPr.append(b)

def add_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body_ = cells[0], cells[1:]
    t = d.add_table(rows=1 + len(body_), cols=len(header)); set_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; add_runs(c.paragraphs[0], h, size=9, bold=True); shade(c, "E8E8E8")
    for ri, row in enumerate(body_, 1):
        for ci in range(len(header)):
            add_runs(t.rows[ri].cells[ci].paragraphs[0], row[ci] if ci < len(row) else "", size=9)
    lens = [max(4, sum(len(x[ci]) if ci < len(x) else 0 for x in cells) / len(cells)) for ci in range(len(header))]
    widths = [6.5 * L / sum(lens) for L in lens]
    widths = [max(0.8, w) for w in widths]; s = 6.5 / sum(widths); widths = [w * s for w in widths]
    t.autofit = False
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", 20), ("bottom", 20), ("left", 70), ("right", 70)):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    t._tbl.tblPr.append(mar)
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for ci, w in enumerate(widths):
            row.cells[ci].width = Inches(w)
            for p in row.cells[ci].paragraphs:
                p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.line_spacing = 1.0

text = SRC.split("## 1. Introduction", 1)[1]
lines = ("## 1. Introduction" + text).splitlines()
para, kind = [], "normal"
def flush():
    global para, kind
    if para:
        p = d.add_paragraph()
        line = " ".join(x.strip() for x in para)
        cap = kind == "normal" and re.match(r"^\*(Figure|Table) [^*]+\*$", line)
        add_runs(p, line, size=9 if cap else None)
        p.paragraph_format.space_after = Pt(6)
        if kind == "list":
            p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(-0.2)
            p.paragraph_format.space_after = Pt(3)
        if cap:
            p.paragraph_format.space_after = Pt(10)
    para, kind = [], "normal"

i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("## "):
        flush(); d.add_paragraph(ln[3:].strip(), style="Heading 2")
    elif ln.startswith("### "):
        flush(); d.add_paragraph(ln[4:].strip(), style="Heading 3")
    elif re.fullmatch(r"\*\*(Limitations|Future Work|Dual use|Ethics|Post-hoc changes|Robustness)\*\*", ln.strip()):
        flush(); d.add_paragraph(ln.strip().strip("*"), style="Heading 3")
    elif ln.startswith("|"):
        flush(); block = []
        while i < len(lines) and lines[i].startswith("|"):
            if not re.match(r"^\|\s*:?-", lines[i]): block.append(lines[i])
            i += 1
        add_table(block); continue
    elif ln.startswith("!["):
        flush(); path = re.search(r"\((.+)\)", ln).group(1)
        width = 4.9 if "/" not in path.replace("figures/", "", 1) else 4.5
        d.add_picture(path, width=Inches(width))
        d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        d.paragraphs[-1].paragraph_format.keep_with_next = True
    elif ln.strip() == "":
        flush()
    elif re.match(r"^\d+\. ", ln):
        flush(); para = [ln]; kind = "list"
    elif ln.startswith("- "):
        flush(); para = ["• " + ln[2:]]; kind = "list"
    else:
        para.append(ln)
    i += 1
flush()
d.save(OUT); print("saved", OUT)
