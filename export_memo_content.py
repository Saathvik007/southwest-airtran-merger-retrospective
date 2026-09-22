"""Serialize the memo's flowable story to JSON so the .docx build cannot drift from the PDF.

Both documents are generated from one content model, which is itself generated
from the result JSON, so a rerun of the analysis updates the PDF and the Word
file together.
"""
from pathlib import Path
import json
import os
import tempfile

os.environ.setdefault("AIRLINE_MEMO_OUTPUT", str(Path(tempfile.gettempdir()) / "_memo_probe.pdf"))
import build_airline_case_quarterly_pdf as memo  # noqa: E402  (builds STORY_SNAPSHOT on import)

from reportlab.graphics import renderPDF  # noqa: E402
from reportlab.graphics.shapes import Drawing  # noqa: E402
from reportlab.platypus import Paragraph, Table, PageBreak, Spacer, KeepTogether  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "memo_docx_build"
OUT.mkdir(exist_ok=True)


def render_drawing_png(drawing, png_path, dpi=300):
    """Rasterize via PDF; the renderPM C/cairo backends are not available here."""
    import subprocess
    from reportlab.pdfgen import canvas as pdfcanvas
    tmp_pdf = OUT / "_chart.pdf"
    c = pdfcanvas.Canvas(str(tmp_pdf), pagesize=(drawing.width, drawing.height))
    renderPDF.draw(drawing, c, 0, 0)
    c.showPage()
    c.save()
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
                    str(tmp_pdf), str(png_path.with_suffix(""))], check=True)
    tmp_pdf.unlink()


def cell_text(cell):
    """Recover the source string from a table cell.

    reportlab normalizes a flowable cell into a one-element list during layout,
    so the Paragraph is usually nested rather than bare.
    """
    if isinstance(cell, Paragraph):
        return cell.text
    if isinstance(cell, (list, tuple)):
        return "".join(cell_text(c) for c in cell)
    return "" if cell is None else str(cell)


def walk(flowables, items):
    for f in flowables:
        if isinstance(f, KeepTogether):
            inner = []
            walk(f._content, inner)
            if inner:
                inner[0]["keep_with_next"] = True
            items.extend(inner)
        elif isinstance(f, Paragraph):
            items.append({"kind": "paragraph", "style": f.style.name, "text": f.text})
        elif isinstance(f, Table):
            rows = [[cell_text(c) for c in row] for row in f._cellvalues]
            widths = [w / 72.0 for w in f._colWidths]
            items.append({"kind": "table", "rows": rows, "widths_inches": widths})
        elif isinstance(f, Drawing):
            png = OUT / "chart.png"
            render_drawing_png(f, png)
            items.append({"kind": "image", "path": png.name,
                          "width_inches": f.width / 72.0, "height_inches": f.height / 72.0})
        elif isinstance(f, PageBreak):
            items.append({"kind": "page_break"})
        elif isinstance(f, Spacer):
            items.append({"kind": "spacer", "height_points": f.height})
    return items


content = walk(memo.STORY_SNAPSHOT, [])
(OUT / "memo_content.json").write_text(json.dumps(content, indent=1))
counts = {}
for item in content:
    counts[item["kind"]] = counts.get(item["kind"], 0) + 1
print(json.dumps(counts, indent=1))
