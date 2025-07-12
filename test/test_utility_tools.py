"""
Unit tests for utility tools (LangChain tools).

These tests verify that utility LangChain tools work correctly outside of the LangGraph context.
Utility tools don't require database connections, so they can be tested reliably.
"""

import pytest
from datetime import datetime

from tools.utility_tools import (
    process_text_tool,
    calculate_tool,
    datetime_operations_tool,
    format_data_tool,
    validate_input_tool
)


class TestProcessTextTool:
    """Test text processing tool functionality."""
    
    def test_process_text_clean_operation(self):
        """Test text cleaning operation."""
        messy_text = "  This   is    messy   text  \n\n\n  with   extra   spaces  "
        
        result = process_text_tool.invoke({
            "text": messy_text,
            "operation": "clean"
        })
        
        assert isinstance(result, str)
        expected = "This is messy text with extra spaces"
        assert result == expected
    
    def test_process_text_word_count_operation(self):
        """Test word count operation."""
        text = "Hello world! This is a test sentence."
        
        result = process_text_tool.invoke({
            "text": text,
            "operation": "word_count"
        })
        
        assert isinstance(result, str)
        assert "Words: 7" in result
        assert "Characters:" in result
        assert "Sentences:" in result
    
    def test_process_text_extract_keywords_operation(self):
        """Test keyword extraction operation."""
        text = "This is a test about database management systems and SQL queries"
        
        result = process_text_tool.invoke({
            "text": text,
            "operation": "extract_keywords"
        })
        
        assert isinstance(result, str)
        # Should extract meaningful words (length > 3, not stop words)
        keywords = result.split(", ")
        assert len(keywords) > 0
        assert any(len(word) > 3 for word in keywords)
    
    def test_process_text_summarize_operation(self):
        """Test text summarization operation."""
        text = "First sentence here. Second sentence follows. Third sentence ends it."
        
        result = process_text_tool.invoke({
            "text": text,
            "operation": "summarize"
        })
        
        assert isinstance(result, str)
        assert len(result) <= len(text)  # Summary should be shorter or equal
    
    def test_process_text_invalid_operation(self):
        """Test invalid operation handling."""
        result = process_text_tool.invoke({
            "text": "test text",
            "operation": "invalid_operation"
        })
        
        assert isinstance(result, str)
        assert "Unknown operation" in result


class TestCalculateTool:
    """Test mathematical calculation tool."""
    
    def test_calculate_basic_operations(self):
        """Test basic mathematical operations."""
        test_cases = [
            ("2 + 3", "5"),
            ("10 - 4", "6"),
            ("3 * 4", "12"),
            ("15 / 3", "5.0"),
            ("2 ** 3", "8"),
        ]
        
        for expression, expected in test_cases:
            result = calculate_tool.invoke({"expression": expression})
            assert isinstance(result, str)
            assert expected in result
            assert expression in result
    
    def test_calculate_complex_expression(self):
        """Test complex mathematical expression."""
        result = calculate_tool.invoke({"expression": "2 + 3 * 4 - 1"})
        
        assert isinstance(result, str)
        assert "13" in result  # 2 + (3 * 4) - 1 = 13
    
    def test_calculate_with_parentheses(self):
        """Test calculation with parentheses."""
        result = calculate_tool.invoke({"expression": "(2 + 3) * 4"})
        
        assert isinstance(result, str)
        assert "20" in result  # (2 + 3) * 4 = 20
    
    def test_calculate_division_by_zero(self):
        """Test division by zero handling."""
        result = calculate_tool.invoke({"expression": "10 / 0"})
        
        assert isinstance(result, str)
        assert "Division by zero" in result
    
    def test_calculate_unsafe_expression(self):
        """Test that unsafe expressions are rejected."""
        unsafe_expressions = [
            "__import__('os').system('ls')",
            "exec('print(1)')",
            "eval('1+1')"
        ]
        
        for expr in unsafe_expressions:
            result = calculate_tool.invoke({"expression": expr})
            assert isinstance(result, str)
            # Should either be rejected or safely handled
            assert "error" in result.lower() or "unsafe" in result.lower()


