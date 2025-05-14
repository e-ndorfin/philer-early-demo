"""
Workflow Definition

This module defines the LangGraph workflow for the conversational intake form.
It sets up the nodes, edges, and compiles the graph.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ConversationState
from ..agents.question_asker import ask_question_node
from ..agents.intent_classifier import classify_intent_node
from ..agents.retry import handle_confusion_node
from ..agents.deviation_answer import handle_question_node
from ..agents.entity_extraction import extract_entities_node
from ..agents.redo_agent import handle_redo_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os


from langgraph.types import Command, interrupt

# from twilio_flow.generate_twiml import question_twiml
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Hangup
from flask import (
    request,
    url_for,
)

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
model = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile", temperature=0.1)


def format_form_summary(form_data: Dict[str, Any]) -> str:
    """Format the form data for display in the prompt"""
    if not form_data:
        return "No information collected yet."
    
    summary = []
    for key, value in form_data.items():
        if value and not key.endswith("_retries"):  # Only include fields that have been filled
            summary.append(f"{key}: {value}")
    
    if not summary:
        return "No information collected yet."
    
    return "\n".join(summary)

def get_user_input_node(state: ConversationState) -> Dict[str, Any]:
    """Node to get user input using keyboard input."""
    last_agent_response = state.get("agent_response")
    if last_agent_response:
        print(f"\nAssistant: {last_agent_response}")
    
    if state.get("is_done", False):
        print("\nConversation complete. Thank you for using our service!")
        return END
    
    # Comment out speech-to-text
    # user_input = speech_to_text()
    
    #interrupt langgraph workflow until user provides response
    user_input = interrupt(value = last_agent_response)
    print(f"> Received an input from the interrupt: {user_input}")
    
    # No need to print the input again as it's already visible
    # print(f"\nYou: {user_input}")
    
    history = state["conversation_history"] + [("User", user_input)]
    
    return {"user_response": user_input, "conversation_history": history, "agent_response": None}

def should_continue(state: ConversationState) -> str:
    """Determines whether to continue the conversation or end."""
    if state["is_done"]:
        # When we're done (farewell is delivered), immediately terminate
        return END
    return "get_user_input"

def route_after_user_input(state: ConversationState) -> str:
    """Routes after user input - handles potential END state"""
    return "classify_intent"

def route_after_intent(state: ConversationState) -> str:
    """Routes the conversation based on the classified intent."""
    intent = state["intent"]
    if intent == "confusion":
        return "handle_confusion"
    elif intent == "question":
        return "handle_question"
    elif intent == "correction":
        return "handle_correction"
    else: # intent == "answer"
        return "extract_entities"

def route_after_correction(state: ConversationState) -> str:
    """Routes after a correction is handled."""
    # Check if this was actually a correction or just an answer
    if state.get("redo_is_correction") is False:
        # Not a correction, treat as an answer and proceed with entity extraction
        return "extract_entities"
    
    # This is a legitimate correction
    if "agent_response" in state and state["agent_response"]:
        # The redo agent has already provided a complete response including acknowledgment and question
        return "get_user_input"
    else:
        # Something went wrong, fall back to asking the current question
        return "ask_question"

def create_intake_workflow():
    """
    Creates and returns the compiled LangGraph workflow for the intake form.
    
    The recursion limit should be set at runtime when invoking the workflow:
    
    Example:
        result = intake_workflow.invoke(
            inputs, 
            config={"recursion_limit": 500, "configurable": {...}}
        )
        
    Returns:
        The compiled graph application
    """
    workflow = StateGraph(ConversationState)
    
    workflow.add_node("ask_question", ask_question_node)
    workflow.add_node("get_user_input", get_user_input_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("handle_confusion", handle_confusion_node)
    workflow.add_node("handle_question", handle_question_node)
    workflow.add_node("handle_correction", handle_redo_agent)
    workflow.add_node("extract_entities", extract_entities_node)
    
    workflow.set_entry_point("ask_question")
    
    workflow.add_conditional_edges(
        "ask_question",
        should_continue,
        {
            END: END,
            "get_user_input": "get_user_input"
        }
    )
    
    # Using conditional edge to handle potential END state
    workflow.add_conditional_edges(
        "get_user_input",
        lambda state: END if state == END else "classify_intent",
        {
            END: END, 
            "classify_intent": "classify_intent"
        }
    )
    
    workflow.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "handle_confusion": "handle_confusion",
            "handle_question": "handle_question",
            "handle_correction": "handle_correction",
            "extract_entities": "extract_entities"
        }
    )
    
    # Updated workflow connections for better correction and confusion handling
    workflow.add_edge("handle_confusion", "get_user_input")
    workflow.add_edge("handle_question", "get_user_input")
    
    # Simplified correction handling - the redo agent handles everything
    workflow.add_conditional_edges(
        "handle_correction",
        route_after_correction,
        {
            "get_user_input": "get_user_input",
            "ask_question": "ask_question"
        }
    )
    
    workflow.add_edge("extract_entities", "ask_question")
    
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app

intake_workflow = create_intake_workflow() 
