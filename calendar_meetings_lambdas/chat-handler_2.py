# import json
# import boto3
# from datetime import datetime

# # Initialize clients
# bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
# lambda_client = boto3.client("lambda", region_name="eu-north-1")

# # Define the calendar GET tool
# CALENDAR_TOOL = {
#     "toolSpec": {
#         "name": "get_calendar_events",
#         "description": "Fetches calendar events for a specified user within a date range. Use this when the user asks about someone's schedule, meetings, or calendar.",
#         "inputSchema": {
#             "json": {
#                 "type": "object",
#                 "properties": {
#                     "name": {
#                         "type": "string",
#                         "description": "The name of the person whose calendar to check. Can be a first name, last name, or full name."
#                     },
#                     "start_date": {
#                         "type": "string",
#                         "description": "Start date in YYYY-MM-DD format, or use 'today', 'tomorrow'. Examples: '2026-01-29', 'today', 'tomorrow'"
#                     },
#                     "end_date": {
#                         "type": "string",
#                         "description": "End date in YYYY-MM-DD format, or use 'today', 'tomorrow'. If not specified, defaults to same as start_date. Examples: '2026-02-05', 'tomorrow'"
#                     }
#                 },
#                 "required": ["name"]
#             }
#         }
#     }
# }

# CREATE_EVENT_TOOL = {
#     "toolSpec": {
#         "name": "create_calendar_event",
#         "description": "Creates a new calendar event/meeting. Use this when the user wants to create, schedule, or book a meeting/event.",
#         "inputSchema": {
#             "json": {
#                 "type": "object",
#                 "properties": {
#                     "subject": {
#                         "type": "string",
#                         "description": "Event title/subject. If not provided by user, generate a descriptive title like 'Meeting with [attendees]'"
#                     },
#                     "start_datetime": {
#                         "type": "string",
#                         "description": "Start date and time in 'YYYY-MM-DD HH:MM' format (24-hour). Example: '2026-01-30 15:00' for 3pm on Jan 30"
#                     },
#                     "end_datetime": {
#                         "type": "string",
#                         "description": "End date and time in 'YYYY-MM-DD HH:MM' format (24-hour). If not provided, default to 1 hour after start time"
#                     },
#                     "attendees": {
#                         "type": "array",
#                         "items": {"type": "string"},
#                         "description": "List of attendee names to invite. Can be first names, full names, or emails. Example: ['Ehsaan', 'Abdul Majid']"
#                     },
#                     "location": {
#                         "type": "string",
#                         "description": "Meeting location (optional). Default is 'Microsoft Teams Meeting'"
#                     },
#                     "is_online": {
#                         "type": "boolean",
#                         "description": "Create a Microsoft Teams meeting link. Default: true"
#                     }
#                 },
#                 "required": ["subject", "start_datetime", "attendees"]
#             }
#         }
#     }
# }

# EMAIL_TOOL = {
#     "toolSpec": {
#         "name": "send_email",
#         "description": "Sends an email to one or more recipients. Use when user wants to send, email, or message someone.",
#         "inputSchema": {
#             "json": {
#                 "type": "object",
#                 "properties": {
#                     "recipients": {
#                         "type": "array",
#                         "items": {"type": "string"},
#                         "description": "List of recipient names or emails. Example: ['Ehsaan', 'Abdul Majid']"
#                     },
#                     "subject": {
#                         "type": "string",
#                         "description": "Email subject line"
#                     },
#                     "body": {
#                         "type": "string",
#                         "description": "Email message body/content"
#                     },
#                     "cc": {
#                         "type": "array",
#                         "items": {"type": "string"},
#                         "description": "Optional CC recipients (names or emails)"
#                     }
#                 },
#                 "required": ["recipients", "subject", "body"]
#             }
#         }
#     }
# }

# def lambda_handler(event, context):
#     try:
#         body = json.loads(event.get("body", "{}"))
#         message = body.get("message")
#         history = body.get("history", [])
#         user_context = body.get("user_context", {})
        
#         print(f"📩 Received message: {message}")
#         print(f"👤 User context: {user_context}")
        
#         now = datetime.utcnow()
#         current_date = now.strftime('%Y-%m-%d')
#         current_time = now.strftime('%H:%M')
        
#         system_prompt = [{
#             "text": f"""You are a helpful calendar assistant. The logged-in user is {user_context.get('name', 'Unknown')} ({user_context.get('email', 'unknown@email.com')}).

