# import boto3, json, os
# from dotenv import load_dotenv

# load_dotenv()

# client = boto3.client(
#     "bedrock-runtime",
#     region_name="us-east-1",  # Changed to us-east-1 which has all models
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
# )

# # Use Claude 3 Haiku - most compatible, available everywhere
# MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# def ask_llm(prompt, history=None):
#     """
#     Ask the LLM with conversation history support
    
#     Args:
#         prompt: Current user message
#         history: List of messages from Gradio 6.x
#     """
#     # Build messages array with history
#     messages = []
    
#     if history:
#         for item in history:
#             # Gradio 6.x format: {'role': 'user/assistant', 'content': [{'text': '...', 'type': 'text'}]}
#             if isinstance(item, dict) and 'role' in item and 'content' in item:
#                 role = item['role']
#                 # Extract text from content array
#                 if isinstance(item['content'], list) and len(item['content']) > 0:
#                     text = item['content'][0].get('text', '')
#                     messages.append({"role": role, "content": text})
#             elif isinstance(item, (list, tuple)) and len(item) == 2:
#                 # Old format fallback: (user_msg, assistant_msg)
#                 user_msg, assistant_msg = item
#                 messages.append({"role": "user", "content": user_msg})
#                 if assistant_msg:
#                     messages.append({"role": "assistant", "content": assistant_msg})
    
#     # Add current prompt
#     messages.append({"role": "user", "content": prompt})
    
#     response = client.invoke_model(
#         modelId=MODEL_ID,
#         contentType="application/json",
#         accept="application/json",
#         body=json.dumps({
#             "anthropic_version": "bedrock-2023-05-31",
#             "messages": messages,
#             "max_tokens": 1000,
#             "temperature": 0.7
#         })
#     )

#     result = json.loads(response["body"].read())
#     return result["content"][0]["text"]

import boto3, json, os
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",  
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# Use Claude 3 Haiku - most compatible, available everywhere
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# System prompt - customize this for your demo!
SYSTEM_PROMPT = """You are PufferSoft AI, a helpful and friendly AI assistant created by PufferSoft. 

Your key characteristics:
- You specialize in Cloud computing and AI solutions
- You're enthusiastic about helping developers build amazing products
- You always introduce yourself as "PufferSoft AI" when greeting new users
- You maintain a professional yet approachable tone

When users ask about you, mention that you're powered by AWS Bedrock and built to assist with technical questions and problem-solving."""

def ask_llm(prompt, history=None):
    """
    Ask the LLM with conversation history support
    
    Args:
        prompt: Current user message
        history: List of messages from Gradio 6.x
    """
    # Build messages array with history
    messages = []
    
    if history:
        for item in history:
            # Gradio 6.x format: {'role': 'user/assistant', 'content': [{'text': '...', 'type': 'text'}]}
            if isinstance(item, dict) and 'role' in item and 'content' in item:
                role = item['role']
                # Extract text from content array
                if isinstance(item['content'], list) and len(item['content']) > 0:
                    text = item['content'][0].get('text', '')
                    messages.append({"role": role, "content": text})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                # Old format fallback: (user_msg, assistant_msg)
                user_msg, assistant_msg = item
                messages.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": assistant_msg})
    
    # Add current prompt
    messages.append({"role": "user", "content": prompt})
    
    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": SYSTEM_PROMPT, 
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        })
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]