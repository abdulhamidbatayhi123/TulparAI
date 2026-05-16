import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

print(f"Testing with BASE_URL: {BASE_URL}")

client = OpenAI(
  api_key=API_KEY,
  base_url=BASE_URL
)

try:
    print("Listing models...")
    # Some providers support listing models
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(f"{BASE_URL}/models", headers=headers)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print(f"Found {len(models)} models available.")
        # print first 5 models
        for m in models[:5]:
            print(f" - {m.get('id')}")
    else:
        print(f"Failed to list models: {response.text}")
        
    print("\nTrying chat completion with nvidia/nemotron-3-nano-omni-30b-a3b-reasoning...")
    completion = client.chat.completions.create(
      model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
      messages=[{"role":"user","content":"Write a short haiku about a winged horse."}],
      temperature=0.2,
      top_p=0.7,
      max_tokens=1024,
    )
    print("\nResponse:")
    print(completion.choices[0].message.content)
    print("\n✅ Smoke test successful!")
except Exception as e:
    print(f"❌ Error during smoke test: {e}")
