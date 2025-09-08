"""
Enhanced complaint processor using LangGraph and TrustCall patterns
Combines the best of both approaches from the courses
"""
from typing import Optional, Dict, Any, List, Literal, Annotated, TypedDict
from datetime import datetime, timedelta
import uuid
import logging
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, AnyMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()

from .models import Priority, Category
from .database import DatabaseManager

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION (from Module 2 - State Management)
# ============================================================================

class PassengerInfo(BaseModel):
    """Passenger information with Pydantic validation"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    flight_number: Optional[str] = None
    booking_reference: Optional[str] = None


def merge_passenger_info(existing: Optional[PassengerInfo], new: Optional[PassengerInfo]) -> Optional[PassengerInfo]:
    """Custom reducer for merging passenger info (Module 2 pattern)"""
    if not existing:
        return new
    if not new:
        return existing
    
    merged_dict = existing.model_dump()
    for key, value in new.model_dump().items():
        if value is not None:
            merged_dict[key] = value
    
    return PassengerInfo(**merged_dict)


class ComplaintState(TypedDict):
    """State schema using TypedDict (Module 2 best practice)"""
    # Messages with reducer
    messages: Annotated[List[AnyMessage], add_messages]
    
    # Session tracking
    thread_id: Optional[str]
    
    # Core data with custom reducer
    passenger_info: Annotated[Optional[PassengerInfo], merge_passenger_info]
    original_complaint: Optional[str]
    
    # Analysis results
    category: Optional[Category]
    priority: Optional[Priority]
    
    # Ticket management
    ticket_id: Optional[str]
    assigned_team: Optional[str]
    status: Optional[str]
    
    # Control flow
    info_complete: bool
    missing_fields: List[str]
    ticket_exists: bool
    
    # Progressive complaint building (Module 2 pattern)
    complaint_parts: List[str]
    is_building_complaint: bool
    
    # Action routing
    next_action: Optional[str]
    action_type: Optional[str]
    action_result: Optional[str]
    response: Optional[str]
    is_complaint: Optional[bool]
    classification_confidence: Optional[float]


# ============================================================================
# TRUSTCALL STRUCTURED OUTPUTS (from Agents course)
# ============================================================================

class ClassificationOutput(BaseModel):
    """Structured output for message classification"""
    is_complaint: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    

class ExtractionOutput(BaseModel):
    """Structured output for information extraction"""
    passenger_info: PassengerInfo
    complaint_description: Optional[str] = None
    is_complete: bool = False
    

class AnalysisOutput(BaseModel):
    """Structured output for complaint analysis"""
    category: Category
    priority: Priority
    sentiment: Literal["POSITIVE", "NEUTRAL", "NEGATIVE", "VERY_NEGATIVE"]
    key_issues: List[str]


class ActionDecision(BaseModel):
    """Structured decision for next action (TrustCall pattern)"""
    action: Literal["create_ticket", "update_ticket", "request_info", "acknowledge", "end"]
    missing_fields: Optional[List[str]] = None
    response_message: Optional[str] = None


# ============================================================================
# ENHANCED NODES WITH TRUSTCALL
# ============================================================================

class ComplaintGraphProcessor:
    """Main processor using LangGraph with TrustCall patterns"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1"))
        )
        
        # Build the graph
        self.graph = self._build_graph()
        self.graph_builder = None  # Store builder for visualization
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow (Module 1-2 patterns)"""
        
        # Initialize graph with state schema
        builder = StateGraph(ComplaintState)
        
        # Add nodes (simplified from 11 to 6 essential nodes)
        builder.add_node("classify", self._classify_message)
        builder.add_node("extract", self._extract_information)
        builder.add_node("analyze", self._analyze_complaint)
        builder.add_node("decide_action", self._decide_action)
        builder.add_node("execute_action", self._execute_action)
        builder.add_node("respond", self._generate_response)
        
        # Define flow with conditional routing
        builder.add_edge(START, "classify")
        
        # Route based on classification
        builder.add_conditional_edges(
            "classify",
            lambda state: "extract" if state.get("is_complaint") else "respond",
            {
                "extract": "extract",
                "respond": "respond"
            }
        )
        
        # After extraction, decide action
        builder.add_edge("extract", "decide_action")
        
        # Route based on action decision
        builder.add_conditional_edges(
            "decide_action",
            lambda state: state.get("next_action", "end"),
            {
                "analyze": "analyze",
                "execute": "execute_action",
                "respond": "respond",
                "end": END
            }
        )
        
        # Analysis leads to execution
        builder.add_edge("analyze", "execute_action")
        
        # Execution leads to response
        builder.add_edge("execute_action", "respond")
        
        # Response ends the flow
        builder.add_edge("respond", END)
        
        # Store builder for visualization
        self.graph_builder = builder
        
        # Compile with memory checkpointer (Module 5 pattern)
        memory = MemorySaver()
        return builder.compile(checkpointer=memory)
    
    
    def _classify_message(self, state: ComplaintState) -> Dict[str, Any]:
        """Classify if message is a complaint (using TrustCall structured output)"""
        
        # Get the latest message
        latest_msg = state["messages"][-1].content if state["messages"] else ""
        
        # Use structured output for reliable classification
        prompt = f"""Classify if this message is related to a complaint or issue:
        
