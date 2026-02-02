# test_bedrock.py
import boto3, json, os
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

models_to_test = [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-instant-v1",
    "anthropic.claude-v2:1",
]

for model_id in models_to_test:
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            })
        )
        print(f"✅ WORKS: {model_id}")
        break
    except Exception as e:
        print(f"❌ FAILED: {model_id} - {str(e)[:100]}")