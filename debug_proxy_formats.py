import requests
import json

URL = "http://127.0.0.1:8317/v1/messages"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "dummy"
}

def test_model(model_name):
    print(f"\n--- Testing: {model_name} ---")
    data = {
        "model": model_name,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    try:
        resp = requests.post(URL, headers=HEADERS, json=data, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

models_to_test = [
    "claude-sonnet-4-5-20250929",
    "anthropic/claude-sonnet-4-5-20250929",
    "antigravity/claude-sonnet-4-5",
    "sonnet"
]

for m in models_to_test:
    test_model(m)
