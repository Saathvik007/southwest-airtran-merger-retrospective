/*
 * Build the Word version of the case memo from the same content model the PDF uses.
 *
 * Run `python export_memo_content.py` first; it writes memo_docx_build/memo_content.json
 * and memo_docx_build/chart.png from the reportlab story, so the two documents cannot
 * drift apart and both trace back to the result JSON.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ExternalHyperlink, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  AlignmentType, HeadingLevel, PageBreak, Footer, PageNumber,
  LevelFormat, convertInchesToTwip,
} = require("docx");

const HERE = __dirname;
const BUILD = path.join(HERE, "memo_docx_build");
const content = JSON.parse(fs.readFileSync(path.join(BUILD, "memo_content.json"), "utf8"));
const OUT = process.env.AIRLINE_MEMO_DOCX || path.join(HERE, "Airline_Merger_Expert_Style_Memo.docx");

const NAVY = "18344D";
const GRAY = "56616B";
const LIGHT = "D9E3E9";
const ZEBRA = "F5F8FA";

/* ---- inline markup -------------------------------------------------------
   The source strings carry reportlab's mini-markup: <b>, <i>, <link href>,
   plus XML entities. Turn that into docx runs rather than dropping it.        */
function decode(s) {
  return s
    .replace(/&#8226;\s*/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ");
}

function inlineRuns(text, base) {
  const tokens = [];
  const re = /<b>(.*?)<\/b>|<i>(.*?)<\/i>|<link href='([^']*)'>(.*?)<\/link>/gs;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) tokens.push({ text: text.slice(last, m.index) });
    if (m[1] !== undefined) tokens.push({ text: m[1], bold: true });
    else if (m[2] !== undefined) tokens.push({ text: m[2], italics: true });
    else tokens.push({ text: m[4], link: m[3] });
    last = re.lastIndex;
  }
  if (last < text.length) tokens.push({ text: text.slice(last) });

  const out = [];
  for (const t of tokens) {
    const value = decode(t.text);
    if (!value) continue;
    const run = new TextRun({ ...base, text: value, bold: t.bold || base.bold, italics: t.italics });
    if (t.link) {
      out.push(new ExternalHyperlink({
        children: [new TextRun({ ...base, text: value, style: "Hyperlink" })],
        link: t.link,
      }));
    } else {
      out.push(run);
    }
  }
  return out.length ? out : [new TextRun({ ...base, text: "" })];
}

/* ---- style map ----------------------------------------------------------- */
const STYLES = {
  TitleX: { size: 30, bold: true, color: NAVY, space: { before: 60, after: 120 } },
  DeckX: { size: 18, color: GRAY, space: { after: 240 } },
  SectionX: { size: 21, bold: true, color: NAVY, space: { before: 220, after: 100 } },
  BodyX: { size: 18, space: { after: 120 } },
  SmallX: { size: 15, color: GRAY, space: { after: 100 } },
  BulletX: { size: 17, space: { after: 80 } },
};

function paragraph(item) {
  const s = STYLES[item.style] || STYLES.BodyX;
  const base = { size: s.size, color: s.color, bold: s.bold, font: "Calibri" };
  const opts = {
    children: inlineRuns(item.text, base),
    spacing: { before: s.space.before || 0, after: s.space.after, line: 264 },
    keepNext: Boolean(item.keep_with_next),
  };
  if (item.style === "TitleX") opts.heading = HeadingLevel.HEADING_1;
  if (item.style === "SectionX") opts.heading = HeadingLevel.HEADING_2;
  if (item.style === "BulletX") {
    opts.numbering = { reference: "memo-bullets", level: 0 };
    opts.spacing = { after: 80, line: 264 };
  }
  return new Paragraph(opts);
}

function table(item) {
  const widths = item.widths_inches.map((w) => Math.round(w * 1440));
  const total = widths.reduce((a, b) => a + b, 0);
  const rows = item.rows.map((cells, r) => new TableRow({
    tableHeader: r === 0,
    children: cells.map((cell, c) => new TableCell({
      width: { size: widths[c], type: WidthType.DXA },
      shading: {
        type: ShadingType.CLEAR,
        fill: r === 0 ? NAVY : (r % 2 === 0 ? ZEBRA : "FFFFFF"),
        color: "auto",
      },
      margins: { top: 90, bottom: 90, left: 110, right: 110 },
      children: [new Paragraph({
        children: inlineRuns(cell, {
          size: 15,
          bold: r === 0,
          color: r === 0 ? "FFFFFF" : "000000",
          font: "Calibri",
        }),
        spacing: { after: 0, line: 240 },
      })],
    })),
  }));
  return new Table({
    columnWidths: widths,
    width: { size: total, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: LIGHT },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: LIGHT },
      left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: LIGHT },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    },
    rows,
  });
}

function image(item) {
  const png = fs.readFileSync(path.join(BUILD, item.path));
  const width = 7.0;
  const height = (item.height_inches / item.width_inches) * width;
  return new Paragraph({
    children: [new ImageRun({
      type: "png",
      data: png,
      transformation: { width: Math.round(width * 72), height: Math.round(height * 72) },
    })],
    spacing: { before: 60, after: 120 },
  });
}

const children = [];
for (const item of content) {
  if (item.kind === "paragraph") children.push(paragraph(item));
  else if (item.kind === "table") { children.push(table(item)); children.push(new Paragraph({ spacing: { after: 80 }, children: [] })); }
  else if (item.kind === "image") children.push(image(item));
  else if (item.kind === "page_break") children.push(new Paragraph({ children: [new PageBreak()] }));
  else if (item.kind === "spacer") children.push(new Paragraph({ spacing: { after: Math.round(item.height_points * 20) }, children: [] }));
}

const doc = new Document({
  creator: "Saathvik Maheshuni",
  lastModifiedBy: "Saathvik Maheshuni",
  title: "Southwest and AirTran: what the fare comparison actually measures",
  description: "Case study using BTS airline ticket data, 2007 Q1 to 2015 Q4.",
  numbering: {
    config: [{
      reference: "memo-bullets",
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.25), hanging: convertInchesToTwip(0.15) } } },
      }],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 850, right: 936, bottom: 1080, left: 936 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: LIGHT, space: 6 } },
          tabStops: [{ type: "right", position: 10368 }],
          children: [
            new TextRun({ text: "\t", size: 14 }),
            new TextRun({ children: [PageNumber.CURRENT], size: 14, color: GRAY, font: "Calibri" }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(OUT, buf.length, "bytes");
});