Message: {latest_msg}

Consider the conversation context. Even greetings can lead to complaints."""
        
        result = self.llm.with_structured_output(ClassificationOutput).invoke(prompt)
        
        return {
            "is_complaint": result.is_complaint,
            "classification_confidence": result.confidence
        }
    
    def _extract_information(self, state: ComplaintState) -> Dict[str, Any]:
        """Extract passenger info and complaint (Module 2 pattern with merging)"""
        
        # Process all messages for progressive extraction
        all_messages = "\n".join([
            msg.content for msg in state["messages"] 
            if hasattr(msg, 'content')
        ])
        
        prompt = f"""Extract passenger information and complaint details from this conversation:

{all_messages}

Extract all available information. Mark as complete if we have:
- Name
- At least one contact method (email or phone)
- Clear complaint description"""
        
        result = self.llm.with_structured_output(ExtractionOutput).invoke(prompt)
        
        # Build complaint from parts if needed
        complaint = result.complaint_description
        if not complaint and state.get("complaint_parts"):
            complaint = " ".join(state["complaint_parts"])
        
        return {
            "passenger_info": result.passenger_info,
            "original_complaint": complaint,
            "info_complete": result.is_complete
        }
    
    def _analyze_complaint(self, state: ComplaintState) -> Dict[str, Any]:
        """Analyze complaint for category and priority"""
        
        prompt = f"""Analyze this airline complaint:

Complaint: {state['original_complaint']}
Passenger: {state['passenger_info'].name if state['passenger_info'] else 'Unknown'}

