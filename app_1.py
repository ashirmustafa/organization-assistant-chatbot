import gradio as gr
from bedrock_client import ask_llm

def chat(message, history):
    """
    Handle chat interaction
    
    Args:
        message: Current user message
        history: List of messages
    """
    if not message.strip():
        return ""
    
    print(f"User: {message}")
    print(f"History type: {type(history)}")
    print(f"History: {history}")
    
    # Get response from LLM
    response = ask_llm(message, history)
    
    print(f"Assistant: {response}\n")
    
    return response

# ChatInterface for Gradio 6.x
demo = gr.ChatInterface(
    fn=chat,
    title="Puffersoft AI",
    description="Testing Claude 3 Haiku via AWS Bedrock",
    examples=["Hello! How are you?", "What is AWS Bedrock?", "Tell me a joke"]
)

if __name__ == "__main__":
    print("Starting Gradio app...")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
    print("App launched!")

