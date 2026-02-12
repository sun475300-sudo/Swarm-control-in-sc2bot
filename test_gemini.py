import google.generativeai as genai
import os
import sys

# Windows UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "YOUR_API_KEY_HERE"
genai.configure(api_key=API_KEY)

print(f"Testing Gemini with key: {API_KEY[:10]}...")

model_name = 'gemini-1.5-pro'
print(f"Attempting to call {model_name}...")

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello, this is a connection test. Reply with 'OK' if you see this.")
    print("--- RESPONSE ---")
    print(response.text)
    print("--- END ---")
except Exception as e:
    print(f"ERROR: {e}")
