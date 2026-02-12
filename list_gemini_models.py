import google.generativeai as genai
import os
import sys

# Windows UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "YOUR_API_KEY_HERE"
genai.configure(api_key=API_KEY)

print(f"Listing models for key: {API_KEY[:10]}...")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model: {m.name}")
except Exception as e:
    print(f"ERROR: {e}")
