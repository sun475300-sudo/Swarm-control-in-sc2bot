import requests
import re

def scrape_ids():
    url = "https://lotv.spawningtool.com/replays/?race=1&tag=9" # Tag 9 = Professional? Or just race=1 (Zerg)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        if response.status_code == 200:
            # Regex to find replay links: <a href="/replays/123456/">
            pattern = r'href="/replays/(\d+)/"'
            ids = re.findall(pattern, response.text)
            unique_ids = list(set(ids))
            print(f"Found {len(unique_ids)} replay IDs: {unique_ids[:5]}...")
            
            # Check for download link pattern if possible, but usually it is constructed.
            pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_ids()
