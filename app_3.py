import json 
import gradio as gr
import requests
import os
from jose import jwt
# We no longer need 'from bedrock_client import ask_llm' if we are using the API

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
        if "id_token" not in tokens: return None
        return jwt.get_unverified_claims(tokens["id_token"])
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return None

# --- NEW CHAT WRAPPER (TALKS TO API GATEWAY) ---
def chat_wrapper(message, history):
    if not message.strip():
        return ""
    
    payload = {"message": message, "history": history}
    
    try:
        response = requests.post(API_GATEWAY_URL, json=payload, timeout=30)
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Raw Response: {response.text}") # Look at your terminal for this!
        
        response_data = response.json()
        return response_data.get("response", f"Error: Key 'response' missing. Got: {response.text}")
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return f"Error connecting to Backend: {str(e)}"

# --- UI LAYOUT (Kept same as your working login code) ---
with gr.Blocks(title="Puffersoft AI") as demo:
    user_state = gr.State(None)

    with gr.Row(variant="compact"):
        user_info_md = gr.Markdown("### 🔒 Authentication Required")
        logout_btn = gr.Button("Logout", visible=False, size="sm", variant="secondary")

    with gr.Column(visible=True) as login_panel:
        gr.Markdown("## Welcome to Puffersoft AI\nPlease sign in with your corporate account.")
        login_btn = gr.Button("Login with Microsoft", variant="primary")
        login_btn.click(None, None, None, js=f"() => window.location.href = '{LOGIN_URL}'")

    with gr.Column(visible=False) as chat_panel:
        # ChatInterface now uses the updated chat_wrapper
        gr.ChatInterface(
            fn=chat_wrapper,
            examples=["Hello!", "Explain AWS Bedrock"],
        )

    logout_btn.click(None, None, None, js=f"() => window.location.href = '{LOGOUT_URL}'")

    def on_page_load(request: gr.Request):
        params = dict(request.query_params)
        if "code" in params:
            user = get_user_from_code(params["code"])
            if user:
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