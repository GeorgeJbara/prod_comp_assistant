"""
Enhanced Airline Complaint API with TrustCall and LangGraph
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import uuid
import logging
import base64
from src.database import DatabaseManager
from src.trustcall_processor import TrustCallProcessor
from src.graph_processor import ComplaintGraphProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conversation_store: Dict[str, List[Dict[str, str]]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    logger.info("Initializing enhanced complaint system...")
    app.state.db = DatabaseManager()
    
    # Initialize processors
    app.state.trustcall_processor = TrustCallProcessor(app.state.db)
    app.state.graph_processor = ComplaintGraphProcessor(app.state.db)
    
    logger.info("All processors initialized successfully")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Complaint System ",
    description="Production ready",
    version="3.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComplaintRequest(BaseModel):
    """Request model for complaint processing"""
    message: str = Field(..., description="The user's message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I had a terrible experience on flight AA123. My luggage was lost!",
                "thread_id": "optional_thread_id"
            }
        }


class ComplaintResponse(BaseModel):
    """Response model for complaint processing"""
    response: str
    status: str
    ticket_id: Optional[str] = None
    thread_id: str
    missing_fields: Optional[List[str]] = None


@app.post("/api/v2/complaint", response_model=ComplaintResponse)
async def process_complaint(request: ComplaintRequest):
    """
    Process a complaint using TrustCall structured outputs
    
    This is the main endpoint using the production-ready TrustCall approach
    with structured outputs and validation.
    """
    try:
        # Generate or use existing thread ID
        thread_id = request.thread_id or f"thread_{uuid.uuid4().hex[:8]}"
        
        # Get conversation history
        history = conversation_store.get(thread_id, [])
        
        # Process with TrustCall processor (main approach)
        result = app.state.trustcall_processor.process_message(
            message=request.message,
            thread_id=thread_id,
            conversation_history=history
        )
        
        # Store conversation history
        history.append({"role": "user", "content": request.message})
        history.append({"role": "assistant", "content": result['response']})
        conversation_store[thread_id] = history[-20:]  # Keep last 20 messages
        
        # Return response
        return ComplaintResponse(
            response=result['response'],
            status=result['status'],
            ticket_id=result.get('ticket_id'),
            thread_id=thread_id,
            missing_fields=result.get('missing_fields')
        )
        
    except Exception as e:
        logger.error(f"Error processing complaint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/tickets/{ticket_id}")
async def get_ticket_by_id(ticket_id: str):
    """Get a specific ticket by ID"""
    try:
        ticket = app.state.db.get_ticket_by_id(ticket_id)
        if ticket:
            return {"ticket": ticket}
        else:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v2/tickets/clear")
async def clear_all_tickets():
    """Clear all tickets from the database"""
    try:
        # Clear the database
        count = app.state.db.clear_all_tickets()
        
        # Also clear conversation store
        conversation_store.clear()
        
        return {
            "status": "success",
            "message": f"Cleared {count} tickets from database",
            "conversations_cleared": True
        }
    except Exception as e:
        logger.error(f"Error clearing tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/tickets")
async def get_tickets():
    """Get all tickets"""
    try:
        tickets = app.state.db.get_all_tickets()
        return {"tickets": tickets, "count": len(tickets)}
    except Exception as e:
        logger.error(f"Error getting tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/graph")
async def get_graph():
    """Display the LangGraph workflow as an image"""
    try:
        # Try to generate PNG image
        from io import BytesIO
        graph = app.state.graph_processor.graph
        
        # First try draw_mermaid_png which requires additional deps
        try:
            png_bytes = graph.get_graph().draw_mermaid_png()
            return Response(content=png_bytes, media_type="image/png")
        except:
            pass
        
        # If that fails, try to generate ASCII representation
        try:
            graph_repr = graph.get_graph().draw_ascii()
            # Wrap in HTML for better display
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Workflow</title>
    <style>
        body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
        pre {{ background: #2d2d2d; padding: 20px; border-radius: 5px; overflow: auto; }}
    </style>
</head>
<body>
    <h1>LangGraph Workflow - ASCII View</h1>
    <pre>{graph_repr}</pre>
</body>
</html>"""
            return HTMLResponse(content=html_content)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Error generating graph: {e}")
    
    # Ultimate fallback - HTML with Mermaid
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Workflow - Airline Complaint System</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({ startOnLoad: true, theme: 'default' });</script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            padding: 20px; 
            margin: 0; 
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 15px; 
            padding: 40px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
        }
        h1 { 
            text-align: center; 
            color: #333; 
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .mermaid { 
            text-align: center; 
            background: #f8f9fa; 
            padding: 30px; 
            border-radius: 10px; 
            border: 2px solid #e0e0e0;
        }
        .info {
            margin-top: 30px;
            padding: 20px;
            background: #f0f4f8;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .info h3 {
            color: #333;
            margin-top: 0;
        }
        .info p {
            color: #666;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔄 LangGraph Workflow</h1>
        <p class="subtitle">Airline Complaint Processing System with TrustCall Patterns</p>
        
        <div class="mermaid">
            graph TD
                Start([🟢 Start]) --> Classify[📋 Classify Message]
                Classify -->|Is Complaint| Extract[📝 Extract Information]
                Classify -->|Not Complaint| Respond[💬 Generate Response]
                Extract --> Decide[🤔 Decide Action]
                Decide -->|Need Analysis| Analyze[🔍 Analyze Complaint]
                Decide -->|Execute| Execute[⚡ Execute Action]
                Decide -->|Need Info| Respond
                Analyze --> Execute
                Execute --> Respond
                Respond --> End([🔴 End])
                
                style Start fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
                style End fill:#ffe1e1,stroke:#f44336,stroke-width:3px
                style Classify fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
                style Extract fill:#fff3e0,stroke:#ff9800,stroke-width:2px
                style Analyze fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
                style Execute fill:#fff9c4,stroke:#ffeb3b,stroke-width:2px
                style Respond fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
                style Decide fill:#fce4ec,stroke:#e91e63,stroke-width:2px
        </div>
        
        <div class="info">
            <h3>📊 Workflow Description</h3>
            <p>
                This LangGraph workflow processes airline complaints through a series of intelligent nodes:
            </p>
            <ul style="color: #666;">
                <li><strong>Classify:</strong> Determines if the message is a complaint using TrustCall structured outputs</li>
                <li><strong>Extract:</strong> Extracts passenger information and complaint details from the conversation</li>
                <li><strong>Decide:</strong> Routes to appropriate action based on available information</li>
                <li><strong>Analyze:</strong> Categorizes the complaint and assigns priority level</li>
                <li><strong>Execute:</strong> Creates or updates tickets in the database</li>
                <li><strong>Respond:</strong> Generates appropriate customer service responses</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.get("/api/v2/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "processors": ["trustcall", "langgraph"]
    }


@app.get("/")
async def root():
    """API Information"""
    return {
        "name": "Airline Complaint System",
        "version": "3.0.0",
        "endpoints": {
            "/api/v2/complaint": "Process complaints (TrustCall)",
            "/api/v2/tickets": "Get all tickets",
            "/api/v2/tickets/{ticket_id}": "Get specific ticket",
            "/api/v2/tickets/clear": "Clear all tickets (DELETE)",
            "/api/v2/graph": "View LangGraph workflow diagram",
            "/docs": "API documentation"
        },
        "graph": "http://localhost:8002/api/v2/graph"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_enhanced:app", host="0.0.0.0", port=8002, reload=True)