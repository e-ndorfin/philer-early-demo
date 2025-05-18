
"""
Question Asker Agent

This agent is responsible for asking questions based on the current state of the form.
It will select the next question to ask based on the state and present it in a conversational way.
"""

from typing import Dict, Any, Optional, List, Tuple
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from ..questions.questions import QUESTIONS
from ..utils.question_utils import get_question_by_id, get_next_question_id
from ..core.state import ConversationState
# from utils.tts import text_to_speech

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.2)

QUESTION_ASKER_PROMPT = """
You are an intelligent phone intake assistant for a real estate closing service named Philer.
Your role is to guide users through a form-filling process by asking questions in a natural, conversational way.

Current form data:
{form_summary}

The next question to ask is: {question_text}

IMPORTANT GUIDELINES:
1. Present the question in a conversational tone
2. Make slight variations to the wording if it helps the flow, but don't change the meaning
3. Keep your response brief and focused on the question
4. Don't add additional explanations unless they're part of the original question
5. ALWAYS use GENDER-NEUTRAL language - never use he/him or she/her pronouns

Your response should only contain the question itself, with gender-neutral language, nothing more.
"""

VERIFICATION_PROMPT = """
You are an intelligent phone intake assistant for a real estate closing service named Philer.
Your role is to verify pre-filled information with the user instead of assuming it's correct.

Current form data:
{form_summary}

Question to verify: {question_text}
Field to verify: {field_id}
Pre-filled value: {field_value}

IMPORTANT GUIDELINES:
1. Generate a brief, conversational question asking if the pre-filled value is correct
2. Reference the specific value clearly so the user can confirm or correct it
3. Keep your response brief and focused
4. ALWAYS use GENDER-NEUTRAL language - never use he/him or she/her pronouns
5. Phrase it as a verification question, not a new question

Examples:
- For an address: "I see the property address is 123 Main Street. Is that correct?"
- For a name: "I have your first name as John. Is that correct?"
- For a date: "It looks like your closing date is set for June 15, 2023. Is that right?"

Your response should only contain the verification question with gender-neutral language, nothing more.
"""

SUMMARY_PROMPT = """
You are an intelligent phone intake assistant for a real estate closing service named Philer.
You need to briefly acknowledge what information has already been collected.

Current form data:
{form_summary}

Next question coming up: {next_question}

IMPORTANT GUIDELINES:
1. Be extremely brief - no more than one short sentence
2. Don't list all the information you have - just acknowledge we have some basic information
3. Don't mention specific details like names, addresses, or dates
4. Make a very short transition to the next question
5. Keep the total response under 20 words

Example good response: "Thanks for the information so far. What's the postal code for this property?"
Example bad response (too long): "So far, we've got the basics covered - your name is John Smith, and you're looking to purchase a condo apartment at 123 Main Street in Toronto as an investment property, with a planned closing date of December 1, 2023. As the sole owner, you're a first-time homebuyer. Now, let's move forward with a few more details - can you tell me the postal code for this property, or we can look it up together if you're not sure?"
"""

question_asker_prompt = ChatPromptTemplate.from_template(QUESTION_ASKER_PROMPT)
verification_prompt = ChatPromptTemplate.from_template(VERIFICATION_PROMPT)
summary_prompt = ChatPromptTemplate.from_template(SUMMARY_PROMPT)

def format_form_summary(form_data: Dict[str, Any]) -> str:
    """Format the form data for display in the prompt"""
    if not form_data:
        return "No information collected yet."
    
    summary = []
    for key, value in form_data.items():
        if value and not key.endswith("_retries"):
            summary.append(f"{key}: {value}")
    
    if not summary:
        return "No information collected yet."
    
    return "\n".join(summary)

def has_prefilled_data(question_id: str, form_data: Dict[str, Any]) -> bool:
    """
    Check if a question has pre-filled data.
    
    Args:
        question_id: The ID of the question to check
        form_data: The current form data
        
    Returns:
        True if the question has pre-filled data, False otherwise
    """
    if question_id in ['welcome', 'farewell']:
        return False
    
    if question_id in form_data and form_data[question_id]:
        return True
    
    if question_id == 'applicant_first_name' and 'applicant_first_name' in form_data:
        return True
    if question_id == 'applicant_last_name' and 'applicant_last_name' in form_data:
        return True
    
    if question_id.startswith('spouse_') and question_id in form_data:
        return True
        
    if question_id == 'property_postal_code' and 'property_postal_code' in form_data:
        return True
    
    return False

