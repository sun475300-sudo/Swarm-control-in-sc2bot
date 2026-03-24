"""
JARVIS Location Service — MCP Server
=====================================
Amazon Location Service 연동: 장소 검색, 경로 계산, 지오코딩.

Tools (5):
  1. search_place       — 텍스트로 장소 검색
  2. calculate_route    — 두 좌표 간 경로/거리/시간 계산
  3. geocode_address    — 주소 → 좌표 변환
  4. reverse_geocode    — 좌표 → 주소 변환
  5. search_nearby      — 주변 장소 검색

사전 요구사항:
  pip install boto3
  .env.jarvis에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION 설정

Usage:
  python location_mcp_server.py          # MCP stdio 모드
  npx @modelcontextprotocol/inspector python location_mcp_server.py
"""

import json
import logging
import os
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("JARVIS-Location-Service")

# ──────────────────────────────────────────────
# AWS Location Service 클라이언트 (lazy init)
# ──────────────────────────────────────────────
_location_client = None
_places_client = None
_routes_client = None

# 기본 리소스 이름 (AWS 콘솔에서 생성 필요)
_PLACE_INDEX = os.environ.get("AWS_LOCATION_PLACE_INDEX", "jarvis-place-index")
_ROUTE_CALC = os.environ.get("AWS_LOCATION_ROUTE_CALC", "jarvis-route-calc")
_AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")


def _get_location_client():
    """boto3 location 클라이언트를 lazy-init으로 반환."""
    global _location_client
    if _location_client is not None:
        return _location_client
    try:
        import boto3
        _location_client = boto3.client("location", region_name=_AWS_REGION)
        return _location_client
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"AWS Location client init failed: {e}")
        return None


def _require_client():
    """클라이언트가 없으면 에러 메시지 반환."""
    client = _get_location_client()
    if client is None:
        return None, (
            "AWS Location Service를 사용할 수 없습니다.\n"
            "1. pip install boto3\n"
            "2. .env.jarvis에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 설정\n"
            "3. AWS 콘솔에서 Place Index, Route Calculator 리소스 생성"
        )
    return client, None


# ──────────────────────────────────────────────
# Tool 1: 장소 검색
# ──────────────────────────────────────────────
@mcp.tool()
async def search_place(query: str, max_results: int = 5) -> str:
    """텍스트로 장소를 검색합니다. 예: '서울역', 'Starbucks Gangnam'

    Args:
        query: 검색어
        max_results: 최대 결과 수 (1-10, 기본 5)
    """
    client, err = _require_client()
    if err:
        return err

    max_results = max(1, min(max_results, 10))
    try:
        resp = client.search_place_index_for_text(
            IndexName=_PLACE_INDEX,
            Text=query,
            MaxResults=max_results,
            Language="ko",
        )
        results = resp.get("Results", [])
        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다."

        lines = [f"장소 검색: '{query}' ({len(results)}건)"]
        lines.append("━" * 40)
        for i, r in enumerate(results, 1):
            place = r.get("Place", {})
            geo = place.get("Geometry", {}).get("Point", [0, 0])
            label = place.get("Label", "알 수 없음")
            addr = place.get("Address", {})
            municipality = addr.get("Municipality", "")
            region = addr.get("Region", "")
            country = addr.get("Country", "")

            lines.append(f"{i}. {label}")
            if municipality or region:
                lines.append(f"   지역: {municipality} {region} {country}".strip())
            lines.append(f"   좌표: {geo[1]:.6f}, {geo[0]:.6f}")  # lat, lng
        return "\n".join(lines)

    except client.exceptions.ResourceNotFoundException:
        return f"Place Index '{_PLACE_INDEX}'를 찾을 수 없습니다. AWS 콘솔에서 생성하세요."
    except Exception as e:
        logger.error(f"search_place error: {e}")
        return f"장소 검색 실패: {e}"


