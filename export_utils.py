"""
export_utils.py
───────────────
Converts the final_report string (Markdown) into PDF bytes
that Streamlit can serve via st.download_button.

PDF → reportlab (pure-Python, no system deps beyond `pip install reportlab`)
"""

from __future__ import annotations

import io
import re


# ── Markdown parser (minimal, enough for the writer's output) ─────────────────

def _parse_md(text: str) -> list[dict]:
    """
    Converts Markdown text into a simple list of block dicts:
      {"type": "h1"|"h2"|"h3"|"bullet"|"rule"|"paragraph", "text": str}
    """
    blocks = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("### "):
            blocks.append({"type": "h3", "text": stripped[4:]})
        elif stripped.startswith("## "):
            blocks.append({"type": "h2", "text": stripped[3:]})
        elif stripped.startswith("# "):
            blocks.append({"type": "h1", "text": stripped[2:]})
        elif re.match(r"^[-*] ", stripped):
            blocks.append({"type": "bullet", "text": stripped[2:]})
        elif stripped.startswith("===") or stripped.startswith("---"):
            blocks.append({"type": "rule", "text": ""})
        elif stripped == "":
            blocks.append({"type": "blank", "text": ""})
        else:
            blocks.append({"type": "paragraph", "text": stripped})
    return blocks


# ── PDF export ────────────────────────────────────────────────────────────────

def to_pdf(report: str) -> bytes:
    """Renders the Markdown report as a styled PDF using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )

    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontSize=18, spaceAfter=10, spaceBefore=16,
            textColor=colors.HexColor("#1a3c5e"),
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontSize=14, spaceAfter=8, spaceBefore=12,
            textColor=colors.HexColor("#2e5f8a"),
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"],
            fontSize=12, spaceAfter=6, spaceBefore=10,
            textColor=colors.HexColor("#3a7abd"),
        ),
        "paragraph": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10, spaceAfter=6, leading=14,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"],
            fontSize=10, spaceAfter=4, leading=14,
            leftIndent=20, bulletIndent=8,
        ),
    }

    def _safe(text: str) -> str:
        """Escape special ReportLab XML chars but preserve inline bold/italic."""
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Convert **bold** → <b>bold</b>
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Convert *italic* → <i>italic</i>
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        return text

    story = []
    for block in _parse_md(report):
        t = block["type"]
        txt = _safe(block["text"])

        if t == "h1":
            story.append(Paragraph(txt, styles["h1"]))
        elif t == "h2":
            story.append(Paragraph(txt, styles["h2"]))
        elif t == "h3":
            story.append(Paragraph(txt, styles["h3"]))
        elif t == "bullet":
            story.append(Paragraph(f"• {txt}", styles["bullet"]))
        elif t == "rule":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 4))
        elif t == "paragraph" and txt.strip():
            story.append(Paragraph(txt, styles["paragraph"]))
        elif t == "blank":
            story.append(Spacer(1, 6))

    doc.build(story)
    return buf.getvalue()