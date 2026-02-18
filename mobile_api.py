"""
#183: 모바일 앱 API (Mobile API) — 스텁

REST API 엔드포인트 정의.
실제 서버 구현은 향후 aiohttp/FastAPI 통합 예정.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("mobile_api")


class MobileAPI:
    """모바일 앱 REST API 인터페이스 (스텁)

    모바일 앱에서 사용할 REST API 엔드포인트를 정의한다.
    실제 HTTP 서버는 미구현 — 엔드포인트 스펙과 핸들러 로직만 정의.
    """

    # API 버전
    VERSION = "v1"

    # 엔드포인트 정의
    ENDPOINTS = {
        "GET /api/v1/portfolio": {
            "description": "현재 포트폴리오 조회",
            "auth_required": True,
            "params": [],
            "response": {
                "total_krw": "float",
                "holdings": "list",
                "updated_at": "str (ISO 8601)",
            },
        },
        "GET /api/v1/portfolio/history": {
            "description": "포트폴리오 히스토리 조회",
            "auth_required": True,
            "params": [
                {"name": "days", "type": "int", "default": 7, "description": "조회 기간 (일)"},
            ],
            "response": {"history": "list of snapshots"},
        },
        "GET /api/v1/trades": {
            "description": "거래 내역 조회",
            "auth_required": True,
            "params": [
                {"name": "limit", "type": "int", "default": 50, "description": "최대 건수"},
                {"name": "ticker", "type": "str", "default": None, "description": "종목 필터"},
            ],
            "response": {"trades": "list"},
        },
        "POST /api/v1/trade/buy": {
            "description": "매수 주문",
            "auth_required": True,
            "params": [
                {"name": "ticker", "type": "str", "required": True, "description": "종목 코드"},
                {"name": "amount_krw", "type": "float", "required": True, "description": "주문 금액"},
            ],
            "response": {"order_id": "str", "status": "str"},
        },
        "POST /api/v1/trade/sell": {
            "description": "매도 주문",
            "auth_required": True,
            "params": [
                {"name": "ticker", "type": "str", "required": True, "description": "종목 코드"},
                {"name": "volume", "type": "float", "required": True, "description": "매도 수량"},
            ],
            "response": {"order_id": "str", "status": "str"},
        },
        "GET /api/v1/market/tickers": {
            "description": "마켓 티커 목록",
            "auth_required": False,
            "params": [],
            "response": {"tickers": "list"},
        },
        "GET /api/v1/market/price/{ticker}": {
            "description": "특정 종목 현재가",
            "auth_required": False,
            "params": [
                {"name": "ticker", "type": "str", "required": True, "description": "종목 코드 (URL path)"},
            ],
            "response": {"ticker": "str", "price": "float", "change_pct": "float"},
        },
        "GET /api/v1/sc2/stats": {
            "description": "SC2 봇 전적 요약",
            "auth_required": True,
            "params": [],
            "response": {"wins": "int", "losses": "int", "win_rate": "float"},
        },
        "GET /api/v1/system/status": {
            "description": "시스템 상태",
            "auth_required": True,
            "params": [],
            "response": {"status": "str", "uptime": "str", "modules": "dict"},
        },
        "POST /api/v1/auth/login": {
            "description": "로그인 (JWT 토큰 발급)",
            "auth_required": False,
            "params": [
                {"name": "username", "type": "str", "required": True},
                {"name": "password", "type": "str", "required": True},
            ],
            "response": {"token": "str", "expires_at": "str"},
        },
        "POST /api/v1/notifications/register": {
            "description": "푸시 알림 디바이스 등록",
            "auth_required": True,
            "params": [
                {"name": "device_token", "type": "str", "required": True},
                {"name": "platform", "type": "str", "required": True, "description": "ios / android"},
            ],
            "response": {"registered": "bool"},
        },
        "GET /api/v1/alerts": {
            "description": "최근 알림 조회",
            "auth_required": True,
            "params": [
                {"name": "limit", "type": "int", "default": 20},
            ],
            "response": {"alerts": "list"},
        },
    }

    def __init__(self):
        """초기화"""
        self._project_root = Path(__file__).parent
        self._registered_devices: list = []
        logger.info("MobileAPI 초기화 (스텁 모드)")

    def get_endpoint_list(self) -> list:
        """등록된 엔드포인트 목록 반환

        Returns:
            list: 엔드포인트 스펙 리스트
        """
        endpoints = []
        for route, spec in self.ENDPOINTS.items():
            method, path = route.split(" ", 1)
            endpoints.append({
                "method": method,
                "path": path,
                "description": spec["description"],
                "auth_required": spec["auth_required"],
                "params": spec.get("params", []),
            })
        return endpoints

    def get_api_spec(self) -> dict:
        """전체 API 스펙 반환 (OpenAPI-like)

        Returns:
            dict: API 사양
        """
        return {
            "api_version": self.VERSION,
            "title": "JARVIS Mobile API",
            "description": "암호화폐 + SC2 봇 모바일 API",
            "base_url": f"/api/{self.VERSION}",
            "endpoints": self.ENDPOINTS,
            "auth": {
                "type": "Bearer Token (JWT)",
                "header": "Authorization: Bearer <token>",
            },
            "generated_at": datetime.now().isoformat(),
        }

    def handle_request(self, method: str, path: str, params: dict = None,
                       auth_token: str = None) -> dict:
        """요청 처리 (스텁)

        Args:
            method: HTTP 메서드
            path: 요청 경로
            params: 요청 파라미터
            auth_token: 인증 토큰

        Returns:
            dict: 응답 (status_code, body)
        """
        route_key = f"{method.upper()} {path}"

        # 엔드포인트 매칭
        matched_spec = None
        for registered_route, spec in self.ENDPOINTS.items():
            # 정확 매칭 또는 path param 매칭
            reg_method, reg_path = registered_route.split(" ", 1)
            if reg_method == method.upper():
                if reg_path == path or ('{' in reg_path and self._match_path(reg_path, path)):
                    matched_spec = spec
                    break

        if not matched_spec:
            return {"status_code": 404, "body": {"error": "Endpoint not found"}}

        # 인증 검사 (스텁)
        if matched_spec["auth_required"] and not auth_token:
            return {"status_code": 401, "body": {"error": "Authentication required"}}

        # 스텁 응답
        return {
            "status_code": 200,
            "body": {
                "message": "스텁 응답 — 실제 데이터 미구현",
                "endpoint": route_key,
                "params": params or {},
                "response_schema": matched_spec.get("response", {}),
            },
        }

    @staticmethod
    def _match_path(pattern: str, path: str) -> bool:
        """URL 패턴 매칭 (간단한 path parameter 처리)"""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        if len(pattern_parts) != len(path_parts):
            return False
        for pp, pa in zip(pattern_parts, path_parts):
            if pp.startswith("{") and pp.endswith("}"):
                continue  # path parameter → 어떤 값이든 매칭
            if pp != pa:
                return False
        return True

    def register_device(self, device_token: str, platform: str) -> dict:
        """푸시 알림 디바이스 등록 (스텁)"""
        device = {
            "token": device_token,
            "platform": platform,
            "registered_at": datetime.now().isoformat(),
        }
        self._registered_devices.append(device)
        return {"registered": True, "device": device}


if __name__ == "__main__":
    api = MobileAPI()
    print("=== JARVIS Mobile API Spec ===\n")
    spec = api.get_api_spec()
    print(json.dumps(spec, indent=2, ensure_ascii=False))
