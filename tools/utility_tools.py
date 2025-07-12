"""
Utility tools for LangChain agents.

This module provides general-purpose tools that can be used by any agent
in the Luca project for common operations like text processing, calculations,
and data formatting.
"""

import logging
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class TextProcessingInput(BaseModel):
    """Input schema for text processing operations."""
    text: str = Field(description="Text to process")
    operation: str = Field(
        description="Operation to perform: 'clean', 'extract_keywords', 'word_count', 'summarize'"
    )


class CalculationInput(BaseModel):
    """Input schema for mathematical calculations."""
    expression: str = Field(
        description="Mathematical expression to evaluate (e.g., '2 + 3 * 4')"
    )


class DateTimeInput(BaseModel):
    """Input schema for date/time operations."""
    operation: str = Field(
        description="Operation: 'current_time', 'add_days', 'format_date'"
    )
    date_string: Optional[str] = Field(
        None, 
        description="Date string for operations (ISO format: YYYY-MM-DD)"
    )
    days: Optional[int] = Field(
        None,
        description="Number of days to add/subtract"
    )
    format_string: Optional[str] = Field(
        None,
        description="Format string for date formatting (e.g., '%B %d, %Y')"
    )


class DataFormatInput(BaseModel):
    """Input schema for data formatting operations."""
    data: str = Field(description="Data to format (JSON string or delimited text)")
    format_type: str = Field(
        description="Output format: 'table', 'json', 'csv', 'list'"
    )
    delimiter: Optional[str] = Field(
        default=",",
        description="Delimiter for parsing delimited text"
    )


@tool("process_text", args_schema=TextProcessingInput)
def process_text_tool(text: str, operation: str) -> str:
    """
    Process text using various operations.
    
    Available operations:
    - 'clean': Remove extra whitespace and normalize text
    - 'extract_keywords': Extract potential keywords from text
    - 'word_count': Count words, characters, and sentences
    - 'summarize': Create a brief summary (simple truncation)
    
    Args:
        text: Text to process
        operation: Type of processing to perform
        
    Returns:
        Processed text or analysis results
    """
    try:
        text = text.strip()
        
        if operation == 'clean':
            # Remove extra whitespace, normalize line endings
            cleaned = re.sub(r'\s+', ' ', text)
            cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
            return cleaned.strip()
        
        elif operation == 'extract_keywords':
            # Simple keyword extraction (words longer than 3 chars, remove common words)
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'this', 'that', 'these', 'those'}
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            keywords = [word for word in set(words) if word not in stop_words]
            return ', '.join(sorted(keywords)[:20])  # Top 20 keywords
        
        elif operation == 'word_count':
            words = len(text.split())
            chars = len(text)
            chars_no_spaces = len(text.replace(' ', ''))
            sentences = len(re.findall(r'[.!?]+', text))
            
            return f"Words: {words}, Characters: {chars}, Characters (no spaces): {chars_no_spaces}, Sentences: {sentences}"
        
        elif operation == 'summarize':
            # Simple summarization by taking first few sentences
            sentences = re.split(r'[.!?]+', text)
            summary_sentences = sentences[:3]  # First 3 sentences
            summary = '. '.join(s.strip() for s in summary_sentences if s.strip())
            if len(summary) > 200:
                summary = summary[:200] + "..."
            return summary
        
        else:
            return f"Unknown operation: {operation}. Available operations: clean, extract_keywords, word_count, summarize"
    
    except Exception as e:
        logger.error(f"Error in process_text_tool: {e}")
        return f"Error processing text: {str(e)}"


@tool("calculate", args_schema=CalculationInput)
def calculate_tool(expression: str) -> str:
    """
    Perform mathematical calculations.
    
    Safely evaluates mathematical expressions with basic operations.
    Supports +, -, *, /, **, (), and common math functions.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Result of the calculation
    """
    try:
        # Security: Only allow safe mathematical operations
        allowed_chars = set('0123456789+-*/().** ')
        allowed_names = {'abs', 'round', 'min', 'max', 'pow', 'sqrt'}
        
        # Check for dangerous patterns
        if any(char not in allowed_chars for char in expression if char.isalnum() == False):
            dangerous_chars = [char for char in expression if char not in allowed_chars and not char.isalnum()]
            if dangerous_chars:
                return f"Expression contains unsafe characters: {dangerous_chars}"
        
        # Replace some common math functions
        safe_expression = expression.replace('sqrt', 'pow')
        
        # Evaluate safely
        try:
            result = eval(safe_expression, {"__builtins__": {}}, {
                "abs": abs, "round": round, "min": min, "max": max, "pow": pow
            })
            return f"{expression} = {result}"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except OverflowError:
            return "Error: Result too large"
        except ValueError as ve:
            return f"Error: Invalid value - {ve}"
    
    except Exception as e:
        logger.error(f"Error in calculate_tool: {e}")
        return f"Error calculating expression: {str(e)}"


