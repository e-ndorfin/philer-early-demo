"""
State definition for the LangGraph workflow.
"""

from typing import TypedDict, List, Tuple, Dict, Any, Optional
from enum import Enum, auto

class IntentType(str, Enum):
    """Types of user response intents."""
    CONFUSION = "confusion"
    QUESTION = "question" 
    ANSWER = "answer"
    CORRECTION = "correction"

class CorrectionType(str, Enum):
    """Types of corrections a user might want to make."""
    GO_BACK = "go_back"
    INLINE_UPDATE = "inline_update"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_A_CORRECTION = "not_a_correction"

class CorrectionDetails(TypedDict, total=False):
    """Details about a correction request."""
    correction_type: str
    target_question_id: Optional[str]
    corrected_value: Optional[str]
    explanation: str

class ConversationState(TypedDict):
    """Represents the state of the conversation and form filling process."""
    
    form_data: Dict[str, Any]
    
    conversation_history: List[Tuple[str, str]] # List of (speaker, message)
    
    current_question_id: str
    
    user_response: Optional[str]
    
    intent: Optional[str]
    
    agent_response: Optional[str]
    
    is_done: bool
    
    is_verification: Optional[bool] 