# CURRENT DATE: {current_date}
# CURRENT TIME: {current_time} UTC
# USER TIMEZONE: Pakistan Standard Time (UTC+5)

# CAPABILITIES:
# ✅ I CAN: Check calendars, compare schedules, find availability
# ✅ I CAN: Create meetings with attendees (Teams links included)
# ✅ I CAN: Send emails to one or more people
# ❌ I CANNOT: Create personal events (use calendar app directly)

# TIMEZONE HANDLING:
# - Calendar times are already converted to Pakistan time (PKT)
# - When displaying times, mention "Pakistan time" or "PKT"
# - For creating meetings: extract time EXACTLY as user says it (e.g., "3 PM" → "15:00")

# CALENDAR VIEWING:
# When checking calendars, you can specify dates:
# 1. Specific dates: Use YYYY-MM-DD format (e.g., "2026-01-29")
# 2. Relative terms: Use "today" or "tomorrow"

# When you receive a tool result with multiple matching users (count > 1), format as numbered list.
# If user responds with just a number, they are selecting that item.

# You can call multiple tools in parallel when needed.

# EVENT CREATION:
# Extract date/time in 'YYYY-MM-DD HH:MM' format (24-hour):
# - "tomorrow at 3pm" → "2026-01-30 15:00"
# - "Feb 15 at 2:30pm" → "2026-02-15 14:30"

# If end time not specified, default to 1 hour after start.
# Default to Teams meeting unless specified otherwise.

# EMAIL SENDING:
# CRITICAL: ALWAYS use the send_email tool when user asks to send email.
# NEVER say "email sent" without actually calling the tool.
# Even if you just sent an email, you MUST call the tool again for each new request.

# Recipients can be names (resolved to emails) or direct emails.
# Subject and body must be provided.
# CC is optional.

# If user says "send another email" or "send it again", you MUST call the send_email tool again.
# When user says "my calendar", use logged-in user's name: {user_context.get('name', 'Unknown')}.

# Always provide clear responses with complete details."""
#         }]
        
#         messages = []
#         for turn in history:
#             role = "user" if turn.get("role") == "user" else "assistant"
#             raw_content = turn.get("content", "")
            
#             if isinstance(raw_content, list):
#                 text_content = ""
#                 for item in raw_content:
#                     if isinstance(item, dict) and "text" in item:
#                         text_content += item["text"]
#                     elif isinstance(item, str):
#                         text_content += item
#             elif isinstance(raw_content, dict):
#                 text_content = raw_content.get("text", str(raw_content))
#             else:
#                 text_content = str(raw_content)
            
#             messages.append({"role": role, "content": [{"text": text_content}]})
        
#         messages.append({"role": "user", "content": [{"text": str(message)}]})
        
#         print("🤖 Calling Bedrock...")
#         response = bedrock.converse(
#             modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
#             messages=messages,
#             system=system_prompt,
#             toolConfig={"tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL, EMAIL_TOOL]}
#         )
        
#         print(f"📤 Bedrock response: {json.dumps(response, default=str)}")
        
#         stop_reason = response.get("stopReason")
        
#         if stop_reason == "tool_use":
#             print("🔧 Tool use requested")
            
#             content_blocks = response["output"]["message"]["content"]
#             tool_use_blocks = [block["toolUse"] for block in content_blocks if "toolUse" in block]
            
#             print(f"🔨 Found {len(tool_use_blocks)} tool(s)")
            
#             tool_results = []
            
#             for tool_use_block in tool_use_blocks:
#                 tool_name = tool_use_block["name"]
#                 tool_input = tool_use_block["input"]
#                 tool_use_id = tool_use_block["toolUseId"]
                
#                 print(f"🔨 Tool: {tool_name}")
#                 print(f"📥 Input: {tool_input}")
                
#                 if tool_name == "get_calendar_events":
#                     if "name" in tool_input:
#                         extracted_name = tool_input.get("name", "").strip().lower()
#                         if extracted_name in ["me", "my", "mine", "i", "myself", ""] or "my" in extracted_name:
#                             if user_context.get("name"):
#                                 tool_input["name"] = user_context.get("name")
                    
#                     try:
#                         calendar_response = lambda_client.invoke(
#                             FunctionName="puffersoft-graph-action",
#                             InvocationType="RequestResponse",
#                             Payload=json.dumps({"body": json.dumps(tool_input)})
#                         )
                        
