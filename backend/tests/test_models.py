"""
Unit tests for data models
Tests Finding, Report, ExtractedDoc, and Para classes
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Finding, Report, ExtractedDoc, Para


class TestFinding:
    """Test Finding model"""
    
    def test_finding_creation(self):
        """Test creating a Finding instance"""
        finding = Finding(
            check_id="AI01_NA_Justification",
            severity="Major",
            message="N/A without justification found",
            evidence="Section 1.1: N/A is used",
            section="Section 1.1"
        )
        
        assert finding.check_id == "AI01_NA_Justification"
        assert finding.severity == "Major"
        assert finding.message == "N/A without justification found"
        assert finding.evidence == "Section 1.1: N/A is used"
        assert finding.section == "Section 1.1"
    
    def test_finding_minimal(self):
        """Test Finding with minimal required fields"""
        finding = Finding(
            check_id="AI02_Testability",
            severity="Moderate",
            message="Requirement is not testable"
        )
        
        assert finding.check_id == "AI02_Testability"
        assert finding.severity == "Moderate"
        assert finding.message == "Requirement is not testable"
        assert finding.evidence == ""  # Default value
        assert finding.span is None  # Default value
        assert finding.section is None  # Default value
    
    def test_finding_with_span(self):
        """Test Finding with span tuple"""
        finding = Finding(
            check_id="AI03_Terminology",
            severity="Minor",
            message="Inconsistent terminology",
            span=(100, 150)
        )
        
        assert finding.span == (100, 150)
        assert isinstance(finding.span, tuple)
        assert len(finding.span) == 2
    
    def test_finding_dataclass_fields(self):
        """Test that Finding is a proper dataclass"""
        finding = Finding("TEST", "Major", "Test message")
        assert hasattr(finding, 'check_id')
        assert hasattr(finding, 'severity')
        assert hasattr(finding, 'message')
        assert hasattr(finding, 'evidence')
        assert hasattr(finding, 'span')
        assert hasattr(finding, 'section')


class TestPara:
    """Test Para model"""
    
    def test_para_creation(self):
        """Test creating a Para instance"""
        para = Para(
            text="This is a test paragraph.",
            style="Normal"
        )
        
        assert para.text == "This is a test paragraph."
        assert para.style == "Normal"
    
    def test_para_minimal(self):
        """Test Para with minimal fields"""
        para = Para(text="Test text")
        
        assert para.text == "Test text"
        assert para.style == ""  # Default value
    
    def test_para_with_heading_style(self):
        """Test Para with heading style"""
        para = Para(text="Section 1", style="Heading 1")
        
        assert para.text == "Section 1"
        assert para.style == "Heading 1"


class TestExtractedDoc:
    """Test ExtractedDoc model"""
    
    def test_extracted_doc_creation(self):
        """Test creating an ExtractedDoc instance"""
        doc = ExtractedDoc()
        
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.raw_text == ""
        assert doc.headings == []
    
    def test_extracted_doc_with_paragraphs(self):
        """Test ExtractedDoc with paragraphs"""
        para1 = Para("Introduction text", "Normal")
        para2 = Para("Section 1", "Heading 1")
        
        doc = ExtractedDoc(
            paragraphs=[para1, para2],
            raw_text="Introduction text\nSection 1"
        )
        
        assert len(doc.paragraphs) == 2
        assert doc.paragraphs[0].text == "Introduction text"
        assert doc.paragraphs[1].style == "Heading 1"
        assert "Introduction text" in doc.raw_text
    
    def test_extracted_doc_with_tables(self):
        """Test ExtractedDoc with tables"""
        table1 = [
            ["Header 1", "Header 2"],
            ["Cell 1", "Cell 2"]
        ]
        table2 = [
            ["Col A", "Col B"],
            ["Data A", "Data B"]
        ]
        
        doc = ExtractedDoc(tables=[table1, table2])
        
        assert len(doc.tables) == 2
        assert len(doc.tables[0]) == 2  # 2 rows
        assert len(doc.tables[0][0]) == 2  # 2 columns
        assert doc.tables[0][0][0] == "Header 1"
        assert doc.tables[1][1][1] == "Data B"
    
    def test_extracted_doc_with_headings(self):
        """Test ExtractedDoc with headings list"""
        doc = ExtractedDoc(
            headings=["1. Introduction", "2. Requirements", "2.1 Functional"]
        )
        
        assert len(doc.headings) == 3
        assert "1. Introduction" in doc.headings
        assert "2.1 Functional" in doc.headings
    
    def test_extracted_doc_complete(self):
        """Test ExtractedDoc with all fields"""
        para1 = Para("Intro", "Normal")
        table1 = [["A", "B"]]
        
        doc = ExtractedDoc(
            paragraphs=[para1],
            tables=[table1],
            raw_text="Intro A B",
            headings=["Section 1"]
        )
        
        assert len(doc.paragraphs) == 1
        assert len(doc.tables) == 1
        assert doc.raw_text == "Intro A B"
        assert len(doc.headings) == 1


class TestReport:
    """Test Report model"""
    
    def test_report_creation(self):
        """Test creating a Report instance"""
        report = Report()
        
        assert isinstance(report.ai_findings, dict)
        assert isinstance(report.brand_findings, list)
        assert isinstance(report.meta, dict)
    
    def test_report_with_ai_findings(self):
        """Test Report with AI findings"""
        finding1 = Finding("AI01", "Major", "Issue 1")
        finding2 = Finding("AI01", "Major", "Issue 2")
        finding3 = Finding("AI02", "Minor", "Issue 3")
        
        report = Report()
        report.ai_findings["AI01"].append(finding1)
        report.ai_findings["AI01"].append(finding2)
        report.ai_findings["AI02"].append(finding3)
        
        assert len(report.ai_findings["AI01"]) == 2
        assert len(report.ai_findings["AI02"]) == 1
        assert report.ai_findings["AI01"][0].message == "Issue 1"
    
    def test_report_with_brand_findings(self):
        """Test Report with brand findings"""
        finding1 = Finding("CHK20", "Minor", "Brand casing issue")
        finding2 = Finding("CHK03", "Moderate", "Acronym undefined")
        
        report = Report(brand_findings=[finding1, finding2])
        
        assert len(report.brand_findings) == 2
        assert report.brand_findings[0].check_id == "CHK20"
        assert report.brand_findings[1].severity == "Moderate"
    
    def test_report_with_meta(self):
        """Test Report with metadata"""
        report = Report(
            meta={
                "document_name": "Test.docx",
                "timestamp": "2025-12-13",
                "total_checks": 21
            }
        )
        
        assert report.meta["document_name"] == "Test.docx"
        assert report.meta["timestamp"] == "2025-12-13"
        assert report.meta["total_checks"] == 21
    
    def test_report_defaultdict_behavior(self):
        """Test that ai_findings behaves like defaultdict"""
        report = Report()
        
        # Access non-existent key should create empty list
        report.ai_findings["AI99"].append(Finding("AI99", "Major", "Test"))
        
        assert len(report.ai_findings["AI99"]) == 1
        assert report.ai_findings["AI99"][0].message == "Test"


class TestModelIntegration:
    """Test integration between models"""
    
    def test_complete_workflow(self):
        """Test creating a complete document analysis workflow"""
        # Create document structure
        para1 = Para("Introduction", "Heading 1")
        para2 = Para("This document describes requirements.", "Normal")
        para3 = Para("Requirements", "Heading 1")
        para4 = Para("The system shall implement feature X.", "Normal")
        
        doc = ExtractedDoc(
            paragraphs=[para1, para2, para3, para4],
            raw_text="Introduction\nThis document describes requirements.\nRequirements\nThe system shall implement feature X.",
            headings=["Introduction", "Requirements"]
        )
        
        # Create findings
        finding1 = Finding(
            check_id="AI01_NA_Justification",
            severity="Major",
            message="N/A without justification",
            evidence="Section 2.1",
            section="Requirements"
        )
        
        finding2 = Finding(
            check_id="AI02_Testability",
            severity="Moderate",
            message="Vague requirement",
            evidence="feature X",
            section="Requirements"
        )
        
        # Create report
        report = Report(
            meta={"document_name": "Test Requirements.docx"}
        )
        report.ai_findings["AI01_NA_Justification"].append(finding1)
        report.ai_findings["AI02_Testability"].append(finding2)
        
        # Verify complete structure
        assert len(doc.paragraphs) == 4
        assert len(doc.headings) == 2
        assert len(report.ai_findings) == 2
        assert report.meta["document_name"] == "Test Requirements.docx"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
    
    def test_finding_to_dict(self):
        """Test Finding to_dict method"""
        finding = Finding(
            check_id="AI02_Testability",
            severity="Moderate",
            issues=[
                {"issue": "Test issue", "suggestion": "Fix it", "location": "Page 1"}
            ]
        )
        
        result = finding.to_dict()
        
        assert result["check_id"] == "AI02_Testability"
        assert result["severity"] == "Moderate"
        assert "issues" in result
        assert len(result["issues"]) == 1
    
    def test_finding_empty_issues(self):
        """Test Finding with empty issues list"""
        finding = Finding(
            check_id="AI03_Terminology",
            severity="Minor",
            issues=[]
        )
        
        assert finding.issues == []
        assert finding.to_dict()["issues"] == []
    
    def test_finding_multiple_issues(self):
        """Test Finding with multiple issues"""
        issues = [
            {"issue": "Issue 1", "suggestion": "Fix 1", "location": "Section 1"},
            {"issue": "Issue 2", "suggestion": "Fix 2", "location": "Section 2"},
            {"issue": "Issue 3", "suggestion": "Fix 3", "location": "Section 3"}
        ]
        
        finding = Finding(
            check_id="AI04_RevisionSpecificity",
            severity="Major",
            issues=issues
        )
        
        assert len(finding.issues) == 3
    
    def test_finding_serialization(self):
        """Test Finding can be serialized to JSON"""
        finding = Finding(
            check_id="AI05_SpellingGrammar",
            severity="Minor",
            issues=[{"issue": "Typo", "suggestion": "Correct spelling", "location": "Para 2"}]
        )
        
        json_str = json.dumps(finding.to_dict())
        data = json.loads(json_str)
        
        assert data["check_id"] == "AI05_SpellingGrammar"
        assert data["severity"] == "Minor"


class TestReport:
    """Test Report model"""
    
    def test_report_creation(self):
        """Test creating a Report instance"""
        report = Report()
        
        assert isinstance(report.ai_findings, dict)
        assert isinstance(report.brand_findings, list)
        assert isinstance(report.meta, dict)
    
    def test_report_with_ai_findings(self):
        """Test Report with AI findings"""
        finding1 = Finding("AI01", "Major", "Issue 1")
        finding2 = Finding("AI01", "Major", "Issue 2")
        finding3 = Finding("AI02", "Minor", "Issue 3")
        
        report = Report()
        report.ai_findings["AI01"].append(finding1)
        report.ai_findings["AI01"].append(finding2)
        report.ai_findings["AI02"].append(finding3)
        
        assert len(report.ai_findings["AI01"]) == 2
        assert len(report.ai_findings["AI02"]) == 1
        assert report.ai_findings["AI01"][0].message == "Issue 1"
    
    def test_report_with_brand_findings(self):
        """Test Report with brand findings"""
        finding1 = Finding("CHK20", "Minor", "Brand casing issue")
        finding2 = Finding("CHK03", "Moderate", "Acronym undefined")
        
        report = Report(brand_findings=[finding1, finding2])
        
        assert len(report.brand_findings) == 2
        assert report.brand_findings[0].check_id == "CHK20"
        assert report.brand_findings[1].severity == "Moderate"
    
    def test_report_with_meta(self):
        """Test Report with metadata"""
        report = Report(
            meta={
                "document_name": "Test.docx",
                "timestamp": "2025-12-13",
                "total_checks": 21
            }
        )
        
        assert report.meta["document_name"] == "Test.docx"
        assert report.meta["timestamp"] == "2025-12-13"
        assert report.meta["total_checks"] == 21
    
    def test_report_defaultdict_behavior(self):
        """Test that ai_findings behaves like defaultdict"""
        report = Report()
        
        # Access non-existent key should create empty list
        report.ai_findings["AI99"].append(Finding("AI99", "Major", "Test"))
        
        assert len(report.ai_findings["AI99"]) == 1
        assert report.ai_findings["AI99"][0].message == "Test"


class TestExtractedDoc:
    """Test ExtractedDoc model"""
    
    def test_extracted_doc_creation(self):
        """Test creating an ExtractedDoc instance"""
        doc = ExtractedDoc()
        
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.raw_text == ""
        assert doc.headings == []
    
    def test_extracted_doc_with_paragraphs(self):
        """Test ExtractedDoc with paragraphs"""
        para1 = Para("Introduction text", "Normal")
        para2 = Para("Section 1", "Heading 1")
        
        doc = ExtractedDoc(
            paragraphs=[para1, para2],
            raw_text="Introduction text\nSection 1"
        )
        
        assert len(doc.paragraphs) == 2
        assert doc.paragraphs[0].text == "Introduction text"
        assert doc.paragraphs[1].style == "Heading 1"
        assert "Introduction text" in doc.raw_text
    
    def test_extracted_doc_with_tables(self):
        """Test ExtractedDoc with tables"""
        table1 = [
            ["Header 1", "Header 2"],
            ["Cell 1", "Cell 2"]
        ]
        table2 = [
            ["Col A", "Col B"],
            ["Data A", "Data B"]
        ]
        
        doc = ExtractedDoc(tables=[table1, table2])
        
        assert len(doc.tables) == 2
        assert len(doc.tables[0]) == 2  # 2 rows
        assert len(doc.tables[0][0]) == 2  # 2 columns
        assert doc.tables[0][0][0] == "Header 1"
        assert doc.tables[1][1][1] == "Data B"
    
    def test_extracted_doc_with_headings(self):
        """Test ExtractedDoc with headings list"""
        doc = ExtractedDoc(
            headings=["1. Introduction", "2. Requirements", "2.1 Functional"]
        )
        
        assert len(doc.headings) == 3
        assert "1. Introduction" in doc.headings
        assert "2.1 Functional" in doc.headings
    
    def test_extracted_doc_complete(self):
        """Test ExtractedDoc with all fields"""
        para1 = Para("Intro", "Normal")
        table1 = [["A", "B"]]
        
        doc = ExtractedDoc(
            paragraphs=[para1],
            tables=[table1],
            raw_text="Intro A B",
            headings=["Section 1"]
        )
        
        assert len(doc.paragraphs) == 1
        assert len(doc.tables) == 1
        assert doc.raw_text == "Intro A B"
        assert len(doc.headings) == 1


class TestModelIntegration:
    """Test integration between models"""
    
    def test_complete_workflow(self):
        """Test creating a complete document analysis workflow"""
        # Create document structure
        para1 = Para("Introduction", "Heading 1")
        para2 = Para("This document describes requirements.", "Normal")
        para3 = Para("Requirements", "Heading 1")
        para4 = Para("The system shall implement feature X.", "Normal")
        
        doc = ExtractedDoc(
            paragraphs=[para1, para2, para3, para4],
            raw_text="Introduction\nThis document describes requirements.\nRequirements\nThe system shall implement feature X.",
            headings=["Introduction", "Requirements"]
        )
        
        # Create findings
        finding1 = Finding(
            check_id="AI01_NA_Justification",
            severity="Major",
            message="N/A without justification",
            evidence="Section 2.1",
            section="Requirements"
        )
        
        finding2 = Finding(
            check_id="AI02_Testability",
            severity="Moderate",
            message="Vague requirement",
            evidence="feature X",
            section="Requirements"
        )
        
        # Create report
        report = Report(
            meta={"document_name": "Test Requirements.docx"}
        )
        report.ai_findings["AI01_NA_Justification"].append(finding1)
        report.ai_findings["AI02_Testability"].append(finding2)
        
        # Verify complete structure
        assert len(doc.paragraphs) == 4
        assert len(doc.headings) == 2
        assert len(report.ai_findings) == 2
        assert report.meta["document_name"] == "Test Requirements.docx"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
