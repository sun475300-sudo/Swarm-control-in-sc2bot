import os
import requests
import json

def test_google():
    api_key = "YOUR_API_KEY_HERE"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "안녕? 반가워."}]}]
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"[Google Test] Status: {response.status_code}")
        if response.status_code == 200:
            print(f"[Google Test] Success: {response.json()['candidates'][0]['content']['parts'][0]['text']}")
        else:
            print(f"[Google Test] Error: {response.text}")
    except Exception as e:
        print(f"[Google Test] Exception: {e}")

def test_proxy():
    url = "http://127.0.0.1:8317/v1/messages"
    payload = {
        "model": "claude-sonnet-4-5",
        "messages": [{"role": "user", "content": "안녕?"}],
        "max_tokens": 100
    }
    try:
        response = requests.post(url, json=payload, headers={"x-api-key": "dummy", "anthropic-version": "2023-06-01"}, timeout=10)
        print(f"[Proxy Test] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"[Proxy Test] Success: {data.get('content', [{}])[0].get('text', 'No text')}")
        else:
            print(f"[Proxy Test] Error: {response.text}")
    except Exception as e:
        print(f"[Proxy Test] Exception: {e}")

if __name__ == "__main__":
    print("--- AI Connectivity Diagnostics ---")
    test_google()
    test_proxy()
