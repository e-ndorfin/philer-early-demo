"""
Redo Agent

This agent intelligently analyzes correction requests from users and determines
which question to go back to based on the content of their request and the conversation history.
It can also make inline corrections to previous answers without changing the flow.
"""

from typing import Dict, Any, List, Optional, Literal
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from core.state import ConversationState, CorrectionDetails, CorrectionType
from questions.questions import QUESTIONS
from utils.question_utils import get_question_by_id, get_previous_question_id, get_readable_field_name
from utils.extraction_utils import format_conversation_history

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.1)

# Define the structured output schema for correction analysis
class CorrectionAnalysis(BaseModel):
    correction_type: Literal["go_back", "inline_update", "needs_clarification", "not_a_correction"] = Field(
        description="The type of correction needed: go_back (return to a previous question), inline_update (update a value but continue), needs_clarification (user intent is unclear), or not_a_correction (this is actually an answer to the current question)"
    )
    target_question_id: Optional[str] = Field(
        default=None,
        description="The ID of the question to go back to or the ID of the question whose answer needs updating"
    )
    corrected_value: Optional[str] = Field(
        default=None,
        description="The new value for the field (if an inline update)"
    )
    explanation: str = Field(
        description="A brief reason for this decision"
    )

# Create a parser for the structured output
parser = PydanticOutputParser(pydantic_object=CorrectionAnalysis)

CORRECTION_ANALYZER_PROMPT = """
You're analyzing a user's intent to correct some previously provided information in a real estate intake form.

Current question being asked: {current_question}
Current question ID: {current_question_id}
User's response: {user_response}

Recent conversation history (most recent first):
{conversation_history}

Your task is to determine if the user is actually trying to make a correction, or just answering the current question.

IMPORTANT GUIDELINES:

1. Carefully distinguish between:
   - Actual corrections (user wants to change a previous answer)
   - Answers to the current question (user is directly responding to what was asked)

2. When a user directly answers the current question, classify as "not_a_correction", even if:
   - Their answer contains negative words (like "no")
   - They are explaining their answer
   - They are providing clarification
   - They are reiterating what they said before

3. For yes/no questions:
   - "Yes" or "No" responses followed by explanation are still direct answers
   - "No, I haven't" or "Yes, I have" are direct answers, not corrections
   - "No, I am a first time buyer" to a first-time buyer question is an ANSWER, not a correction

4. Only classify as a correction when the user is clearly trying to change a previous answer from an earlier question.

5. Remember: A direct response to the current question, even if it contains "no" or explanation, is NOT a correction.

{format_instructions}

EXAMPLES OF NON-CORRECTIONS (direct answers):
{{
  "correction_type": "not_a_correction",
  "target_question_id": null,
  "corrected_value": null,
  "explanation": "User is directly answering the first-time buyer question with 'no I have not, I am a first time house buyer'"
}}

{{
  "correction_type": "not_a_correction",
  "target_question_id": null,
  "corrected_value": null,
  "explanation": "User said 'yes' to the question about being a first-time buyer, which is a direct answer"
}}

EXAMPLES OF ACTUAL CORRECTIONS:
{{
  "correction_type": "go_back",
  "target_question_id": "applicant_first_name",
  "corrected_value": null,
  "explanation": "User explicitly wants to change their name from a previous question, not answering the current question"
}}

{{
  "correction_type": "inline_update",
  "target_question_id": "applicant_first_time_buyer",
  "corrected_value": "no",
  "explanation": "User is clearly correcting a previous answer about being a first-time buyer, not responding to the current question"
}}
"""

COMBINED_RESPONSE_PROMPT = """
You are helping a user complete a real estate intake form. The user has just made a correction to a previous answer, and you need to:
1. Acknowledge the correction
2. Continue with the current question

Previous correction acknowledgment: {acknowledgment}
Current question to ask: {question_text}

Provide a SINGLE response that:
1. First acknowledges the correction naturally and briefly
2. Then asks the current question
3. Makes the transition feel natural and conversational

Keep your response concise and focused. Don't add unnecessary explanation or commentary.
"""

correction_analyzer_prompt = ChatPromptTemplate.from_template(CORRECTION_ANALYZER_PROMPT) \
    .partial(format_instructions=parser.get_format_instructions())

def handle_redo_agent(state: ConversationState) -> Dict[str, Any]:
    """
    Intelligent agent that determines how to handle corrections based on user input.
    """
    current_question_id = state["current_question_id"]
    current_question = get_question_by_id(current_question_id)
    user_response = state.get("user_response", "")
    history = state["conversation_history"]
    form_data = state.get("form_data", {})
    
    # Format the conversation history
    formatted_history = format_conversation_history(history)
    
    # Analyze correction intent using LLM with structured output parsing
    chain = correction_analyzer_prompt | model | parser
    
    try:
        # Try to get a structured response from the LLM
        correction_details = chain.invoke({
            "current_question": current_question["text"],
            "current_question_id": current_question_id,
            "user_response": user_response,
            "conversation_history": formatted_history
        })
        
        if correction_details.correction_type == "not_a_correction":
            return {
                "redo_is_correction": False,
                "explanation": correction_details.explanation
            }
        
        if correction_details.correction_type == "inline_update" and correction_details.target_question_id and correction_details.corrected_value is not None:
            updated_form_data = form_data.copy()
            updated_form_data[correction_details.target_question_id] = correction_details.corrected_value
            
            field_name = get_readable_field_name(correction_details.target_question_id)
                
            ack_msg = f"I've updated your {field_name} to '{correction_details.corrected_value}'. "
            full_response = f"{ack_msg}Now, {current_question['text']}"
            
            updated_history = history + [("Assistant", full_response)]
            
            return {
                "agent_response": full_response,
                "form_data": updated_form_data,
                "conversation_history": updated_history,
                "redo_is_correction": True
            }
            
        elif correction_details.correction_type == "needs_clarification":
            previous_id = get_previous_question_id(current_question_id)
            previous_question = get_question_by_id(previous_id)
            
            full_response = f"Let's go back to the previous question. {previous_question['text']}"
            updated_history = history + [("Assistant", full_response)]
            
            return {
                "agent_response": full_response,
                "current_question_id": previous_id,
                "conversation_history": updated_history,
                "redo_is_correction": True
            }
            
        elif correction_details.correction_type == "go_back" and correction_details.target_question_id:
            target_question = get_question_by_id(correction_details.target_question_id)
            if not target_question:
                target_question_id = get_previous_question_id(current_question_id)
                target_question = get_question_by_id(target_question_id)
            else:
                target_question_id = correction_details.target_question_id
            
            field_name = get_readable_field_name(target_question_id)
            
            ack_msg = f"Let's go back to update your {field_name}. "
            full_response = f"{ack_msg}{target_question['text']}"
            
            updated_history = history + [("Assistant", full_response)]
            
            return {
                "agent_response": full_response,
                "current_question_id": target_question_id,
                "conversation_history": updated_history,
                "redo_is_correction": True
            }
        
    except Exception as e:
        print(f"Error in correction analysis: {e}")
    
    # If we reach here, either the LLM failed to produce a valid output or parsing failed
    return {
        "redo_is_correction": False,
        "explanation": "Failed to parse correction intent"
    } 