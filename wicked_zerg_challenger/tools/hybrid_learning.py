# -*- coding: utf-8 -*-
"""
Hybrid Learning Pipeline (MLOps)
--------------------------------
Web Scraping + Automated Learning Pipeline for SC2 Bot

Features:
1. [Collect] Scrape Spawning Tool for latest Zerg pro replays (bypassing API limits)
2. [Extract] Download and unzip replays automatically 
3. [Place] Organize files into learning directories
4. [Learn] Trigger iterative learning cycles
"""

import requests
import re
import os
import sys
import shutil
import time
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add project root to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from local_training.scripts.replay_build_order_learner import ReplayBuildOrderLearner

class ReplayPipeline:
    def __init__(self):
        self.base_dir = project_root
        self.download_dir = self.base_dir / "temp_downloads"
        self.replays_dir = self.base_dir / "replays"
        self.processed_dir = self.base_dir / "replays_processed"
        self.archive_dir = self.base_dir / "data" / "replays" / "archive" # Legacy support

        # Ensure directories exist
        for d in [self.download_dir, self.replays_dir, self.processed_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://lotv.spawningtool.com/replays/?race=1&tag=9"
        }
        
    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [MLOps] {msg}")

    def scrape_replay_links(self, limit: int = 5) -> List[str]:
        """Scrape replay detail URLs from Spawning Tool"""
        url = "https://lotv.spawningtool.com/replays/?race=1&tag=9" # Zerg (1) + Pro (9)
        self._log(f"Scraping {url}...")
        
        links = []
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=30)
            if response.status_code != 200:
                self._log(f"Scraping failed: Status {response.status_code}")
                return []
            
            # Regex to find replay links
            # Pattern 1: <a href="/replays/12345/">
            # Pattern 2: <a href="/replays/download/12345/"> (Direct download)
            # Pattern 3: <a href="/12345/"> (Short)
            
            # Try finding digits inside hrefs that look like replay paths
            links_found = re.findall(r'href=["\'](/replays/download/\d+/|/replays/\d+/|/\d+/)["\']', response.text)
            
            ids = set()
            for link in links_found:
                # Extract digits
                match = re.search(r'(\d+)', link)
                if match:
                    ids.add(match.group(1))
            
            ids = list(ids)
            self._log(f"Found {len(ids)} replay IDs: {ids[:5]}...")
            
            # Convert to full download URLs (Spawning Tool convention)
            # Link format: https://lotv.spawningtool.com/{rid}/download/
            for rid in ids[:limit]:
                # rid might contain slashes if extracted poorly, ensure it's clean
                clean_rid = rid.strip("/")
                links.append(f"https://lotv.spawningtool.com/{clean_rid}/download/")
                
        except Exception as e:
            self._log(f"Error scraping links: {e}")
            
        return links

    def download_file(self, url: str) -> Optional[Path]:
        """Download file and verify content"""
        try:
            # Extract Replay ID from URL for filename
            # url: .../download/12345/
            rid = url.split('/')[-2]
            filename = f"replay_{rid}.zip" # Spawning tool usually gives zips? Or .SC2Replay directly?
            # Actually spawning tool download often returns the .SC2Replay file directly with content-disposition
            # safely assume it might be a file. We'll inspect headers.
            
            save_path = self.download_dir / filename
            
            self._log(f"Downloading {url}...")
            response = requests.get(url, headers=self.headers, verify=False, stream=True, timeout=60)
            response.raise_for_status()
            
            # Use final URL (after redirects) to guess extension
            final_url = response.url
            if final_url.lower().endswith('.sc2replay') or '.sc2replay?' in final_url.lower():
                filename = f"replay_{rid}.SC2Replay"
            else:
                # Try to guess from headers or default to zip
                cd = response.headers.get('content-disposition')
                if cd:
                    fname = re.findall('filename="(.+)"', cd)
                    if fname:
                        filename = fname[0]
                else:
                    filename = f"replay_{rid}.zip"

            save_path = self.download_dir / filename
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return save_path
        except Exception as e:
            self._log(f"Download failed for {url}: {e}")
            return None

    def extract_and_organize(self, file_path: Path) -> List[Path]:
        """Extract if zip, move to replays dir"""
        extracted_files = []
        
        try:
            if str(file_path).lower().endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(self.download_dir)
                    for name in zip_ref.namelist():
                        if name.lower().endswith('.sc2replay'):
                            extracted_files.append(self.download_dir / name)
                # Remove zip
                file_path.unlink() 
            elif str(file_path).lower().endswith('.sc2replay'):
                extracted_files.append(file_path)
            else:
                self._log(f"Unknown file type: {file_path}")
                return []

            # Move to replays/ folder
            final_paths = []
            for p in extracted_files:
                target_name = f"pro_{int(time.time())}_{p.name}"
                target_path = self.replays_dir / target_name
                shutil.move(str(p), str(target_path))
                final_paths.append(target_path)
                self._log(f"Staged for learning: {target_name}")
                
            return final_paths

        except Exception as e:
            self._log(f"Extraction error: {e}")
            return []

    def run_pipeline(self, num_replays=5, epochs=5):
        self._log("=== Starting MLOps Pipeline ===")
        
        # 1. Collect
        links = self.scrape_replay_links(limit=num_replays)
        if not links:
            self._log("No links found. Aborting.")
            return

        # 2. Extract & Place
        new_replays = []
        for link in links:
            fpath = self.download_file(link)
            if fpath:
                batch = self.extract_and_organize(fpath)
                new_replays.extend(batch)
        
        self._log(f"Successfully collected {len(new_replays)} new replays.")
        if not new_replays:
            return

        # 3. Learn
        self._log(f"Triggering learning cycle (Epochs: {epochs})...")
        learner = ReplayBuildOrderLearner(
            replay_dir=str(self.replays_dir),
            output_dir=None # Use default
        )
        
        for i in range(epochs):
            self._log(f"--- Epoch {i+1}/{epochs} ---")
            learner.learn_from_replays()
            
        # 4. Cleanup/Archive
        self._log("run_pipeline completed. Archiving processed replays...")
        for p in new_replays:
            try:
                if p.exists():
                    shutil.move(str(p), str(self.processed_dir / p.name))
            except Exception as e:
                self._log(f"Archive failed for {p.name}: {e}")
                
        self._log("=== Pipeline Finished Successfully ===")

def main():
    # Disable HTTPS warnings for verify=False
    import urllib3
    import argparse
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    parser = argparse.ArgumentParser(description="MLOps Pipeline for SC2 Bot")
    parser.add_argument("--limit", type=int, default=10, help="Number of replays to download")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    args = parser.parse_args()
    
    pipeline = ReplayPipeline()
    pipeline.run_pipeline(num_replays=args.limit, epochs=args.epochs)

if __name__ == "__main__":
    main()
