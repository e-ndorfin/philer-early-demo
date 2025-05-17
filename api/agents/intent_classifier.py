"""
Intent Classifier Agent

This agent classifies user responses into one of four categories:
1. Confusion/silence - User doesn't understand or needs the question repeated, or gives an irrelevant response
2. Clarifying question - User has a question about the current question
3. Answer - User has provided an answer to the question
4. Correction - User wants to correct a previous answer or go back
"""

from typing import Dict, Any, Literal
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.state import ConversationState

from questions.questions import QUESTIONS
from utils.question_utils import get_question_by_id

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.1)

INTENT_CLASSIFIER_PROMPT = """
You are an intent classifier for a conversational AI assistant that helps users fill out forms.
Your task is to analyze the user's response and classify it into one of four categories:

1. "confusion" - The user is confused, doesn't understand, needs the question repeated, or has provided an irrelevant/off-topic/incomplete response
2. "question" - The user has asked a clarifying question about the CURRENT form question
3. "answer" - The user has provided a clear, direct answer to the question
4. "correction" - The user wants to go back, undo, or correct a previous answer

Current question being asked: {question_text}
Recent conversation context: {conversation_context}
User response: {user_response}

IMPORTANT CLASSIFICATION GUIDELINES:

For "confusion" classification:
- Filler words or expressions of uncertainty (like "um", "uh", "hmm")
- Partial answers that are clearly incomplete 
- Responses that are too short to be meaningful answers to the specific question
- Off-topic statements or questions unrelated to the form
- Statements like "stop", "wait", "hold on" without clear context
- Any response that doesn't logically align with the question asked

For "answer" classification, the response must:
- Directly address the specific question asked
- Provide sufficient information to be considered a complete answer
- Make sense in the context of the question (e.g., a real name for a name question)
- If the user states they've already answered this question, consider it as an "answer" NOT a "correction"

For "correction" classification:
- Clear indication that the user wants to change something, go back, or correct a mistake
- Phrases like "go back", "previous", "undo", "I made a mistake", "I want to change", "that's wrong"
- Explicit mention of changing information from a DIFFERENT question than the current one
- Expression of dissatisfaction with a previously recorded answer, not the current question

VERY IMPORTANT DISTINCTIONS:
- When a user directly answers the current question, even with explanation, it's an "answer"
- "No, I haven't" or "Yes, I have" followed by explanation to a yes/no question is an "answer", not a "correction"
- Only classify as "correction" when the user clearly wants to change a DIFFERENT answer than what's currently being asked about

Always remember:
- Use gender-neutral language in any explanations
- For names, preserve exact spelling as given by users
- Never make assumptions about gender based on names
- When in doubt between "answer" and "correction" for a direct response to the current question, choose "answer"

Return ONLY the category name (confusion, question, answer, or correction) with no additional explanation.
"""

VERIFICATION_INTENT_PROMPT = """
You are an intent classifier for a conversational AI assistant that helps users fill out forms.
Your task is to analyze the user's response to a verification question and classify it into one of four categories.

We are verifying pre-filled data with the user. The assistant has just asked the user to confirm if some information is correct.

1. "confirmation" - The user confirms the information is correct (e.g., "yes", "correct", "that's right")
2. "correction" - The user indicates the information is wrong and provides a correction
3. "question" - The user asks a clarifying question about the verification
4. "confusion" - The user's response is unclear, irrelevant, or doesn't address the verification

Current verification question: {question_text}
Recent conversation context: {conversation_context}
User response: {user_response}

IMPORTANT CLASSIFICATION GUIDELINES:
- For simple confirmations like "yes", "correct", "that's right", classify as "confirmation"
- When the user provides new information to correct the pre-filled data, classify as "correction"
- If the user asks for clarification about what's being verified, classify as "question"
- Any response that doesn't clearly address the verification should be "confusion"

Return ONLY the category name (confirmation, correction, question, or confusion) with no additional explanation.
"""

intent_classifier_prompt = ChatPromptTemplate.from_template(INTENT_CLASSIFIER_PROMPT)
verification_intent_prompt = ChatPromptTemplate.from_template(VERIFICATION_INTENT_PROMPT)

def classify_intent_node(state: ConversationState) -> Dict[str, Any]:
    """
    LangGraph node to classify the user's response intent.
    Updates the intent field in the state.
    """
    current_question_id = state["current_question_id"]
    
    if current_question_id == "farewell":
        return {"is_done": True}
    
    current_question = get_question_by_id(current_question_id)
    
    user_response = state.get("user_response", "")
    
    conversation_history = state.get("conversation_history", [])
    recent_exchanges = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    conversation_context = "\n".join([f"{'User' if role == 'User' else 'Assistant'}: {message}" for role, message in recent_exchanges])
    
    # Special handling for verification questions
    if state.get("is_verification", False):
        chain = verification_intent_prompt | model
        intent_response = chain.invoke({
            "question_text": current_question["text"],
            "user_response": user_response,
            "conversation_context": conversation_context
        })
        
        verification_intent = intent_response.content.strip().lower()
        
        # Map verification intents to standard intents for the workflow
        if verification_intent == "confirmation":
            # User confirmed the data is correct
            return {"intent": "answer"}
        elif verification_intent == "correction":
            # User provided a correction to the pre-filled data
            return {"intent": "answer"} # Still treat as answer, entity extraction will handle it
        elif verification_intent == "question":
            return {"intent": "question"}
        else:
            return {"intent": "confusion"}
    
    # Normal intent classification for non-verification questions
    chain = intent_classifier_prompt | model
    intent_response = chain.invoke({
        "question_text": current_question["text"],
        "user_response": user_response,
        "conversation_context": conversation_context
    })
    
    intent = intent_response.content.strip().lower()
    
    if intent not in ["confusion", "question", "answer", "correction"]:
        intent = "confusion"
    
    return {"intent": intent} 