#                         calendar_result = json.loads(calendar_response["Payload"].read())
#                         calendar_body = json.loads(calendar_result.get("body", "{}"))
                        
#                         print(f"📅 Result: {json.dumps(calendar_body, indent=2)}")
                        
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": calendar_body}]
#                         })
#                     except Exception as e:
#                         print(f"❌ Error: {str(e)}")
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": {"error": f"Failed: {str(e)}"}}]
#                         })
                
#                 elif tool_name == "create_calendar_event":
#                     print("📝 Creating event...")
                    
#                     attendee_names = tool_input.get("attendees", [])
#                     resolved_attendees = []
#                     unresolved = []
                    
#                     for name in attendee_names:
#                         try:
#                             search_response = lambda_client.invoke(
#                                 FunctionName="puffersoft-graph-action",
#                                 InvocationType="RequestResponse",
#                                 Payload=json.dumps({"body": json.dumps({"name": name})})
#                             )
                            
#                             search_result = json.loads(search_response["Payload"].read())
#                             search_body = json.loads(search_result.get("body", "{}"))
                            
#                             if "user" in search_body:
#                                 user = search_body["user"]
#                                 resolved_attendees.append({"name": user["name"], "email": user["email"]})
#                                 print(f"✅ {name} → {user['email']}")
#                             elif "count" in search_body and search_body["count"] > 1:
#                                 users_list = search_body.get("users", [])
#                                 clarification = f"Found {search_body['count']} people named '{name}':\n\n"
#                                 for idx, u in enumerate(users_list, 1):
#                                     clarification += f"{idx}. {u['name']} - {u['email']}\n"
#                                 clarification += f"\nWhich '{name}'?"
                                
#                                 tool_results.append({
#                                     "toolUseId": tool_use_id,
#                                     "content": [{"json": {
#                                         "error": "Ambiguous attendee",
#                                         "message": clarification,
#                                         "matches": users_list
#                                     }}]
#                                 })
#                                 unresolved.append(name)
#                                 break
#                             else:
#                                 unresolved.append(name)
#                         except Exception as e:
#                             print(f"❌ Error: {e}")
#                             unresolved.append(name)
                    
#                     if unresolved and not any("Ambiguous" in str(r) for r in tool_results):
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": {"error": f"Could not find: {', '.join(unresolved)}"}}]
#                         })
#                         continue
                    
#                     if unresolved:
#                         continue
                    
#                     event_payload = {
#                         "action": "create",
#                         "organizer_id": user_context.get("email"),
#                         "organizer_name": user_context.get("name"),
#                         "subject": tool_input.get("subject"),
#                         "start_datetime": tool_input.get("start_datetime"),
#                         "end_datetime": tool_input.get("end_datetime"),
#                         "attendees": resolved_attendees,
#                         "location": tool_input.get("location", "Microsoft Teams Meeting"),
#                         "is_online": tool_input.get("is_online", True)
#                     }
                    
#                     try:
#                         create_response = lambda_client.invoke(
#                             FunctionName="puffersoft-graph-action",
#                             InvocationType="RequestResponse",
#                             Payload=json.dumps({"body": json.dumps(event_payload)})
#                         )
                        
#                         create_result = json.loads(create_response["Payload"].read())
#                         create_body = json.loads(create_result.get("body", "{}"))
                        
#                         print(f"📅 Result: {json.dumps(create_body, indent=2)}")
                        
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": create_body}]
#                         })
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": {"error": f"Failed: {str(e)}"}}]
#                         })
                
#                 elif tool_name == "send_email":
#                     print("📧 Sending email...")
                    
#                     recipient_names = tool_input.get("recipients", [])
                    
#                     if not recipient_names:
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": {
#                                 "success": False,
#                                 "message": "❌ No recipients provided"
#                             }}]
#                         })
#                         continue
                    
#                     resolved_recipients = []
#                     unresolved = []
                    
#                     for name in recipient_names:
#                         if "@" in name:
#                             resolved_recipients.append({"email": name, "name": name})
#                             continue
                        
#                         try:
#                             search_response = lambda_client.invoke(
#                                 FunctionName="puffersoft-graph-action",
#                                 InvocationType="RequestResponse",
#                                 Payload=json.dumps({"body": json.dumps({"name": name})})
#                             )
                            
