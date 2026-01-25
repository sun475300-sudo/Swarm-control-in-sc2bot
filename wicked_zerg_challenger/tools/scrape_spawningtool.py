import requests
import re
import os
import zipfile
import io
from pathlib import Path
import time
import random

# Configuration
BASE_URL = "https://lotv.spawningtool.com"
SEARCH_URL = "https://lotv.spawningtool.com/replays/?pro_only=on&query=&p1-race=2&p2-race=&after_played_on=&before_played_on=&patch=&p="
DOWNLOAD_DIR = Path("D:/replays/replays")
MAX_PAGES = 5  # Start with 5 pages to test (approx 100-125 replays)
DELAY_MIN = 1.0
DELAY_MAX = 3.0

def setup_directories():
    if not DOWNLOAD_DIR.exists():
        DOWNLOAD_DIR.mkdir(parents=True)
    print(f"[SETUP] Download directory: {DOWNLOAD_DIR}")

def get_replay_links(page_num):
    url = f"{SEARCH_URL}{page_num}"
    try:
        print(f"[CRAWL] Fetching page {page_num}...")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch page {page_num}: Status {response.status_code}")
            return []
        
        # Simple regex to find replay links mostly like /12345/
        # Format: <a href="/12345/">
        links = re.findall(r'href="/(\d+)/"', response.text)
        unique_links = list(set(links))
        print(f"[CRAWL] Found {len(unique_links)} replays on page {page_num}")
        return unique_links
    except Exception as e:
        print(f"[ERROR] {e}")
        return []

def download_and_extract(replay_id):
    # Check if already exists (heuristic)
    # We don't know the exact filename yet, but we can check if we processed this ID? 
    # For now, just try download.
    
    download_url = f"{BASE_URL}/{replay_id}/download/"
    try:
        print(f"[DOWNLOAD] Fetching replay {replay_id}...")
        response = requests.get(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            print(f"[ERROR] Failed download {replay_id}: {response.status_code}")
            return

        # Check content type
        content_type = response.headers.get('content-type', '')
        
        # Try to unzip
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Extract all
                for filename in z.namelist():
                    if filename.endswith(".SC2Replay"):
                        target_path = DOWNLOAD_DIR / filename
                        # Rename if exists
                        if target_path.exists():
                            timestamp = int(time.time())
                            target_path = DOWNLOAD_DIR / f"{Path(filename).stem}_{timestamp}.SC2Replay"
                            
                        with z.open(filename) as source, open(target_path, "wb") as target:
                            target.write(source.read())
                        print(f"[SUCCESS] Extracted: {target_path.name}")
        except zipfile.BadZipFile:
            # Maybe it's not a zip, just a replay file?
            # Spawning tool usually sends zips, but just in case
            if response.content.startswith(b"MPQ"): # SC2Replay signature start
                 target_path = DOWNLOAD_DIR / f"{replay_id}.SC2Replay"
                 with open(target_path, "wb") as f:
                     f.write(response.content)
                 print(f"[SUCCESS] Saved directly: {target_path.name}")
            else:
                 print(f"[WARNING] Content is not ZIP nor SC2Replay for {replay_id}")

    except Exception as e:
        print(f"[ERROR] Failed processing {replay_id}: {e}")

def main():
    setup_directories()
    
    total_downloaded = 0
    for page in range(1, MAX_PAGES + 1):
        replay_ids = get_replay_links(page)
        
        if not replay_ids:
            print("[INFO] No more replays found or error.")
            break
            
        for rid in replay_ids:
            download_and_extract(rid)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            total_downloaded += 1
            
        print(f"[INFO] Page {page} done.")
        
    print(f"[DONE] Total processed: {total_downloaded}")

if __name__ == "__main__":
    main()