Determine category, priority, and sentiment."""
        
        result = self.llm.with_structured_output(AnalysisOutput).invoke(prompt)
        
        # Determine team assignment based on priority
        team_map = {
            Priority.CRITICAL: "Emergency Response",
            Priority.HIGH: "Priority Support",
            Priority.MEDIUM: "Customer Service",
            Priority.LOW: "General Support"
        }
        
        return {
            "category": result.category,
            "priority": result.priority,
            "assigned_team": team_map.get(result.priority, "Customer Service")
        }
    
    def _decide_action(self, state: ComplaintState) -> Dict[str, Any]:
        """Decide next action using TrustCall pattern"""
        
        # Check what's missing
        missing = []
        if state.get("passenger_info"):
            info = state["passenger_info"]
            if not info.name:
                missing.append("name")
            if not info.email and not info.phone:
                missing.append("contact information (email or phone)")
        else:
            missing.extend(["name", "contact information"])
        
        if not state.get("original_complaint"):
            missing.append("complaint details")
        
        # Decide action
        if state.get("ticket_exists"):
            action = "execute"  # Update existing
            next_action = "execute"
        elif missing:
            action = "request_info"
            next_action = "respond"
        elif state.get("info_complete"):
            action = "analyze"
            next_action = "analyze"
        else:
            action = "acknowledge"
            next_action = "respond"
        
        return {
            "next_action": next_action,
            "missing_fields": missing,
            "action_type": action
        }
    
    def _execute_action(self, state: ComplaintState) -> Dict[str, Any]:
        """Execute the decided action (create/update ticket)"""
        
        if state.get("ticket_exists"):
            # Update existing ticket
            updates = {}
            if state.get("passenger_info"):
                info = state["passenger_info"]
                if info.phone:
                    updates["passenger_phone"] = info.phone
                if info.email:
                    updates["passenger_email"] = info.email
            
            if state.get("original_complaint"):
                updates["original_complaint"] = state["original_complaint"]
            
            success = self.db.update_ticket(state["ticket_id"], updates)
            
            return {
                "action_result": "ticket_updated" if success else "update_failed"
            }
        else:
            # Create new ticket
            ticket_id = f"TCK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            ticket_data = {
                "ticket_id": ticket_id,
                "thread_id": state.get("thread_id"),
                "passenger_name": state["passenger_info"].name if state.get("passenger_info") else None,
                "passenger_email": state["passenger_info"].email if state.get("passenger_info") else None,
                "passenger_phone": state["passenger_info"].phone if state.get("passenger_info") else None,
                "flight_number": state["passenger_info"].flight_number if state.get("passenger_info") else None,
                "booking_reference": state["passenger_info"].booking_reference if state.get("passenger_info") else None,
                "original_complaint": state.get("original_complaint"),
                "category": state.get("category"),
                "priority": state.get("priority"),
                "assigned_team": state.get("assigned_team"),
                "status": "OPEN"
            }
            
            success = self.db.create_ticket(ticket_data)
            
            return {
                "ticket_id": ticket_id if success else None,
                "action_result": "ticket_created" if success else "creation_failed"
            }
    
    def _generate_response(self, state: ComplaintState) -> Dict[str, Any]:
        """Generate appropriate response based on state"""
        
        if state.get("missing_fields"):
            # Request missing information
            fields_text = ", ".join(state["missing_fields"])
            response = f"To process your complaint, I'll need {fields_text}. Could you please provide these details?"
        
        elif state.get("ticket_id"):
            # Ticket created/updated
            name = state["passenger_info"].name if state.get("passenger_info") else "Valued Customer"
            response = f"""Dear {name},

Thank you for contacting us. Your complaint has been registered.

**Ticket Reference:** {state['ticket_id']}
**Priority:** {state.get('priority', 'MEDIUM')}
**Assigned to:** {state.get('assigned_team', 'Customer Service')}

We will respond within our service level agreement timeframe.

Best regards,
Customer Service Team"""
        
        elif not state.get("is_complaint"):
            # Non-complaint message
            response = "Thank you for contacting us. How may I assist you today?"
        
        else:
            # General acknowledgment
            response = "Thank you for your message. Please provide more details about your concern."
        
        return {
            "response": response
        }
    
    def process_message(self, message: str, thread_id: str, conversation_history: List[Any] = None) -> Dict[str, Any]:
        """Main entry point - process message through the graph"""
        
        # Check for existing ticket
        existing_ticket = self.db.get_ticket_by_thread(thread_id)
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "thread_id": thread_id,
            "ticket_exists": existing_ticket is not None,
            "ticket_id": existing_ticket["ticket_id"] if existing_ticket else None
        }
        
        # Add existing ticket info to state if present
        if existing_ticket:
            initial_state["passenger_info"] = PassengerInfo(
                name=existing_ticket.get("passenger_name"),
                email=existing_ticket.get("passenger_email"),
                phone=existing_ticket.get("passenger_phone"),
                flight_number=existing_ticket.get("flight_number"),
                booking_reference=existing_ticket.get("booking_reference")
            )
            initial_state["original_complaint"] = existing_ticket.get("original_complaint")
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") == "user":
                    initial_state["messages"].append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    initial_state["messages"].append(AIMessage(content=msg["content"]))
        
        # Run through the graph with thread_id for memory
        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.graph.invoke(initial_state, config)
        
        # Return result
        return {
            "response": final_state.get("response", "Thank you for contacting us."),
            "status": final_state.get("action_result", "processed"),
            "ticket_id": final_state.get("ticket_id"),
            "missing_fields": final_state.get("missing_fields")
        }