#                             search_result = json.loads(search_response["Payload"].read())
#                             search_body = json.loads(search_result.get("body", "{}"))
                            
#                             if "user" in search_body:
#                                 user = search_body["user"]
#                                 resolved_recipients.append({"name": user["name"], "email": user["email"]})
#                                 print(f"✅ {name} → {user['email']}")
#                             elif "count" in search_body and search_body["count"] > 1:
#                                 users_list = search_body.get("users", [])
#                                 clarification = f"Found {search_body['count']} people named '{name}':\n\n"
#                                 for idx, u in enumerate(users_list, 1):
#                                     clarification += f"{idx}. {u['name']} - {u['email']}\n"
#                                 clarification += f"\nWhich '{name}'?"
                                
#                                 tool_results.append({
#                                     "toolUseId": tool_use_id,
#                                     "content": [{"json": {
#                                         "success": False,
#                                         "message": clarification,
#                                         "matches": users_list
#                                     }}]
#                                 })
#                                 unresolved.append(name)
#                                 break
#                             else:
#                                 unresolved.append(name)
#                         except Exception as e:
#                             print(f"❌ Error: {e}")
#                             unresolved.append(name)
                    
#                     if unresolved:
#                         if not any("Found" in str(r) for r in tool_results):
#                             tool_results.append({
#                                 "toolUseId": tool_use_id,
#                                 "content": [{"json": {
#                                     "success": False,
#                                     "message": f"❌ Could not find: {', '.join(unresolved)}"
#                                 }}]
#                             })
#                         continue
                    
#                     cc_names = tool_input.get("cc", [])
#                     resolved_cc = []
#                     if cc_names:
#                         for name in cc_names:
#                             if "@" in name:
#                                 resolved_cc.append({"email": name, "name": name})
                    
#                     email_payload = {
#                         "action": "send_email",
#                         "sender_email": user_context.get("email"),
#                         "sender_name": user_context.get("name"),
#                         "recipients": resolved_recipients,
#                         "cc": resolved_cc,
#                         "subject": tool_input.get("subject"),
#                         "body": tool_input.get("body")
#                     }
                    
#                     try:
#                         email_response = lambda_client.invoke(
#                             FunctionName="puffersoft-graph-action",
#                             InvocationType="RequestResponse",
#                             Payload=json.dumps({"body": json.dumps(email_payload)})
#                         )
                        
#                         email_result = json.loads(email_response["Payload"].read())
#                         email_body = json.loads(email_result.get("body", "{}"))
                        
#                         print(f"📧 Result: {json.dumps(email_body, indent=2)}")
                        
#                         if email_body.get("success"):
#                             recipient_emails = ', '.join([r['email'] for r in resolved_recipients])
#                             tool_results.append({
#                                 "toolUseId": tool_use_id,
#                                 "content": [{"json": {
#                                     "success": True,
#                                     "message": f"✅ Email sent to: {recipient_emails}",
#                                     "subject": tool_input.get("subject")
#                                 }}]
#                             })
#                         else:
#                             error_msg = email_body.get("error", "Unknown error")
#                             tool_results.append({
#                                 "toolUseId": tool_use_id,
#                                 "content": [{"json": {
#                                     "success": False,
#                                     "message": f"❌ FAILED: {error_msg}"
#                                 }}]
#                             })
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
#                         import traceback
#                         print(traceback.format_exc())
#                         tool_results.append({
#                             "toolUseId": tool_use_id,
#                             "content": [{"json": {
#                                 "success": False,
#                                 "message": f"❌ System error: {str(e)}"
#                             }}]
#                         })
            
#             messages.append({
#                 "role": "assistant",
#                 "content": response["output"]["message"]["content"]
#             })
            
#             messages.append({
#                 "role": "user",
#                 "content": [{"toolResult": result} for result in tool_results]
#             })
            
#             print(f"📤 Sending {len(tool_results)} result(s) to Bedrock")
            
#             final_response = bedrock.converse(
#                 modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
#                 messages=messages,
#                 system=system_prompt,
#                 toolConfig={"tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL, EMAIL_TOOL]}
#             )
            
#             final_text = final_response["output"]["message"]["content"][0]["text"]
            
