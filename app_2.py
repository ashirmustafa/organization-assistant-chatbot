# import gradio as gr
# from bedrock_client import ask_llm

# def chat(message, history):
#     """
#     Handle chat interaction
    
#     Args:
#         message: Current user message
#         history: List of messages
#     """
#     if not message.strip():
#         return ""
    
#     print(f"User: {message}")
#     print(f"History type: {type(history)}")
#     print(f"History: {history}")
    
#     # Get response from LLM
#     response = ask_llm(message, history)
    
#     print(f"Assistant: {response}\n")
    
#     return response

# # ChatInterface for Gradio 6.x
# demo = gr.ChatInterface(
#     fn=chat,
#     title="Puffersoft AI",
#     description="Testing Claude 3 Haiku via AWS Bedrock",
#     examples=["Hello! How are you?", "What is AWS Bedrock?", "Tell me a joke"]
# )

# if __name__ == "__main__":
#     print("Starting Gradio app...")
#     demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
#     print("App launched!")

# # new code

import json 
import gradio as gr
import requests
import os
from jose import jwt
from bedrock_client import ask_llm

# --- CONFIGURATION ---
COGNITO_DOMAIN = "ap-northeast-3a7zupoaxl.auth.ap-northeast-3.amazoncognito.com"
CLIENT_ID = "5q534ed2r1lan9m606bsnpnood"
CLIENT_SECRET = "1gaq1nib9oijqpmkr4nedqalu8naqf7k363atib3gf4en5pcms3e"
REDIRECT_URI = "https://localhost:7860/"

# Cognito URLs
LOGIN_URL = f"https://{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid+profile&redirect_uri={REDIRECT_URI}"
TOKEN_URL = f"https://{COGNITO_DOMAIN}/oauth2/token"
# Cognito Logout URL: Clears the session on AWS side and redirects back to your app
LOGOUT_URL = f"https://{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={REDIRECT_URI}"


def get_user_from_code(code):
    """Exchanges auth code for user info"""
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers)
        tokens = response.json()
        
        if "id_token" not in tokens:
            print(f"❌ TOKEN ERROR: {tokens}")
            return None
            
        # Decode the ID Token
        user_info = jwt.get_unverified_claims(tokens["id_token"])
        
        # --- DEBUG BLOCK: SEE EVERYTHING ---
        print("\n" + "="*50)
        print("RAW USER DATA FROM COGNITO:")
        print(json.dumps(user_info, indent=4)) # This prints the pretty JSON to your terminal
        print("="*50 + "\n")
        # ------------------------------------
        
        return user_info
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return None

def chat_wrapper(message, history):
    if not message.strip():
        return ""
    return ask_llm(message, history)

# --- UI LAYOUT ---
with gr.Blocks(title="Puffersoft AI") as demo:
    user_state = gr.State(None)

    # Header Row
    with gr.Row(variant="compact"):
        user_info_md = gr.Markdown("### 🔒 Authentication Required")
        # We now have the logout button ready
        logout_btn = gr.Button("Logout", visible=False, size="sm", variant="secondary")

    # Login Panel
    with gr.Column(visible=True) as login_panel:
        gr.Markdown("## Welcome to Puffersoft AI\nPlease sign in with your corporate account.")
        login_btn = gr.Button("Login with Microsoft", variant="primary")
        login_btn.click(None, None, None, js=f"() => window.location.href = '{LOGIN_URL}'")

    # Main Chat Panel
    with gr.Column(visible=False) as chat_panel:
        gr.ChatInterface(
            fn=chat_wrapper,
            examples=["Hello!", "Explain AWS Bedrock"],
        )

    # --- LOGIC ---

    # Logout Functionality: Just redirects to Cognito logout URL
    logout_btn.click(None, None, None, js=f"() => window.location.href = '{LOGOUT_URL}'")

    def on_page_load(request: gr.Request):
        params = dict(request.query_params)
        
        if "code" in params:
            user = get_user_from_code(params["code"])
            if user:
                email = user.get("preferred_username", "User")
                name = user.get("name", email)
                return (
                    gr.update(visible=False), # login_panel
                    gr.update(visible=True),  # chat_panel
                    f"### 👤 Logged in as: {name} ({email})", # user_info_md
                    gr.update(visible=True),  # logout_btn
                    user                      # user_state
                )
        
        return gr.update(visible=True), gr.update(visible=False), "### 🔒 Authentication Required", gr.update(visible=False), None

    demo.load(
        on_page_load, 
        inputs=None, 
        outputs=[login_panel, chat_panel, user_info_md, logout_btn, user_state]
    )

if __name__ == "__main__":
    CERT_FILE = "localhost+2.pem"
    KEY_FILE = "localhost+2-key.pem"

    if os.path.exists(CERT_FILE):
        # Setting theme here for Gradio 6.0 compatibility
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            ssl_certfile=CERT_FILE,
            ssl_keyfile=KEY_FILE,
            ssl_verify=False,
            share=False
        )