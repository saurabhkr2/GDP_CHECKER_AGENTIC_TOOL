"""
Generates a formal 2-slide stakeholder deck for the DHF / GDP Checker
agentic system.

Slide 1: Problem statement
Slide 2: Solution architecture, technical flow, and benefits

Design intent: corporate, restrained palette (navy / grey / single accent),
clean typography, no emoji, generous whitespace.

Run from repo root:
    python architect_diagram/_build_2pager.py
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

OUT = Path(__file__).parent / "dhf_gdp_checker_2pager.pptx"

# --- Formal corporate palette ---
NAVY        = RGBColor(0x0B, 0x2A, 0x4A)
NAVY_DARK   = RGBColor(0x07, 0x1C, 0x33)
ACCENT      = RGBColor(0x00, 0x6C, 0xB5)
RULE        = RGBColor(0xD0, 0xD7, 0xE2)
BG          = RGBColor(0xFF, 0xFF, 0xFF)
PANEL       = RGBColor(0xF5, 0xF7, 0xFA)
TEXT        = RGBColor(0x1F, 0x2A, 0x37)
MUTED       = RGBColor(0x5B, 0x6B, 0x80)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def solid(shape, rgb, *, line=None, line_w=0.75):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)


def add_rect(slide, x, y, w, h, fill, *, rounded=False, radius=0.04,
             line=None, line_w=0.75):
    s = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        x, y, w, h)
    if rounded:
        s.adjustments[0] = radius
    solid(s, fill, line=line, line_w=line_w)
    return s


def add_text(slide, x, y, w, h, runs, *, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.08); tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.03); tf.margin_bottom = Inches(0.03)

    if runs and isinstance(runs[0], tuple):
        paragraphs = [runs]
    else:
        paragraphs = runs

    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for (txt, size, bold, color) in para:
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
            r.font.name = font
    return tb


def add_header(slide, title, subtitle, *, page_label):
    add_rect(slide, 0, 0, prs.slide_width, Inches(0.08), NAVY)
    add_text(slide, Inches(0.6), Inches(0.25), Inches(10.5), Inches(0.55),
             [(title, 24, True, NAVY)])
    add_text(slide, Inches(0.6), Inches(0.78), Inches(10.5), Inches(0.32),
             [(subtitle, 12, False, MUTED)])
    add_text(slide, Inches(11.2), Inches(0.32), Inches(1.7), Inches(0.3),
             [(page_label, 10, True, ACCENT)], align=PP_ALIGN.RIGHT)
    add_rect(slide, Inches(0.6), Inches(1.22), Inches(12.13), Emu(9525), RULE)


def add_footer(slide, page):
    add_rect(slide, Inches(0.6), Inches(7.12), Inches(12.13), Emu(9525), RULE)
    add_text(slide, Inches(0.6), Inches(7.18), Inches(8), Inches(0.22),
             [("DHF / GDP Checker  |  Agentic Document Quality Assurance",
               9, False, MUTED)])
    add_text(slide, Inches(11.0), Inches(7.18), Inches(1.7), Inches(0.22),
             [(f"Page {page} of 2", 9, False, MUTED)], align=PP_ALIGN.RIGHT)


def section_label(slide, x, y, w, text):
    add_rect(slide, x, y, Inches(0.35), Emu(22000), ACCENT)
    add_text(slide, x, y + Inches(0.05), w, Inches(0.3),
             [(text, 10, True, NAVY)])


# =============================================================================
# SLIDE 1 — Problem Statement
# =============================================================================
s1 = prs.slides.add_slide(BLANK)
add_rect(s1, 0, 0, prs.slide_width, prs.slide_height, BG)
add_header(
    s1,
    "Document Review Bottleneck in Regulated Engineering",
    "The case for an AI-assisted quality review process for DHF / GDP documents.",
    page_label="PROBLEM  |  1 of 2",
)

section_label(s1, Inches(0.6), Inches(1.45), Inches(6), "CONTEXT")
add_text(
    s1, Inches(0.6), Inches(1.80), Inches(12.1), Inches(0.85),
    [("Design History File (DHF) and Good Distribution Practice (GDP) documents must "
      "satisfy a fixed set of quality criteria before release. Today this review is "
      "performed manually by senior engineers, page by page. The process is slow, "
      "inconsistent across reviewers, and offers no structured audit trail — a material "
      "compliance and throughput risk for the organisation.",
      12, False, TEXT)],
)

section_label(s1, Inches(0.6), Inches(2.80), Inches(6), "KEY INDICATORS")
ind_y = Inches(3.15); ind_h = Inches(1.0); ind_w = Inches(2.95); gap = Inches(0.13)
indicators = [
    ("100+",     "Pages per DHF document"),
    ("21",       "Mandatory compliance checks"),
    ("4 – 8 h",  "Expert review time per file"),
    ("0 %",      "Tolerated AI-authored content without sign-off"),
]
ix = Inches(0.6)
for value, label in indicators:
    add_rect(s1, ix, ind_y, ind_w, ind_h, PANEL, line=RULE)
    add_rect(s1, ix, ind_y, Inches(0.06), ind_h, ACCENT)
    add_text(s1, ix + Inches(0.2), ind_y + Inches(0.12), ind_w - Inches(0.25), Inches(0.5),
             [(value, 22, True, NAVY)])
    add_text(s1, ix + Inches(0.2), ind_y + Inches(0.58), ind_w - Inches(0.25), Inches(0.4),
             [(label, 10, False, MUTED)])
    ix += ind_w + gap

panel_y = Inches(4.45); panel_h = Inches(2.55); panel_w = Inches(6.0)

def panel(slide, x, label, heading, items):
    add_rect(slide, x, panel_y, panel_w, panel_h, PANEL, line=RULE)
    add_rect(slide, x, panel_y, Inches(0.06), panel_h, NAVY)
    add_text(slide, x + Inches(0.25), panel_y + Inches(0.15),
             panel_w - Inches(0.4), Inches(0.3),
             [(label, 10, True, ACCENT)])
    add_text(slide, x + Inches(0.25), panel_y + Inches(0.42),
             panel_w - Inches(0.4), Inches(0.4),
             [(heading, 15, True, NAVY)])
    py = panel_y + Inches(0.95)
    for title, body in items:
        add_text(slide, x + Inches(0.25), py,
                 panel_w - Inches(0.4), Inches(0.28),
                 [(f"•  {title}", 11, True, NAVY)])
        add_text(slide, x + Inches(0.45), py + Inches(0.25),
                 panel_w - Inches(0.6), Inches(0.32),
                 [(body, 10, False, TEXT)])
        py += Inches(0.5)

panel(s1, Inches(0.6), "CURRENT STATE",
      "Manual review is slow, inconsistent, and opaque.",
      [
          ("Repetitive effort",
           "Reviewers re-apply the same 21 checks on every document."),
          ("Inconsistent verdicts",
           "Different reviewers produce different findings on identical content."),
          ("Limited audit trail",
           "Decisions live in email and tracked changes, not in a controlled record."),
      ])

panel(s1, Inches(6.73), "REQUIRED CAPABILITY",
      "AI-assisted review with mandatory human sign-off.",
      [
          ("Automated detection",
           "Deterministic rules and LLM checks identify findings in seconds."),
          ("Human-in-the-loop approval",
           "Every AI-authored comment is reviewed before it enters the document."),
          ("Traceable, resumable workflow",
           "Each session is checkpointed and produces a structured report."),
      ])

add_footer(s1, 1)


# =============================================================================
# SLIDE 2 — Solution: Architecture, Flow & Benefits
# =============================================================================
s2 = prs.slides.add_slide(BLANK)
add_rect(s2, 0, 0, prs.slide_width, prs.slide_height, BG)
add_header(
    s2,
    "Solution Architecture and Business Benefits",
    "An agentic, human-in-the-loop pipeline built on LangGraph and Azure OpenAI.",
    page_label="SOLUTION  |  2 of 2",
)

section_label(s2, Inches(0.6), Inches(1.45), Inches(6), "END-TO-END PROCESS FLOW")

nodes = [
    ("01", "Ingest",  "Upload DOCX and template through the web interface."),
    ("02", "Parse",   "Extract structure, headings and content via doc_loader."),
    ("03", "Analyse", "Run 21 checks (10 rule-based, 11 GPT-4) in parallel."),
    ("04", "Draft",   "Anchor findings to the nearest heading as draft comments."),
    ("05", "Review",  "Reviewer approves, edits or rejects each draft comment."),
    ("06", "Publish", "Emit reviewed DOCX with comments and a Markdown report."),
]
fy = Inches(1.85); fh = Inches(1.55); fw = Inches(1.95); gap = Inches(0.12)
fx = Inches(0.6)
for i, (num, title, body) in enumerate(nodes):
    add_rect(s2, fx, fy, fw, fh, PANEL, line=RULE)
    add_rect(s2, fx, fy, fw, Inches(0.32), NAVY)
    add_text(s2, fx + Inches(0.15), fy + Inches(0.03),
             Inches(0.6), Inches(0.28),
             [(num, 11, True, WHITE)])
    add_text(s2, fx + Inches(0.6), fy + Inches(0.03),
             fw - Inches(0.7), Inches(0.28),
             [(title.upper(), 11, True, WHITE)])
    add_text(s2, fx + Inches(0.18), fy + Inches(0.45),
             fw - Inches(0.35), fh - Inches(0.55),
             [(body, 10, False, TEXT)])
    if i < len(nodes) - 1:
        ax = fx + fw + Emu(20000)
        ay = fy + fh / 2 - Inches(0.08)
        arrow = s2.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                     ax, ay, gap - Emu(40000), Inches(0.16))
        solid(arrow, ACCENT)
    fx += fw + gap

hitl_x = Inches(0.6) + (fw + gap) * 4
add_text(s2, hitl_x, fy + fh + Inches(0.05), fw, Inches(0.3),
         [("Mandatory human approval gate", 9, True, ACCENT)],
         align=PP_ALIGN.CENTER)

section_label(s2, Inches(0.6), Inches(3.95), Inches(6), "ARCHITECTURE & TECHNOLOGY")

arch_y = Inches(4.30); arch_h = Inches(1.55); arch_w = Inches(6.0)

add_rect(s2, Inches(0.6), arch_y, arch_w, arch_h, PANEL, line=RULE)
add_text(s2, Inches(0.8), arch_y + Inches(0.12), arch_w - Inches(0.4), Inches(0.32),
         [("Agentic Pipeline (LangGraph)", 12, True, NAVY)])
arch_items = [
    "State machine: load → analyse → draft → review → publish",
    "Interrupt before review node; checkpointed via MemorySaver",
    "Flask REST API exposes draft comments and resume endpoints",
    "Production: Postgres checkpointer, Azure Blob, App Service",
]
ay = arch_y + Inches(0.5)
for it in arch_items:
    add_text(s2, Inches(0.8), ay, arch_w - Inches(0.4), Inches(0.26),
             [(f"•  {it}", 10, False, TEXT)])
    ay += Inches(0.24)

tx = Inches(6.73)
add_rect(s2, tx, arch_y, arch_w, arch_h, PANEL, line=RULE)
add_text(s2, tx + Inches(0.2), arch_y + Inches(0.12), arch_w - Inches(0.4), Inches(0.32),
         [("Technology Stack", 12, True, NAVY)])

stack = [
    ("Orchestration",      "LangGraph state machine with checkpointer"),
    ("Language model",     "Azure OpenAI GPT-4 (primary + secondary)"),
    ("Backend",            "Python 3.x, Flask REST, python-docx"),
    ("Frontend",           "HTML, CSS, Vanilla JavaScript (ES6+)"),
    ("Hosting & security", "Azure App Service, Key Vault, Managed Identity"),
]
ry = arch_y + Inches(0.5)
for k, v in stack:
    add_text(s2, tx + Inches(0.2), ry, Inches(1.85), Inches(0.24),
             [(k, 10, True, NAVY)])
    add_text(s2, tx + Inches(2.1), ry, arch_w - Inches(2.3), Inches(0.24),
             [(v, 10, False, TEXT)])
    ry += Inches(0.22)

section_label(s2, Inches(0.6), Inches(6.0), Inches(6), "BUSINESS BENEFITS")

benefits = [
    ("Faster review cycles",
     "Reduces expert review from hours to minutes per document."),
    ("Compliance assurance",
     "No AI-authored content is published without explicit reviewer approval."),
    ("Consistent quality",
     "The same 21 checks are applied identically to every document."),
    ("Auditability",
     "Every session is checkpointed and produces a structured report."),
]
by = Inches(6.35); bh = Inches(0.7); bw = Inches(3.0)
bx = Inches(0.6)
for title, body in benefits:
    add_rect(s2, bx, by, bw, bh, PANEL, line=RULE)
    add_rect(s2, bx, by, Inches(0.06), bh, ACCENT)
    add_text(s2, bx + Inches(0.18), by + Inches(0.06),
             bw - Inches(0.25), Inches(0.3),
             [(title, 11, True, NAVY)])
    add_text(s2, bx + Inches(0.18), by + Inches(0.32),
             bw - Inches(0.25), Inches(0.36),
             [(body, 9, False, MUTED)])
    bx += bw + Inches(0.07)

add_footer(s2, 2)


prs.save(OUT)
print(f"Wrote: {OUT}")
