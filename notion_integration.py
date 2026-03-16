"""Notion 연동 모듈.

환경변수:
    NOTION_API_KEY     - Notion Integration 토큰
    NOTION_DATABASE_ID - 저장할 데이터베이스 ID
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from functools import partial
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("jarvis.notion")

class NotionIntegration:
    def __init__(self):
        self.api_key = os.environ.get("NOTION_API_KEY", "")
        self.database_id = os.environ.get("NOTION_DATABASE_ID", "")
        self.base_url = "https://api.notion.com/v1"
        self.version = "2022-06-28"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.version,
        }

    def _api_call_sync(self, method: str, path: str, body: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 401:
                logger.error("Notion API 인증 실패 (401)")
                return {"error": "Notion API 키가 유효하지 않습니다"}
            elif e.code == 429:
                logger.warning("Notion API 요청 한도 초과 (429)")
                return {"error": "요청 한도 초과. 잠시 후 재시도하세요"}
            logger.error(f"Notion API HTTP 오류: {e.code}")
            return {"error": f"Notion API 오류 ({e.code})"}
        except URLError as e:
            logger.error(f"Notion 연결 실패: {e.reason}")
            return {"error": f"Notion 연결 실패: {e.reason}"}

    async def _api_call(self, method: str, path: str, body: dict = None) -> dict:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, partial(self._api_call_sync, method, path, body)
        )

    async def save_note(self, title: str, content: str, tags: list = None) -> str:
        """Notion 데이터베이스에 메모를 저장합니다."""
        if not self.api_key or not self.database_id:
            return (
                "Notion이 설정되지 않았습니다.\n"
                "설정 방법:\n"
                "1. https://www.notion.so/my-integrations 에서 Integration 생성\n"
                "2. .env.jarvis에 NOTION_API_KEY=<토큰> 추가\n"
                "3. 저장할 데이터베이스에서 Connection 추가\n"
                "4. .env.jarvis에 NOTION_DATABASE_ID=<DB ID> 추가"
            )

        try:
            properties = {
                "Name": {"title": [{"text": {"content": title}}]},
            }
            if tags:
                properties["Tags"] = {"multi_select": [{"name": t} for t in tags]}

            children = []
            for i in range(0, len(content), 2000):
                chunk = content[i:i + 2000]
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    },
                })

            body = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children,
            }

            result = await self._api_call("POST", "/pages", body)
            if "error" in result:
                return f"Notion 저장 실패: {result['error']}"
            page_url = result.get("url", "")
            return f"✅ Notion에 저장 완료: {title}\n링크: {page_url}"
        except (URLError, HTTPError) as e:
            return f"Notion 저장 실패: {e}"
        except Exception as e:
            return f"Notion 저장 실패: {e}"

    async def search_notes(self, query: str, limit: int = 5) -> str:
        """Notion에서 메모를 검색합니다."""
        if not self.api_key:
            return "Notion API 키가 설정되지 않았습니다."

        try:
            body = {
                "query": query,
                "filter": {"value": "page", "property": "object"},
                "page_size": limit,
            }
            result = await self._api_call("POST", "/search", body)
            if "error" in result:
                return f"Notion 검색 실패: {result['error']}"
            pages = result.get("results", [])

            if not pages:
                return f"'{query}'에 대한 검색 결과가 없습니다."

            lines = [f"🔍 Notion 검색: '{query}' ({len(pages)}건)"]
            for p in pages:
                props = p.get("properties", {})
                title_prop = props.get("Name", props.get("title", {}))
                if "title" in title_prop:
                    title_texts = title_prop["title"]
                    title = title_texts[0]["plain_text"] if title_texts else "(제목 없음)"
                else:
                    title = "(제목 없음)"
                url = p.get("url", "")
                created = p.get("created_time", "")[:10]
                lines.append(f"  [{created}] {title}\n    {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion 검색 실패: {e}"

    async def list_recent_notes(self, limit: int = 5) -> str:
        """최근 Notion 메모를 조회합니다."""
        if not self.api_key or not self.database_id:
            return "Notion이 설정되지 않았습니다."

        try:
            body = {
                "page_size": limit,
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
            }
            result = await self._api_call("POST", f"/databases/{self.database_id}/query", body)
            if "error" in result:
                return f"Notion 조회 실패: {result['error']}"
            pages = result.get("results", [])

            if not pages:
                return "저장된 메모가 없습니다."

            lines = [f"📝 최근 메모 ({len(pages)}건)"]
            for p in pages:
                props = p.get("properties", {})
                title_prop = props.get("Name", props.get("title", {}))
                if "title" in title_prop:
                    title_texts = title_prop["title"]
                    title = title_texts[0]["plain_text"] if title_texts else "(제목 없음)"
                else:
                    title = "(제목 없음)"
                created = p.get("created_time", "")[:10]
                lines.append(f"  [{created}] {title}")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion 조회 실패: {e}"

