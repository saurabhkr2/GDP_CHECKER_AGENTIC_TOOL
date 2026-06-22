import re
import json
import threading
import time
import os
from typing import List, Dict, Any, Tuple, Optional
from models import Finding, ExtractedDoc
from docx import Document as DocxDocument

# Import openai dependencies
_HAS_OPENAI = False
try:
    from openai import OpenAI, AzureOpenAI
    _HAS_OPENAI = True
except ImportError:
    # This will only print a warning if openai is not installed, allowing the app to run without AI features.
    print("⚠️ 'openai' package not found. AI checks will be skipped. Install with: pip install openai")


# ============================================================================
# GLOBAL CONSTANTS
# ============================================================================
# Load AI prompts from JSON file
_AI_PROMPTS = {}
try:
    prompts_path = os.path.join(os.path.dirname(__file__), 'ai_prompts.json')
    with open(prompts_path, 'r', encoding='utf-8') as f:
        _AI_PROMPTS = json.load(f)
except Exception as e:
    print(f"⚠️ Failed to load AI prompts: {e}")

def get_prompt(check_id: str, **kwargs) -> Dict[str, str]:
    """Get system prompt, task, and severity from JSON file, with optional variable substitution. Returns check_id as the task name."""
    prompt_data = _AI_PROMPTS.get(check_id, {})
    system_prompt = prompt_data.get('system_prompt', '')
    task = prompt_data.get('task', '')
    severity = prompt_data.get('severity', 'Moderate')
    
    # Substitute variables if provided (e.g., {brand}, {brand_lower})
    for key, value in kwargs.items():
        system_prompt = system_prompt.replace(f'{{{key}}}', str(value))
        task = task.replace(f'{{{key}}}', str(value))
    
    return {'system_prompt': system_prompt, 'task': task, 'check_id': check_id, 'severity': severity}

# ============================================================================
# ORIGINAL CONSTANTS
# ============================================================================
# Azure OpenAI Service - loaded from environment / .env (NEVER hardcode keys)
try:
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
    _load_dotenv()
except Exception:
    pass
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

DEFAULT_BRAND = "Philips"

def init_openai_client(api_key: Optional[str], deployment_name: str, enable_http_logs: bool = False) -> Optional[Any]:
    if not _HAS_OPENAI:
        return None
    
    # Check for Azure OpenAI
    azure_endpoint = AZURE_OPENAI_ENDPOINT
    azure_api_key = AZURE_OPENAI_API_KEY
    
    try:
        # Configure HTTP logging if requested
        if enable_http_logs:
            import logging
            import httpx
            # Enable detailed httpx logging
            httpx_logger = logging.getLogger("httpx")
            httpx_logger.setLevel(logging.DEBUG)
            if not httpx_logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('%(levelname)s [%(name)s] %(message)s'))
                httpx_logger.addHandler(handler)
            print("🔍 HTTP communication logging enabled for AI requests")
        
        if azure_endpoint and azure_api_key:
            # Use default API version if not specified
            azure_api_version = AZURE_OPENAI_API_VERSION
            
            # Create httpx client with logging if enabled
            if enable_http_logs:
                import httpx
                http_client = httpx.Client(event_hooks={'request': [lambda r: print(f"→ REQUEST: {r.method} {r.url}")],
                                                         'response': [lambda r: print(f"← RESPONSE: {r.status_code} from {r.url}")]})
            else:
                http_client = None
            
            client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                api_version=azure_api_version,
                http_client=http_client
            )
            print(f"✓ Connected to Azure OpenAI for model {deployment_name} at {azure_endpoint} (API version: {azure_api_version})")
            return client
        elif api_key:
            client = OpenAI(api_key=api_key)
            print("✓ Connected to OpenAI")
            return client
        return None
    except Exception as e:
        print(f"⚠️ Failed to initialize client for {deployment_name}: {e}")
        return None

