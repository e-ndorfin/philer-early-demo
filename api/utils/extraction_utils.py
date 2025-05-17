"""
Extraction Utilities

This module provides utility functions for extracting structured information from user responses.
"""

from typing import Dict, Any, List, Tuple

# Mapping of question IDs to expected field types and formats
FIELD_MAPPING = {
    # Main applicant fields
    "applicant_first_name": {"type": "name", "format": "text"},
    "applicant_last_name": {"type": "name", "format": "text"},
    "applicant_dob": {"type": "date", "format": "YYYY-MM-DD"},
    "applicant_first_time_buyer": {"type": "boolean", "format": "yes/no"},
    "applicant_citizenship": {"type": "boolean", "format": "yes/no"},
    "applicant_decision_making": {"type": "boolean", "format": "yes/no"},
    
    # Spouse fields
    "spouse_first_name": {"type": "name", "format": "text"},
    "spouse_last_name": {"type": "name", "format": "text"},
    "spouse_dob": {"type": "date", "format": "YYYY-MM-DD"},
    "spouse_first_time_buyer": {"type": "boolean", "format": "yes/no"},
    "spouse_citizenship": {"type": "boolean", "format": "yes/no"},
    
    # Property information
    "transaction_type": {"type": "choice", "format": "Purchase/Sell/Refinance"},
    "property_construction_status": {"type": "text", "format": "text"},
    "property_type": {"type": "choice", "format": "text"},
    "closing_date": {"type": "date", "format": "YYYY-MM-DD"},
    "property_postal_code": {"type": "text", "format": "text"},
    "property_address": {"type": "address", "format": "text"},
    "living_at_property": {"type": "boolean", "format": "yes/no"},
    "alternative_address": {"type": "address", "format": "text"},
    "alternative_postal_code": {"type": "text", "format": "text"},
    "property_usage": {"type": "choice", "format": "text"},
    "client_living_address": {"type": "address", "format": "text"},
    "client_living_postal_code": {"type": "text", "format": "text"},
    
    # Marital status and applicants
    "marital_status": {"type": "choice", "format": "text"},
    "additional_applicants_question": {"type": "boolean", "format": "yes/no"},
    "single_additional_applicants_question": {"type": "boolean", "format": "yes/no"},
    
    # Title holding
    "multiple_owners_question": {"type": "boolean", "format": "yes/no"},
    "title_holding_question": {"type": "choice", "format": "text"},
    "primary_applicant_ownership_percentage": {"type": "percentage", "format": "number"},
    "spouse_ownership_percentage": {"type": "percentage", "format": "number"},
    "additional_applicant_ownership_percentage": {"type": "percentage", "format": "number"},
    
    # Professional info
    "mortgage_advisor": {"type": "structured", "format": "name|company|lender"},
    "real_estate_agent": {"type": "structured", "format": "name|company"},
    "home_insurance": {"type": "boolean", "format": "yes/no"},
    "home_insurance_details": {"type": "structured", "format": "company|advisor"}
}

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

def get_extraction_prompt(question_id: str, question_text: str, user_response: str, field_mapping: Dict = None) -> Dict[str, Any]:
    """
    Get the appropriate prompt for the question type based on field mappings.
    
    Args:
        question_id: The ID of the current question
        question_text: The text of the current question
        user_response: The user's response to extract from
        field_mapping: Dictionary mapping question IDs to field types and formats (defaults to FIELD_MAPPING)
        
    Returns:
        Dictionary with template key and data for the prompt
    """
    # Use the provided field_mapping or default to the module's FIELD_MAPPING
    if field_mapping is None:
        field_mapping = FIELD_MAPPING
        
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