def generate_verification_question(form_data: Dict[str, Any], question_id: str, question_text: str) -> str:
    """
    Generate a verification question for pre-filled data.\
    """
    form_summary = format_form_summary(form_data)
    field_value = form_data.get(question_id, "")
    
    chain = verification_prompt | model
    verification_response = chain.invoke({
        "form_summary": form_summary,
        "question_text": question_text,
        "field_id": question_id,
        "field_value": field_value
    })
    
    return verification_response.content

def generate_summary(form_data: Dict[str, Any], next_question: Dict[str, Any]) -> str:
    """
    Generate a very brief summary before asking the next question.
    
    Args:
        form_data: The current form data
        next_question: The next question to ask
        
    Returns:
        A brief transition to the next question
    """
    form_summary = format_form_summary(form_data)
    
    chain = summary_prompt | model
    summary_response = chain.invoke({
        "form_summary": form_summary,
        "next_question": next_question["text"]
    })
    
    return summary_response.content

def ask_question_node(state: ConversationState) -> Dict[str, Any]:
    """
    LangGraph node to determine and ask the next question.
    Updates the agent_response, current_question_id, and is_done fields in the state.
    """
    current_question_id = state.get("current_question_id", "welcome")
    form_data = state["form_data"]
    
    if current_question_id == "farewell":
        return {"is_done": True}
    
    if current_question_id == "welcome" and len(form_data) > 0 and len(state["conversation_history"]) == 0:
        welcome_question = get_question_by_id("welcome")
        agent_response = welcome_question["text"]
        history = state["conversation_history"] + [("Assistant", agent_response)]
        
        # Return the welcome message first
        return {
            "agent_response": agent_response,
            "conversation_history": history,
            "is_done": False
        }
    
    if state.get("agent_response") and "Let's go back to the question" in state.get("agent_response"):
        next_question_id = current_question_id
    else:
        next_question_id = get_next_question_id(current_question_id, form_data)
    
    if has_prefilled_data(next_question_id, form_data) and next_question_id != "welcome" and next_question_id != "farewell":
        next_question = get_question_by_id(next_question_id)
        
        verification_question = generate_verification_question(
            form_data, 
            next_question_id, 
            next_question["text"]
        )
        
        history = state["conversation_history"] + [("Assistant", verification_question)]
        
        return {
            "agent_response": verification_question,
            "current_question_id": next_question_id,
            "conversation_history": history,
            "is_verification": True,
            "is_done": False
        }
    
    skipped_questions = []
    while has_prefilled_data(next_question_id, form_data) and next_question_id not in ["welcome", "farewell"]:
        skipped_questions.append(next_question_id)
        next_question_id = get_next_question_id(next_question_id, form_data)
        
        if next_question_id is None or next_question_id == "farewell":
            break
    
    if next_question_id is None:
        farewell_question = get_question_by_id("farewell")
        agent_response = farewell_question["text"]
        history = state["conversation_history"] + [("Assistant", agent_response)]
        
        print(f"\nAssistant: {agent_response}")
        print("\nConversation complete. Thank you for using our service!")
        
        # Comment out TTS
        # text_to_speech(agent_response, voice="Celeste-PlayAI")
        
        return {
            "agent_response": agent_response,
            "current_question_id": "farewell",
            "is_done": True,
            "conversation_history": history
        }
    
    next_question = get_question_by_id(next_question_id)
    
    form_summary = format_form_summary(form_data)
    
    if len(skipped_questions) > 0 and len(state["conversation_history"]) == 2:
        agent_response = next_question["text"]
        if current_question_id == "welcome":
            agent_response = next_question["text"]
        else:
            agent_response = generate_summary(form_data, next_question)
    else:
        chain = question_asker_prompt | model
        question_response = chain.invoke({
            "form_summary": form_summary,
            "question_text": next_question["text"]
        })
        
        agent_response = question_response.content
    
    if current_question_id == next_question_id and "correction" in state.get("intent", ""):
        agent_response = "Let me ask that question again. " + agent_response
    
    history = state["conversation_history"] + [("Assistant", agent_response)]
    
    # Comment out TTS
    # text_to_speech(agent_response, voice="Celeste-PlayAI")
    
    # Return the updates for the state
    return {
        "agent_response": agent_response,
        "current_question_id": next_question_id,
        "conversation_history": history,
        "is_verification": False,
        "is_done": False 
    } 
