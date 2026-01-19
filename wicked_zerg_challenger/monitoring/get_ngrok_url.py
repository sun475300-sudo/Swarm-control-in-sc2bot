#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ngrok 터널 URL 가져오기
터널이 실행 중일 때 현재 URL을 반환합니다.
"""

import sys
import requests
from pathlib import Path


def get_ngrok_url_from_api() -> str:
    """Ngrok API에서 현재 터널 URL 가져오기"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout = 5)
 if response.status_code == 200:
     data = response.json()
     tunnels = data.get("tunnels", [])
 if tunnels:
     # HTTPS 터널 우선 선택
 for tunnel in tunnels:
     if tunnel.get("proto") == "https":
         pass
     return tunnel.get("public_url", "")
 # HTTPS가 없으면 HTTP 선택
 if tunnels:
     return tunnels[0].get("public_url", "")
 except Exception:
     pass
    return ""

def get_ngrok_url_from_file() -> str:
    """저장된 파일에서 터널 URL 가져오기"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     url_file = Path(__file__).parent / ".ngrok_url.txt"
 if url_file.exists():
     with open(url_file, 'r', encoding='utf-8') as f:
 return f.read().strip()
 except Exception:
     pass
    return ""

def main():
    """메인 함수"""
 # 1. API에서 시도
 url = get_ngrok_url_from_api()
 if url:
     print(url)
 return 0

 # 2. 파일에서 시도
 url = get_ngrok_url_from_file()
 if url:
     print(url)
 return 0

 # 3. 없으면 에러
    print("Ngrok 터널 URL을 찾을 수 없습니다.", file = sys.stderr)
    print("터널이 실행 중인지 확인하세요.", file = sys.stderr)
 return 1

if __name__ == "__main__":
    sys.exit(main())
