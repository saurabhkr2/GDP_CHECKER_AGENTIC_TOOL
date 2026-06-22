"""
Unit tests for AI check functions
Tests function signatures and basic structure
"""
import pytest
import sys
import os
import inspect

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_checks
from models import Finding


class TestAICheckFunctionSignatures:
    """Test that all AI check functions exist and have correct signatures"""
    
    def test_ai_check_na_justification_exists(self):
        """Test N/A justification check function exists"""
        assert hasattr(ai_checks, 'ai_check_na_justification')
        func = ai_checks.ai_check_na_justification
        sig = inspect.signature(func)
        assert 'client' in sig.parameters
        assert 'model' in sig.parameters
        assert 'doc_text' in sig.parameters
    def test_ai_check_na_justification_exists(self):
        """Test N/A justification check function exists"""
        assert hasattr(ai_checks, 'ai_check_na_justification')
        func = ai_checks.ai_check_na_justification
        sig = inspect.signature(func)
        assert 'client' in sig.parameters
        assert 'model' in sig.parameters
        assert 'doc_text' in sig.parameters
    
    def test_ai_check_requirement_testability_exists(self):
        """Test testability check function exists"""
        assert hasattr(ai_checks, 'ai_check_requirement_testability')
    
    def test_ai_check_terminology_consistency_exists(self):
        """Test terminology check function exists"""
        assert hasattr(ai_checks, 'ai_check_terminology_consistency')
    
    def test_ai_check_revision_specificity_exists(self):
        """Test revision specificity check function exists"""
        assert hasattr(ai_checks, 'ai_check_revision_specificity')
    
    def test_ai_check_spelling_grammar_exists(self):
        """Test spelling and grammar check function exists"""
        assert hasattr(ai_checks, 'ai_check_spelling_grammar')
    
    def test_ai_check_template_compliance_exists(self):
        """Test template compliance check function exists"""
        assert hasattr(ai_checks, 'ai_check_template_compliance')
    
    def test_ai_check_open_issues_exists(self):
        """Test open issues check function exists"""
        assert hasattr(ai_checks, 'ai_check_open_issues')
    
    def test_ai_check_test_verdicts_exists(self):
        """Test test verdicts check function exists"""
        assert hasattr(ai_checks, 'ai_check_test_verdicts')
    
    def test_ai_check_test_traceability_exists(self):
        """Test test traceability check function exists"""
        assert hasattr(ai_checks, 'ai_check_test_traceability')
    
    def test_ai_check_authorship_exists(self):
        """Test authorship check function exists"""
        assert hasattr(ai_checks, 'ai_check_authorship')
    
    def test_ai_check_external_files_qms_exists(self):
        """Test external files QMS check function exists"""
        assert hasattr(ai_checks, 'ai_check_external_files_qms')
    
    def test_ai_check_acronym_definitions_exists(self):
        """Test acronym definitions check function exists"""
        assert hasattr(ai_checks, 'ai_check_acronym_definitions')
    
    def test_ai_check_date_format_exists(self):
        """Test date format check function exists"""
        assert hasattr(ai_checks, 'ai_check_date_format')
    
    def test_ai_check_double_spaces_exists(self):
        """Test double spaces check function exists"""
        assert hasattr(ai_checks, 'ai_check_double_spaces')
    
    def test_ai_check_risky_modals_exists(self):
        """Test risky modals check function exists"""
        assert hasattr(ai_checks, 'ai_check_risky_modals')
    
    def test_ai_check_figures_tables_exists(self):
        """Test figures and tables check function exists"""
        assert hasattr(ai_checks, 'ai_check_figures_tables')
    
    def test_ai_check_placeholders_exists(self):
        """Test placeholders check function exists"""
        assert hasattr(ai_checks, 'ai_check_placeholders')
    
    def test_ai_check_brand_casing_exists(self):
        """Test brand casing check function exists"""
        assert hasattr(ai_checks, 'ai_check_brand_casing')
    
    def test_ai_check_section_numbering_exists(self):
        """Test section numbering check function exists"""
        assert hasattr(ai_checks, 'ai_check_section_numbering')
    
    def test_ai_check_toc_validation_exists(self):
        """Test TOC validation check function exists"""
        assert hasattr(ai_checks, 'ai_check_toc_validation')
    
    def test_ai_check_template_id_exists(self):
        """Test template ID check function exists"""
        assert hasattr(ai_checks, 'ai_check_template_id')
    
    def test_all_21_functions_callable(self):
        """Test that all 21 AI check functions are callable"""
        functions = [
            'ai_check_na_justification',
            'ai_check_requirement_testability',
            'ai_check_terminology_consistency',
            'ai_check_revision_specificity',
            'ai_check_spelling_grammar',
            'ai_check_template_compliance',
            'ai_check_open_issues',
            'ai_check_test_verdicts',
            'ai_check_test_traceability',
            'ai_check_authorship',
            'ai_check_external_files_qms',
            'ai_check_acronym_definitions',
            'ai_check_date_format',
            'ai_check_double_spaces',
            'ai_check_risky_modals',
            'ai_check_figures_tables',
            'ai_check_placeholders',
            'ai_check_brand_casing',
            'ai_check_section_numbering',
            'ai_check_toc_validation',
            'ai_check_template_id'
        ]
        
        for func_name in functions:
            assert hasattr(ai_checks, func_name), f"Missing function: {func_name}"
            func = getattr(ai_checks, func_name)
            assert callable(func), f"Not callable: {func_name}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
