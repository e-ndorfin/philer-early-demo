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
from ..questions.questions import QUESTIONS
from ..core.state import ConversationState
from ..utils.date_utils import normalize_date
from ..utils.json_utils import update_test_json
from ..utils.extraction_utils import get_extraction_prompt, process_structured_field, is_date_question
from ..utils.question_utils import get_question_by_id

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key,
                 model="llama-3.3-70b-versatile", temperature=0.1)

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
    "transaction_type": {"type": "choice", "format": "Buy/Sell/Refinance"},
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

    # Check if this is a date question
    if is_date_question(current_question["text"]):
        # Try to normalize the date first
        normalized_date = normalize_date(user_response)
        if normalized_date != "incomplete":
            updated_form_data = state["form_data"].copy()
            updated_form_data[current_question_id] = normalized_date

            # TESTING ONLY: Update test JSON
            # update_test_json(updated_form_data, current_question_id, normalized_date)

            return {"form_data": updated_form_data}

    # Get the appropriate prompt for the question type
    prompt_info = get_extraction_prompt(
        current_question_id,
        current_question["text"],
        user_response,
        FIELD_MAPPING
    )

    # Create the prompt template
    prompt_template = PROMPTS[prompt_info["template_key"]]
    extraction_prompt = ChatPromptTemplate.from_template(prompt_template)

    # Run extraction with the LLM
    chain = extraction_prompt | model
    extraction_response = chain.invoke(prompt_info["data"])

    # Process the raw extracted value
    extracted_value = extraction_response.content.strip()

    if extracted_value.lower() == "incomplete":
        return {}

    # Special handling for structured fields
    field_info = FIELD_MAPPING.get(current_question_id, {"type": "text"})
    if field_info["type"] == "structured":
        extracted_value = process_structured_field(
            extracted_value, current_question_id)

    updated_form_data = state["form_data"].copy()
    updated_form_data[current_question_id] = extracted_value

    # TESTING ONLY: Update test JSON
    # update_test_json(updated_form_data, current_question_id, extracted_value)

    return {"form_data": updated_form_data}