@tool("datetime_operations", args_schema=DateTimeInput)
def datetime_operations_tool(
    operation: str,
    date_string: Optional[str] = None,
    days: Optional[int] = None,
    format_string: Optional[str] = None
) -> str:
    """
    Perform date and time operations.
    
    Available operations:
    - 'current_time': Get current date and time
    - 'add_days': Add/subtract days from a date
    - 'format_date': Format a date string
    
    Args:
        operation: Type of operation to perform
        date_string: Date in ISO format (YYYY-MM-DD) for operations
        days: Number of days to add (positive) or subtract (negative)
        format_string: Format string for date formatting
        
    Returns:
        Formatted date/time result
    """
    try:
        if operation == 'current_time':
            now = datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S")
        
        elif operation == 'add_days':
            if not date_string or days is None:
                return "Error: date_string and days are required for add_days operation"
            
            base_date = datetime.fromisoformat(date_string)
            new_date = base_date + timedelta(days=days)
            return new_date.strftime("%Y-%m-%d")
        
        elif operation == 'format_date':
            if not date_string:
                return "Error: date_string is required for format_date operation"
            
            date_obj = datetime.fromisoformat(date_string)
            if format_string:
                return date_obj.strftime(format_string)
            else:
                return date_obj.strftime("%B %d, %Y")  # Default: "January 01, 2024"
        
        else:
            return f"Unknown operation: {operation}. Available operations: current_time, add_days, format_date"
    
    except ValueError as ve:
        return f"Error: Invalid date format - {ve}"
    except Exception as e:
        logger.error(f"Error in datetime_operations_tool: {e}")
        return f"Error with date/time operation: {str(e)}"


@tool("format_data", args_schema=DataFormatInput)
def format_data_tool(data: str, format_type: str, delimiter: str = ",") -> str:
    """
    Format data into different structures.
    
    Converts data between different formats for better presentation.
    
    Available formats:
    - 'table': Format as a simple text table
    - 'json': Format as JSON (if data is structured)
    - 'csv': Format as CSV
    - 'list': Format as a bulleted list
    
    Args:
        data: Data to format (JSON string or delimited text)
        format_type: Output format type
        delimiter: Delimiter for parsing delimited text
        
    Returns:
        Formatted data string
    """
    try:
        if format_type == 'json':
            # Try to parse and pretty-format JSON
            try:
                parsed = json.loads(data)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return "Error: Invalid JSON data"
        
        elif format_type == 'list':
            # Convert to bulleted list
            if data.startswith('[') and data.endswith(']'):
                # Try JSON array
                try:
                    items = json.loads(data)
                    return '\n'.join(f"• {item}" for item in items)
                except json.JSONDecodeError:
                    pass
            
            # Try delimited text
            items = data.split(delimiter)
            return '\n'.join(f"• {item.strip()}" for item in items if item.strip())
        
        elif format_type == 'csv':
            # Ensure proper CSV formatting
            lines = data.strip().split('\n')
            csv_lines = []
            for line in lines:
                if delimiter in line:
                    # Already delimited
                    csv_lines.append(line)
                else:
                    # Single value per line
                    csv_lines.append(line)
            return '\n'.join(csv_lines)
        
        elif format_type == 'table':
            # Simple table formatting
            lines = data.strip().split('\n')
            if len(lines) == 1:
                # Single line, try to split by delimiter
                items = data.split(delimiter)
                if len(items) > 1:
                    # Create a simple two-column table
                    table_lines = ["Item | Value", "---- | -----"]
                    for i, item in enumerate(items):
                        table_lines.append(f"{i+1} | {item.strip()}")
                    return '\n'.join(table_lines)
            
            # Multi-line data
            table_lines = ["Line | Content", "---- | -------"]
            for i, line in enumerate(lines[:10]):  # Limit to 10 lines
                table_lines.append(f"{i+1} | {line.strip()}")
            return '\n'.join(table_lines)
        
        else:
            return f"Unknown format: {format_type}. Available formats: table, json, csv, list"
    
    except Exception as e:
        logger.error(f"Error in format_data_tool: {e}")
        return f"Error formatting data: {str(e)}"


@tool("validate_input")
def validate_input_tool(input_data: str, validation_type: str = "email") -> str:
    """
    Validate different types of input data.
    
    Available validation types:
    - 'email': Check if string is a valid email format
    - 'url': Check if string is a valid URL format
    - 'number': Check if string is a valid number
    - 'date': Check if string is a valid date
    
    Args:
        input_data: Data to validate
        validation_type: Type of validation to perform
        
    Returns:
        Validation result and feedback
    """
    try:
        input_data = input_data.strip()
        
        if validation_type == 'email':
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = re.match(email_pattern, input_data) is not None
            return f"Email '{input_data}' is {'valid' if is_valid else 'invalid'}"
        
        elif validation_type == 'url':
            url_pattern = r'^https?://.+\..+'
            is_valid = re.match(url_pattern, input_data) is not None
            return f"URL '{input_data}' is {'valid' if is_valid else 'invalid'}"
        
        elif validation_type == 'number':
            try:
                float(input_data)
                return f"'{input_data}' is a valid number"
            except ValueError:
                return f"'{input_data}' is not a valid number"
        
        elif validation_type == 'date':
            try:
                datetime.fromisoformat(input_data)
                return f"'{input_data}' is a valid date"
            except ValueError:
                return f"'{input_data}' is not a valid date format (expected: YYYY-MM-DD)"
        
        else:
            return f"Unknown validation type: {validation_type}. Available types: email, url, number, date"
    
    except Exception as e:
        logger.error(f"Error in validate_input_tool: {e}")
        return f"Error validating input: {str(e)}"


def get_utility_tools() -> List:
    """
    Get all available utility tools.
    
    Returns:
        List of LangChain tool functions for utility operations
    """
    return [
        process_text_tool,
        calculate_tool,
        datetime_operations_tool,
        format_data_tool,
        validate_input_tool
    ]