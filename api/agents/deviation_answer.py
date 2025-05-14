"""
Deviation Answer Agent

This agent answers clarifying questions from the user.
It will provide helpful responses to questions about the form, process, or current question.
"""

from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.state import ConversationState
# from utils.tts import text_to_speech

from questions.questions import QUESTIONS
from utils.question_utils import get_question_by_id

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.2)

DEVIATION_ANSWER_PROMPT = """
You are an intelligent phone intake assistant for a real estate closing service.
The user has asked a question during the form-filling process. Answer their question clearly and concisely.

Current question being asked in the form: {question_text}
User's question/response: {user_response}

IMPORTANT GUIDELINES:
1. Answer their question helpfully and accurately, but keep your response concise
2. ALWAYS use GENDER-NEUTRAL language - never use he/him or she/her pronouns

Information about the Philer real estate closing service:
- Philer helps with the legal aspects of property closing
- All information collected is confidential and protected
- Users can update information later through the Philer platform
- The intake process takes about 10-15 minutes
- Responses are used to prepare legal documents for closing

Keep your response brief, accurate, and direct.
"""

deviation_answer_prompt = ChatPromptTemplate.from_template(DEVIATION_ANSWER_PROMPT)

def handle_question_node(state: ConversationState) -> Dict[str, Any]:
    """
    LangGraph node to handle user clarifying questions.
    Updates the agent_response field in the state.
    """
    current_question_id = state["current_question_id"]
    
    # Check if we're at the farewell - if so, immediately terminate
    if current_question_id == "farewell":
        print("\nConversation complete. Thank you for using our service!")
        return {"is_done": True}
    
    current_question = get_question_by_id(current_question_id)
    
    user_response = state.get("user_response", "")
    
    chain = deviation_answer_prompt | model
    answer_response = chain.invoke({
        "question_text": current_question["text"],
        "user_response": user_response
    })
    
    agent_response = answer_response.content
    history = state["conversation_history"] + [("Assistant", agent_response)]
    
    # Comment out TTS
    # text_to_speech(agent_response, voice="Calum-PlayAI")
    
    return {"agent_response": agent_response, "conversation_history": history} 