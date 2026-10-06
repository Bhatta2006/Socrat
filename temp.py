import os
from dotenv import dotenv_values
from openai import OpenAI

values = dotenv_values(".env")
key = os.environ.get("NEBIUS_API_KEY") or values.get("NEBIUS_API_KEY") or values.get("SOCRAT_TUTOR_GATEWAY_SECRET")
if not key:
    raise SystemExit("Configure NEBIUS_API_KEY or SOCRAT_TUTOR_GATEWAY_SECRET privately.")

client = OpenAI(
    base_url="https://api.tokenfactory.us-north1.nebius.com/v1/",
    api_key=key,
    max_retries=0,
    timeout=30,
)


response = client.chat.completions.create(
    model="zai-org/GLM-5.3-Flash",
    messages=[
        {
            "role": "system",
            "content": """SYSTEM_PROMPT"""
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """USER_MESSAGE"""
                }
            ]
        }
    ]
)

print(response.to_json())
