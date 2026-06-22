"""
Unit tests for document loader
Tests document extraction and processing
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doc_loader import load_docx
from models import ExtractedDoc, Para


@pytest.fixture
def mock_docx_document():
    """Mock a python-docx Document object"""
    mock_doc = Mock()
    
    # Mock paragraphs
    para1 = Mock()
    para1.text = "This is the introduction."
    para1.style = Mock()
    para1.style.name = "Normal"
    
    para2 = Mock()
    para2.text = "1. Requirements"
    para2.style = Mock()
    para2.style.name = "Heading 1"
    
    para3 = Mock()
    para3.text = "The system shall implement feature X."
    para3.style = Mock()
    para3.style.name = "Normal"
    
    para4 = Mock()
    para4.text = "1.1 Functional Requirements"
    para4.style = Mock()
    para4.style.name = "Heading 2"
    
    para5 = Mock()
    para5.text = "The system shall provide functionality Y."
    para5.style = Mock()
    para5.style.name = "Normal"
    
    mock_doc.paragraphs = [para1, para2, para3, para4, para5]
    
    # Mock tables
    mock_table = Mock()
    mock_row = Mock()
    mock_cell1 = Mock()
    mock_cell1.text = "Column 1"
    mock_cell2 = Mock()
    mock_cell2.text = "Column 2"
    mock_row.cells = [mock_cell1, mock_cell2]
    mock_table.rows = [mock_row]
    
    mock_doc.tables = [mock_table]
    
    return mock_doc


class TestLoadDocx:
    """Test document loading from DOCX files"""
    
    def test_load_docx_basic(self, mock_docx_document):
        """Test basic document loading"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            assert isinstance(result, ExtractedDoc)
            assert len(result.paragraphs) > 0
            assert len(result.raw_text) > 0
    
    def test_load_docx_includes_paragraphs(self, mock_docx_document):
        """Test that loading includes all paragraphs"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            assert "This is the introduction." in result.raw_text
            assert "1. Requirements" in result.raw_text
            assert "The system shall implement feature X." in result.raw_text
    
    def test_load_docx_includes_tables(self, mock_docx_document):
        """Test that loading includes table content"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            assert len(result.tables) > 0
            assert "Column 1" in result.raw_text or len(result.tables[0]) > 0
    
    def test_load_docx_empty_document(self):
        """Test loading from empty document"""
        mock_doc = Mock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        
        with patch('doc_loader.DocxDocument', return_value=mock_doc):
            result = load_docx("fake_path.docx")
            
            assert isinstance(result, ExtractedDoc)
            assert result.raw_text == ""
    
    def test_load_docx_paragraph_styles(self, mock_docx_document):
        """Test that paragraph styles are captured"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            # Check that we have Para objects with styles
            assert len(result.paragraphs) > 0
            assert hasattr(result.paragraphs[0], 'style')
    
    def test_load_docx_preserves_order(self, mock_docx_document):
        """Test that document order is preserved"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            # Check that text appears in expected order
            intro_pos = result.raw_text.find("This is the introduction.")
            req_pos = result.raw_text.find("1. Requirements")
            
            assert intro_pos < req_pos


class TestDocLoaderErrorHandling:
    """Test error handling in document loader"""
    
    def test_load_docx_invalid_file(self):
        """Test handling of invalid file"""
        with patch('doc_loader.DocxDocument', side_effect=Exception("Invalid file")):
            with pytest.raises(Exception):
                load_docx("invalid_path.docx")
    
    def test_load_docx_missing_style(self):
        """Test handling of paragraphs with missing style"""
        mock_doc = Mock()
        para = Mock()
        para.text = "Valid text"
        para.style = None  # Missing style
        
        mock_doc.paragraphs = [para]
        mock_doc.tables = []
        
        with patch('doc_loader.DocxDocument', return_value=mock_doc):
            # Should handle gracefully
            result = load_docx("fake_path.docx")
            assert isinstance(result, ExtractedDoc)


class TestDocLoaderHeadings:
    """Test heading extraction functionality"""
    
    def test_headings_identified(self, mock_docx_document):
        """Test that headings are properly identified"""
        with patch('doc_loader.DocxDocument', return_value=mock_docx_document):
            result = load_docx("fake_path.docx")
            
            # Check that heading paragraphs exist
            heading_styles = [p.style for p in result.paragraphs if 'Heading' in p.style]
            assert len(heading_styles) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
