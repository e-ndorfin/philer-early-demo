"""
Extraction Utilities

This module provides utility functions for extracting structured information from user responses.
"""

from typing import Dict, Any, List, Tuple

def format_conversation_history(history: List) -> str:
    """
    Format the conversation history for prompt templates.
    Returns most recent messages first.
    
    Args:
        history: List of (role, message) tuples
        
    Returns:
        Formatted string with each message on a new line
    """
    formatted_history = []
    for i, (role, message) in enumerate(reversed(history[-20:])):  # Get last 20 messages, reversed for most recent first
        formatted_history.append(f"{role}: {message}")
    return "\n".join(formatted_history)

def get_extraction_prompt(question_id: str, question_text: str, user_response: str, field_mapping: Dict) -> Dict[str, Any]:
    """
    Get the appropriate prompt for the question type based on field mappings.
    
    Args:
        question_id: The ID of the current question
        question_text: The text of the current question
        user_response: The user's response to extract from
        field_mapping: Dictionary mapping question IDs to field types and formats
        
    Returns:
        Dictionary with template key and data for the prompt
    """
    field_info = field_mapping.get(question_id, {"type": "text", "format": "text"})
    field_type = field_info["type"]
    field_format = field_info["format"]
    
    prompt_data = {
        "question_text": question_text,
        "question_id": question_id,
        "user_response": user_response,
        "expected_format": field_format
    }
    
    # Template names should be defined in the agent
    if field_type == "structured":
        structure_type = ""
        expected_fields = ""
        
        if question_id == "mortgage_advisor":
            structure_type = "mortgage advisor"
            expected_fields = "- Name: The mortgage advisor's full name\n- Company: Their brokerage company\n- Lender: The lending institution"
        elif question_id == "real_estate_agent":
            structure_type = "real estate agent"
            expected_fields = "- Name: The real estate agent's full name\n- Company: Their brokerage company"
        elif question_id == "home_insurance_details":
            structure_type = "insurance information"
            expected_fields = "- Company: The insurance company name\n- Advisor: The insurance advisor's name"
            
        prompt_data["structure_type"] = structure_type
        prompt_data["expected_fields"] = expected_fields
        template_key = "structured"
        
    elif field_type == "name":
        template_key = "name"
    elif field_type == "boolean":
        template_key = "boolean"
    else:
        template_key = "default"
        
    return {"template_key": template_key, "data": prompt_data}

def process_structured_field(extracted_value: str, question_id: str) -> str:
    """
    Minimal processing for structured fields, focusing on format consistency
    rather than complex parsing.
    
    Args:
        extracted_value: The raw extracted value from the LLM
        question_id: The ID of the current question
        
    Returns:
        Properly formatted string value
    """
    # Return the original value if we can't process it
    if not extracted_value:
        return extracted_value
        
    # Basic cleanup - just normalize pipe separators and whitespace
    if "|" in extracted_value:
        # Clean up whitespace around pipes
        return "|".join([part.strip() for part in extracted_value.split("|")])
    
    # For structured fields without pipes, just return the cleaned value
    return extracted_value.strip()

def is_date_question(question_text: str) -> bool:
    """
    Check if a question is asking for a date.
    
    Args:
        question_text: The text of the question
        
    Returns:
        True if the question is asking for a date, False otherwise
    """
    return any(date_term in question_text.lower() 
              for date_term in ["date of birth", "dob", "closing date", "born", "birthday"]) 