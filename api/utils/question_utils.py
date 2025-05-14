"""
Question Utility Functions

This module provides utility functions for working with questions,
such as finding questions by ID and determining the next question.
"""

from ..questions.questions import QUESTIONS

def get_question_by_id(question_id):
    """
    Get a question by its ID
    
    Args:
        question_id (str): The ID of the question to find
        
    Returns:
        dict: The question object if found, or None if not found
    """
    for question in QUESTIONS:
        if question["id"] == question_id:
            return question
    return None

def get_next_question_id(current_question_id, state):
    """
    Determine the next question ID based on current question and state
    
    Args:
        current_question_id (str): The ID of the current question
        state (dict): The current state of the form
        
    Returns:
        str: The ID of the next question
    """
    current_question = get_question_by_id(current_question_id)
    if not current_question:
        return "welcome"  # Default to welcome if we don't have a current question
    
    next_question = current_question.get("next")
    
    # If next_question is a function, call it with the state
    if callable(next_question):
        return next_question(state)
    
    return next_question

def get_previous_question_id(current_id: str) -> str:
    """
    Get the previous question's ID based on the normal workflow sequence in QUESTIONS.
    This is a general solution that works for any question in the flow.
    
    Args:
        current_id: The ID of the current question
        
    Returns:
        The ID of the previous question, or "applicant_first_name" if not found
    """
    question_ids = [q["id"] for q in QUESTIONS]
    
    try:
        current_index = question_ids.index(current_id)
        
        if current_index > 0:
            return question_ids[current_index - 1]
    except ValueError:
        pass
        
    return "applicant_first_name"

def get_readable_field_name(question_id: str) -> str:
    """
    Convert any question ID to a human-readable field name by systematically
    analyzing the ID and question structure.
    
    Args:
        question_id: The ID of the question field
        
    Returns:
        A human-readable field name
    """
    question = get_question_by_id(question_id)
    
    parts = question_id.split('_')
    
    categories = {
        'applicant': 'your',
        'spouse': 'your spouse\'s',
        'additional_applicant': 'the additional applicant\'s',
        'property': 'the property\'s',
        'mortgage': 'the mortgage',
        'realtor': 'the realtor',
        'insurance': 'the insurance',
        'title': 'the title',
    }
    
    category = None
    category_prefix = None
    for prefix in categories:
        if question_id.startswith(prefix):
            category = categories[prefix]
            category_prefix = prefix
            break
    
    if question and question.get("text"):
        text = question["text"].lower()
        
        key_phrases = {
            "first name": "first name",
            "last name": "last name",
            "full name": "full name",
            "date of birth": "date of birth",
            "citizenship": "citizenship status",
            "canadian citizen": "citizenship status",
            "permanent resident": "citizenship status",
            "first-time": "first-time homebuyer status",
            "first time": "first-time homebuyer status",
            "marital status": "marital status",
            "married": "marital status",
            "single": "marital status",
            "email": "email address",
            "phone": "phone number",
            "address": "address",
            "postal code": "postal code",
            "closing date": "closing date",
            "buying": "transaction type",
            "selling": "transaction type",
            "refinancing": "transaction type",
            "property type": "property type",
            "condo": "property type",
            "house": "property type",
            "percentage": "ownership percentage",
            "share": "ownership percentage",
            "decision": "decision-making capacity",
            "insurance": "insurance details",
            "mortgage": "mortgage details",
            "realtor": "realtor details",
            "brokerage": "brokerage details",
            "title": "title holding"
        }
        
        for phrase, field_name in key_phrases.items():
            if phrase in text:
                if category:
                    return f"{category} {field_name}"
                return field_name
    
    if category_prefix and len(parts) > 1:
        field_parts = [part for part in parts if part not in category_prefix.split('_')]
        field = '_'.join(field_parts)
        
        field_mappings = {
            'first_name': 'first name',
            'firstname': 'first name',
            'last_name': 'last name',
            'lastname': 'last name',
            'full_name': 'full name',
            'name': 'name',
            'dob': 'date of birth',
            'birth': 'date of birth',
            'birthday': 'date of birth',
            'first_time_buyer': 'first-time homebuyer status',
            'citizenship': 'citizenship status',
            'citizen': 'citizenship status',
            'decision_making': 'decision-making capacity',
            'marital_status': 'marital status',
            'marital': 'marital status',
            'transaction_type': 'transaction type',
            'transaction': 'transaction type',
            'type': 'type',
            'address': 'address',
            'postal_code': 'postal code',
            'postal': 'postal code',
            'closing_date': 'closing date',
            'closing': 'closing date',
            'property_type': 'property type',
            'email': 'email address',
            'phone': 'phone number',
            'percentage': 'ownership percentage',
            'ownership': 'ownership details',
            'insurance': 'insurance details',
            'mortgage': 'mortgage details',
            'realtor': 'realtor details',
            'brokerage': 'brokerage',
            'title': 'title holding'
        }
        
        if field in field_mappings:
            if category:
                return f"{category} {field_mappings[field]}"
            return field_mappings[field]
        
        for key, value in field_mappings.items():
            if key in field:
                if category:
                    return f"{category} {value}"
                return value
        
        clean_field = field.replace('_', ' ')
        if category:
            return f"{category} {clean_field}"
        return clean_field
    
    return question_id.replace('_', ' ') 
