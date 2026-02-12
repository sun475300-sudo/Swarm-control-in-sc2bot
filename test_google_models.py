import os
import requests
import json

def test_google():
    api_key = "YOUR_API_KEY_HERE"
    models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": "hi"}]}]}
        try:
            response = requests.post(url, json=payload, timeout=5)
            print(f"Model {model}: {response.status_code}")
            if response.status_code != 200:
                print(f"  Info: {response.text[:200]}")
        except:
            print(f"Model {model}: failed")

if __name__ == "__main__":
    test_google()
