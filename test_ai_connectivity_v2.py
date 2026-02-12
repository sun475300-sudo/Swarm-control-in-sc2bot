import os
import requests
import json

def test_google():
    api_key = "YOUR_API_KEY_HERE"
    # Try v1 instead of v1beta and simpler model name
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "안녕? 반가워."}]}]
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"[Google Test] Status: {response.status_code}")
        if response.status_code == 200:
            print(f"[Google Test] Success!")
        else:
            print(f"[Google Test] Error: {response.text}")
    except Exception as e:
        print(f"[Google Test] Exception: {e}")

if __name__ == "__main__":
    test_google()
