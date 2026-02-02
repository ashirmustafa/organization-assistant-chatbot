import json
import boto3

# Initialize clients
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
lambda_client = boto3.client("lambda", region_name="eu-north-1")

# Define the calendar tool for Bedrock
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
                    "days": {
                        "type": "integer",
                        "description": "Number of days ahead to check (1 = tomorrow, 7 = next week, 0 = today). Default is 1."
                    }
                },
                "required": ["name"]
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
        
        # Build system prompt
        system_prompt = [{
            "text": f"""You are a helpful calendar assistant. The logged-in user is {user_context.get('name', 'Unknown')} ({user_context.get('email', 'unknown@email.com')}).

When you receive a tool result with multiple matching users (indicated by a 'count' field greater than 1), format it as a clear numbered list and remember it in the conversation context.

If the user responds with just a number after you've shown them a list, they are selecting that numbered item from the list you just showed. Extract the corresponding person's name from the list and use it in your next tool call with the same parameters (like days) they originally requested.

Example conversation flow:
- User: "check abdul's calendar for next 2 days"
- You call tool: get_calendar_events(name="abdul", days=2)
- Tool returns: {{"count": 3, "users": [{{"name": "Abdul Basit", ...}}, {{"name": "Abdul Majid", ...}}, {{"name": "Abdul Rehman", ...}}]}}
- You respond: "I found 3 people named 'abdul': 1. Abdul Basit - abasit@... 2. Abdul Majid - amajid@... 3. Abdul Rehman - arehman@... Which person's calendar would you like to check?"
- User: "2"
- You understand: They want Abdul Majid's calendar for next 2 days
- You call tool: get_calendar_events(name="Abdul Majid", days=2)

When the user asks about "my calendar", "my schedule", or uses "me"/"my", use the logged-in user's name.

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
        
        # Call Bedrock with tool configuration
        print("🤖 Calling Bedrock with tool support...")
        response = bedrock.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=messages,
            system=system_prompt,
            toolConfig={
                "tools": [CALENDAR_TOOL]
            }
        )
        
        print(f"📤 Bedrock response: {json.dumps(response, default=str)}")
        
        # Check if Bedrock wants to use a tool
        stop_reason = response.get("stopReason")
        
        if stop_reason == "tool_use":
            print("🔧 Bedrock requested tool use")
            
            # Extract tool use from response
            content_blocks = response["output"]["message"]["content"]
            tool_use_block = None
            
            for block in content_blocks:
                if "toolUse" in block:
                    tool_use_block = block["toolUse"]
                    break
            
            if tool_use_block:
                tool_name = tool_use_block["name"]
                tool_input = tool_use_block["input"]
                tool_use_id = tool_use_block["toolUseId"]
                
                print(f"🔨 Tool: {tool_name}")
                print(f"📥 Input BEFORE processing: {tool_input}")
                print(f"👤 User context available: {user_context}")
                
                # Handle "me" keyword - replace with logged-in user's name
                extracted_name = tool_input.get("name", "").strip().lower()
                
                # Check if it's a "me" reference or empty
                if extracted_name in ["me", "my", "mine", "i", "myself", ""] or "my" in extracted_name:
                    if user_context.get("name"):
                        tool_input["name"] = user_context.get("name")
                        print(f"🔄 Replaced '{extracted_name}' with logged-in user: {tool_input['name']}")
                    else:
                        print(f"⚠️ No user context available, cannot replace 'me'")
                
                print(f"📥 Input AFTER processing: {tool_input}")
                
                # Invoke the calendar Lambda
                calendar_response = lambda_client.invoke(
                    FunctionName="puffersoft-graph-action",
                    InvocationType="RequestResponse",
                    Payload=json.dumps({
                        "body": json.dumps(tool_input)
                    })
                )
                
                # Parse calendar Lambda response
                calendar_result = json.loads(calendar_response["Payload"].read())
                calendar_body = json.loads(calendar_result.get("body", "{}"))
                
                print(f"📅 Calendar result: {json.dumps(calendar_body, indent=2)}")
                
                # Build tool result for Bedrock - ALWAYS pass to Bedrock, no bypassing
                messages.append({
                    "role": "assistant",
                    "content": response["output"]["message"]["content"]
                })
                
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [
                                    {"json": calendar_body}
                                ]
                            }
                        }
                    ]
                })
                
                # Call Bedrock again with the tool result
                print("🤖 Calling Bedrock again with tool result...")
                final_response = bedrock.converse(
                    modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                    messages=messages,
                    system=system_prompt,
                    toolConfig={
                        "tools": [CALENDAR_TOOL]
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
