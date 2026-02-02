
import json
import boto3
from datetime import datetime

# Initialize clients
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
lambda_client = boto3.client("lambda", region_name="eu-north-1")

# Define the calendar GET tool
CALENDAR_TOOL = {
    "toolSpec": {
        "name": "get_calendar_events",
        "description": "Fetches calendar events for a specified user within a date range. Use this when the user asks about someone's schedule, meetings, or calendar.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person whose calendar to check. Can be a first name, last name, or full name."
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format, or use 'today', 'tomorrow'. Examples: '2026-01-29', 'today', 'tomorrow'"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format, or use 'today', 'tomorrow'. If not specified, defaults to same as start_date. Examples: '2026-02-05', 'tomorrow'"
                    }
                },
                "required": ["name"]
            }
        }
    }
}

# NEW: Define the calendar CREATE tool
CREATE_EVENT_TOOL = {
    "toolSpec": {
        "name": "create_calendar_event",
        "description": "Creates a new calendar event/meeting. Use this when the user wants to create, schedule, or book a meeting/event.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Event title/subject. If not provided by user, generate a descriptive title like 'Meeting with [attendees]'"
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Start date and time in 'YYYY-MM-DD HH:MM' format (24-hour). Example: '2026-01-30 15:00' for 3pm on Jan 30"
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "End date and time in 'YYYY-MM-DD HH:MM' format (24-hour). If not provided, default to 1 hour after start time"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee names to invite. Can be first names, full names, or emails. Example: ['Ehsaan', 'Abdul Majid', 'ashir@puffersoft.com']"
                    },
                    "location": {
                        "type": "string",
                        "description": "Meeting location (optional). Default is 'Microsoft Teams Meeting' if is_online=true"
                    },
                    "is_online": {
                        "type": "boolean",
                        "description": "Create a Microsoft Teams meeting link. Default: true"
                    }
                },
                "required": ["subject", "start_datetime", "attendees"]
            }
        }
    }
}

