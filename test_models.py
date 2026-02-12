import asyncio
import aiohttp
import json

PROXY_URL = "http://127.0.0.1:8317/v1/messages"
SYSTEM_PROMPT = "You are a test bot."

MODELS = [
    "anthropic/claude-sonnet-4-5-20250929",
    "google/gemini-3-pro-preview"
]

print(f"Checking Proxy at {PROXY_URL}...")

async def test_model(model):
    print(f"\nTesting {model}...")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "system": SYSTEM_PROMPT,
        "max_tokens": 100,
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(PROXY_URL, json=payload, headers={"x-api-key": "dummy", "anthropic-version": "2023-06-01"}, timeout=10) as resp:
                status = resp.status
                text = await resp.text()
                
                if status == 200:
                    print(f"✅ Success! ({status})")
                    print(text[:200])
                else:
                    print(f"❌ Failed! ({status})")
                    print(f"Response: {text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

async def main():
    for model in MODELS:
        await test_model(model)

if __name__ == "__main__":
    asyncio.run(main())
