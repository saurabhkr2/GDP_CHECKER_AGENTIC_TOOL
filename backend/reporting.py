"""
Functions for generating reports.
"""
import textwrap
from collections import Counter, defaultdict
from typing import Dict
from models import Report
from datetime import datetime

def build_markdown(report: Report, _unused_checklist: str, output_path: str, inputs: Dict[str, str]) -> None:
    """
    Builds a detailed Markdown report from the findings.
    Note: checklist parameter is kept for backward compatibility but not used.
    """
    from collections import Counter
    
    # Severity sort order
    severity_order = {"Major": 1, "Moderate": 2, "Minor": 3}
    
    # Group AI findings by check_id
    ai_findings_by_check = defaultdict(list)
    for check_id, findings in report.ai_findings.items():
        for f in findings:
            ai_findings_by_check[check_id].append(f)
    
    # Sort findings within each group by severity
    for check_id in ai_findings_by_check:
        ai_findings_by_check[check_id].sort(key=lambda f: severity_order.get(f.severity, 99))
    
    # Count findings
    ai_counts = {check_id: len(findings) for check_id, findings in ai_findings_by_check.items()}
    total_ai = sum(ai_counts.values())
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Document Quality Report\n\n")
        f.write(f"**Generated:** {timestamp}\n\n")
        
        # --- Summary Section ---
        f.write("## Summary\n\n")
        f.write("| Category | Findings |\n")
        f.write("|:---|---:|\n")
        if total_ai > 0:
            f.write(f"| **AI-Powered Checks** | **{total_ai}** |\n")
        f.write(f"| **TOTAL** | **{total_ai}** |\n\n")
        
        # --- Inputs Section ---
        f.write("### Analysis Inputs\n\n")
        f.write("| Parameter | Value |\n")
        f.write("|:---|:---|\n")
        for key, value in inputs.items():
            f.write(f"| {key} | `{value}` |\n")
        f.write("\n")
        
        # --- AI Findings Section ---
        if total_ai > 0:
            f.write("## AI-Powered Findings\n\n")
            
            # Summary table for AI checks
            f.write("### AI Checks Summary\n\n")
            f.write("| Check ID | Findings |\n")
            f.write("|:---|---:|\n")
            
            sorted_ai_checks = sorted(ai_counts.keys())
            for check_id in sorted_ai_checks:
                if ai_counts[check_id] > 0:
                    f.write(f"| {check_id} | {ai_counts[check_id]} |\n")
            f.write("\n")
            
            # Detailed findings for each AI check
            for check_id in sorted_ai_checks:
                if check_id in ai_findings_by_check and ai_findings_by_check[check_id]:
                    f.write(f"### {check_id} ({len(ai_findings_by_check[check_id])} findings)\n\n")
                    
                    for finding in ai_findings_by_check[check_id]:
                        f.write(f"**Severity:** {finding.severity}\n")
                        f.write(f"**Message:** {finding.message}\n")
                        if finding.evidence:
                            # Format evidence as a blockquote
                            evidence_text = textwrap.indent(finding.evidence, '> ', lambda line: True)
                            f.write(f"**Evidence:**\n{evidence_text}\n")
                        f.write("---\n")
                    f.write("\n")
    
    print(f"✓ Markdown report generated at: {output_path}")