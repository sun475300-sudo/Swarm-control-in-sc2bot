import requests
import json

def test_api():
    url = "https://lotv.spawningtool.com/api/replays/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "limit": 1,
        "race": "Zerg"
    }
    print(f"Testing connectivity to {url}...")
    try:
        response = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        print(f"Content Sample: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