def lambda_handler(event, context):
    try:
        # Parse request
        body = json.loads(event.get("body", "{}"))
        message = body.get("message")
        history = body.get("history", [])
        user_context = body.get("user_context", {})
        
        print(f"📩 Received message: {message}")
        print(f"👤 User context: {user_context}")
        
        # Get current date for system prompt
        now = datetime.utcnow()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        current_day = now.strftime('%A')
        
        # Build system prompt
        system_prompt = [{
            "text": f"""You are a helpful calendar assistant. The logged-in user is {user_context.get('name', 'Unknown')} ({user_context.get('email', 'unknown@email.com')}).

CURRENT DATE: {current_date}
CURRENT TIME: {current_time} UTC

CRITICAL CONSTRAINTS:
1. ONLY CREATE MEETINGS: You can only create 'Meeting' events with start/end times and fetch calendar details.
2. REFUSE OTHER EVENTS: If asked for 'All Day' events, 'Tasks', 'Reminders', or 'Birthdays', you MUST say: "I am only capable of creating meeting events at the moment."
3. TIMEZONE HANDLING: 
   - Extract the date and time EXACTLY as the user says it.
   - If user says "3 PM", use "15:00". 
   - DO NOT subtract or add hours. The backend tool handles the timezone conversion.

CALENDAR VIEWING:
When checking calendars, you can specify dates in two ways:
1. Specific dates: Use YYYY-MM-DD format (e.g., "2026-01-29")
2. Relative terms: Use "today" or "tomorrow"

When you receive a tool result with multiple matching users (indicated by a 'count' field greater than 1), format it as a clear numbered list and remember it in the conversation context.

If the user responds with just a number after you've shown them a list, they are selecting that numbered item from the list you just showed.

You can call multiple tools in parallel when needed (e.g., checking multiple people's calendars at once for availability comparison).

EVENT CREATION:
When creating events:
1. Extract date/time in 'YYYY-MM-DD HH:MM' format (24-hour clock)
   - "tomorrow at 3pm" → "2026-01-30 15:00"
   - "Feb 15 at 2:30pm" → "2026-02-15 14:30"
   - "next Monday at 10am" → calculate the date → "2026-02-02 10:00"

2. If end time not specified, default to 1 hour after start time

3. If subject not provided, generate one like "Meeting with [attendees]"

4. Default to online Teams meeting (is_online: true) unless user specifies otherwise

5. Attendee names will be resolved to emails automatically - just pass the names as the user provides them

When the user asks about "my calendar", "my schedule", or uses "me"/"my", use the logged-in user's name: {user_context.get('name', 'Unknown')}.

Always tell the user what specific dates you checked or what event you created with full details.

Always provide clear, well-formatted responses with complete event details including subject, time, location, and organizer."""
        }]
        
        # Build messages for Bedrock
        messages = []
        for turn in history:
            role = "user" if turn.get("role") == "user" else "assistant"
            raw_content = turn.get("content", "")
            
            # Extract text from Gradio's format
            if isinstance(raw_content, list):
                text_content = ""
                for item in raw_content:
                    if isinstance(item, dict) and "text" in item:
                        text_content += item["text"]
                    elif isinstance(item, str):
                        text_content += item
            elif isinstance(raw_content, dict):
                text_content = raw_content.get("text", str(raw_content))
            else:
                text_content = str(raw_content)
            
            messages.append({"role": role, "content": [{"text": text_content}]})
        
        # Add current user message
        messages.append({"role": "user", "content": [{"text": str(message)}]})
        
        # Call Bedrock with BOTH tools
        print("🤖 Calling Bedrock with tool support...")
        response = bedrock.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=messages,
            system=system_prompt,
            toolConfig={
                "tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL]  # Both tools available
            }
        )
        
        print(f"📤 Bedrock response: {json.dumps(response, default=str)}")
        
        # Check if Bedrock wants to use a tool
        stop_reason = response.get("stopReason")
        
        if stop_reason == "tool_use":
            print("🔧 Bedrock requested tool use")
            
            # Extract ALL tool uses from response (not just the first one)
            content_blocks = response["output"]["message"]["content"]
            tool_use_blocks = []
            
            for block in content_blocks:
                if "toolUse" in block:
                    tool_use_blocks.append(block["toolUse"])
            
            print(f"🔨 Found {len(tool_use_blocks)} tool use(s)")
            
            # Process each tool use
            tool_results = []
            
            for tool_use_block in tool_use_blocks:
                tool_name = tool_use_block["name"]
                tool_input = tool_use_block["input"]
                tool_use_id = tool_use_block["toolUseId"]
                
                print(f"🔨 Processing tool: {tool_name}")
                print(f"📥 Input BEFORE processing: {tool_input}")
                
                # Handle different tools
                if tool_name == "get_calendar_events":
                    # Handle "me" keyword for GET events
                    if "name" in tool_input:
                        extracted_name = tool_input.get("name", "").strip().lower()
                        
                        if extracted_name in ["me", "my", "mine", "i", "myself", ""] or "my" in extracted_name:
                            if user_context.get("name"):
                                tool_input["name"] = user_context.get("name")
                                print(f"🔄 Replaced '{extracted_name}' with logged-in user: {tool_input['name']}")
                    
                    print(f"📥 Input AFTER processing: {tool_input}")
                    
                    # Call calendar Lambda for GET
                    try:
                        calendar_response = lambda_client.invoke(
                            FunctionName="puffersoft-graph-action",
                            InvocationType="RequestResponse",
                            Payload=json.dumps({
                                "body": json.dumps(tool_input)
                            })
                        )
                        
                        calendar_result = json.loads(calendar_response["Payload"].read())
                        calendar_body = json.loads(calendar_result.get("body", "{}"))
                        
                        print(f"📅 Calendar GET result: {json.dumps(calendar_body, indent=2)}")
                        
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": calendar_body}]
                        })
                        
                    except Exception as e:
                        print(f"❌ Error in GET: {str(e)}")
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {"error": f"Failed to fetch calendar: {str(e)}"}}]
                        })
                
                elif tool_name == "create_calendar_event":
                    # NEW: Handle event creation
                    print("📝 Creating calendar event...")
                    
                    # Extract attendee names
                    attendee_names = tool_input.get("attendees", [])
                    print(f"👥 Resolving {len(attendee_names)} attendee(s): {attendee_names}")
                    
                    # Resolve each attendee name to email
                    resolved_attendees = []
                    unresolved_attendees = []
                    
                    for attendee_name in attendee_names:
                        # Search for user
                        try:
                            search_response = lambda_client.invoke(
                                FunctionName="puffersoft-graph-action",
                                InvocationType="RequestResponse",
                                Payload=json.dumps({
                                    "body": json.dumps({"name": attendee_name})
                                })
                            )
                            
                            search_result = json.loads(search_response["Payload"].read())
                            search_body = json.loads(search_result.get("body", "{}"))
                            
                            # Check if single user found
                            if "user" in search_body:
                                user = search_body["user"]
                                resolved_attendees.append({
                                    "name": user["name"],
                                    "email": user["email"]
                                })
                                print(f"✅ Resolved '{attendee_name}' → {user['name']} ({user['email']})")
                            
                            # Check if multiple users found
                            elif "count" in search_body and search_body["count"] > 1:
                                # Return to user for clarification
                                users_list = search_body.get("users", [])
                                clarification_text = f"I found {search_body['count']} people named '{attendee_name}':\n\n"
                                for idx, u in enumerate(users_list, 1):
                                    clarification_text += f"{idx}. {u['name']} - {u['email']}\n"
                                clarification_text += f"\nPlease specify which '{attendee_name}' you meant before I create the event."
                                
                                tool_results.append({
                                    "toolUseId": tool_use_id,
                                    "content": [{"json": {
                                        "error": "Ambiguous attendee",
                                        "message": clarification_text,
                                        "ambiguous_attendee": attendee_name,
                                        "matches": users_list
                                    }}]
                                })
                                
                                # Stop processing this event creation
                                unresolved_attendees.append(attendee_name)
                                break
                            
                            # User not found
                            else:
                                unresolved_attendees.append(attendee_name)
                                print(f"❌ Could not find user '{attendee_name}'")
                        
                        except Exception as e:
                            print(f"❌ Error searching for '{attendee_name}': {str(e)}")
                            unresolved_attendees.append(attendee_name)
                    
                    # If there are unresolved attendees (not due to ambiguity), report error
                    if unresolved_attendees and not any("Ambiguous" in str(r) for r in tool_results):
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {
                                "error": f"Could not find the following attendees: {', '.join(unresolved_attendees)}. Please check the spelling or provide their full names."
                            }}]
                        })
                        continue
                    
                    # If ambiguity was found, we already added the result - skip creation
                    if unresolved_attendees:
                        continue
                    
                    # All attendees resolved - create the event
                    print(f"✅ All attendees resolved: {resolved_attendees}")
                    
                    # Build event creation payload
                    event_payload = {
                        "action": "create",
                        "organizer_id": user_context.get("email"),  # Logged-in user is organizer
                        "organizer_name": user_context.get("name"),
                        "subject": tool_input.get("subject"),
                        "start_datetime": tool_input.get("start_datetime"),
                        "end_datetime": tool_input.get("end_datetime"),
                        "attendees": resolved_attendees,
                        "location": tool_input.get("location", "Microsoft Teams Meeting"),
                        "is_online": tool_input.get("is_online", True)
                    }
                    
                    print(f"📤 Sending event creation request: {json.dumps(event_payload, indent=2)}")
                    
                    # Call calendar Lambda for CREATE
                    try:
                        create_response = lambda_client.invoke(
                            FunctionName="puffersoft-graph-action",
                            InvocationType="RequestResponse",
                            Payload=json.dumps({
                                "body": json.dumps(event_payload)
                            })
                        )
                        
                        create_result = json.loads(create_response["Payload"].read())
                        create_body = json.loads(create_result.get("body", "{}"))
                        
                        print(f"📅 Event CREATE result: {json.dumps(create_body, indent=2)}")
                        
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": create_body}]
                        })
                        
                    except Exception as e:
                        print(f"❌ Error creating event: {str(e)}")
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {"error": f"Failed to create event: {str(e)}"}}]
                        })
            
            # Build tool results for Bedrock - pass ALL results back
            messages.append({
                "role": "assistant",
                "content": response["output"]["message"]["content"]
            })
            
            # Add all tool results in a single user message
            messages.append({
                "role": "user",
                "content": [{"toolResult": result} for result in tool_results]
            })
            
            print(f"📤 Sending {len(tool_results)} tool result(s) back to Bedrock")
            
            # Call Bedrock again with the tool results
            print("🤖 Calling Bedrock again with tool result(s)...")
            final_response = bedrock.converse(
                modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                messages=messages,
                system=system_prompt,
                toolConfig={
                    "tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL]
                }
            )
            
            # Extract final text response
            final_text = final_response["output"]["message"]["content"][0]["text"]
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                },
                "body": json.dumps({"response": final_text})
            }
        
        # No tool use - return direct response
        output_text = response["output"]["message"]["content"][0]["text"]
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": json.dumps({"response": output_text})
        }
        
    except Exception as e:
        print(f"❌ Lambda Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "statusCode": 500, 
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": str(e)})
        }