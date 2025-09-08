"""
Simplified models for airline complaint system using function calling approach
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Category(str, Enum):
    DELAY = "DELAY"
    CANCELLATION = "CANCELLATION"
    BAGGAGE = "BAGGAGE"
    SERVICE = "SERVICE"
    REFUND = "REFUND"
    OTHER = "OTHER"


class PassengerInfo(BaseModel):
    """Passenger information model"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    flight_number: Optional[str] = None
    booking_reference: Optional[str] = None
    travel_date: Optional[str] = None


class TicketCreate(BaseModel):
    """Parameters for creating a new ticket"""
    passenger_info: PassengerInfo
    complaint: str = Field(description="The full complaint description")
    priority: Priority
    category: Category
    

class TicketUpdate(BaseModel):
    """Parameters for updating an existing ticket"""
    ticket_id: str
    passenger_info_updates: Optional[PassengerInfo] = None
    complaint_update: Optional[str] = None
    corrections: Optional[Dict[str, str]] = Field(
        None, 
        description="Any corrections to existing data (e.g., flight number corrections)"
    )


class InformationRequest(BaseModel):
    """Parameters for requesting missing information"""
    missing_fields: List[str] = Field(
        description="List of missing required fields"
    )
    current_info: PassengerInfo = Field(
        description="Information collected so far"
    )
    
    
class Ticket(BaseModel):
    """Database ticket model"""
    ticket_id: str
    thread_id: str
    passenger_name: Optional[str]
    passenger_email: Optional[str]
    passenger_phone: Optional[str]
    flight_number: Optional[str]
    booking_reference: Optional[str]
    original_complaint: str
    category: Optional[str]
    priority: Optional[str]
    assigned_team: Optional[str]
    status: str = "OPEN"
    created_at: datetime
    updated_at: datetime