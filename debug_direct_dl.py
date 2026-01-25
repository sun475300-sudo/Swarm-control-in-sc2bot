import requests

def test_direct_dl():
    # Use a likely valid ID found previously
    url = "https://lotv.spawningtool.com/89323/download/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://lotv.spawningtool.com/replays/?race=1&tag=9"
    }
    print(f"Testing direct download: {url}")
    try:
        response = requests.get(url, headers=headers, verify=False, allow_redirects=False, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        if response.status_code in [301, 302]:
            print(f"Redirect Location: {response.headers.get('Location')}")
            
        if response.status_code == 200:
             print("Direct access allowed (200 OK)")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_dl()
