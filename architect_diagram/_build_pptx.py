"""
Generates architecture.pptx for the DHF / GDP Checker.
Run: python architect_diagram/_build_pptx.py
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

OUT = Path(__file__).parent / "architecture.pptx"

# --- Palette ---
AZURE_BLUE   = RGBColor(0x00, 0x78, 0xD4)
AZURE_DARK   = RGBColor(0x0B, 0x3D, 0x91)
AZURE_LIGHT  = RGBColor(0xEA, 0xF3, 0xFF)
PURPLE       = RGBColor(0x6A, 0x1B, 0x9A)
PURPLE_LIGHT = RGBColor(0xF3, 0xE5, 0xF5)
GREEN        = RGBColor(0x2E, 0x7D, 0x32)
GREEN_LIGHT  = RGBColor(0xE8, 0xF5, 0xE9)
ORANGE       = RGBColor(0xD7, 0x9B, 0x00)
ORANGE_LIGHT = RGBColor(0xFF, 0xF6, 0xE5)
RED          = RGBColor(0xFF, 0x6B, 0x6B)
GREY_TEXT    = RGBColor(0x33, 0x33, 0x33)
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)

BLANK = prs.slide_layouts[6]


def add_text(slide, x, y, w, h, text, *, size=14, bold=False, color=GREY_TEXT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = line
        r.font.size = Pt(size); r.font.bold = bold
        r.font.color.rgb = color
    return tb


def add_box(slide, x, y, w, h, text, *, fill=AZURE_BLUE, border=AZURE_DARK,
            text_color=WHITE, size=12, bold=True, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    s.line.color.rgb = border; s.line.width = Pt(1.25)
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = line
        r.font.size = Pt(size if i == 0 else max(size - 2, 9))
        r.font.bold = bold if i == 0 else False
        r.font.color.rgb = text_color
    return s


def add_arrow(slide, x1, y1, x2, y2, *, color=AZURE_DARK, weight=1.75,
              dashed=False, label=None):
    line = slide.shapes.add_connector(1, x1, y1, x2, y2)
    line.line.color.rgb = color
    line.line.width = Pt(weight)
    ln = line.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn('a:tailEnd'))
    tail.set('type', 'triangle'); tail.set('w', 'med'); tail.set('h', 'med')
    if dashed:
        prstDash = etree.SubElement(ln, qn('a:prstDash'))
        prstDash.set('val', 'dash')
    if label:
        mx = (x1 + x2) // 2; my = (y1 + y2) // 2
        add_text(slide, mx - Inches(0.5), my - Inches(0.15),
                 Inches(1.0), Inches(0.3),
                 label, size=9, color=color, align=PP_ALIGN.CENTER)
    return line


def slide_header(slide, title, subtitle=None):
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                  prs.slide_width, Inches(0.55))
    band.fill.solid(); band.fill.fore_color.rgb = AZURE_DARK
    band.line.fill.background()
    add_text(slide, Inches(0.3), Inches(0.05), Inches(13), Inches(0.45),
             title, size=22, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_text(slide, Inches(0.3), Inches(0.6), Inches(13), Inches(0.3),
                 subtitle, size=12, color=GREY_TEXT)


# ============================================================
# SLIDE 1 — Title
# ============================================================
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                        prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = AZURE_DARK; bg.line.fill.background()

add_text(s, Inches(0.5), Inches(2.4), Inches(12.3), Inches(1.0),
         "DHF / GDP Checker", size=48, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(3.4), Inches(12.3), Inches(0.6),
         "Production Technical Architecture on Microsoft Azure",
         size=24, color=AZURE_LIGHT, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(4.3), Inches(12.3), Inches(0.4),
         "FastAPI · LangGraph · Azure OpenAI (GPT-5.1) · PostgreSQL · Blob Storage",
         size=16, color=WHITE, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.4),
         "Architecture Overview · v2.0", size=12, color=AZURE_LIGHT, align=PP_ALIGN.CENTER)

# ============================================================
# SLIDE 2 — Goals & Principles
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "Goals & Architectural Principles")
bullets = [
    ("Regulated-domain compliance", "Every AI-suggested edit must be reviewed by a human before it lands in the DOCX (HITL)."),
    ("Deterministic + AI checks",   "10 regex checks (always-on) + 11 LLM checks (parallel) using Azure OpenAI GPT-5.1."),
    ("Stateful, resumable runs",    "LangGraph state machine with PostgreSQL checkpointer enables interrupt / resume."),
    ("Azure-native, managed-first", "PaaS only: Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, Monitor."),
    ("Secure by default",           "Entra ID SSO, Managed Identity, Private Endpoints, Key Vault, WAF via Front Door."),
    ("Observable",                  "Structured logs, OpenTelemetry traces, metrics → App Insights + Log Analytics."),
]
y = Inches(1.3)
for title, desc in bullets:
    add_box(s, Inches(0.5), y, Inches(3.0), Inches(0.7), title,
            fill=AZURE_BLUE, border=AZURE_DARK, text_color=WHITE, size=13)
    add_text(s, Inches(3.7), y + Inches(0.1), Inches(9.3), Inches(0.6),
             desc, size=13, color=GREY_TEXT)
    y += Inches(0.85)

# ============================================================
# SLIDE 3 — Logical Architecture
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "Logical Architecture — Azure",
             "User · Application Tier · Data, AI & Platform Services")

def lane(x, w, color, label):
    bgr = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, Inches(1.0), w, Inches(6.0))
    bgr.fill.solid(); bgr.fill.fore_color.rgb = color
    bgr.line.color.rgb = GREY_TEXT; bgr.line.width = Pt(0.5)
    add_text(s, x, Inches(1.05), w, Inches(0.3), label,
             size=12, bold=True, color=AZURE_DARK, align=PP_ALIGN.CENTER)

lane(Inches(0.3),  Inches(2.4), AZURE_LIGHT,  "User & Edge")
lane(Inches(2.8),  Inches(7.0), ORANGE_LIGHT, "Application Tier  (Azure Container Apps · VNet)")
lane(Inches(9.9),  Inches(3.1), GREEN_LIGHT,  "Data, AI & Platform")

user  = add_box(s, Inches(0.65), Inches(1.5), Inches(1.7), Inches(0.7),
                "Reviewer (Browser)", fill=WHITE, border=AZURE_DARK, text_color=AZURE_DARK)
entra = add_box(s, Inches(0.65), Inches(2.5), Inches(1.7), Inches(0.7),
                "Microsoft Entra ID\n(OIDC / SSO)", fill=AZURE_BLUE, border=AZURE_DARK, size=11)
afd   = add_box(s, Inches(0.65), Inches(3.5), Inches(1.7), Inches(0.7),
                "Azure Front Door\n+ WAF", fill=AZURE_BLUE, border=AZURE_DARK, size=11)
add_box(s, Inches(0.65), Inches(4.5), Inches(1.7), Inches(0.7),
        "Azure DNS", fill=AZURE_BLUE, border=AZURE_DARK, size=11)

swa = add_box(s, Inches(3.0),  Inches(1.5), Inches(2.0), Inches(0.7),
              "Azure Static Web Apps\n(Flask / React UI)", fill=AZURE_BLUE, border=AZURE_DARK, size=11)
api = add_box(s, Inches(5.3),  Inches(1.5), Inches(2.2), Inches(0.7),
              "FastAPI Service (Container App)\n/jobs · /review · /download",
              fill=AZURE_BLUE, border=AZURE_DARK, size=11)
acr = add_box(s, Inches(7.8),  Inches(1.5), Inches(1.8), Inches(0.7),
              "Azure Container Registry", fill=AZURE_BLUE, border=AZURE_DARK, size=11)

worker_bg = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                               Inches(3.0), Inches(2.6), Inches(6.6), Inches(2.7))
worker_bg.fill.solid(); worker_bg.fill.fore_color.rgb = PURPLE_LIGHT
worker_bg.line.color.rgb = PURPLE; worker_bg.line.width = Pt(1.5)
add_text(s, Inches(3.05), Inches(2.65), Inches(6.5), Inches(0.3),
         "LangGraph Orchestrator  (Container App · auto-scaled · KEDA)",
         size=12, bold=True, color=PURPLE)

nodes = [
    ("1. load_documents",                Inches(3.15), Inches(3.05)),
    ("2. run_checks\n10 regex + 11 LLM", Inches(4.55), Inches(3.05)),
    ("3. draft_comments",                Inches(5.95), Inches(3.05)),
    ("4. ⏸ HITL interrupt",               Inches(7.35), Inches(3.05)),
    ("5. apply_comments",                Inches(4.55), Inches(4.25)),
    ("6. save_output",                   Inches(5.95), Inches(4.25)),
]
node_shapes = []
for i, (txt, x, y) in enumerate(nodes):
    fill = RED if i == 3 else PURPLE
    node_shapes.append(add_box(s, x, y, Inches(1.3), Inches(0.9), txt,
                               fill=fill, border=PURPLE, text_color=WHITE, size=10))

def arr(a, b, **kw):
    add_arrow(s, a.left + a.width, a.top + a.height // 2,
                 b.left,           b.top + b.height // 2,
                 color=PURPLE, **kw)

arr(node_shapes[0], node_shapes[1])
arr(node_shapes[1], node_shapes[2])
arr(node_shapes[2], node_shapes[3])
add_arrow(s, node_shapes[3].left + node_shapes[3].width // 2,
              node_shapes[3].top + node_shapes[3].height,
              node_shapes[4].left + node_shapes[4].width // 2,
              node_shapes[4].top, color=PURPLE, dashed=True, label="resume")
arr(node_shapes[4], node_shapes[5])

cicd = add_box(s, Inches(7.8), Inches(2.4), Inches(1.8), Inches(0.55),
               "GitHub Actions\nCI/CD · Bicep IaC",
               fill=RGBColor(0x24, 0x29, 0x2E), border=RGBColor(0,0,0), size=10)

aoai = add_box(s, Inches(10.05), Inches(1.5), Inches(2.8), Inches(0.85),
               "Azure OpenAI\nGPT-5.1  (Private Endpoint)",
               fill=GREEN, border=GREEN, size=12)
blob = add_box(s, Inches(10.05), Inches(2.55), Inches(2.8), Inches(0.85),
               "Azure Blob Storage\nDOCX in/out · templates · reports",
               fill=GREEN, border=GREEN, size=11)
pg   = add_box(s, Inches(10.05), Inches(3.6), Inches(2.8), Inches(1.0),
               "Azure DB for PostgreSQL\nFlexible Server\njobs · findings · decisions · checkpoints",
               fill=GREEN, border=GREEN, size=11)
kv   = add_box(s, Inches(10.05), Inches(4.8), Inches(1.35), Inches(0.7),
               "Azure Key Vault", fill=GREEN, border=GREEN, size=10)
appi = add_box(s, Inches(11.5),  Inches(4.8), Inches(1.35), Inches(0.7),
               "App Insights\n+ Log Analytics", fill=GREEN, border=GREEN, size=10)

def edge(a, b, **kw):
    add_arrow(s,
              a.left + a.width, a.top + a.height // 2,
              b.left,           b.top + b.height // 2, **kw)

edge(user,  afd,   color=AZURE_DARK)
edge(user,  entra, color=AZURE_DARK, dashed=True)
edge(afd,   swa,   color=AZURE_DARK)
edge(swa,   api,   color=AZURE_DARK)
add_arrow(s, api.left + api.width // 2, api.top + api.height,
              node_shapes[0].left + node_shapes[0].width // 2, node_shapes[0].top,
              color=AZURE_DARK)
add_arrow(s, node_shapes[5].left + node_shapes[5].width,
              node_shapes[5].top + node_shapes[5].height // 2,
              blob.left, blob.top + blob.height // 2, color=GREEN)
add_arrow(s, node_shapes[1].left + node_shapes[1].width,
              node_shapes[1].top + node_shapes[1].height // 2,
              aoai.left, aoai.top + aoai.height // 2, color=GREEN)
add_arrow(s, node_shapes[3].left + node_shapes[3].width,
              node_shapes[3].top + node_shapes[3].height // 2,
              pg.left, pg.top + pg.height // 2, color=GREEN, dashed=True)
add_arrow(s, api.left + api.width, api.top + api.height // 2,
              pg.left, pg.top + Inches(0.2), color=GREEN, dashed=True)
add_arrow(s, api.left + api.width, api.top + api.height,
              kv.left, kv.top, color=PURPLE, dashed=True)
add_arrow(s, worker_bg.left + worker_bg.width,
              worker_bg.top + worker_bg.height,
              appi.left, appi.top, color=PURPLE, dashed=True)
edge(acr, api, color=GREY_TEXT, dashed=True)
add_arrow(s, cicd.left + cicd.width // 2, cicd.top,
              acr.left + acr.width // 2,   acr.top + acr.height,
              color=GREY_TEXT, dashed=True)

add_text(s, Inches(0.3), Inches(7.05), Inches(13), Inches(0.4),
         "Solid = data/request flow    Dashed = control / auth / telemetry    "
         "Purple block = LangGraph state machine    Green block = Azure managed data & platform",
         size=10, color=GREY_TEXT, align=PP_ALIGN.CENTER)

# ============================================================
# SLIDE 4 — Component responsibilities
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "Component Responsibilities")
rows = [
    ("Azure Static Web Apps", "Serves the Flask/React review UI; static asset CDN; Entra ID auth integration."),
    ("FastAPI Service (Container App)", "REST API: upload DOCX, list findings, accept/reject decisions, download annotated DOCX."),
    ("LangGraph Orchestrator (Container App)", "State machine: load_documents → run_checks → draft_comments → HITL interrupt → apply_comments → save_output."),
    ("Azure OpenAI (GPT-5.1)",  "Hosts LLM deployment used by 11 AI checks; called via Managed Identity over Private Endpoint."),
    ("Azure Blob Storage",      "Stores uploaded DOCX, template DOCX, annotated outputs, and Markdown reports (job-scoped containers)."),
    ("PostgreSQL Flexible Server", "Persists jobs, findings, human decisions, and LangGraph checkpoints (resumable runs)."),
    ("Azure Key Vault",         "OpenAI keys, DB credentials, signing secrets — accessed by Managed Identity (no secrets in code)."),
    ("App Insights + Log Analytics", "OpenTelemetry traces from FastAPI & LangGraph, structured logs, latency / error metrics, alerts."),
    ("Azure Front Door + WAF",  "Global entry point, TLS termination, OWASP rules, DDoS protection, custom domain via Azure DNS."),
    ("Azure Container Registry + GitHub Actions", "Container images built & scanned in CI; Bicep IaC deploys to Container Apps environments."),
]
y = Inches(1.05)
for name, desc in rows:
    add_box(s, Inches(0.4), y, Inches(3.4), Inches(0.55), name,
            fill=AZURE_BLUE, border=AZURE_DARK, text_color=WHITE, size=11)
    add_text(s, Inches(3.95), y + Inches(0.08), Inches(9.1), Inches(0.5),
             desc, size=11, color=GREY_TEXT)
    y += Inches(0.6)

# ============================================================
# SLIDE 5 — End-to-end flow
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "End-to-End Flow", "From upload to approved, annotated DOCX")
steps = [
    "1. Reviewer signs in via Microsoft Entra ID (OIDC) and lands on the SPA served by Azure Static Web Apps.",
    "2. SPA POSTs the DOCX + template to FastAPI; the file is streamed into Azure Blob Storage and a 'job' row is written to PostgreSQL.",
    "3. FastAPI starts the LangGraph run; node load_documents reads the DOCX from Blob.",
    "4. run_checks fans out 10 regex checks and 11 LLM checks in parallel; LLM calls hit Azure OpenAI (GPT-5.1) over a Private Endpoint.",
    "5. draft_comments anchors each finding to the nearest heading and produces DraftComment[] (status = pending). State is checkpointed to PostgreSQL.",
    "6. The graph hits the HITL interrupt and pauses. The reviewer fetches drafts via GET /jobs/{id}/review and posts approve / reject decisions.",
    "7. On resume, apply_comments inserts ONLY approved comments into the DOCX and save_output writes the annotated file + Markdown report back to Blob.",
    "8. Reviewer downloads the annotated DOCX via GET /jobs/{id}/download. All steps emit traces/metrics to Application Insights.",
]
y = Inches(1.1)
for line in steps:
    add_text(s, Inches(0.5), y, Inches(12.3), Inches(0.55),
             "•  " + line, size=14, color=GREY_TEXT)
    y += Inches(0.65)

# ============================================================
# SLIDE 6 — Tech stack & hosting
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "Technology Stack & Hosting")
cols = [
    ("Frontend", AZURE_BLUE, [
        "Flask / Jinja templates (current)",
        "Optional React migration",
        "Hosted on Azure Static Web Apps",
        "Auth: Entra ID (MSAL.js)",
    ]),
    ("Backend", PURPLE, [
        "Python 3.11 · FastAPI",
        "LangGraph (orchestration)",
        "python-docx (DOCX I/O)",
        "Hosted on Azure Container Apps",
    ]),
    ("AI / Data", GREEN, [
        "Azure OpenAI · GPT-5.1",
        "PostgreSQL Flexible Server",
        "Azure Blob Storage",
        "LangGraph Postgres checkpointer",
    ]),
    ("Platform / Ops", ORANGE, [
        "Azure Key Vault (secrets)",
        "App Insights + Log Analytics",
        "Azure Front Door + WAF",
        "GitHub Actions + Bicep IaC",
    ]),
]
col_w = Inches(3.0); gap = Inches(0.15); x = Inches(0.5)
for title, color, items in cols:
    add_box(s, x, Inches(1.2), col_w, Inches(0.55), title,
            fill=color, border=color, size=14)
    body = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                              x, Inches(1.8), col_w, Inches(4.5))
    body.fill.solid(); body.fill.fore_color.rgb = WHITE
    body.line.color.rgb = color; body.line.width = Pt(1.25)
    tf = body.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.15)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run(); r.text = "• " + item
        r.font.size = Pt(13); r.font.color.rgb = GREY_TEXT
        p.space_after = Pt(8)
    x += col_w + gap

add_box(s, Inches(0.5), Inches(6.5), Inches(12.3), Inches(0.7),
        "Hosting: single Azure Resource Group · Container Apps environment in a VNet · "
        "Private Endpoints for OpenAI / PostgreSQL / Blob · Multi-region ready via Front Door",
        fill=AZURE_DARK, border=AZURE_DARK, text_color=WHITE, size=13)

# ============================================================
# SLIDE 7 — Security & Observability
# ============================================================
s = prs.slides.add_slide(BLANK)
slide_header(s, "Security, Compliance & Observability")
items = [
    ("Identity",        "Entra ID SSO for users; Managed Identity for service-to-service (no secrets in code)."),
    ("Network",         "VNet-injected Container Apps · Private Endpoints for OpenAI, PostgreSQL, Blob · Front Door + WAF at the edge."),
    ("Secrets",         "All keys / connection strings in Azure Key Vault, mounted via Managed Identity."),
    ("Data protection", "TLS 1.2+ everywhere · Storage and DB encrypted at rest (CMK-ready) · job data scoped per tenant."),
    ("HITL audit trail", "Every accept / reject decision (who, when, comment id) persisted in PostgreSQL — regulator-friendly."),
    ("Observability",   "OpenTelemetry traces, structured logs and metrics → App Insights + Log Analytics; alerts on error rate & LLM latency."),
    ("DR / BCP",        "PostgreSQL geo-redundant backups · Blob RA-GRS · Bicep IaC enables redeploy to a paired region."),
]
y = Inches(1.2)
for title, desc in items:
    add_box(s, Inches(0.5), y, Inches(2.6), Inches(0.65), title,
            fill=AZURE_BLUE, border=AZURE_DARK, size=12)
    add_text(s, Inches(3.3), y + Inches(0.1), Inches(9.7), Inches(0.6),
             desc, size=13, color=GREY_TEXT)
    y += Inches(0.78)

prs.save(OUT)
print(f"Wrote {OUT}")
