import requests
import json

base_url = "http://127.0.0.1:8765/chat"

# Step 1: User A introduces self
payload_a = {
    "message": "안녕? 내 이름은 선우야. 기억해줘!",
    "user": "user_a"
}
print(f"User A: {payload_a['message']}")
r1 = requests.post(base_url, json=payload_a)
print(f"JARVIS A: {r1.json().get('reply')}")

print("-" * 30)

# Step 2: User B asks about the name (Memory Test)
payload_b = {
    "message": "방금 내 이름이 뭐라고 했는지 알려줘.",
    "user": "user_b"
}
print(f"User B: {payload_b['message']}")
r2 = requests.post(base_url, json=payload_b)
print(f"JARVIS B: {r2.json().get('reply')}")

if "선우" in r2.json().get('reply', ''):
    print("\n✅ SUCCESS: Memory is shared across users!")
else:
    print("\n❌ FAILURE: Memory is still fragmented.")
