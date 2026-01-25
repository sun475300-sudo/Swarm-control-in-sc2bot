import requests

def test_html():
    url = "https://lotv.spawningtool.com/replays/?race=1" # Zerg?
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"Fetching HTML from {url}...")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
             print("Success! HTML Content Sample:")
             print(response.text[:500])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_html()
