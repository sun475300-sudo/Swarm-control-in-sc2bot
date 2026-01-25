import requests

def test_download(rid):
    # Step 1: Visit detail page (Try short URL)
    detail_url = f"https://lotv.spawningtool.com/{rid}/"
    print(f"Fetching detail page: {detail_url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        s = requests.Session()
        resp = s.get(detail_url, headers=headers, verify=False)
        
        with open("dump_detail.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
            
        print("Saved dump_detail.html")
        
        # Find context of "Download"
        idx = resp.text.find("Download")
        if idx != -1:
             print(f"Context: {resp.text[idx-100:idx+100]}")
        else:
             print("Word 'Download' not found in page.")

        # Look for download link in detail page
        # Usually <a href="/replays/download/12345/">Download Replay</a> or similar
        import re
        # Find any link with 'download' in it
        downloads = re.findall(r'href=["\']([^"\']*)["\'][^>]*>.*?Download.*?</a>', resp.text, re.IGNORECASE)
        print(f"Download candidates (text search): {downloads}")
        
        # Also try generic href search for download path
        all_downloads = re.findall(r'href=["\'](/replays/download/\d+/?)["\']', resp.text)
        print(f"Download candidates (regex): {all_downloads}")
        
        if all_downloads:
            target_url = "https://lotv.spawningtool.com" + all_downloads[0]
            print(f"Attempting download from: {target_url}")
            
            resp_dl = s.get(target_url, headers=headers, verify=False, stream=True)
            print(f"DL Status: {resp_dl.status_code}")
            print(f"DL Headers: {resp_dl.headers}")
            
            if resp_dl.status_code == 200 and 'html' not in resp_dl.headers.get('Content-Type', ''):
                with open("test_replay.zip", "wb") as f:
                     for chunk in resp_dl.iter_content(chunk_size=8192):
                         f.write(chunk)
                print("Download SUCCESS!")
            else:
                print("Download failed (got HTML or error)")
        else:
            print("No download link found on detail page.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Use one of the IDs found: 89323
    test_download("89323")
