"""
Main Application Entry Point
"""

import json
import os
from core.state import ConversationState
from core.workflow import intake_workflow
from utils.json_utils import load_input_json, format_initial_form_data

def main():
    """
    Run the intake form application using the LangGraph workflow.
    """
    print("Starting Philer Intake Form")
    print("---------------------------")
    print("Answer the questions to complete your real estate closing intake form.")
    print("You can ask questions at any time if you need clarification.")
    print("---------------------------")
    
    config = {
        "recursion_limit": 500, 
        "configurable": {"thread_id": "intake-thread-1"}
    }
    
    # Check if input_json.json exists and load its data
    initial_form_data = {}
    input_json_path = "input_json.json"
    if os.path.exists(input_json_path):
        print(f"Loading initial data from {input_json_path}")
        initial_form_data = format_initial_form_data(load_input_json(input_json_path))
    
    initial_state: ConversationState = {
        "form_data": initial_form_data,
        "conversation_history": [],
        "current_question_id": "welcome",
        "user_response": None,
        "intent": None,
        "agent_response": None,
        "is_done": False
    }

    final_state = None
    try:
        for event in intake_workflow.stream(initial_state, config=config, stream_mode="values"):
            final_state = event # Keep track of the latest state
            pass 
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        if final_state:
            print("\n--- State at Error ---")
            print(json.dumps(final_state, indent=2))
        return # Exit if an error occurs
    
    if final_state and final_state.get("is_done") and final_state.get("agent_response"):
         print(f"\nAssistant: {final_state['agent_response']}")
    
    if final_state:
        print(f"\n--- Final Form Data ---")
        print(json.dumps(final_state.get("form_data", {}), indent=2))
    
    print("\nThank you for using Philer!")

if __name__ == "__main__":
    main() 