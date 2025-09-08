# Airline Complaint System - Simplified Version

## Overview

This is a **dramatically simplified** version of the airline complaint system using **function calling** instead of complex graph flows.

## Comparison

| Metric | Original (Graph) | Simplified (Functions) |
|--------|-----------------|----------------------|
| **Lines of Code** | ~740 | ~350 |
| **Number of Files** | 8+ | 4 |
| **Nodes/Functions** | 11 nodes | 3 functions |
| **Complexity** | High | Low |
| **LLM Calls** | Variable (1-3) | Always 1 |

## Architecture

### Original Approach (Complex)
```
START → check_session → classify → extract → check_complete → 
analyze → assign → create_ticket → respond → END
```

### New Approach (Simple)
```
START → LLM with Functions → Execute Function → END
```

## Key Improvements

1. **Single LLM Call**: The LLM decides what to do in one call
2. **No Complex Routing**: No conditional edges or state machines
3. **Natural Abstraction**: Functions map directly to business operations
4. **Easy to Debug**: See exactly which function was called and why
5. **Maintainable**: Add new capabilities by adding functions

## Available Functions

1. **create_ticket**: Create new support ticket
2. **update_ticket**: Update existing ticket with new info
3. **request_information**: Ask for missing required fields

## Setup

1. Copy your `.env` file from the original project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the API:
   ```bash
   python api.py
   ```
   The API will run on port 8001 (different from original on 8000)

4. Test the system:
   ```bash
   python test_scenarios.py
   ```

## How It Works

1. **Message arrives** with thread_id
2. **Check for existing ticket** in database
3. **Send to LLM** with conversation history and available functions
4. **LLM decides** which function to call (or none for simple responses)
5. **Execute function** if called
6. **Return response** to user

## Example Flow

### Scenario: Complete Complaint
```
User: "I'm John Smith, john@email.com. Flight AA123 was delayed 5 hours"
LLM: Calls create_ticket(name="John Smith", email="john@email.com", 
                        flight="AA123", complaint="Flight delayed 5 hours", 
                        priority="HIGH", category="DELAY")
System: Creates ticket, returns confirmation
```

### Scenario: Missing Information
```
User: "I want to complain about my flight"
LLM: Calls request_information(missing_fields=["name", "contact", "flight"])
System: Returns request for missing info
```

### Scenario: Update Existing
```
User: "My phone is 555-1234" (existing ticket)
LLM: Calls update_ticket(ticket_id="TCK-123", phone="555-1234")
System: Updates database, confirms update
```

## Code Structure

```
airline-complaint-simplified/
├── api.py                 # FastAPI application (120 lines)
├── src/
│   ├── models.py         # Pydantic models (80 lines)
│   ├── database.py       # Database operations (110 lines)
│   └── processor.py      # Core logic with functions (240 lines)
├── test_scenarios.py     # Test suite
└── requirements.txt
```

## Benefits Over Original

1. **50% Less Code**: 350 lines vs 740 lines
2. **Easier to Understand**: Functions are self-explanatory
3. **Faster Development**: Add features by adding functions
4. **Better Debugging**: Clear function calls with arguments
5. **More Flexible**: LLM adapts to conversation naturally

## Trade-offs

- **Less Control**: Can't fine-tune individual decision points
- **Higher Cost**: Every message goes through LLM (no rule-based shortcuts)
- **Less Predictable**: LLM might make different decisions for similar inputs

## Conclusion

This simplified approach demonstrates how **function calling** can replace complex state machines for many use cases, resulting in cleaner, more maintainable code while preserving all functionality.