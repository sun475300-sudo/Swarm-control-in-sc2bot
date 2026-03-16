"""Google Calendar 연동 모듈.

환경변수:
    GOOGLE_APPLICATION_CREDENTIALS - 서비스 계정 JSON 경로
    또는 credentials.json + token.json (OAuth2)
"""
import asyncio
import json
import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("jarvis.calendar")

KST = timezone(timedelta(hours=9))

# Google API 가용 여부
_google_available = False
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    _google_available = True
except ImportError:
    logger.warning("google-api-python-client 미설치. pip install google-api-python-client google-auth")

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
class CalendarIntegration:
    def __init__(self):
        self._service = None
        self._google_available = _google_available

    def _get_service(self):
        if self._service:
            return self._service
        if not self._google_available:
            return None

        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if creds_path and os.path.exists(creds_path):
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=_SCOPES)
            self._service = build("calendar", "v3", credentials=creds)
            return self._service

        # OAuth2 token.json 방식
        token_path = os.path.join(os.path.dirname(__file__), "token.json")
        if os.path.exists(token_path):
            try:
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request as GRequest

                creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(GRequest())
                self._service = build("calendar", "v3", credentials=creds)
                return self._service
            except Exception as e:
                logger.error(f"OAuth2 인증 실패: {e}")

        logger.warning("Google Calendar 인증 정보 없음. GOOGLE_APPLICATION_CREDENTIALS 환경변수를 설정하세요.")
        return None

    async def get_today_events(self) -> str:
        """오늘의 일정을 조회합니다."""
        svc = self._get_service()
        if not svc:
            return "Google Calendar가 설정되지 않았습니다.\n설정 방법: GOOGLE_APPLICATION_CREDENTIALS 환경변수에 서비스 계정 JSON 경로 지정"

        try:
            now = datetime.now(KST)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

            events_result = None
            for attempt in range(3):
                try:
                    events_result = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: svc.events().list(
                            calendarId="primary",
                            timeMin=start_of_day,
                            timeMax=end_of_day,
                            singleEvents=True,
                            orderBy="startTime",
                        ).execute()
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        return f"일정 조회 실패 (3회 재시도 후): {e}"
                    logger.warning(f"일정 조회 재시도 {attempt + 1}/3: {e}")
                    await asyncio.sleep(1)

            if events_result is None:
                return "API 호출에 실패했습니다."

            events = events_result.get("items", [])

            if not events:
                return f"📅 오늘 ({now.strftime('%m/%d %a')}) 일정이 없습니다."

            lines = [f"📅 오늘의 일정 ({now.strftime('%m/%d %a')}) - {len(events)}건"]
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date", ""))
                if "T" in start:
                    t = datetime.fromisoformat(start).strftime("%H:%M")
                else:
                    t = "종일"
                summary = e.get("summary", "(제목 없음)")
                lines.append(f"  {t} - {summary}")
            return "\n".join(lines)
        except Exception as e:
            return f"일정 조회 실패: {e}"

    async def get_upcoming_events(self, days: int = 7) -> str:
        """다가오는 일정을 조회합니다."""
        svc = self._get_service()
        if not svc:
            return "Google Calendar가 설정되지 않았습니다."

        try:
            now = datetime.now(KST)
            time_min = now.isoformat()
            time_max = (now + timedelta(days=days)).isoformat()

            events_result = None
            for attempt in range(3):
                try:
                    events_result = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: svc.events().list(
                            calendarId="primary",
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True,
                            orderBy="startTime",
                            maxResults=20,
                        ).execute()
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        return f"일정 조회 실패 (3회 재시도 후): {e}"
                    logger.warning(f"일정 조회 재시도 {attempt + 1}/3: {e}")
                    await asyncio.sleep(1)

            if events_result is None:
                return "API 호출에 실패했습니다."

            events = events_result.get("items", [])

            if not events:
                return f"📅 향후 {days}일간 일정이 없습니다."

            lines = [f"📅 향후 {days}일 일정 ({len(events)}건)"]
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date", ""))
                if "T" in start:
                    dt = datetime.fromisoformat(start)
                    t = dt.strftime("%m/%d %H:%M")
                else:
                    t = start
                summary = e.get("summary", "(제목 없음)")
                lines.append(f"  {t} - {summary}")
            return "\n".join(lines)
        except Exception as e:
            return f"일정 조회 실패: {e}"

    async def create_event(self, title: str, start_str: str, end_str: str = "", description: str = "") -> str:
        """일정을 생성합니다."""
        svc = self._get_service()
        if not svc:
            return "Google Calendar가 설정되지 않았습니다."

        try:
            is_all_day = len(start_str.strip()) <= 10

            if is_all_day:
                # Bug fix #25: For all-day events without end_str, set end to start + 1 day
                if end_str:
                    end_date = end_str.strip()
                else:
                    # Google Calendar requires end date to be exclusive (start + 1 day)
                    start_date_obj = datetime.strptime(start_str.strip(), "%Y-%m-%d")
                    end_date = (start_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                event = {
                    "summary": title,
                    "start": {"date": start_str.strip()},
                    "end": {"date": end_date},
                }
            else:
                start_dt = datetime.strptime(start_str.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
                if end_str:
                    end_dt = datetime.strptime(end_str.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
                else:
                    end_dt = start_dt + timedelta(hours=1)

                event = {
                    "summary": title,
                    "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Seoul"},
                    "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Seoul"},
                }

            if description:
                event["description"] = description

            created = None
            for attempt in range(3):
                try:
                    created = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: svc.events().insert(calendarId="primary", body=event).execute()
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        return f"일정 생성 실패 (3회 재시도 후): {e}"
                    logger.warning(f"일정 생성 재시도 {attempt + 1}/3: {e}")
                    await asyncio.sleep(1)

            if created is None:
                return "API 호출에 실패했습니다."

            return f"✅ 일정 생성 완료: {title}\n링크: {created.get('htmlLink', '')}"
        except Exception as e:
            return f"일정 생성 실패: {e}"

    async def delete_event(self, event_id: str) -> str:
        """일정을 삭제합니다."""
        svc = self._get_service()
        if not svc:
            return "Google Calendar가 설정되지 않았습니다."
        try:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: svc.events().delete(calendarId="primary", eventId=event_id).execute()
            )
            return f"✅ 일정 삭제 완료 (ID: {event_id})"
        except Exception as e:
            return f"일정 삭제 실패: {e}"