#             return {
#                 "statusCode": 200,
#                 "headers": {
#                     "Content-Type": "application/json",
#                     "Access-Control-Allow-Origin": "*",
#                     "Access-Control-Allow-Methods": "POST,OPTIONS"
#                 },
#                 "body": json.dumps({"response": final_text})
#             }
        
#         output_text = response["output"]["message"]["content"][0]["text"]
        
#         return {
#             "statusCode": 200,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Methods": "POST,OPTIONS"
#             },
#             "body": json.dumps({"response": output_text})
#         }
        
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
#         import traceback
#         print(traceback.format_exc())
#         return {
#             "statusCode": 500,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*"
#             },
#             "body": json.dumps({"error": str(e)})
#         }


#  march 12 


import json
import boto3
from datetime import datetime
from decimal import Decimal

# Initialize clients
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
lambda_client = boto3.client("lambda", region_name="eu-north-1")

# Global cache for knowledge base (loaded once per Lambda container)
KNOWLEDGE_BASE_CACHE = {"content": None, "loaded_at": None}

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
                        "description": "List of attendee names to invite. Can be first names, full names, or emails. Example: ['Ehsaan', 'Abdul Majid']"
                    },
                    "location": {
                        "type": "string",
                        "description": "Meeting location (optional). Default is 'Microsoft Teams Meeting'"
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

EMAIL_TOOL = {
    "toolSpec": {
        "name": "send_email",
        "description": "Sends an email to one or more recipients. Use when user wants to send, email, or message someone.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of recipient names or emails. Example: ['Ehsaan', 'Abdul Majid']"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email message body/content"
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CC recipients (names or emails)"
                    }
                },
                "required": ["recipients", "subject", "body"]
            }
        }
    }
}

# def load_knowledge_base():
#     """
#     Loads company knowledge base from SharePoint (cached)
#     Only loads once per Lambda container lifecycle
#     """
#     global KNOWLEDGE_BASE_CACHE
    
#     # Check if already loaded
#     if KNOWLEDGE_BASE_CACHE["content"] is not None:
#         print("📚 Using cached knowledge base")
#         return KNOWLEDGE_BASE_CACHE["content"]
    
#     # Load from graph-action Lambda
#     print("📚 Loading knowledge base from SharePoint...")
    
#     try:
#         kb_response = lambda_client.invoke(
#             FunctionName="puffersoft-graph-action",
#             InvocationType="RequestResponse",
#             Payload=json.dumps({"body": json.dumps({"action": "get_knowledge_base"})})
#         )
        
#         kb_result = json.loads(kb_response["Payload"].read())
#         kb_body = json.loads(kb_result.get("body", "{}"))
        
#         if kb_body.get("success"):
#             content = kb_body.get("content", "")
#             KNOWLEDGE_BASE_CACHE["content"] = content
#             KNOWLEDGE_BASE_CACHE["loaded_at"] = datetime.utcnow()
#             print(f"✅ Knowledge base loaded: {len(content)} chars from {kb_body.get('file_count', 0)} files")
#             return content
#         else:
#             print(f"⚠️ Knowledge base load failed: {kb_body.get('error')}")
#             return ""
    
#     except Exception as e:
#         print(f"⚠️ Could not load knowledge base: {e}")
#         return ""

