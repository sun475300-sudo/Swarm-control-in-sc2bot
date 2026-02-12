import requests

def test_proxy_specific():
    url = "http://127.0.0.1:8317/v1/messages"
    # Try the alias from config.yaml
    payload = {
        "model": "gemini-claude-sonnet-4-5",
        "messages": [{"role": "user", "content": "안녕? 반가워."}],
        "max_tokens": 100
    }
    try:
        # The proxy often expects a header to trigger specific logic or just works like Anthropic SDK
        headers = {
            "x-api-key": "dummy", 
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_proxy_specific()
