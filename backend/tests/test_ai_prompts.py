"""
Unit tests for AI prompts configuration
Tests that all prompts are properly configured with required fields
"""
import pytest
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_checks import get_prompt, _AI_PROMPTS


class TestAIPromptsConfiguration:
    """Test AI prompts JSON configuration"""
    
    def test_prompts_file_loaded(self):
        """Test that ai_prompts.json is loaded"""
        assert _AI_PROMPTS is not None
        assert len(_AI_PROMPTS) > 0
    
    def test_all_21_checks_exist(self):
        """Test that all 21 AI checks are defined"""
        expected_checks = [
            'AI01_NA_Justification',
            'AI02_Testability',
            'AI03_Terminology',
            'AI04_RevisionSpecificity',
            'AI05_SpellingGrammar',
            'AI06_TemplateCompliance',
            'AI07_OpenIssues',
            'AI08_TestVerdicts',
            'AI09_TestTraceability',
            'AI10_Authorship',
            'AI11_ExternalFilesQMS',
            'AI12_AcronymDefinitions',
            'AI13_DateFormat',
            'AI14_DoubleSpaces',
            'AI15_RiskyModals',
            'AI16_FiguresTables',
            'AI17_Placeholders',
            'AI18_BrandCasing',
            'AI19_SectionNumbering',
            'AI20_TOCValidation',
            'AI21_TemplateID'
        ]
        
        for check in expected_checks:
            assert check in _AI_PROMPTS, f"Missing AI check: {check}"
    
    def test_required_fields_present(self):
        """Test that all prompts have required fields"""
        required_fields = ['severity', 'description', 'system_prompt', 'task']
        
        for check_id, prompt_data in _AI_PROMPTS.items():
            for field in required_fields:
                assert field in prompt_data, f"{check_id} missing required field: {field}"
    
    def test_severity_values_valid(self):
        """Test that all severity values are valid"""
        valid_severities = ['Major', 'Moderate', 'Minor']
        
        for check_id, prompt_data in _AI_PROMPTS.items():
            severity = prompt_data.get('severity')
            assert severity in valid_severities, f"{check_id} has invalid severity: {severity}"
    
    def test_no_empty_fields(self):
        """Test that no required fields are empty"""
        for check_id, prompt_data in _AI_PROMPTS.items():
            assert prompt_data.get('severity'), f"{check_id} has empty severity"
            assert prompt_data.get('description'), f"{check_id} has empty description"
            assert prompt_data.get('system_prompt'), f"{check_id} has empty system_prompt"
            assert prompt_data.get('task'), f"{check_id} has empty task"
    
    def test_get_prompt_returns_complete_data(self):
        """Test that get_prompt returns all expected fields"""
        result = get_prompt('AI01_NA_Justification')
        
        assert 'check_id' in result
        assert 'severity' in result
        assert 'system_prompt' in result
        assert 'task' in result
        assert result['check_id'] == 'AI01_NA_Justification'
    
    def test_get_prompt_variable_substitution(self):
        """Test that get_prompt substitutes variables correctly"""
        result = get_prompt('AI18_BrandCasing', brand='Philips', brand_lower='philips')
        
        assert 'Philips' in result['system_prompt'] or 'philips' in result['task']
        assert '{brand}' not in result['system_prompt']
        assert '{brand_lower}' not in result['task']
    
    def test_get_prompt_default_severity(self):
        """Test that get_prompt provides default severity for missing entries"""
        # Test with a non-existent check
        result = get_prompt('NonExistentCheck')
        assert result['severity'] == 'Moderate'  # Default value
    
    def test_severity_distribution(self):
        """Test that severity levels are reasonably distributed"""
        severity_counts = {'Major': 0, 'Moderate': 0, 'Minor': 0}
        
        for prompt_data in _AI_PROMPTS.values():
            severity = prompt_data.get('severity')
            severity_counts[severity] += 1
        
        # Ensure we have a reasonable distribution
        assert severity_counts['Major'] > 0, "Should have at least one Major severity check"
        assert severity_counts['Moderate'] > 0, "Should have at least one Moderate severity check"
        assert severity_counts['Minor'] > 0, "Should have at least one Minor severity check"
        
        print(f"\nSeverity distribution: {severity_counts}")


class TestAIPromptContent:
    """Test specific content requirements in prompts"""
    
    def test_system_prompts_request_json(self):
        """Test that system prompts request JSON format"""
        json_keywords = ['json', 'JSON', 'schema']
        
        for check_id, prompt_data in _AI_PROMPTS.items():
            system_prompt = prompt_data.get('system_prompt', '').lower()
            has_json_request = any(keyword.lower() in system_prompt for keyword in json_keywords)
            assert has_json_request, f"{check_id} system prompt doesn't request JSON format"
    
    def test_prompts_have_clear_instructions(self):
        """Test that task fields have clear instructions"""
        for check_id, prompt_data in _AI_PROMPTS.items():
            task = prompt_data.get('task', '')
            assert len(task) > 20, f"{check_id} task is too short (possibly unclear)"
    
    def test_descriptions_are_informative(self):
        """Test that descriptions explain the check purpose"""
        for check_id, prompt_data in _AI_PROMPTS.items():
            description = prompt_data.get('description', '')
            assert len(description) > 30, f"{check_id} description is too short"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
