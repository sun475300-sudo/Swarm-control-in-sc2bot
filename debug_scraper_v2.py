import requests
import sys

def fetch_and_save(url, filename):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        print(f"Status: {response.status_code}")
        
        # Save with explicit encoding
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved to {filename}")
        
        # Print a snippet safely
        print("Snippet:")
        print(response.text[:500].encode('utf-8', errors='ignore').decode('utf-8'))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test 1: Replays page (Best for raw files)
    fetch_and_save("https://lotv.spawningtool.com/replays/?race=1", "dump_replays.html")
    
    # Test 2: Build Order page (User suggestion)
    fetch_and_save("https://lotv.spawningtool.com/build/zvx/", "dump_builds.html")

    print("\n--- Parsing Links ---")
    import re
    for fname in ["dump_replays.html", "dump_builds.html"]:
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Parsing {fname}...")
            # Look for numeric links
            links = re.findall(r'href=["\'](/replays/\d+/|/build/\d+/|/\d+/)["\']', content)
            print(f"Found {len(links)} links: {links[:5]}")
            
            # Look for any href
            all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', content)
            # Filter for likely candidates
            candidates = [h for h in all_hrefs if any(x in h for x in ['replays', 'build', 'download'])]
            print(f"Candidates: {candidates[:5]}")
            
        except Exception as e:
            print(f"Error parsing {fname}: {e}")
