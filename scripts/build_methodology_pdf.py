"""
Build docs/methodology.pdf from docs/METHODOLOGY.md using ReportLab.

We don't depend on pandoc / wkhtmltopdf so this script can run anywhere
ReportLab is installed. It's a pragmatic Markdown subset (headings,
paragraphs, lists, code blocks, tables, blockquotes) — enough for the
methodology doc, not a full Markdown renderer.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

ROOT = Path(__file__).parent.parent
SRC = ROOT / "docs" / "METHODOLOGY.md"
OUT = ROOT / "docs" / "methodology.pdf"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="DocTitle", parent=styles["Title"],
    fontSize=22, leading=26, spaceAfter=8, textColor=colors.HexColor("#0b8a5e"),
))
styles.add(ParagraphStyle(
    name="DocSubtitle", parent=styles["Italic"],
    fontSize=11, leading=14, spaceAfter=18, textColor=colors.HexColor("#555"),
))
styles.add(ParagraphStyle(
    name="H1", parent=styles["Heading1"],
    fontSize=16, leading=20, spaceBefore=18, spaceAfter=8,
    textColor=colors.HexColor("#0b8a5e"),
))
styles.add(ParagraphStyle(
    name="H2", parent=styles["Heading2"],
    fontSize=13, leading=17, spaceBefore=14, spaceAfter=6,
    textColor=colors.HexColor("#1d2230"),
))
styles.add(ParagraphStyle(
    name="H3", parent=styles["Heading3"],
    fontSize=11, leading=14, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor("#1d2230"),
))
styles.add(ParagraphStyle(
    name="Body", parent=styles["BodyText"],
    fontSize=10, leading=14, spaceAfter=6, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="BulletItem", parent=styles["BodyText"],
    fontSize=10, leading=14, leftIndent=14, bulletIndent=4, spaceAfter=2,
))
styles.add(ParagraphStyle(
    name="CodeBlock", parent=styles["BodyText"],
    fontName="Courier", fontSize=8.5, leading=11,
    backColor=colors.HexColor("#f1f5f4"),
    borderPadding=6, spaceAfter=8,
    textColor=colors.HexColor("#1d2230"),
))
styles.add(ParagraphStyle(
    name="Quote", parent=styles["BodyText"],
    fontSize=10, leading=14, leftIndent=14, spaceAfter=8,
    textColor=colors.HexColor("#3a3f4f"),
    backColor=colors.HexColor("#fafbfa"),
    borderPadding=8,
    italic=True,
))


# ---------------------------------------------------------------------------
# Inline-formatting (bold / italic / code) → ReportLab paragraph markup
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _inline(text: str) -> str:
    """Convert markdown inline syntax into reportlab paragraph markup.

    ReportLab supports a subset of HTML tags inside paragraphs.
    """
    text = _escape(text)
    # Code spans
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" backColor="#eef2ee">\1</font>', text)
    # Bold then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    # Markdown links [text](url) -> <link>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#0b8a5e">\1</link>', text)
    return text


# ---------------------------------------------------------------------------
# Block parser
# ---------------------------------------------------------------------------

def _parse_table(lines: list[str], i: int):
    """Parse a Markdown pipe table starting at lines[i].

    Returns (Table flowable, new_i).
    """
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(lines[i].strip().strip("|"))
        i += 1
    if len(rows) < 2:
        return None, i
    # Drop the alignment row (---|---)
    cleaned = [rows[0]] + [r for r in rows[1:] if not re.match(r"^[\s|:-]+$", r)]
    parsed = [[c.strip() for c in r.split("|")] for r in cleaned]
    width = max(len(r) for r in parsed)
    parsed = [r + [""] * (width - len(r)) for r in parsed]

    flow = []
    for row in parsed:
        flow.append([Paragraph(_inline(c), styles["Body"]) for c in row])

    page_w = LETTER[0] - 1.4 * inch  # margins
    col_w = page_w / width
    tbl = Table(flow, colWidths=[col_w] * width, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f4")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#0b8a5e")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#dbe0e0")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#fafbfa")]),
    ]))
    return tbl, i


def md_to_flowables(md: str) -> list:
    lines = md.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Page break sentinel
        if stripped == "---":
            out.append(Spacer(1, 6))
            i += 1
            continue

        # Code fence
        if stripped.startswith("```"):
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            text = _escape("\n".join(block)).replace(" ", "&nbsp;").replace("\n", "<br/>")
            out.append(Paragraph(text, styles["Code"]))
            continue

        # Tables
        if stripped.startswith("|") and "|" in stripped[1:]:
            tbl, i = _parse_table(lines, i)
            if tbl is not None:
                out.append(tbl)
                out.append(Spacer(1, 6))
                continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            depth = len(m.group(1))
            title = _inline(m.group(2))
            if depth == 1:
                if i == 0:
                    out.append(Paragraph(title, styles["DocTitle"]))
                else:
                    out.append(PageBreak())
                    out.append(Paragraph(title, styles["H1"]))
            elif depth == 2:
                out.append(Paragraph(title, styles["H1"]))
            elif depth == 3:
                out.append(Paragraph(title, styles["H2"]))
            else:
                out.append(Paragraph(title, styles["H3"]))
            i += 1
            continue

        # Block-quote
        if stripped.startswith(">"):
            block = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").lstrip())
                i += 1
            out.append(Paragraph(_inline(" ".join(block)), styles["Quote"]))
            continue

        # Bulleted list
        if re.match(r"^\s*[-*]\s+", line):
            block = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                block.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            for item in block:
                out.append(Paragraph(_inline(item), styles["BulletItem"], bulletText="•"))
            out.append(Spacer(1, 4))
            continue

        # Numbered list
        if re.match(r"^\s*\d+\.\s+", line):
            block = []
            n_idx = 1
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                content = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                block.append((n_idx, content))
                n_idx += 1
                i += 1
            for idx, item in block:
                out.append(Paragraph(_inline(item), styles["BulletItem"],
                                     bulletText=f"{idx}."))
            out.append(Spacer(1, 4))
            continue

        # Blank
        if not stripped:
            i += 1
            continue

        # Paragraph (collect until blank)
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|>|\s*[-*]\s|\s*\d+\.\s|\|.*\||```)", lines[i]):
            para.append(lines[i])
            i += 1
        joined = " ".join(p.strip() for p in para)
        out.append(Paragraph(_inline(joined), styles["Body"]))

    return out


def main():
    md = SRC.read_text()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        topMargin=0.7 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        title="Hospital Medicine Demand Forecasting — Methodology",
        author="Hamza Nadeem · FAST NUCES",
    )
    story = md_to_flowables(md)
    doc.build(story)
    print(f"Wrote {OUT} ({OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