# ──────────────────────────────────────────────
# Tool 2: 경로 계산
# ──────────────────────────────────────────────
@mcp.tool()
async def calculate_route(
    departure_lat: float,
    departure_lng: float,
    destination_lat: float,
    destination_lng: float,
    travel_mode: str = "Car",
) -> str:
    """두 좌표 간 경로를 계산합니다.

    Args:
        departure_lat: 출발지 위도
        departure_lng: 출발지 경도
        destination_lat: 도착지 위도
        destination_lng: 도착지 경도
        travel_mode: 이동 수단 (Car, Walking, Truck)
    """
    client, err = _require_client()
    if err:
        return err

    if travel_mode not in ("Car", "Walking", "Truck"):
        return "travel_mode는 Car, Walking, Truck 중 하나여야 합니다."

    try:
        resp = client.calculate_route(
            CalculatorName=_ROUTE_CALC,
            DeparturePosition=[departure_lng, departure_lat],
            DestinationPosition=[destination_lng, destination_lat],
            TravelMode=travel_mode,
            IncludeLegGeometry=False,
        )
        summary = resp.get("Summary", {})
        distance_km = summary.get("Distance", 0)
        duration_sec = summary.get("DurationSeconds", 0)

        dur_min = int(duration_sec // 60)
        dur_hr = dur_min // 60
        dur_min_rem = dur_min % 60

        lines = [
            "경로 계산 결과",
            "━" * 40,
            f"이동 수단: {travel_mode}",
            f"거리: {distance_km:.1f} km",
        ]
        if dur_hr > 0:
            lines.append(f"소요 시간: {dur_hr}시간 {dur_min_rem}분")
        else:
            lines.append(f"소요 시간: {dur_min}분")

        legs = resp.get("Legs", [])
        if legs:
            steps = legs[0].get("Steps", [])
            if steps and len(steps) <= 10:
                lines.append(f"\n경로 안내 ({len(steps)} 단계):")
                for j, step in enumerate(steps, 1):
                    dist = step.get("Distance", 0)
                    dur = int(step.get("DurationSeconds", 0) // 60)
                    lines.append(f"  {j}. {dist:.1f}km ({dur}분)")

        return "\n".join(lines)

    except client.exceptions.ResourceNotFoundException:
        return f"Route Calculator '{_ROUTE_CALC}'를 찾을 수 없습니다."
    except Exception as e:
        logger.error(f"calculate_route error: {e}")
        return f"경로 계산 실패: {e}"


# ──────────────────────────────────────────────
# Tool 3: 지오코딩 (주소 → 좌표)
# ──────────────────────────────────────────────
@mcp.tool()
async def geocode_address(address: str) -> str:
    """주소를 위도/경도 좌표로 변환합니다.

    Args:
        address: 변환할 주소 (예: '서울특별시 중구 세종대로 110')
    """
    client, err = _require_client()
    if err:
        return err

    try:
        resp = client.search_place_index_for_text(
            IndexName=_PLACE_INDEX,
            Text=address,
            MaxResults=1,
            Language="ko",
        )
        results = resp.get("Results", [])
        if not results:
            return f"'{address}'의 좌표를 찾을 수 없습니다."

        place = results[0].get("Place", {})
        geo = place.get("Geometry", {}).get("Point", [0, 0])
        label = place.get("Label", address)

        return (
            f"지오코딩 결과\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"주소: {label}\n"
            f"위도: {geo[1]:.6f}\n"
            f"경도: {geo[0]:.6f}"
        )
    except Exception as e:
        logger.error(f"geocode_address error: {e}")
        return f"지오코딩 실패: {e}"


# ──────────────────────────────────────────────
# Tool 4: 역지오코딩 (좌표 → 주소)
# ──────────────────────────────────────────────
@mcp.tool()
async def reverse_geocode(lat: float, lng: float) -> str:
    """좌표를 주소로 변환합니다.

    Args:
        lat: 위도
        lng: 경도
    """
    client, err = _require_client()
    if err:
        return err

    try:
        resp = client.search_place_index_for_position(
            IndexName=_PLACE_INDEX,
            Position=[lng, lat],
            MaxResults=1,
            Language="ko",
        )
        results = resp.get("Results", [])
        if not results:
            return f"좌표 ({lat}, {lng})에 대한 주소를 찾을 수 없습니다."

        place = results[0].get("Place", {})
        label = place.get("Label", "알 수 없음")
        addr = place.get("Address", {})

        lines = [
            "역지오코딩 결과",
            "━" * 40,
            f"좌표: {lat:.6f}, {lng:.6f}",
            f"주소: {label}",
        ]
        if addr.get("Street"):
            lines.append(f"도로: {addr['Street']}")
        if addr.get("Municipality"):
            lines.append(f"시/구: {addr['Municipality']}")
        if addr.get("Region"):
            lines.append(f"지역: {addr['Region']}")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"reverse_geocode error: {e}")
        return f"역지오코딩 실패: {e}"


# ──────────────────────────────────────────────
# Tool 5: 주변 장소 검색
# ──────────────────────────────────────────────
@mcp.tool()
async def search_nearby(
    lat: float,
    lng: float,
    category: str = "",
    radius_km: float = 5.0,
    max_results: int = 5,
) -> str:
    """주변 장소를 검색합니다.

    Args:
        lat: 중심 위도
        lng: 중심 경도
        category: 카테고리 필터 (예: 'restaurant', 'gas_station', 'hotel'). 비우면 전체.
        radius_km: 검색 반경 (km, 기본 5)
        max_results: 최대 결과 수 (1-10)
    """
    client, err = _require_client()
    if err:
        return err

    max_results = max(1, min(max_results, 10))
    try:
        kwargs = {
            "IndexName": _PLACE_INDEX,
            "Position": [lng, lat],
            "MaxResults": max_results,
            "Language": "ko",
        }
        if radius_km and radius_km > 0:
            kwargs["MaxDistance"] = radius_km * 1000  # km → meters
        if category:
            kwargs["FilterCategories"] = [category]

        resp = client.search_place_index_for_position(**kwargs)
        results = resp.get("Results", [])
        if not results:
            cat_msg = f" (카테고리: {category})" if category else ""
            return f"주변{cat_msg} 장소를 찾을 수 없습니다."

        cat_msg = f" [{category}]" if category else ""
        lines = [f"주변 장소 검색{cat_msg} (반경 {radius_km}km, {len(results)}건)"]
        lines.append("━" * 40)
        for i, r in enumerate(results, 1):
            place = r.get("Place", {})
            label = place.get("Label", "알 수 없음")
            dist = r.get("Distance", 0)  # meters
            dist_km = dist / 1000
            lines.append(f"{i}. {label}")
            lines.append(f"   거리: {dist_km:.1f}km")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"search_nearby error: {e}")
        return f"주변 검색 실패: {e}"


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting JARVIS Location Service MCP Server...")
    mcp.run()