class TestDateTimeOperationsTool:
    """Test date/time operations tool."""
    
    def test_datetime_current_time(self):
        """Test getting current time."""
        result = datetime_operations_tool.invoke({"operation": "current_time"})
        
        assert isinstance(result, str)
        # Should be in YYYY-MM-DD HH:MM:SS format
        assert len(result) == 19
        assert result[4] == "-" and result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":" and result[16] == ":"
    
    def test_datetime_add_days(self):
        """Test adding days to a date."""
        result = datetime_operations_tool.invoke({
            "operation": "add_days",
            "date_string": "2024-01-01",
            "days": 10
        })
        
        assert isinstance(result, str)
        assert result == "2024-01-11"
    
    def test_datetime_subtract_days(self):
        """Test subtracting days from a date."""
        result = datetime_operations_tool.invoke({
            "operation": "add_days",
            "date_string": "2024-01-15",
            "days": -5
        })
        
        assert isinstance(result, str)
        assert result == "2024-01-10"
    
    def test_datetime_format_date(self):
        """Test date formatting."""
        result = datetime_operations_tool.invoke({
            "operation": "format_date",
            "date_string": "2024-01-15",
            "format_string": "%B %d, %Y"
        })
        
        assert isinstance(result, str)
        assert "January 15, 2024" == result
    
    def test_datetime_format_date_default(self):
        """Test date formatting with default format."""
        result = datetime_operations_tool.invoke({
            "operation": "format_date",
            "date_string": "2024-12-25"
        })
        
        assert isinstance(result, str)
        assert "December 25, 2024" == result
    
    def test_datetime_invalid_date(self):
        """Test invalid date handling."""
        result = datetime_operations_tool.invoke({
            "operation": "add_days",
            "date_string": "invalid-date",
            "days": 1
        })
        
        assert isinstance(result, str)
        assert "Error" in result and "Invalid date format" in result


class TestFormatDataTool:
    """Test data formatting tool."""
    
    def test_format_data_as_list(self):
        """Test formatting data as bulleted list."""
        data = "apple,banana,cherry"
        
        result = format_data_tool.invoke({
            "data": data,
            "format_type": "list"
        })
        
        assert isinstance(result, str)
        assert "• apple" in result
        assert "• banana" in result
        assert "• cherry" in result
    
    def test_format_data_as_json(self):
        """Test formatting data as JSON."""
        data = '{"name": "test", "value": 123}'
        
        result = format_data_tool.invoke({
            "data": data,
            "format_type": "json"
        })
        
        assert isinstance(result, str)
        # Should be properly formatted JSON
        assert '"name": "test"' in result
        assert '"value": 123' in result
    
    def test_format_data_as_table(self):
        """Test formatting data as table."""
        data = "Name,Age\nJohn,25\nJane,30"
        
        result = format_data_tool.invoke({
            "data": data,
            "format_type": "table"
        })
        
        assert isinstance(result, str)
        assert "Line | Content" in result
        assert "Name,Age" in result
    
    def test_format_data_invalid_json(self):
        """Test invalid JSON handling."""
        data = '{"invalid": json}'
        
        result = format_data_tool.invoke({
            "data": data,
            "format_type": "json"
        })
        
        assert isinstance(result, str)
        assert "Invalid JSON" in result


class TestValidateInputTool:
    """Test input validation tool."""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        result = validate_input_tool.invoke({
            "input_data": "test@example.com",
            "validation_type": "email"
        })
        
        assert isinstance(result, str)
        assert "valid" in result.lower()
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        result = validate_input_tool.invoke({
            "input_data": "not-an-email",
            "validation_type": "email"
        })
        
        assert isinstance(result, str)
        assert "invalid" in result.lower()
    
    def test_validate_url_valid(self):
        """Test valid URL validation."""
        result = validate_input_tool.invoke({
            "input_data": "https://example.com",
            "validation_type": "url"
        })
        
        assert isinstance(result, str)
        assert "valid" in result.lower()
    
    def test_validate_url_invalid(self):
        """Test invalid URL validation."""
        result = validate_input_tool.invoke({
            "input_data": "not-a-url",
            "validation_type": "url"
        })
        
        assert isinstance(result, str)
        assert "invalid" in result.lower()
    
    def test_validate_number_valid(self):
        """Test valid number validation."""
        test_cases = ["123", "45.67", "-89", "0"]
        
        for number in test_cases:
            result = validate_input_tool.invoke({
                "input_data": number,
                "validation_type": "number"
            })
            
            assert isinstance(result, str)
            assert "valid number" in result
    
    def test_validate_number_invalid(self):
        """Test invalid number validation."""
        result = validate_input_tool.invoke({
            "input_data": "not-a-number",
            "validation_type": "number"
        })
        
        assert isinstance(result, str)
        assert "not a valid number" in result
    
    def test_validate_date_valid(self):
        """Test valid date validation."""
        result = validate_input_tool.invoke({
            "input_data": "2024-01-15",
            "validation_type": "date"
        })
        
        assert isinstance(result, str)
        assert "valid date" in result
    
    def test_validate_date_invalid(self):
        """Test invalid date validation."""
        result = validate_input_tool.invoke({
            "input_data": "not-a-date",
            "validation_type": "date"
        })
        
        assert isinstance(result, str)
        assert "not a valid date" in result


