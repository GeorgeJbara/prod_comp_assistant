"""
Pure TrustCall implementation - simplified but robust function calling
Based on structured outputs pattern from the courses
"""
from typing import Optional, Dict, Any, List, Literal, Union
from datetime import datetime
import uuid
import logging
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

from .models import Priority, Category
from .database import DatabaseManager

logger = logging.getLogger(__name__)


# ============================================================================
# TRUSTCALL STRUCTURED OUTPUT SCHEMAS
# ============================================================================

class PassengerInfoSchema(BaseModel):
    """Structured passenger information"""
    name: Optional[str] = Field(None, description="Passenger's full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    flight_number: Optional[str] = Field(None, description="Flight number")
    booking_reference: Optional[str] = Field(None, description="Booking reference")


class CreateTicketAction(BaseModel):
    """Action to create a new ticket"""
    action: Literal["create_ticket"]
    passenger_info: PassengerInfoSchema
    complaint: str = Field(description="Full complaint description")
    priority: Priority
    category: Category


class UpdateTicketAction(BaseModel):
    """Action to update existing ticket"""
    action: Literal["update_ticket"]
    ticket_id: str
    passenger_phone: Optional[str] = None
    passenger_email: Optional[str] = None
    flight_number: Optional[str] = None
    complaint_update: Optional[str] = Field(None, description="Additional complaint details")
    corrections: Optional[Dict[str, str]] = Field(None, description="Field corrections")


class RequestInfoAction(BaseModel):
    """Action to request missing information"""
    action: Literal["request_info"]
    missing_fields: List[str]
    current_info: PassengerInfoSchema


class AcknowledgeAction(BaseModel):
    """Action for simple acknowledgments"""
    action: Literal["acknowledge"]
    message: str


# Union type for all possible actions
ActionResponse = Union[
    CreateTicketAction,
    UpdateTicketAction,
    RequestInfoAction,
    AcknowledgeAction
]


class ConversationAnalysis(BaseModel):
    """Complete conversation analysis with action decision"""
    situation_summary: str = Field(description="Brief summary of the situation")
    has_complaint: bool = Field(description="Whether this involves a complaint")
    is_trivial_response: bool = Field(description="Whether this is just 'ok', 'thanks', etc.")
    extracted_info: PassengerInfoSchema
    action: ActionResponse = Field(description="The action to take")


# ============================================================================
# TRUSTCALL PROCESSOR
# ============================================================================

class TrustCallProcessor:
    """Processor using pure TrustCall structured outputs"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1"))
        )
    
    def process_message(self, message: str, thread_id: str, conversation_history: List[Any] = None) -> Dict[str, Any]:
        """Process message using TrustCall structured output"""
        
        # Early exit for trivial messages (no LLM call needed)
        trivial_messages = {
            'ok', 'okay', 'thanks', 'thank you', 'yes', 'no', 'sure', 
            'got it', 'understood', 'alright', 'fine', 'good', 'great'
        }
        
        if message.lower().strip() in trivial_messages:
            existing_ticket = self.db.get_ticket_by_thread(thread_id)
            if existing_ticket:
                return {
                    "response": f"Thank you. Your ticket {existing_ticket['ticket_id']} is being processed.",
                    "status": "acknowledged",
                    "ticket_id": existing_ticket['ticket_id']
                }
            else:
                return {
                    "response": "How can I help you with your flight complaint today?",
                    "status": "awaiting_complaint"
                }
        
        # Check for repetitive messages (same as last message)
        if conversation_history and len(conversation_history) > 0:
            last_user_msg = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "").lower().strip()
                    break
            
            if last_user_msg and last_user_msg == message.lower().strip():
                return {
                    "response": "I've already received this message. Is there anything else you'd like to add?",
                    "status": "duplicate_message"
                }
        
        # Check for existing ticket
        existing_ticket = self.db.get_ticket_by_thread(thread_id)
        
        # If ticket exists and is complete, limit further messages
        if existing_ticket and existing_ticket.get('status') == 'OPEN':
            # Count recent messages in this thread
            message_count = len([m for m in (conversation_history or []) if m.get('role') == 'user'])
            
            if message_count > 10:  # After 10 messages with an open ticket
                return {
                    "response": f"Your ticket {existing_ticket['ticket_id']} is already being processed. For urgent updates, please call our support line directly.",
                    "status": "ticket_exists",
                    "ticket_id": existing_ticket['ticket_id']
                }
        
        # Build conversation context
        context_messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = "User" if msg.get("role") == "user" else "Assistant"
                context_messages.append(f"{role}: {msg.get('content', '')}")
        
        conversation_text = "\n".join(context_messages)
        
        # Prepare the analysis prompt
        system_prompt = """You are an airline customer service AI with access to a ticket management system.

Analyze the conversation and decide on the appropriate action using these rules:

1. **Trivial Responses** (ok, thanks, yes, no): Return acknowledge action with polite response
2. **New Complaints**: If all required info is present, create_ticket. Otherwise request_info
3. **Existing Tickets**: Update if new info provided, otherwise acknowledge
4. **General Queries**: Acknowledge with helpful response

Required for new tickets:
- Passenger name
- Contact method (email OR phone)
- Clear complaint description
- You should determine priority and category based on the complaint

When analyzing, extract ALL available information from the ENTIRE conversation, not just the latest message."""

        # Add existing ticket context if present
        ticket_context = ""
        if existing_ticket:
            ticket_context = f"""
EXISTING TICKET FOUND:
- Ticket ID: {existing_ticket['ticket_id']}
- Name: {existing_ticket['passenger_name']}
- Email: {existing_ticket['passenger_email']}
- Phone: {existing_ticket['passenger_phone'] or 'Not provided'}
- Flight: {existing_ticket['flight_number']}
- Complaint: {existing_ticket['original_complaint']}
"""

        # Prepare the user prompt
        user_prompt = f"""{ticket_context}

Previous conversation:
{conversation_text}

Current message: {message}

Analyze this conversation and determine the appropriate action."""

        # Get structured response using TrustCall pattern
        try:
            # Use with_structured_output for reliable parsing
            analysis = self.llm.with_structured_output(ConversationAnalysis).invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Execute the action based on type
            action = analysis.action
            
            if isinstance(action, CreateTicketAction):
                return self._create_ticket(action, thread_id)
            elif isinstance(action, UpdateTicketAction):
                return self._update_ticket(action, existing_ticket)
            elif isinstance(action, RequestInfoAction):
                return self._request_info(action)
            elif isinstance(action, AcknowledgeAction):
                return self._acknowledge(action, existing_ticket)
            
        except Exception as e:
            logger.error(f"TrustCall processing error: {e}")
            # Fallback response
            return {
                "response": "I apologize, but I'm having trouble processing your request. Please try again or contact support directly.",
                "status": "error"
            }
    
    def _create_ticket(self, action: CreateTicketAction, thread_id: str) -> Dict[str, Any]:
        """Create a new ticket"""
        ticket_id = f"TCK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Determine team assignment
        team_map = {
            Priority.CRITICAL: "Emergency Response",
            Priority.HIGH: "Priority Support",
            Priority.MEDIUM: "Customer Service",
            Priority.LOW: "General Support"
        }
        
        ticket_data = {
            "ticket_id": ticket_id,
            "thread_id": thread_id,
            "passenger_name": action.passenger_info.name,
            "passenger_email": action.passenger_info.email,
            "passenger_phone": action.passenger_info.phone,
            "flight_number": action.passenger_info.flight_number,
            "booking_reference": action.passenger_info.booking_reference,
            "original_complaint": action.complaint,
            "category": action.category.value,
            "priority": action.priority.value,
            "assigned_team": team_map[action.priority],
            "status": "OPEN"
        }
        
        success = self.db.create_ticket(ticket_data)
        
        if success:
            response = f"""Dear {action.passenger_info.name},

Thank you for contacting us. Your complaint has been registered.

**Ticket Reference:** {ticket_id}
**Priority:** {action.priority.value}
**Category:** {action.category.value}
**Assigned to:** {team_map[action.priority]}

We will respond within our service level agreement timeframe:
- Critical: 2 hours
- High: 6 hours
- Medium: 24 hours
- Low: 72 hours

Best regards,
Customer Service Team"""
        else:
            response = "We encountered an error creating your ticket. Please try again."
        
        return {
            "response": response,
            "status": "ticket_created" if success else "error",
            "ticket_id": ticket_id if success else None
        }
    
    def _update_ticket(self, action: UpdateTicketAction, existing_ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing ticket"""
        updates = {}
        
        # Add direct updates
        if action.passenger_phone:
            updates["passenger_phone"] = action.passenger_phone
        if action.passenger_email:
            updates["passenger_email"] = action.passenger_email
        if action.flight_number:
            updates["flight_number"] = action.flight_number
        if action.complaint_update:
            updates["original_complaint"] = action.complaint_update
        
        # Apply corrections
        if action.corrections:
            for field, value in action.corrections.items():
                field_map = {
                    "flight": "flight_number",
                    "email": "passenger_email",
                    "phone": "passenger_phone"
                }
                db_field = field_map.get(field.lower(), field)
                updates[db_field] = value
        
        success = True
        if updates:
            success = self.db.update_ticket(action.ticket_id, updates)
            response = f"""Dear {existing_ticket['passenger_name']},

Your ticket {action.ticket_id} has been updated with the new information.

Thank you for providing these additional details.

Best regards,
Customer Service Team"""
        else:
            response = f"""Dear {existing_ticket['passenger_name']},

Thank you for your message regarding ticket {action.ticket_id}.

Your ticket is being processed by our {existing_ticket.get('assigned_team', 'support')} team.

Best regards,
Customer Service Team"""
        
        return {
            "response": response,
            "status": "ticket_updated" if updates else "acknowledged",
            "ticket_id": action.ticket_id
        }
    
    def _request_info(self, action: RequestInfoAction) -> Dict[str, Any]:
        """Request missing information"""
        missing = action.missing_fields
        
        # Format missing fields nicely
        if len(missing) == 1:
            fields_text = missing[0]
        elif len(missing) == 2:
            fields_text = f"{missing[0]} and {missing[1]}"
        else:
            fields_text = ", ".join(missing[:-1]) + f", and {missing[-1]}"
        
        response = f"""To process your complaint, I'll need {fields_text}.

Could you please provide these details so I can create a ticket for you?"""
        
        return {
            "response": response,
            "status": "awaiting_information",
            "missing_fields": missing
        }
    
    def _acknowledge(self, action: AcknowledgeAction, existing_ticket: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple acknowledgment"""
        return {
            "response": action.message,
            "status": "acknowledged",
            "ticket_id": existing_ticket["ticket_id"] if existing_ticket else None
        }