"""
Entity Extraction Agent

This agent extracts structured information from user responses to form questions.
It will parse and normalize answers to fill in the form correctly.
"""

from typing import Dict, Any, Optional, List, Union
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from questions.questions import QUESTIONS
from core.state import ConversationState
from utils.date_utils import normalize_date
from utils.json_utils import update_test_json
from utils.extraction_utils import get_extraction_prompt, process_structured_field, is_date_question, FIELD_MAPPING
from utils.question_utils import get_question_by_id

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.1)

# Prompt templates for different question types
PROMPTS = {
    "default": """
You are an entity extraction agent for a form-filling system. Extract only the requested information from the user's response.

Current question: {question_text}
Question ID: {question_id}
User's response: {user_response}

Return ONLY the extracted answer. No explanation or additional text.
""",

    "name": """
You are extracting a name from a user response. 
NEVER change or correct the spelling - preserve exactly what the user entered.
Do not include any JSON-like formatting, quotes, or special characters.

Current question: {question_text}
User's response: {user_response}

Return ONLY the extracted name - no JSON formatting, no quotation marks, no explanation.

EXAMPLES:
User response: "My name is Jane Doe"
Correct extraction: Jane Doe

User response: "I'm John Smith"
Correct extraction: John Smith

User response: "Name: {{\"full-name\": \"Robert Johnson\"}}"
Correct extraction: Robert Johnson

User response: "Jane works for ABC Company"
Correct extraction: Jane
""",

    "structured": """
You are extracting structured information about {structure_type}.
Parse the response to extract ONLY the following components:

Current question: {question_text}
User's response: {user_response}

For {structure_type}, extract separately:
{expected_fields}

Return the result as a simple text response with each value separated by a pipe (|) character:
name|company|lender  (example format)

DO NOT include any JSON formatting, quotes, braces, or other special characters. Extract ONLY the plain text values.
NO JSON syntax, NO special characters or quotation marks, ONLY the pipe-separated values.

IMPORTANT: I need clean, plain text values ONLY. Extracting "Jane Doe", not "\\"Jane Doe\\"" or "{{name: Jane Doe}}"
""",

    "boolean": """
You are extracting a yes/no answer.
Parse the response into a clear yes or no.

Current question: {question_text}
User's response: {user_response}

Return ONLY 'yes' or 'no' - nothing else.
""",
    
    "verification": """
You are helping verify pre-filled form data with users.
Analyze the user's response to determine if they are:
1. Confirming the existing data is correct (respond with "confirmed")
2. Providing a new/corrected value (extract and return the new value)

Current question: {question_text}
Pre-filled data: {prefilled_value}
User's response: {user_response}
Field type: {field_type}

EXAMPLES:
- If user says: "Yes that's correct", return "confirmed"
- If user says: "No, it's actually John Smith", return "John Smith"
- If user says: "It's 123 Main St, not 123 Main Street", return "123 Main St"

If the user confirms the data is correct, return ONLY "confirmed".
If the user provides a correction, return ONLY the corrected value without any explanation.
"""
}

def extract_entities_node(state: ConversationState) -> Dict[str, Any]:
    """
    LangGraph node to extract entities from the user's answer.
    Updates the form_data field in the state.
    """
    current_question_id = state["current_question_id"]
    current_question = get_question_by_id(current_question_id)
    
    if not current_question:
        return {}
        
    user_response = state.get("user_response", "")
    
    if state.get("is_verification", False):
        return process_verification_response(state, current_question_id, current_question, user_response)
    
    if is_date_question(current_question["text"]):
        normalized_date = normalize_date(user_response)
        if normalized_date != "incomplete":
            updated_form_data = state["form_data"].copy()
            updated_form_data[current_question_id] = normalized_date
            
            # TESING ONLY: Update test JSON
            update_test_json(updated_form_data, current_question_id, normalized_date)
            
            return {"form_data": updated_form_data}
    
    prompt_info = get_extraction_prompt(
        current_question_id, 
        current_question["text"], 
        user_response
    )
    
    prompt_template = PROMPTS[prompt_info["template_key"]]
    extraction_prompt = ChatPromptTemplate.from_template(prompt_template)
    
    chain = extraction_prompt | model
    extraction_response = chain.invoke(prompt_info["data"])
    
    extracted_value = extraction_response.content.strip()
    
    if extracted_value.lower() == "incomplete":
        return {}
        
    field_info = FIELD_MAPPING.get(current_question_id, {"type": "text"})
    if field_info["type"] == "structured":
        extracted_value = process_structured_field(extracted_value, current_question_id)
        
    updated_form_data = state["form_data"].copy()
    updated_form_data[current_question_id] = extracted_value
    
    # TESTING ONLY: Update test JSON
    update_test_json(updated_form_data, current_question_id, extracted_value)
    
    return {"form_data": updated_form_data}

def process_verification_response(state: ConversationState, 
                                question_id: str, 
                                question: Dict[str, Any], 
                                user_response: str) -> Dict[str, Any]:
    """
    Process a verification response from the user.\
    """
    form_data = state["form_data"]
    prefilled_value = form_data.get(question_id, "")
    field_info = FIELD_MAPPING.get(question_id, {"type": "text"})
    
    verification_prompt = ChatPromptTemplate.from_template(PROMPTS["verification"])
    
    chain = verification_prompt | model
    verification_response = chain.invoke({
        "question_text": question["text"],
        "prefilled_value": prefilled_value,
        "user_response": user_response,
        "field_type": field_info["type"]
    })
    
    extracted_value = verification_response.content.strip()
    
    if extracted_value.lower() == "confirmed":
        return {
            "is_verification": False
        }
    
    updated_form_data = form_data.copy()
    
    if field_info["type"] == "date":
        extracted_value = normalize_date(extracted_value)
    
    if field_info["type"] == "structured":
        extracted_value = process_structured_field(extracted_value, question_id)
    
    updated_form_data[question_id] = extracted_value
    
    # TESTING ONLY: Update test JSON
    update_test_json(updated_form_data, question_id, extracted_value)
    
    return {
        "form_data": updated_form_data,
        "is_verification": False
    } 