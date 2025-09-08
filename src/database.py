"""
Simplified database manager for airline complaint system
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/airline_complaints'
        )
        self.init_tables()
    
    def _get_connection(self):
        return psycopg2.connect(self.connection_string)
    
    def init_tables(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        ticket_id VARCHAR(50) PRIMARY KEY,
                        thread_id VARCHAR(100),
                        passenger_name VARCHAR(200),
                        passenger_email VARCHAR(200),
                        passenger_phone VARCHAR(50),
                        flight_number VARCHAR(20),
                        booking_reference VARCHAR(50),
                        original_complaint TEXT,
                        category VARCHAR(50),
                        priority VARCHAR(20),
                        assigned_team VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'OPEN',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(thread_id)
                    )
                """)
                conn.commit()
        logger.info("Database tables initialized")
    
    def create_ticket(self, ticket_data: Dict[str, Any]) -> bool:
        """Create a new ticket"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tickets (
                            ticket_id, thread_id, passenger_name, passenger_email,
                            passenger_phone, flight_number, booking_reference,
                            original_complaint, category, priority, assigned_team, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        ticket_data['ticket_id'],
                        ticket_data['thread_id'],
                        ticket_data.get('passenger_name'),
                        ticket_data.get('passenger_email'),
                        ticket_data.get('passenger_phone'),
                        ticket_data.get('flight_number'),
                        ticket_data.get('booking_reference'),
                        ticket_data['original_complaint'],
                        ticket_data.get('category'),
                        ticket_data.get('priority'),
                        ticket_data.get('assigned_team'),
                        ticket_data.get('status', 'OPEN')
                    ))
                    conn.commit()
            logger.info(f"Ticket {ticket_data['ticket_id']} created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return False
    
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing ticket"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build dynamic update query
                    update_fields = []
                    values = []
                    
                    for field, value in updates.items():
                        if field not in ['ticket_id', 'thread_id', 'created_at']:
                            update_fields.append(f"{field} = %s")
                            values.append(value)
                    
                    if not update_fields:
                        return True
                    
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(ticket_id)
                    
                    query = f"""
                        UPDATE tickets 
                        SET {', '.join(update_fields)}
                        WHERE ticket_id = %s
                    """
                    
                    cursor.execute(query, values)
                    conn.commit()
                    
            logger.info(f"Ticket {ticket_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            return False
    
    def get_ticket_by_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by thread ID"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM tickets WHERE thread_id = %s",
                        (thread_id,)
                    )
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get ticket for thread {thread_id}: {e}")
            return None
    
    def get_all_tickets(self) -> List[Dict[str, Any]]:
        """Get all tickets"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get tickets: {e}")
            return []
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by ID"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM tickets WHERE ticket_id = %s",
                        (ticket_id,)
                    )
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_id}: {e}")
            return None
    
    def clear_all_tickets(self) -> int:
        """Clear all tickets from database and return count of deleted tickets"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM tickets")
                    count = cursor.fetchone()[0]
                    cursor.execute("DELETE FROM tickets")
                    conn.commit()
                    logger.info(f"Cleared {count} tickets from database")
                    return count
        except Exception as e:
            logger.error(f"Failed to clear tickets: {e}")
            return 0