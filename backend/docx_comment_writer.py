#!/usr/bin/env python3
"""
Word Document Comment Insertion Utilities
"""
import os
import re
import shutil
import zipfile
from collections import defaultdict
from datetime import datetime
from lxml import etree

from models import Report

# This function is no longer used with the direct XML manipulation but kept for reference
# from docx.oxml import OxmlElement
# from docx.oxml.ns import qn


def add_comment_to_word(doc_path: str, output_path: str, report: Report, author: str = "Compliance Checker", progress_callback=None) -> None:
    """
    Add compliance findings as Word comment bubbles using direct XML manipulation.
    
    Key improvements:
    - Stores findings in separate vectors by check type (regex_findings_map, ai_findings_map)
    - Processes each check type with dedicated matching logic
    - AI12_AcronymDefinitions: Matches acronym to its FIRST occurrence in document
    - R06_Terminology: Matches term variants directly from message
    - All other checks: Standard evidence-based matching
    
    This approach ensures that findings like missing acronym definitions are always
    added to the paragraph containing the acronym, not to random locations.
    """
    # First, collect all findings that have evidence and are suitable for commenting.
    all_findings_with_evidence = []
    for check_id, findings in report.ai_findings.items():
        for f in findings:
            # Ensure evidence is substantial enough to be useful for matching.
            if f.evidence and len(f.evidence.strip()) > 15:
                comment_text = f"[AI:{check_id}] {f.severity.upper()}: {f.message}"
                evidence_normalized = ' '.join(f.evidence.strip().split())
                all_findings_with_evidence.append((evidence_normalized, comment_text, author, check_id, f.message))

    # If there are no findings to add as comments, just copy the file and return.
    if not all_findings_with_evidence:
        print("\nNo findings with evidence to add as comments. Copying original document.")
        shutil.copy2(doc_path, output_path)
        print(f"✓ Saved document to: {output_path}")
        return
    
    try:
        # Store findings by check type for separate processing
        ai_findings_map = defaultdict(list)
        
        # Group findings by check_id for specialized processing logic
        for evidence, comment, auth, check_id, msg in all_findings_with_evidence:
            ai_findings_map[check_id].append((evidence, comment, auth, check_id, msg))
        
        total_findings = len(all_findings_with_evidence)
        print(f"\nProcessing {total_findings} findings with evidence...")
        
        # Copy the input file to output
        shutil.copy2(doc_path, output_path)
        
        # Open as zip to manipulate XML
        temp_dir = 'temp_docx_extract'
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) # Clean up from previous runs
        with zipfile.ZipFile(output_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Read document.xml
        doc_xml_path = f'{temp_dir}/word/document.xml'
        with open(doc_xml_path, 'rb') as doc_xml:
            tree = etree.parse(doc_xml)
            root = tree.getroot()
        
        # Create comments structure
        w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        comments_root = etree.Element(f'{w_ns}comments', nsmap={'w': w_ns[1:-1]})
        
        comments_added = 0
        comment_id = 0
        all_paragraphs = root.findall(f'.//{w_ns}p')
        
        # Helper function for evidence matching
        def match_evidence_in_paragraph(evidence_normalized, para_text):
            # Try matching with first 25 chars of evidence
            evidence_key = evidence_normalized[:25].lower() if len(evidence_normalized) > 25 else evidence_normalized.lower()
            
            # Also try matching with last 25 chars if it was truncated at start
            evidence_key_end = evidence_normalized[-25:].lower() if len(evidence_normalized) > 25 else evidence_normalized.lower()
            
            # Match if either part appears in paragraph (case-insensitive)
            if evidence_key in para_text.lower() or evidence_key_end in para_text.lower():
                return True
            # If evidence is short enough, try full match
            elif len(evidence_normalized) <= 100 and evidence_normalized.lower() in para_text.lower():
                return True
            return False
        
        # Helper function to create and add a comment
        def create_comment(para, comment_text, author_name):
            nonlocal comment_id, comments_added
            
            # Create comment range start
            comment_start = etree.Element(f'{w_ns}commentRangeStart')
            comment_start.set(f'{w_ns}id', str(comment_id))
            
            # Create comment range end  
            comment_end = etree.Element(f'{w_ns}commentRangeEnd')
            comment_end.set(f'{w_ns}id', str(comment_id))
            
            # Insert at beginning and end of paragraph
            para.insert(0, comment_start)
            para.append(comment_end)
            
            # Add comment reference in a new run
            run = etree.SubElement(para, f'{w_ns}r')
            comment_ref = etree.SubElement(run, f'{w_ns}commentReference')
            comment_ref.set(f'{w_ns}id', str(comment_id))
            
            # Create the actual comment in comments.xml
            comment_elem = etree.SubElement(comments_root, f'{w_ns}comment')
            comment_elem.set(f'{w_ns}id', str(comment_id))
            comment_elem.set(f'{w_ns}author', author_name)
            comment_elem.set(f'{w_ns}date', datetime.now().isoformat())
            comment_elem.set(f'{w_ns}initials', 'CC')
            
            # Add comment text with proper structure
            comment_para = etree.SubElement(comment_elem, f'{w_ns}p')
            comment_pPr = etree.SubElement(comment_para, f'{w_ns}pPr')
            comment_pStyle = etree.SubElement(comment_pPr, f'{w_ns}pStyle')
            comment_pStyle.set(f'{w_ns}val', 'CommentText')
            
            comment_run = etree.SubElement(comment_para, f'{w_ns}r')
            comment_rPr = etree.SubElement(comment_run, f'{w_ns}rPr')
            
            comment_text_elem = etree.SubElement(comment_run, f'{w_ns}t')
            comment_text_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            # Clean comment text to remove control characters and NULL bytes
            cleaned_comment = ''.join(char for char in comment_text if ord(char) >= 32 or char in '\n\r\t')
            comment_text_elem.text = cleaned_comment
            
            comments_added += 1
            comment_id += 1
        
        # Process each check type separately to ensure proper matching
        total_check_types = len([v for v in ai_findings_map.values() if v])
        current_check = 0
        
        # Process AI findings with check-specific matching logic
        
        # AI12_AcronymDefinitions: Match acronym to first occurrence
        if "AI12_AcronymDefinitions" in ai_findings_map and ai_findings_map["AI12_AcronymDefinitions"]:
            current_check += 1
            if progress_callback:
                progress_callback(f"Adding comments for AI12_AcronymDefinitions ({current_check}/{total_check_types})")
            print(f"Processing AI12_AcronymDefinitions: {len(ai_findings_map['AI12_AcronymDefinitions'])} findings")
            for evidence_normalized, comment_text, author_name, check_id, message in ai_findings_map["AI12_AcronymDefinitions"]:
                # Extract acronym from message
                acronym_match = re.search(r"Acronym '([^']+)'", message)
                if acronym_match:
                    acronym = acronym_match.group(1)
                    acronym_pattern = r'\b' + re.escape(acronym) + r'\b'
                    
                    # Find the FIRST paragraph containing this acronym
                    for para in all_paragraphs:
                        para_text = ' '.join(''.join(para.itertext()).split())
                        if re.search(acronym_pattern, para_text, re.IGNORECASE):
                            create_comment(para, comment_text, author_name)
                            break  # Only add to first occurrence
        
        # R06_Terminology: Match on term variants
        if "R06_Terminology" in ai_findings_map and ai_findings_map["R06_Terminology"]:
            current_check += 1
            if progress_callback:
                progress_callback(f"Adding comments for R06_Terminology ({current_check}/{total_check_types})")
            print(f"Processing R06_Terminology: {len(ai_findings_map['R06_Terminology'])} findings")
            for evidence_normalized, comment_text, author_name, check_id, message in ai_findings_map["R06_Terminology"]:
                if "retire variants:" in message:
                    # Extract variants from message
                    variants_part = message.split("retire variants:")[1].strip()
                    variants = [v.strip() for v in variants_part.split(',')]
                    
                    # Find paragraphs containing any variant
                    added_to_para = set()
                    for para in all_paragraphs:
                        para_id = id(para)  # Use object id to track unique paragraphs
                        if para_id in added_to_para:
                            continue
                        para_text = ' '.join(''.join(para.itertext()).split())
                        for variant in variants:
                            if variant.lower() in para_text.lower():
                                create_comment(para, comment_text, author_name)
                                added_to_para.add(para_id)
                                break  # Only add once per paragraph
        
        # AI18_BrandCasing: Search explicitly for lowercase "philips" only
        if "AI18_BrandCasing" in ai_findings_map and ai_findings_map["AI18_BrandCasing"]:
            current_check += 1
            if progress_callback:
                progress_callback(f"Adding comments for AI18_BrandCasing ({current_check}/{total_check_types})")
            print(f"Processing AI18_BrandCasing: {len(ai_findings_map['AI18_BrandCasing'])} findings")
            
            added_to_para = set()
            for evidence_normalized, comment_text, author_name, check_id, message in ai_findings_map["AI18_BrandCasing"]:
                # Search explicitly for lowercase "philips" in paragraphs (case-sensitive)
                # This is the incorrect form we want to flag
                for para in all_paragraphs:
                    para_id = id(para)
                    if para_id in added_to_para:
                        continue
                    
                    para_text = ' '.join(''.join(para.itertext()).split())
                    # Search for the exact word "philips" (lowercase) only
                    if re.search(r'\bphilips\b', para_text):
                        create_comment(para, comment_text, author_name)
                        added_to_para.add(para_id)
                        # Continue to check other paragraphs
        
        # AI15_RiskyModals: Search for risky modal verbs (can, may, might)
        if "AI15_RiskyModals" in ai_findings_map and ai_findings_map["AI15_RiskyModals"]:
            current_check += 1
            if progress_callback:
                progress_callback(f"Adding comments for AI15_RiskyModals ({current_check}/{total_check_types})")
            print(f"Processing AI15_RiskyModals: {len(ai_findings_map['AI15_RiskyModals'])} findings")
            
            # Define risky modal verbs to search for
            risky_modals = ['can', 'may', 'might']
            
            added_to_para = set()
            for evidence_normalized, comment_text, author_name, check_id, message in ai_findings_map["AI15_RiskyModals"]:
                # Find paragraphs containing risky modal verbs
                for para in all_paragraphs:
                    para_id = id(para)
                    if para_id in added_to_para:
                        continue
                    
                    para_text = ' '.join(''.join(para.itertext()).split())
                    
                    # Find which risky modals are present in this paragraph
                    found_modals = []
                    for modal in risky_modals:
                        if re.search(r'\b' + re.escape(modal) + r'\b', para_text, re.IGNORECASE):
                            found_modals.append(modal)
                    
                    # If any risky modals found, add comment mentioning the specific verbs
                    if found_modals:
                        # Customize comment to mention the actual verbs found
                        modals_str = ', '.join(found_modals)
                        customized_comment = comment_text.replace('may', modals_str) if 'may' in comment_text.lower() else f"{comment_text} (Found: {modals_str})"
                        create_comment(para, customized_comment, author_name)
                        added_to_para.add(para_id)
                        # Continue to check other paragraphs

        # All other AI findings: Standard evidence matching
        for check_id, findings_list in ai_findings_map.items():
            if check_id in ["AI12_AcronymDefinitions", "R06_Terminology", "AI18_BrandCasing", "AI15_RiskyModals"]:
                continue  # Already processed
            
            if not findings_list:
                continue
            
            current_check += 1
            if progress_callback:
                progress_callback(f"Adding comments for {check_id} ({current_check}/{total_check_types})")
            print(f"Processing {check_id}: {len(findings_list)} findings")
            used_indices = set()
            
            for para in all_paragraphs:
                para_text = ' '.join(''.join(para.itertext()).split())
                
                for idx, (evidence_normalized, comment_text, author_name, _, message) in enumerate(findings_list):
                    if idx in used_indices:
                        continue
                    
                    # Match evidence in paragraph
                    if match_evidence_in_paragraph(evidence_normalized, para_text):
                        create_comment(para, comment_text, author_name)
                        used_indices.add(idx)
        
        # Write modified files back
        with open(doc_xml_path, 'wb') as f:
            f.write(etree.tostring(tree, xml_declaration=True, encoding='UTF-8'))
        
        with open(f'{temp_dir}/word/comments.xml', 'wb') as f:
            f.write(etree.tostring(etree.ElementTree(comments_root), xml_declaration=True, encoding='UTF-8'))
        
        # Update [Content_Types].xml to declare comments.xml
        content_types_path = f'{temp_dir}/[Content_Types].xml'
        if os.path.exists(content_types_path):
            with open(content_types_path, 'rb') as f:
                ct_tree = etree.parse(f)
                ct_root = ct_tree.getroot()
            
            # Check if comments override already exists
            ct_ns = '{http://schemas.openxmlformats.org/package/2006/content-types}'
            has_comments_override = False
            for override in ct_root.findall(f'{ct_ns}Override'):
                if override.get('PartName') == '/word/comments.xml':
                    has_comments_override = True
                    break
            
            if not has_comments_override:
                # Add comments override
                new_override = etree.SubElement(ct_root, f'{ct_ns}Override')
                new_override.set('PartName', '/word/comments.xml')
                new_override.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml')
                
                with open(content_types_path, 'wb') as f:
                    f.write(etree.tostring(ct_tree, xml_declaration=True, encoding='UTF-8', standalone=True))
                print("✓ Updated [Content_Types].xml to register comments.xml")
        
        # Update document.xml.rels to reference comments.xml if needed
        rels_path = f'{temp_dir}/word/_rels/document.xml.rels'
        if os.path.exists(rels_path):
            with open(rels_path, 'rb') as f:
                rels_tree = etree.parse(f)
                rels_root = rels_tree.getroot()
            
            # Check if comments relationship already exists
            rels_ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
            has_comments_rel = False
            for rel in rels_root.findall(f'{rels_ns}Relationship'):
                if rel.get('Type') == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments':
                    has_comments_rel = True
                    break
            
            if not has_comments_rel:
                # Find max rId number
                max_id = 0
                for rel in rels_root.findall(f'{rels_ns}Relationship'):
                    rid = rel.get('Id', '')
                    if rid.startswith('rId'):
                        try:
                            num = int(rid[3:])
                            max_id = max(max_id, num)
                        except:
                            pass
                
                # Add comments relationship
                new_rel = etree.SubElement(rels_root, f'{rels_ns}Relationship')
                new_rel.set('Id', f'rId{max_id + 1}')
                new_rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments')
                new_rel.set('Target', 'comments.xml')
                
                with open(rels_path, 'wb') as f:
                    f.write(etree.tostring(rels_tree, xml_declaration=True, encoding='UTF-8'))
                print("✓ Updated document.xml.rels to reference comments.xml")
        
        # Recreate the zip file
        os.remove(output_path)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for folder, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(folder, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_out.write(file_path, arcname)
        
        # Cleanup temp directory with retry for Windows file locks
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                shutil.rmtree(temp_dir)
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Wait before retry
                else:
                    # If cleanup fails, try to mark for deletion on reboot (Windows)
                    try:
                        import stat
                        def handle_remove_readonly(func, path, exc):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
                    except Exception:
                        print(f"⚠️ Could not cleanup temp directory: {temp_dir} (will be cleaned on next run)")
        
        print(f"✓ Added {comments_added} comment bubbles to document")
        print(f"✓ Saved annotated document to: {output_path}")
        
    except Exception as e:
        print(f"⚠️ Failed to add comments to Word document: {e}")
        import traceback
        traceback.print_exc()
        print("   Markdown report is still available.")