def ai_request_json(client, model: str, system_prompt: str, user_payload: Any) -> Optional[Dict[str, Any]]:
    if client is None:
        return None
    
    try:
        # For Azure, use deployment name from the 'model' parameter
        deployment = model
        
        # We explicitly ask for JSON only; no chain-of-thought
        user_content = json.dumps(user_payload) if isinstance(user_payload, dict) else str(user_payload)
        # Per-call timeout is configurable via env so the agent can fail fast
        # on a hung Azure connection instead of blocking the whole pipeline.
        # 45 s is a reasonable default for chunked checks; bump via env if you
        # use a slow reasoning model.
        _per_call_timeout = float(os.getenv("AI_REQUEST_TIMEOUT", "45"))
        _t0 = time.time()
        resp = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            timeout=_per_call_timeout
        )
        
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"\r⚠️ AI request error: {e}")
        return {"_error": str(e)}

def chunk_text(text: str, max_chars: int = 6000) -> List[str]:
    # Conservative chunking for context windows
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # try not to cut in the middle of a sentence
        period = text.rfind(".", start, end)
        if period > start + int(0.6 * (end-start)):
            end = period + 1
        chunks.append(text[start:end])
        start = end
    return chunks

def ai_check_na_justification(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #1: Adequacy of N/A justifications"""
    findings = []
    prompts = get_prompt('AI01_NA_Justification')
    system_prompt = prompts['system_prompt']
    
    chunks = chunk_text(doc_text, 6000)
    total_chunks = len(chunks)
    for idx, ch in enumerate(chunks, 1):
        if progress_callback:
            progress_callback(f"Processing chunk {idx}/{total_chunks}")
        payload = {
            "task": prompts['task'],
            "text": ch
        }
        out = ai_request_json(client, model, system_prompt, payload)
        if not out or "_error" in out:
            continue
        for item in out.get("items", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=item.get("why_inadequate", "Inadequate N/A justification."),
                evidence=item.get("quote",""),
                section=None
            ))
    return findings

def ai_check_requirement_testability(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #2: Requirement testability and risky modals in context"""
    findings = []
    prompts = get_prompt('AI02_Testability')
    system_prompt = prompts['system_prompt']
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for r in out.get("requirements", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=r.get("issue","Non-testable requirement"),
                evidence=r.get("quote",""),
                section=None
            ))
    return findings

def ai_check_terminology_consistency(client, model: str, doc_text: str, brand: str = DEFAULT_BRAND) -> List[Finding]:
    """AI Check #3: Terminology and naming consistency mapping."""
    findings = []
    prompts = get_prompt('AI03_Terminology', brand=brand)
    system_prompt = prompts['system_prompt']
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for t in out.get("terms", []):
            msg = f"Use '{t.get('canonical','')}' as canonical; retire variants: {', '.join(t.get('variants', []))}"
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=msg,
                evidence=t.get("example_text","")  # Use exact text from document
            ))
    return findings

def ai_check_revision_specificity(client, model: str, rev_table_text: str) -> List[Finding]:
    """AI Check #4: Revision history specificity (section numbers, meaningful descriptions)."""
    findings = []
    if not rev_table_text.strip():
        return findings
    prompts = get_prompt('AI04_RevisionSpecificity')
    system_prompt = prompts['system_prompt']
    
    payload = {
        "task": prompts['task'],
        "text": rev_table_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for e in out.get("entries", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=e.get("issue","Vague revision entry"),
                evidence=e.get("quote",""),
                section=None
            ))
    return findings

def ai_check_spelling_grammar(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #5: Spelling and grammar validation - Quick scan for critical errors only"""
    findings = []
    prompts = get_prompt('AI05_SpellingGrammar')
    system_prompt = prompts['system_prompt']
    
    chunks = chunk_text(doc_text, 10000)
    total_chunks = len(chunks)
    for idx, ch in enumerate(chunks, 1):
        if progress_callback:
            progress_callback(f"Processing chunk {idx}/{total_chunks}")
        payload = {
            "task": prompts['task'],
            "text": ch
        }
        out = ai_request_json(client, model, system_prompt, payload)
        if not out or "_error" in out:
            continue
        for err in out.get("errors", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"{err.get('issue', 'Error')}. Suggested: {err.get('correction', 'N/A')}",
                evidence=err.get("quote", ""),
                section=None
            ))
    return findings

