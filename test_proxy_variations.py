import requests

def test_proxy_variations():
    url = "http://127.0.0.1:8317/v1/messages"
    models = [
        "anthropic/claude-sonnet-4-5-20250929",
        "antigravity/claude-sonnet-4-5",
        "claude-sonnet-4-5",
        "gemini-3-pro-preview"
    ]
    for model in models:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10
        }
        try:
            headers = {
                "x-api-key": "dummy", 
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"Model {model}: Status {response.status_code}")
            if response.status_code != 200:
                print(f"  Error: {response.text}")
            else:
                print(f"  Success!")
        except Exception as e:
            print(f"Model {model}: Exception {e}")

if __name__ == "__main__":
    test_proxy_variations()