def search_knowledge_base(query_text, history=[]):
    # 1. Contextualize the query (Optional but helpful)
    # If the user says "What about married ppl?", the search should be "Married employee benefits"
    
    # Generate embedding
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        body=json.dumps({"inputText": query_text})
    )
    query_embedding = json.loads(response['body'].read())['embedding']
    
    table = boto3.resource('dynamodb').Table('knowledge-base-chunks')
    
    # Note: Scanning 136 items is fast, but we should only pull text and embedding to save memory
    items = table.scan(ProjectionExpression="#txt, embedding", 
                       ExpressionAttributeNames={"#txt": "text"})['Items']

    def calculate_cosine_similarity(v1, v2):
        dot_product = sum(float(a) * float(b) for a, b in zip(v1, v2))
        norm_v1 = sum(float(a)**2 for a in v1)**0.5
        norm_v2 = sum(float(b)**2 for b in v2)**0.5
        return dot_product / (norm_v1 * norm_v2)

    scored_chunks = []
    for item in items:
        score = calculate_cosine_similarity(query_embedding, item['embedding'])
        scored_chunks.append((score, item['text']))
    
    # Sort and take top 5
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Print the top score for debugging in CloudWatch
    if scored_chunks:
        print(f"🔝 Top Match Score: {scored_chunks[0][0]}")
    
    relevant_context = "\n\n".join([chunk[1] for chunk in scored_chunks[:8]])
    return relevant_context

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        message = body.get("message")
        history = body.get("history", [])
        user_context = body.get("user_context", {})
        
        print(f"📩 Received message: {message}")
        print(f"👤 User context: {user_context}")
        
        # Load knowledge base (cached after first load)
        knowledge_base = search_knowledge_base(message)
        
        now = datetime.utcnow()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        
        # Build system prompt with knowledge base
        system_prompt = [{
            "text": f"""You are a helpful organizational assistant for Puffersoft. The logged-in user is {user_context.get('name', 'Unknown')} ({user_context.get('email', 'unknown@email.com')}).

CURRENT DATE: {current_date}
CURRENT TIME: {current_time} UTC
USER TIMEZONE: Pakistan Standard Time (UTC+5)

CAPABILITIES:
✅ I CAN: Answer questions about company policies, benefits, and procedures
✅ I CAN: Check calendars, compare schedules, find availability
✅ I CAN: Create meetings with attendees (Teams links included)
✅ I CAN: Send emails to one or more people
❌ I CANNOT: Create personal events (use calendar app directly)

COMPANY KNOWLEDGE BASE:
You have access to the following company documents and policies. Use this information to answer employee questions accurately.

{knowledge_base}

When answering questions about company policies:
- Reference specific policies from the knowledge base above
- Be precise with numbers, dates, and amounts
- If the answer isn't in the knowledge base, say you don't have that information

TIMEZONE HANDLING:
- Calendar times are already converted to Pakistan time (PKT)
- When displaying times, mention "Pakistan time" or "PKT"
- For creating meetings: extract time EXACTLY as user says it (e.g., "3 PM" → "15:00")

CALENDAR VIEWING:
When checking calendars, you can specify dates:
1. Specific dates: Use YYYY-MM-DD format (e.g., "2026-01-29")
2. Relative terms: Use "today" or "tomorrow"

When you receive a tool result with multiple matching users (count > 1), format as numbered list.
If user responds with just a number, they are selecting that item.

You can call multiple tools in parallel when needed.

EVENT CREATION:
Extract date/time in 'YYYY-MM-DD HH:MM' format (24-hour):
- "tomorrow at 3pm" → "2026-01-30 15:00"
- "Feb 15 at 2:30pm" → "2026-02-15 14:30"

If end time not specified, default to 1 hour after start.
Default to Teams meeting unless specified otherwise.

EMAIL SENDING:
CRITICAL: ALWAYS use the send_email tool when user asks to send email.
NEVER say "email sent" without actually calling the tool.
Even if you just sent an email, you MUST call the tool again for each new request.

Recipients can be names (resolved to emails) or direct emails.
Subject and body must be provided.
CC is optional.

If user says "send another email" or "send it again", you MUST call the send_email tool again.
When user says "my calendar", use logged-in user's name: {user_context.get('name', 'Unknown')}.

Always provide clear responses with complete details.""",
        
        }]
        
        messages = []
        for turn in history:
            role = "user" if turn.get("role") == "user" else "assistant"
            raw_content = turn.get("content", "")
            
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
        
        messages.append({"role": "user", "content": [{"text": str(message)}]})
        
        print("🤖 Calling Bedrock...")
        response = bedrock.converse(
            # modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=messages,
            system=system_prompt,
            toolConfig={"tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL, EMAIL_TOOL]}
        )
        
        print(f"📤 Bedrock response: {json.dumps(response, default=str)}")
        
        stop_reason = response.get("stopReason")
        
        if stop_reason == "tool_use":
            print("🔧 Tool use requested")
            
            content_blocks = response["output"]["message"]["content"]
            tool_use_blocks = [block["toolUse"] for block in content_blocks if "toolUse" in block]
            
            print(f"🔨 Found {len(tool_use_blocks)} tool(s)")
            
            tool_results = []
            
            for tool_use_block in tool_use_blocks:
                tool_name = tool_use_block["name"]
                tool_input = tool_use_block["input"]
                tool_use_id = tool_use_block["toolUseId"]
                
                print(f"🔨 Tool: {tool_name}")
                print(f"📥 Input: {tool_input}")
                
                if tool_name == "get_calendar_events":
                    if "name" in tool_input:
                        extracted_name = tool_input.get("name", "").strip().lower()
                        if extracted_name in ["me", "my", "mine", "i", "myself", ""] or "my" in extracted_name:
                            if user_context.get("name"):
                                tool_input["name"] = user_context.get("name")
                    
                    try:
                        calendar_response = lambda_client.invoke(
                            FunctionName="puffersoft-graph-action",
                            InvocationType="RequestResponse",
                            Payload=json.dumps({"body": json.dumps(tool_input)})
                        )
                        
                        calendar_result = json.loads(calendar_response["Payload"].read())
                        calendar_body = json.loads(calendar_result.get("body", "{}"))
                        
                        print(f"📅 Result: {json.dumps(calendar_body, indent=2)}")
                        
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": calendar_body}]
                        })
                    except Exception as e:
                        print(f"❌ Error: {str(e)}")
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {"error": f"Failed: {str(e)}"}}]
                        })
                
                elif tool_name == "create_calendar_event":
                    print("📝 Creating event...")
                    
                    attendee_names = tool_input.get("attendees", [])
                    resolved_attendees = []
                    unresolved = []
                    
                    for name in attendee_names:
                        try:
                            search_response = lambda_client.invoke(
                                FunctionName="puffersoft-graph-action",
                                InvocationType="RequestResponse",
                                Payload=json.dumps({"body": json.dumps({"name": name})})
                            )
                            
                            search_result = json.loads(search_response["Payload"].read())
                            search_body = json.loads(search_result.get("body", "{}"))
                            
                            if "user" in search_body:
                                user = search_body["user"]
                                resolved_attendees.append({"name": user["name"], "email": user["email"]})
                                print(f"✅ {name} → {user['email']}")
                            elif "count" in search_body and search_body["count"] > 1:
                                users_list = search_body.get("users", [])
                                clarification = f"Found {search_body['count']} people named '{name}':\n\n"
                                for idx, u in enumerate(users_list, 1):
                                    clarification += f"{idx}. {u['name']} - {u['email']}\n"
                                clarification += f"\nWhich '{name}'?"
                                
                                tool_results.append({
                                    "toolUseId": tool_use_id,
                                    "content": [{"json": {
                                        "error": "Ambiguous attendee",
                                        "message": clarification,
                                        "matches": users_list
                                    }}]
                                })
                                unresolved.append(name)
                                break
                            else:
                                unresolved.append(name)
                        except Exception as e:
                            print(f"❌ Error: {e}")
                            unresolved.append(name)
                    
                    if unresolved and not any("Ambiguous" in str(r) for r in tool_results):
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {"error": f"Could not find: {', '.join(unresolved)}"}}]
                        })
                        continue
                    
                    if unresolved:
                        continue
                    
                    event_payload = {
                        "action": "create",
                        "organizer_id": user_context.get("email"),
                        "organizer_name": user_context.get("name"),
                        "subject": tool_input.get("subject"),
                        "start_datetime": tool_input.get("start_datetime"),
                        "end_datetime": tool_input.get("end_datetime"),
                        "attendees": resolved_attendees,
                        "location": tool_input.get("location", "Microsoft Teams Meeting"),
                        "is_online": tool_input.get("is_online", True)
                    }
                    
                    try:
                        create_response = lambda_client.invoke(
                            FunctionName="puffersoft-graph-action",
                            InvocationType="RequestResponse",
                            Payload=json.dumps({"body": json.dumps(event_payload)})
                        )
                        
                        create_result = json.loads(create_response["Payload"].read())
                        create_body = json.loads(create_result.get("body", "{}"))
                        
                        print(f"📅 Result: {json.dumps(create_body, indent=2)}")
                        
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": create_body}]
                        })
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {"error": f"Failed: {str(e)}"}}]
                        })
                
                elif tool_name == "send_email":
                    print("📧 Sending email...")
                    
                    recipient_names = tool_input.get("recipients", [])
                    
                    if not recipient_names:
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {
                                "success": False,
                                "message": "❌ No recipients provided"
                            }}]
                        })
                        continue
                    
                    resolved_recipients = []
                    unresolved = []
                    
                    for name in recipient_names:
                        if "@" in name:
                            resolved_recipients.append({"email": name, "name": name})
                            continue
                        
                        try:
                            search_response = lambda_client.invoke(
                                FunctionName="puffersoft-graph-action",
                                InvocationType="RequestResponse",
                                Payload=json.dumps({"body": json.dumps({"name": name})})
                            )
                            
                            search_result = json.loads(search_response["Payload"].read())
                            search_body = json.loads(search_result.get("body", "{}"))
                            
                            if "user" in search_body:
                                user = search_body["user"]
                                resolved_recipients.append({"name": user["name"], "email": user["email"]})
                                print(f"✅ {name} → {user['email']}")
                            elif "count" in search_body and search_body["count"] > 1:
                                users_list = search_body.get("users", [])
                                clarification = f"Found {search_body['count']} people named '{name}':\n\n"
                                for idx, u in enumerate(users_list, 1):
                                    clarification += f"{idx}. {u['name']} - {u['email']}\n"
                                clarification += f"\nWhich '{name}'?"
                                
                                tool_results.append({
                                    "toolUseId": tool_use_id,
                                    "content": [{"json": {
                                        "success": False,
                                        "message": clarification,
                                        "matches": users_list
                                    }}]
                                })
                                unresolved.append(name)
                                break
                            else:
                                unresolved.append(name)
                        except Exception as e:
                            print(f"❌ Error: {e}")
                            unresolved.append(name)
                    
                    if unresolved:
                        if not any("Found" in str(r) for r in tool_results):
                            tool_results.append({
                                "toolUseId": tool_use_id,
                                "content": [{"json": {
                                    "success": False,
                                    "message": f"❌ Could not find: {', '.join(unresolved)}"
                                }}]
                            })
                        continue
                    
                    cc_names = tool_input.get("cc", [])
                    resolved_cc = []
                    if cc_names:
                        for name in cc_names:
                            if "@" in name:
                                resolved_cc.append({"email": name, "name": name})
                    
                    email_payload = {
                        "action": "send_email",
                        "sender_email": user_context.get("email"),
                        "sender_name": user_context.get("name"),
                        "recipients": resolved_recipients,
                        "cc": resolved_cc,
                        "subject": tool_input.get("subject"),
                        "body": tool_input.get("body")
                    }
                    
                    try:
                        email_response = lambda_client.invoke(
                            FunctionName="puffersoft-graph-action",
                            InvocationType="RequestResponse",
                            Payload=json.dumps({"body": json.dumps(email_payload)})
                        )
                        
                        email_result = json.loads(email_response["Payload"].read())
                        email_body = json.loads(email_result.get("body", "{}"))
                        
                        print(f"📧 Result: {json.dumps(email_body, indent=2)}")
                        
                        if email_body.get("success"):
                            recipient_emails = ', '.join([r['email'] for r in resolved_recipients])
                            tool_results.append({
                                "toolUseId": tool_use_id,
                                "content": [{"json": {
                                    "success": True,
                                    "message": f"✅ Email sent to: {recipient_emails}",
                                    "subject": tool_input.get("subject")
                                }}]
                            })
                        else:
                            error_msg = email_body.get("error", "Unknown error")
                            tool_results.append({
                                "toolUseId": tool_use_id,
                                "content": [{"json": {
                                    "success": False,
                                    "message": f"❌ FAILED: {error_msg}"
                                }}]
                            })
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        import traceback
                        print(traceback.format_exc())
                        tool_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": {
                                "success": False,
                                "message": f"❌ System error: {str(e)}"
                            }}]
                        })
            
            messages.append({
                "role": "assistant",
                "content": response["output"]["message"]["content"]
            })
            
            messages.append({
                "role": "user",
                "content": [{"toolResult": result} for result in tool_results]
            })
            
            print(f"📤 Sending {len(tool_results)} result(s) to Bedrock")
            
            final_response = bedrock.converse(
                # modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                messages=messages,
                system=system_prompt,
                toolConfig={"tools": [CALENDAR_TOOL, CREATE_EVENT_TOOL, EMAIL_TOOL]}
            )
            
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
        print(f"❌ Error: {str(e)}")
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

# ## 🧪 Test Questions

# After deploying, try:
# ```
# "How much medical allowance do I get as a bachelor?"
# Expected: Rs 25,000

# "What's the maternity leave policy?"
# Expected: 3 months

# "How many annual leave days do I have?"
# Expected: 22 days

# "What's the minimum internet allowance?"
# Expected: Rs. 4,000 per month