def ai_check_template_compliance(client, model: str, work_doc_text: str, template_doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #6: Template structure and content compliance using document intelligence"""
    findings = []
    prompts = get_prompt('AI06_TemplateCompliance')
    system_prompt = prompts['system_prompt']
    
    # Use entire documents - chunk if necessary
    chunks = chunk_text(work_doc_text, 25000)  # Larger chunks for better context
    total_chunks = len(chunks)
    
    all_chunk_findings = []
    
    for idx, work_chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Analyzing document section {idx + 1}/{total_chunks}")
        # For template, use full text or first substantial chunk
        template_chunk = template_doc_text if len(template_doc_text) <= 15000 else template_doc_text[:15000]
        
        payload = {
            "task": prompts['task'],
            "template_structure": template_chunk,
            "working_document_chunk": work_chunk,
            "chunk_index": idx + 1,
            "total_chunks": len(chunks)
        }
        
        out = ai_request_json(client, model, system_prompt, payload)
        
        if out and "_error" not in out:
            for item in out.get("findings", []):
                severity = item.get("severity", prompts['severity'])
                if severity not in ["Major", "Moderate", "Minor"]:
                    severity = prompts['severity']
                
                issue_type = item.get("issue_type", "compliance_issue")
                section = item.get("section", "Unknown")
                message = item.get("message", "Template compliance issue")
                suggestion = item.get("suggestion", "")
                evidence = item.get("evidence", "")
                
                # Skip findings that reference TOC
                if "table of contents" in evidence.lower() or "table of contents" in section.lower():
                    continue
                
                # Skip duplicate findings across chunks
                finding_key = f"{section}_{issue_type}_{message[:50]}"
                if finding_key not in [f"{f.section}_{f.check_id}_{f.message[:50]}" for f in all_chunk_findings]:
                    # Construct detailed message
                    full_message = f"[{issue_type.replace('_', ' ').title()}] {message}"
                    if suggestion:
                        full_message += f" | Suggestion: {suggestion}"
                    
                    all_chunk_findings.append(Finding(
                        check_id=prompts['check_id'],
                        severity=severity,
                        message=full_message,
                        evidence=evidence,
                        section=section
                    ))
    
    return all_chunk_findings

def ai_check_open_issues(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #7: Open Issues validation - owner, description, closure date"""
    findings = []
    prompts = get_prompt('AI07_OpenIssues')
    system_prompt = prompts['system_prompt']
    
    # Look for open issues section
    if not re.search(r'\bopen\s+issues?\b', doc_text, re.I):
        return findings
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("issues", []):
            missing = item.get("missing_fields", [])
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Open issue incomplete. Missing: {', '.join(missing)}. {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section="Open Issues"
            ))
    return findings

def ai_check_test_verdicts(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #8: Test case verdicts and actual results completeness"""
    findings = []
    prompts = get_prompt('AI08_TestVerdicts')
    system_prompt = prompts['system_prompt']
    
    # Check if document has test cases
    if not re.search(r'\btest\s+(case|result|verdict)', doc_text, re.I):
        return findings
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("test_cases", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Test case {item.get('test_id', 'unknown')}: {item.get('issue', 'Missing verdict or actual result')}",
                evidence=item.get("quote", ""),
                section="Test Cases"
            ))
    return findings

def ai_check_test_traceability(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #9: Test traceability to requirements and document references"""
    findings = []
    prompts = get_prompt('AI09_TestTraceability')
    system_prompt = prompts['system_prompt']
    
    # Check if document has test cases
    if not re.search(r'\btest\s+(case|traceability)', doc_text, re.I):
        return findings
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("trace_issues", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Test {item.get('test_id', 'case')}: {item.get('issue', 'Missing traceability or document references')}",
                evidence=item.get("quote", ""),
                section="Test Traceability"
            ))
    return findings

def ai_check_authorship(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #10: Verify exactly one author is listed"""
    findings = []
    prompts = get_prompt('AI10_Authorship')
    system_prompt = prompts['system_prompt']
    
    payload = {
        "task": prompts['task'],
        "text": doc_text[:3000]  # Usually in beginning
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        count = out.get("author_count", 1)
        if count != 1:
            authors = out.get("authors_found", [])
            issue = out.get("issue", f"Found {count} authors, expected exactly 1")
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"{issue}. Authors found: {', '.join(authors) if authors else 'None'}",
                evidence=out.get("author_section", ""),
                section="Document Properties"
            ))
    return findings

def ai_check_external_files_qms(client, model: str, doc_text: str) -> List[Finding]:
    """AI Check #11: Detect embedded external files or QMS document attachments"""
    findings = []
    prompts = get_prompt('AI11_ExternalFilesQMS')
    system_prompt = prompts['system_prompt']
    
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("violations", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"{item.get('type', 'External file/QMS violation')}: {item.get('issue', 'Embedded files or QMS documents not allowed')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


# ----------------------------------------------------------------------------
# Acronym check: fully deterministic. No LLM call.
# ----------------------------------------------------------------------------
# Acronym validation is text processing, not reasoning. The previous LLM
# implementation took 60-180 s per run (chunked, multiple slow gpt-5.1 calls)
# and frequently hallucinated definitions. This regex-based version runs in
# ~50 ms on a 100-page document and is more reliable.
_ACRONYM_RE = re.compile(r'\b([A-Z][A-Z0-9]{1,9})(?:s)?\b')

# Common English / scientific tokens that match the all-caps shape but are
# not real acronyms. Anything in this list is silently ignored.
_ACRONYM_STOPWORDS = {
    # Articles / pronouns / prepositions / conjunctions in caps (headings)
    "A", "AN", "THE", "I", "IT", "IS", "OR", "AND", "OF", "TO", "IN", "ON",
    "AT", "BY", "FOR", "AS", "BE", "NO", "NOT", "IF", "SO", "WE", "US",
    "OUR", "YOU", "ALL", "ANY", "DO", "WHO", "HOW", "WHY", "MAY", "CAN",
    # Latin / common abbrev that look like acronyms
    "EG", "IE", "ETC", "VS", "NA", "TBD", "TBC", "FAQ",
    # Time / date tokens
    "AM", "PM", "UTC", "GMT", "CET", "EST", "PST",
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG",
    "SEP", "SEPT", "OCT", "NOV", "DEC",
    "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN",
    # Common doc-structure words used in headings / templates
    "TOC", "TBD", "DRAFT", "FINAL", "REV", "VER", "VERSION", "PAGE", "DOC",
    "REF", "FIG", "TBL", "APP", "SEC", "CH", "VOL", "PG", "NO",
    # Units (ALL CAPS appearance)
    "MM", "CM", "KM", "MG", "KG", "ML", "HZ", "KHZ", "MHZ", "GHZ",
    "DB", "PSI", "RPM", "VAC", "VDC", "AC", "DC",
    # Common file/format
    "PDF", "DOC", "DOCX", "XLS", "XLSX", "PPT", "PPTX", "CSV", "XML",
    "JSON", "HTML", "URL", "URI",
}


def _find_glossary_section(doc_text: str) -> str:
    """
    Locate the Abbreviations / Glossary / Acronyms / Definitions section and
    return its raw text. Returns "" if not found.
    """
    # Try a series of section-heading patterns. We grab from the heading
    # to the next top-level heading (or the next blank-line-then-Capitalized
    # line, as a fallback).
    headings = [
        r"abbreviations?\s+and\s+definitions?",
        r"definitions?\s+and\s+abbreviations?",
        r"acronyms?\s+and\s+abbreviations?",
        r"abbreviations?",
        r"acronyms?",
        r"glossary",
        r"definitions?",
        r"terms?\s+and\s+definitions?",
    ]
    for h in headings:
        # Match a heading line. Section ends at the next numbered heading
        # like "5 Something" or "5.1 Something", or end of document.
        pat = re.compile(
            rf"(?:^|\n)\s*(?:\d+(?:\.\d+)*\s+)?{h}\s*\n(.*?)(?=\n\s*\d+(?:\.\d+)*\s+[A-Z]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        m = pat.search(doc_text)
        if m:
            return m.group(1)
    return ""


def _extract_defined_acronyms(glossary_text: str, doc_text: str) -> set:
    """
    Return the set of acronyms that are *defined* anywhere in the document.

    A token is treated as defined if EITHER:
      1. It appears in the glossary section, OR
      2. It is introduced inline as "Full Name (ACR)" or "ACR (Full Name)"
         anywhere in the document.
    """
    defined: set = set()

    # 1. Tokens that appear in the glossary section. We assume any all-caps
    #    token in the glossary is defined.
    if glossary_text:
        for m in _ACRONYM_RE.finditer(glossary_text):
            defined.add(m.group(1))

    # 2. Inline definitions: "Full Name (ACR)" or "ACR (Full Name)".
    #    Pattern A: "Some Words (ACR)"
    for m in re.finditer(
        r"(?:[A-Z][A-Za-z0-9\-]*\s+){1,8}\(([A-Z][A-Z0-9]{1,9})s?\)",
        doc_text,
    ):
        defined.add(m.group(1))
    #    Pattern B: "ACR (Full Name)"
    for m in re.finditer(
        r"\b([A-Z][A-Z0-9]{1,9})\s*\(((?:[A-Z][A-Za-z0-9\-]*\s*){1,8})\)",
        doc_text,
    ):
        defined.add(m.group(1))

    return defined


def _first_sentence_containing(text: str, token: str) -> str:
    """Return the first sentence (≤ 240 chars) that contains `token`."""
    pat = re.compile(rf"[^.\n]*\b{re.escape(token)}\b[^.\n]*[.\n]?")
    m = pat.search(text)
    if not m:
        return ""
    s = m.group(0).strip()
    return s[:240] + ("…" if len(s) > 240 else "")


def ai_check_acronym_definitions(
    client=None,
    model: str = "",
    doc_text: str = "",
    max_retries: int = 0,
    progress_callback=None,
) -> List[Finding]:
    """
    AI Check #12: Acronym Definitions (R04) — DETERMINISTIC, no LLM call.

    Algorithm:
      1. Extract every all-caps token (2-10 chars) from the document.
      2. Drop common English / unit / date / file-format stopwords.
      3. Build the set of defined acronyms from (a) the Abbreviations /
         Glossary section, (b) inline "Full Name (ACR)" patterns.
      4. Anything used but not defined → finding.

    `client` and `model` are accepted but ignored, so the registry signature
    is unchanged.
    """
    t0 = time.time()
    findings: List[Finding] = []
    prompts = get_prompt('AI12_AcronymDefinitions')

    if not doc_text:
        return findings

    if progress_callback:
        progress_callback("Checking acronym definitions (deterministic)")

    glossary_text = _find_glossary_section(doc_text)
    defined = _extract_defined_acronyms(glossary_text, doc_text)

    # Collect all candidate acronyms with one example sentence each.
    seen: set = set()
    for m in _ACRONYM_RE.finditer(doc_text):
        token = m.group(1)
        if token in seen:
            continue
        seen.add(token)
        if token in _ACRONYM_STOPWORDS:
            continue
        if token in defined:
            continue
        # Skip pure numbers / version-like tokens
        if token.isdigit():
            continue
        quote = _first_sentence_containing(doc_text, token)
        findings.append(Finding(
            check_id=prompts['check_id'],
            severity=prompts['severity'],
            message=(
                f"Acronym '{token}' is used but not defined in the "
                f"Abbreviations / Glossary section, and no inline "
                f"'Full Name ({token})' definition was found."
            ),
            evidence=quote,
            section="Acronyms",
        ))

    dt = time.time() - t0
    print(f"  -> Acronym check (deterministic) completed in {dt:.2f}s: "
          f"{len(findings)} undefined acronyms, "
          f"{len(defined)} defined, "
          f"glossary {'found' if glossary_text else 'NOT found'}")
    return findings


def ai_check_date_format(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #13: Date Format Validation - Check dates follow DDMMMYYYY format"""
    findings = []
    prompts = get_prompt('AI13_DateFormat')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text[:15000]  # Sample for speed
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("dates", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Date '{item.get('date', '')}' not in DDMMMYYYY format. {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_double_spaces(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #14: Double Spaces Detection"""
    findings = []
    prompts = get_prompt('AI14_DoubleSpaces')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text[:15000]
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("spaces", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=item.get("issue", "Multiple consecutive spaces found"),
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_risky_modals(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #15: Risky Modal Verbs - Identify ambiguous modals in requirements"""
    findings = []
    prompts = get_prompt('AI15_RiskyModals')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    chunks = chunk_text(doc_text, 10000)
    for ch in chunks:
        payload["text"] = ch
        out = ai_request_json(client, model, system_prompt, payload)
        if out and "_error" not in out:
            for item in out.get("modals", []):
                findings.append(Finding(
                    check_id=prompts['check_id'],
                    severity=prompts['severity'],
                    message=f"Ambiguous modal '{item.get('modal', '')}' in requirement. {item.get('issue', '')}",
                    evidence=item.get("quote", ""),
                    section=None
                ))
    return findings


def ai_check_figures_tables(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #16: Figures & Tables Validation"""
    findings = []
    prompts = get_prompt('AI16_FiguresTables')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("issues", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"{item.get('type', 'Item')} {item.get('number', '')}: {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_placeholders(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #17: Placeholder Detection"""
    findings = []
    prompts = get_prompt('AI17_Placeholders')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text[:15000]
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("placeholders", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Placeholder found: {item.get('text', '')}. {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_brand_casing(client, model: str, doc_text: str, brand: str, progress_callback=None) -> List[Finding]:
    """AI Check #18: Brand Casing Verification"""
    findings = []
    prompts = get_prompt('AI18_BrandCasing', brand=brand, brand_lower=brand.lower())
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("cases", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Brand name casing error: Found '{item.get('text', '')}', expected '{brand}'.",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_section_numbering(client, model: str, doc_text: str, progress_callback=None) -> List[Finding]:
    """AI Check #19: Section Numbering Validation"""
    findings = []
    prompts = get_prompt('AI19_SectionNumbering')
    system_prompt = prompts['system_prompt']
    payload = {
        "task": prompts['task'],
        "text": doc_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("issues", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"Section {item.get('section', '')}: {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_toc_validation(client, model: str, work_doc: ExtractedDoc, progress_callback=None) -> List[Finding]:
    """AI Check #20: TOC Validation - Match TOC entries with actual headings"""
    findings = []
    prompts = get_prompt('AI20_TOCValidation')
    system_prompt = prompts['system_prompt']
    
    # Extract TOC and headings
    toc_text = "\n".join([p.text for p in work_doc.paragraphs if "table of contents" in p.text.lower()])[:2000]
    headings_text = "\n".join([h for h in work_doc.headings])[:3000]
    
    payload = {
        "task": prompts['task'],
        "toc": toc_text,
        "headings": headings_text
    }
    out = ai_request_json(client, model, system_prompt, payload)
    if out and "_error" not in out:
        for item in out.get("issues", []):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"TOC mismatch: {item.get('heading', '')}. {item.get('issue', '')}",
                evidence=item.get("quote", ""),
                section=None
            ))
    return findings


def ai_check_template_id(client, model: str, doc_path: str, template_path: str, progress_callback=None) -> List[Finding]:
    """AI Check #21: Template ID Verification"""
    findings = []
    
    try:
        work_doc = DocxDocument(doc_path)
        template_doc = DocxDocument(template_path)
        
        # Extract footer text
        work_footer = ""
        template_footer = ""
        
        for section in work_doc.sections:
            if section.footer:
                work_footer += " ".join([p.text for p in section.footer.paragraphs])
                
        for section in template_doc.sections:
            if section.footer:
                template_footer += " ".join([p.text for p in section.footer.paragraphs])
        
        prompts = get_prompt('AI21_TemplateID')
        system_prompt = prompts['system_prompt']
        
        payload = {
            "task": prompts['task'],
            "work_footer": work_footer[:500],
            "template_footer": template_footer[:500]
        }
        
        out = ai_request_json(client, model, system_prompt, payload)
        if out and "_error" not in out and not out.get("match", True):
            findings.append(Finding(
                check_id=prompts['check_id'],
                severity=prompts['severity'],
                message=f"{out.get('issue', 'Template ID mismatch')}. Work: {out.get('work_id', 'N/A')}, Template: {out.get('template_id', 'N/A')}",
                evidence=work_footer[:200],
                section=None
            ))
    except Exception as e:
        print(f"Error checking template ID: {e}")
    
    return findings
