from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

print(os.environ["HOME"])
API_KEY = os.getenv("OPENAI_API_KEY")
print(API_KEY)
BASE_URL = "https://nerc.guha-anderson.com/v1"
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
MODEL_NAME = "gpt-4o-mini"

resp = (
    client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You're a helpful assistant."},
            {
                "role": "user",
                "content": "hello - how are you? say a random sentence beginning with telepathy.",
            },
        ],
        temperature=0.1,
    )
    .choices[0]
    .message.content
)

print(resp)
