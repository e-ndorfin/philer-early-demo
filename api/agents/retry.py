"""
Retry Agent

This agent rephrases questions when the user is confused or doesn't understand.
It will restate the question in a simpler or clearer way and steer conversation back on topic.
After 3 retry attempts, it will mark the question as incomplete and move on.
"""

from typing import Dict, Any, Tuple, Optional, List
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import ConversationState
from ..questions.questions import QUESTIONS
from ..utils.question_utils import get_question_by_id, get_next_question_id, get_readable_field_name
# from utils.tts import text_to_speech

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

model = ChatGroq(api_key=groq_api_key,
                 model="llama-3.3-70b-versatile", temperature=0.2)

RETRY_PROMPT = """
You are a helpful assistant for a real estate closing service.
The user responded in a way that suggests they're confused, didn't understand, or provided an irrelevant response to the following question:

Original question: {question_text}
User's response: {user_response}
Current retry attempt: {retry_count} of 3

Your task is to politely rephrase the question and help the user provide a complete answer.

IMPORTANT GUIDELINES:
1. ALWAYS use GENDER-NEUTRAL language - never use he/him or she/her pronouns
2. When referring to any person mentioned (spouse, family member, etc.), use ONLY they/them/their pronouns

For different retry attempts, adjust your tone:
- If this is retry attempt 1: Be gentle and simply rephrase the question
- If this is retry attempt 2: Be more specific about what information you need
- If this is retry attempt 3: Be very direct about what's required to move forward

Remember:
- For names: We need complete, valid names
- For dates: We need full dates (month, day, year)
- For employment: We need one of these categories: Full-time, Part-time, Contract, Self-Employed, Unemployed
- For addresses: We need complete addresses with street, city, and postal code

Keep your response concise and natural - just rephrase the question appropriately for the current retry attempt.
Do NOT include "Retry attempt X:" in your response.
"""

NEXT_QUESTION_PROMPT = """
You are a helpful assistant for a real estate closing service.
The conversation is moving on to a new question in the form.

Next question: {next_question_text}

IMPORTANT GUIDELINES:
1. Present this question in a natural, conversational way
2. ALWAYS use GENDER-NEUTRAL language - never use he/him or she/her pronouns

Keep your response focused ONLY on this new question without referencing any previous questions or struggles.
Do not mention that you're moving on or changing topics - simply ask the new question as if it's the natural next step.

Your response should include only the new question presented in a friendly, conversational tone.
"""

retry_prompt = ChatPromptTemplate.from_template(RETRY_PROMPT)
next_question_prompt = ChatPromptTemplate.from_template(NEXT_QUESTION_PROMPT)

# Maximum number of retry attempts before moving on
MAX_RETRIES = 3


def handle_confusion_node(state: ConversationState) -> Dict[str, Any]:
    """
    LangGraph node to handle user confusion by rephrasing the question.
    Updates the agent_response field in the state.
    After MAX_RETRIES attempts, marks the question as incomplete and moves on.
    """
    current_question_id = state["current_question_id"]

    # Check if we're at the farewell - if so, immediately terminate
    if current_question_id == "farewell":
        print("\nConversation complete. Thank you for using our service!")
        return {"is_done": True}

    current_question = get_question_by_id(current_question_id)
    user_response = state.get("user_response", "")

    # Get or initialize retry counter for current question
    form_data = state.get("form_data", {})
    retries = form_data.get(f"{current_question_id}_retries", 0) + 1
    form_data[f"{current_question_id}_retries"] = retries

    # If we've exceeded max retries, mark as incomplete and move on
    if retries >= MAX_RETRIES:
        form_data[current_question_id] = "[INCOMPLETE]"

        next_question_id = get_next_question_id(current_question_id, form_data)

        # If next question is None (we're at the end), mark as done
        if next_question_id is None:
            farewell_question = get_question_by_id("farewell")
            agent_response = farewell_question["text"]

            # Print the farewell directly
            print(f"\nAssistant: {agent_response}")
            print("\nConversation complete. Thank you for using our service!")

            # Return with done flag
            return {
                "agent_response": agent_response,
                "current_question_id": "farewell",
                "is_done": True,
                "form_data": form_data
            }

        next_question = get_question_by_id(next_question_id)

        chain = next_question_prompt | model
        next_response = chain.invoke({
            "next_question_text": next_question["text"]
        })

        agent_response = next_response.content
        history = state["conversation_history"] + \
            [("Assistant", agent_response)]

        # text_to_speech(agent_response, voice="Fritz-PlayAI")

        # Return the updates for the state, moving to the next question
        return {
            "agent_response": agent_response,
            "conversation_history": history,
            "current_question_id": next_question_id,
            "form_data": form_data
        }

    # Otherwise, retry with a rephrased question
    chain = retry_prompt | model
    retry_response = chain.invoke({
        "question_text": current_question["text"],
        "user_response": user_response,
        "retry_count": retries
    })

    agent_response = retry_response.content
    history = state["conversation_history"] + [("Assistant", agent_response)]

    # text_to_speech(agent_response, voice="Fritz-PlayAI")

    # Return the updates for the state
    return {
        "agent_response": agent_response,
        "conversation_history": history,
        "form_data": form_data
    }