class TestToolSchemas:
    """Test that tools have proper schemas and can be called correctly."""
    
    def test_all_tools_have_required_attributes(self):
        """Test that all tools have required LangChain tool attributes."""
        tools = [
            process_text_tool,
            calculate_tool,
            datetime_operations_tool,
            format_data_tool,
            validate_input_tool
        ]
        
        for tool in tools:
            # Check tool has required attributes
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'invoke')
            
            # Check attributes are not empty
            assert isinstance(tool.name, str) and len(tool.name) > 0
            assert isinstance(tool.description, str) and len(tool.description) > 0
    
    def test_tools_accept_dict_input(self):
        """Test that all tools accept dictionary input (LangChain standard)."""
        try:
            # Test that tools accept dict input and return strings
            result1 = process_text_tool.invoke({"text": "test", "operation": "clean"})
            result2 = calculate_tool.invoke({"expression": "1+1"})
            result3 = datetime_operations_tool.invoke({"operation": "current_time"})
            result4 = format_data_tool.invoke({"data": "a,b,c", "format_type": "list"})
            result5 = validate_input_tool.invoke({"input_data": "test", "validation_type": "email"})
            
            # All should return strings
            results = [result1, result2, result3, result4, result5]
            assert all(isinstance(r, str) for r in results)
            assert all(len(r) > 0 for r in results)
            
        except Exception as e:
            pytest.fail(f"Tools should accept dict input without errors: {e}")


@pytest.mark.tools
class TestToolsIntegration:
    """Integration tests combining multiple utility tools."""
    
    def test_text_processing_workflow(self):
        """Test a realistic text processing workflow."""
        # Step 1: Clean some messy text
        messy_text = "  This   is    a   test   about   database   design  "
        clean_result = process_text_tool.invoke({
            "text": messy_text,
            "operation": "clean"
        })
        
        # Step 2: Count words in the cleaned text
        count_result = process_text_tool.invoke({
            "text": clean_result,
            "operation": "word_count"
        })
        
        # Step 3: Extract keywords
        keywords_result = process_text_tool.invoke({
            "text": clean_result,
            "operation": "extract_keywords"
        })
        
        # Step 4: Format keywords as a list
        list_result = format_data_tool.invoke({
            "data": keywords_result,
            "format_type": "list"
        })
        
        # All steps should succeed
        results = [clean_result, count_result, keywords_result, list_result]
        assert all(isinstance(r, str) and len(r) > 0 for r in results)
        
        # Verify content
        assert "This is a test about database design" in clean_result
        assert "Words:" in count_result
        assert "database" in keywords_result
        assert "•" in list_result
    
    def test_calculation_and_formatting_workflow(self):
        """Test calculation with result formatting."""
        # Step 1: Perform calculation
        calc_result = calculate_tool.invoke({"expression": "15 * 3 + 7"})
        
        # Step 2: Get current date
        date_result = datetime_operations_tool.invoke({"operation": "current_time"})
        
        # Step 3: Validate calculation result contains number
        # Extract number from calc_result
        number_part = calc_result.split("= ")[1] if "= " in calc_result else "52"
        validation_result = validate_input_tool.invoke({
            "input_data": number_part,
            "validation_type": "number"
        })
        
        # All should succeed
        assert "52" in calc_result  # 15 * 3 + 7 = 52
        assert len(date_result) == 19  # YYYY-MM-DD HH:MM:SS format
        assert "valid number" in validation_result