import json 
import gradio as gr
import requests
import os
from jose import jwt

# --- CONFIGURATION ---
API_GATEWAY_URL = "https://yy9z5xqkqe.execute-api.eu-north-1.amazonaws.com/prod/chat"
COGNITO_DOMAIN = "ap-northeast-3a7zupoaxl.auth.ap-northeast-3.amazoncognito.com"
CLIENT_ID = "5q534ed2r1lan9m606bsnpnood"
CLIENT_SECRET = "1gaq1nib9oijqpmkr4nedqalu8naqf7k363atib3gf4en5pcms3e"
REDIRECT_URI = "https://localhost:7860/"

LOGIN_URL = f"https://{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid+profile&redirect_uri={REDIRECT_URI}"
TOKEN_URL = f"https://{COGNITO_DOMAIN}/oauth2/token"
LOGOUT_URL = f"https://{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={REDIRECT_URI}"

def get_user_from_code(code):
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
            return None
        return jwt.get_unverified_claims(tokens["id_token"])
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return None

# Global variable to store current user
current_user = None

def chat_wrapper(message, history):
    """
    Sends message to API Gateway with user context
    """
    if not message.strip():
        return ""
    
    # Extract user info from global state
    user_email = None
    user_name = None
    if current_user:
        user_email = current_user.get("preferred_username") or current_user.get("email")
        user_name = current_user.get("name")
    
    # Build payload with user context
    payload = {
        "message": message, 
        "history": history,
        "user_context": {
            "email": user_email,
            "name": user_name
        }
    }
    
    try:
        print(f"📤 SENDING PAYLOAD: {json.dumps(payload, indent=2)}")
        response = requests.post(API_GATEWAY_URL, json=payload, timeout=30)
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Raw Response: {response.text}")
        
        response_data = response.json()
        return response_data.get("response", f"Error: Key 'response' missing. Got: {response.text}")
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return f"Error connecting to Backend: {str(e)}"

# --- UI LAYOUT ---
with gr.Blocks(title="Puffersoft AI") as demo:
    user_state = gr.State(None)

    with gr.Row(variant="compact"):
        user_info_md = gr.Markdown("### 🔒 Authentication Required")
        logout_btn = gr.Button("Logout", visible=False, size="sm", variant="secondary")

    with gr.Column(visible=True) as login_panel:
        gr.Markdown("## Welcome to Puffersoft AI\nPlease sign in with your corporate account.")
        login_btn = gr.Button("Login", variant="primary")
        login_btn.click(None, None, None, js=f"() => window.location.href = '{LOGIN_URL}'")

    with gr.Column(visible=False) as chat_panel:
        gr.ChatInterface(
            fn=chat_wrapper,
            examples=["Hello!", "What's on my calendar tomorrow?", "Check Ashir's schedule"],
        )

    logout_btn.click(None, None, None, js=f"() => window.location.href = '{LOGOUT_URL}'")

    def on_page_load(request: gr.Request):
        global current_user
        params = dict(request.query_params)
        if "code" in params:
            user = get_user_from_code(params["code"])
            if user:
                current_user = user  # Store in global variable
                email = user.get("preferred_username") or user.get("email") or "User"
                name = user.get("name", email)
                return (
                    gr.update(visible=False), 
                    gr.update(visible=True),  
                    f"### 👤 Logged in as: {name} ({email})", 
                    gr.update(visible=True),  
                    user                      
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
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            ssl_certfile=CERT_FILE,
            ssl_keyfile=KEY_FILE,
            ssl_verify=False,
            share=False
        )