#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple Manus Dashboard connection test"""

import os
import requests

# Set environment variables
os.environ["MANUS_DASHBOARD_URL"] = "https://sc2aidash-bncleqgg.manus.space"
os.environ["MANUS_DASHBOARD_ENABLED"] = "1"

print("=" * 60)
print("Manus Dashboard Connection Test")
print("=" * 60)

# Test 1: Health check
print("\n[1/2] Health check...")
try:
    response = requests.get("https://sc2aidash-bncleqgg.manus.space/health", timeout=5)
    if response.status_code == 200:
        print("? Server connection: SUCCESS")
    else:
        print(f"?? Server response: {response.status_code}")
except Exception as e:
    print(f"? Connection failed: {e}")

# Test 2: Import client
print("\n[2/2] Client import test...")
try:
    from manus_dashboard_client import create_client_from_env
    client = create_client_from_env()
    if client and client.enabled:
        print("? Client created: SUCCESS")
        print(f"   URL: {client.base_url}")
        print(f"   Enabled: {client.enabled}")
    else:
        print("?? Client disabled or not available")
except Exception as e:
    print(f"? Client import failed: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
print("\n? Next steps:")
print("   1. Run bot: python run.py")
print("   2. Play game")
print("   3. Check dashboard: https://sc2aidash-bncleqgg.manus.space")
