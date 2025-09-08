"""
Airline Complaint System - Main Entry Point
===========================================

This system demonstrates production-ready patterns for LLM applications:
- TrustCall Pattern: Structured outputs with Pydantic models
- LangGraph Pattern: State machine workflows (visualization only)

Usage:
    python main.py              # Start the API server
    python main.py --help       # Show help
    python main.py --test       # Run quick test
"""

import sys
import os
import argparse
import uvicorn
import requests
import json
import time
from colorama import init, Fore, Style

# Initialize colorama for Windows
init()

def print_header():
    """Print application header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN} AIRLINE COMPLAINT SYSTEM - Enhanced with TrustCall")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

def start_server(host="0.0.0.0", port=8002, reload=False):
    """Start the FastAPI server"""
    print_header()
    print(f"{Fore.GREEN}Starting API server...{Style.RESET_ALL}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload}")
    print(f"\n{Fore.YELLOW}API Documentation: http://localhost:{port}/docs{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Graph Visualization: http://localhost:{port}/api/v2/graph{Style.RESET_ALL}\n")
    
    uvicorn.run(
        "api_enhanced:app",
        host=host,
        port=port,
        reload=reload
    )

def run_quick_test():
    """Run a quick test of the API"""
    print_header()
    print(f"{Fore.GREEN}Running quick test...{Style.RESET_ALL}\n")
    
    API_URL = "http://localhost:8002"
    
    # Check if server is running
    try:
        response = requests.get(f"{API_URL}/api/v2/health")
        if response.status_code != 200:
            print(f"{Fore.RED}Error: API server is not running!{Style.RESET_ALL}")
            print(f"Please start the server first: python main.py")
            return
    except:
        print(f"{Fore.RED}Error: Cannot connect to API server!{Style.RESET_ALL}")
        print(f"Please start the server first: python main.py")
        return
    
    # Clear database
    print("1. Clearing database...")
    requests.delete(f"{API_URL}/api/v2/tickets/clear")
    
    # Test complete complaint
    print("\n2. Testing complete complaint...")
    complaint = {
        "message": "I am John Doe, john@example.com. Flight AA123 lost my luggage!",
        "thread_id": "test_001"
    }
    response = requests.post(f"{API_URL}/api/v2/complaint", json=complaint)
    data = response.json()
    
    if data.get("ticket_id"):
        print(f"   {Fore.GREEN}[OK] Ticket created: {data['ticket_id']}{Style.RESET_ALL}")
    else:
        print(f"   {Fore.RED}[X] Failed to create ticket{Style.RESET_ALL}")
    
    # Test progressive building
    print("\n3. Testing progressive complaint building...")
    thread_id = "test_002"
    messages = [
        "I want to complain",
        "Flight BA789 was delayed",
        "Sarah Johnson, sarah@test.com"
    ]
    
    for i, msg in enumerate(messages, 1):
        response = requests.post(
            f"{API_URL}/api/v2/complaint",
            json={"message": msg, "thread_id": thread_id}
        )
        data = response.json()
        
        if data.get("ticket_id"):
            print(f"   {Fore.GREEN}[OK] Ticket created after {i} messages: {data['ticket_id']}{Style.RESET_ALL}")
            break
        else:
            print(f"   Message {i}: Awaiting more information...")
    
    # Check tickets
    print("\n4. Checking all tickets...")
    response = requests.get(f"{API_URL}/api/v2/tickets")
    data = response.json()
    print(f"   Total tickets: {data['count']}")
    
    for ticket in data['tickets']:
        print(f"   - {ticket['ticket_id']}: {ticket['passenger_name']} ({ticket['status']})")
    
    print(f"\n{Fore.GREEN}Test completed successfully!{Style.RESET_ALL}")

def show_info():
    """Show system information"""
    print_header()
    print(f"{Fore.YELLOW}System Components:{Style.RESET_ALL}")
    print("  • TrustCall Processor: Structured outputs with Pydantic")
    print("  • LangGraph Processor: State machine workflows")
    print("  • PostgreSQL Database: Remote on Render")
    print("  • OpenAI API: GPT-4.1-mini model")
    
    print(f"\n{Fore.YELLOW}API Endpoints:{Style.RESET_ALL}")
    print("  POST   /api/v2/complaint       - Process complaints")
    print("  GET    /api/v2/tickets          - Get all tickets")
    print("  GET    /api/v2/tickets/{id}     - Get specific ticket")
    print("  DELETE /api/v2/tickets/clear    - Clear all tickets")
    print("  GET    /api/v2/graph            - View workflow diagram")
    print("  GET    /api/v2/health           - Health check")
    
    print(f"\n{Fore.YELLOW}Key Features:{Style.RESET_ALL}")
    print("  [OK] Single LLM call with structured outputs")
    print("  [OK] Progressive information gathering")
    print("  [OK] Conversation context management")
    print("  [OK] Automatic priority assignment")
    print("  [OK] Intelligent complaint summarization")
    print("  [OK] API call optimizations (trivial/duplicate detection)")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Airline Complaint System")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    
    # Use PORT from environment variable if available (for Render)
    default_port = int(os.environ.get("PORT", 8002))
    parser.add_argument("--port", type=int, default=default_port, help="Port to bind to")
    
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--test", action="store_true", help="Run quick test")
    parser.add_argument("--info", action="store_true", help="Show system information")
    
    args = parser.parse_args()
    
    if args.test:
        run_quick_test()
    elif args.info:
        show_info()
    else:
        start_server(args.host, args.port, args.reload)

if __name__ == "__main__":
    main()