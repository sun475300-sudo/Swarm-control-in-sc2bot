
import requests
import random
import datetime
import json
import logging
import warnings
from urllib.parse import quote

logger = logging.getLogger("web_tools")

# duckduckgo-search 패키지 (pip install duckduckgo-search)
DDGS = None
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from duckduckgo_search import DDGS as _DDGS
    DDGS = _DDGS
except ImportError:
    pass

# BeautifulSoup (pip install beautifulsoup4)
BeautifulSoup = None
try:
    from bs4 import BeautifulSoup as _BS
    BeautifulSoup = _BS
except ImportError:
    pass


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# 한국 주요 도시 좌표 (Open-Meteo용)
CITY_COORDS = {
    "광주": (35.1595, 126.8526), "광주광역시": (35.1595, 126.8526),
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014), "인천": (37.4563, 126.7052),
    "대전": (36.3504, 127.3845), "울산": (35.5384, 129.3114),
    "세종": (36.4800, 127.2890), "수원": (37.2636, 127.0286),
    "성남": (37.4200, 127.1267), "고양": (37.6564, 126.8350),
    "용인": (37.2411, 127.1776), "청주": (36.6424, 127.4890),
    "천안": (36.8151, 127.1139), "전주": (35.8242, 127.1480),
    "포항": (36.0190, 129.3435), "창원": (35.2281, 128.6812),
    "제주": (33.4996, 126.5312), "김포": (37.6153, 126.7156),
    "춘천": (37.8813, 127.7298), "강릉": (37.7519, 128.8761),
    "목포": (34.8118, 126.3922), "여수": (34.7604, 127.6622),
    "순천": (34.9508, 127.4872), "안동": (36.5684, 128.7294),
    "경주": (35.8562, 129.2247), "익산": (35.9483, 126.9577),
}

# WMO 날씨 코드 → 한국어 설명
WMO_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "안개(서리)", 51: "가벼운 이슬비", 53: "이슬비",
    55: "짙은 이슬비", 61: "약한 비", 63: "비", 65: "강한 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "눈알갱이",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
    85: "약한 눈보라", 86: "눈보라", 95: "뇌우", 96: "우박 뇌우", 99: "강한 우박 뇌우",
}

# WMO 날씨 코드 → 아이콘 매핑
WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️", 51: "🌦️", 53: "🌦️",
    55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️", 77: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️", 95: "⛈️", 96: "⛈️", 99: "⛈️",
}


def _get_city_coords(city):
    """도시명 → (위도, 경도) 변환. 로컬 매핑 우선, 없으면 API 조회."""
    if city in CITY_COORDS:
        return CITY_COORDS[city], city

    # Open-Meteo Geocoding API
    try:
        resp = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city)}&count=5&language=ko",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            # 인구 많은 순으로 정렬
            results.sort(key=lambda x: x.get("population", 0), reverse=True)
            if results:
                r = results[0]
                name = r.get("name", city)
                return (r["latitude"], r["longitude"]), name
    except Exception:
        pass
    return None, city


def get_weather(city="광주"):
    """Open-Meteo API로 날씨 조회 (빠르고 안정적, API 키 불필요)"""
    # 잘못된 도시명 필터링
    skip_words = ["한국", "전국", "전체", "모든", "각지", "날씨", "알려", "줘"]
    clean_city = city
    for w in skip_words:
        clean_city = clean_city.replace(w, "")
    clean_city = clean_city.strip()
    if not clean_city:
        # 주요 도시 날씨 한번에
        cities = ["서울", "부산", "광주", "대구", "대전"]
        results = []
        for c in cities:
            try:
                r = _get_weather_openmeteo(c)
                if r:
                    # 첫 줄(제목)과 기온만 추출
                    lines = r.split("\n")
                    temp_line = [l for l in lines if "기온:" in l]
                    desc_line = [l for l in lines if "상태:" in l]
                    t = temp_line[0].strip() if temp_line else ""
                    d = desc_line[0].strip() if desc_line else ""
                    results.append(f"**{c}**: {t} / {d}")
            except Exception:
                pass
        if results:
            return "**주요 도시 날씨**\n" + "\n".join(results)
        return "날씨 조회 실패"

    # 1순위: Open-Meteo (1초 응답)
    try:
        result = _get_weather_openmeteo(clean_city)
        if result:
            return result
    except Exception:
        pass

    # 도시를 찾을 수 없을 때 - wttr.in 폴백 없이 안내
    available = ", ".join(list(CITY_COORDS.keys())[:10])
    return f"'{city}' 날씨를 찾을 수 없습니다.\n사용 예: `날씨 광주`, `날씨 서울`\n지원 도시: {available} 등"


def _get_weather_openmeteo(city):
    """Open-Meteo API (무료, 빠름)"""
    coords, display_name = _get_city_coords(city)
    if not coords:
        return None

    lat, lon = coords
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&hourly=temperature_2m,weather_code,precipitation_probability"
        f"&timezone=Asia/Seoul&forecast_days=1"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning(f"날씨 API 시간 초과: {city}")
        return f"'{city}' 날씨 조회 시간 초과. 잠시 후 재시도하세요."
    except requests.exceptions.ConnectionError:
        logger.warning(f"날씨 API 연결 실패: {city}")
        return f"날씨 서비스에 연결할 수 없습니다."
    except requests.exceptions.HTTPError as e:
        logger.warning(f"날씨 API HTTP 오류: {e}")
        return None

    data = resp.json()
    cur = data.get("current", {})
    daily = data.get("daily", {})

    temp = cur.get("temperature_2m", "?")
    feels = cur.get("apparent_temperature", "?")
    humidity = cur.get("relative_humidity_2m", "?")
    wind = cur.get("wind_speed_10m", "?")
    wind_dir = cur.get("wind_direction_10m", 0)
    code = cur.get("weather_code", -1)
    desc = WMO_CODES.get(code, "알 수 없음")
    icon = WMO_ICONS.get(code, "🌡️")

    max_t = daily.get("temperature_2m_max", ["?"])[0]
    min_t = daily.get("temperature_2m_min", ["?"])[0]
    rain_prob = daily.get("precipitation_probability_max", [0])[0]

    result = (
        f"**{display_name} 현재 날씨** {icon}\n"
        f"상태: {icon} {desc}\n"
        f"기온: {temp}C (체감 {feels}C)\n"
        f"최고/최저: {max_t}C / {min_t}C\n"
        f"습도: {humidity}%\n"
        f"바람: {wind}km/h"
    )
    if rain_prob and rain_prob > 20:
        result += f"\n강수확률: {rain_prob}%"

    # 시간대별 예보 (3시간 간격)
    hourly = data.get("hourly", {})
    h_times = hourly.get("time", [])
    h_temps = hourly.get("temperature_2m", [])
    h_codes = hourly.get("weather_code", [])
    h_rain = hourly.get("precipitation_probability", [])

    if h_times:
        result += "\n\n**시간대별 예보:**\n"
        for i in range(0, min(len(h_times), 24), 3):
            hour = h_times[i].split("T")[1][:5] if "T" in h_times[i] else "?"
            t = h_temps[i] if i < len(h_temps) else "?"
            h_icon = WMO_ICONS.get(h_codes[i], "") if i < len(h_codes) else ""
            c = WMO_CODES.get(h_codes[i], "") if i < len(h_codes) else ""
            r = h_rain[i] if i < len(h_rain) else 0
            line = f"  {hour} {h_icon} {t}C {c}"
            if r and r > 20:
                line += f" (비 {r}%)"
            result += line + "\n"

    return result


def _get_weather_wttr(city):
    """wttr.in 폴백 (느림 - 15초 타임아웃)"""
    url = f"https://wttr.in/{quote(city)}?format=j1"
    resp = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=15)
    if resp.status_code != 200:
        return f"날씨 조회 실패 (HTTP {resp.status_code})"

    data = resp.json()
    current = data.get("current_condition", [{}])[0]
    weather_desc = current.get("lang_ko", [{}])
    if weather_desc:
        desc = weather_desc[0].get("value", current.get("weatherDesc", [{}])[0].get("value", ""))
    else:
        desc = current.get("weatherDesc", [{}])[0].get("value", "")

    temp_c = current.get("temp_C", "?")
    feels_like = current.get("FeelsLikeC", "?")
    humidity = current.get("humidity", "?")
    wind_speed = current.get("windspeedKmph", "?")

    today_forecast = data.get("weather", [{}])[0]
    max_temp = today_forecast.get("maxtempC", "?")
    min_temp = today_forecast.get("mintempC", "?")

    return (
        f"**{city} 현재 날씨**\n"
        f"상태: {desc}\n"
        f"기온: {temp_c}C (체감 {feels_like}C)\n"
        f"최고/최저: {max_temp}C / {min_temp}C\n"
        f"습도: {humidity}%\n"
        f"바람: {wind_speed}km/h"
    )


def search_web(query):
    """웹 검색 (duckduckgo-search 패키지 우선, 실패 시 스크래핑 폴백)"""
    # 1순위: duckduckgo-search 패키지
    if DDGS:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ddg_results = DDGS().text(query, max_results=5)
            if ddg_results:
                results = []
                for r in ddg_results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    entry = f"**{title}**"
                    if body:
                        entry += f"\n{body[:200]}"
                    if href:
                        entry += f"\n{href}"
                    results.append(entry)
                return "\n\n".join(results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            # Fallback to DuckDuckGo HTML scraping
            try:
                # Bug fix #26: Use module-level BeautifulSoup variable instead of re-importing
                if BeautifulSoup is None:
                    raise ImportError("BeautifulSoup not available")
                resp = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=HEADERS, timeout=10)
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for r in soup.select(".result__body")[:5]:
                    title = r.select_one(".result__a")
                    snippet = r.select_one(".result__snippet")
                    if title:
                        results.append(f"• {title.get_text()}: {snippet.get_text() if snippet else ''}")
                if results:
                    return "\n".join(results)
            except Exception:
                pass
            return f"검색 실패: '{query}'"

    # 2순위: DuckDuckGo Lite 스크래핑
    if BeautifulSoup:
        try:
            result = _search_ddg_lite(query)
            if result:
                return result
        except Exception:
            pass

    # 3순위: 네이버 검색 스크래핑
    if BeautifulSoup:
        try:
            result = _search_naver_fallback(query)
            if result and "파싱할 수 없습니다" not in result:
                return result
        except Exception:
            pass

    return f"'{query}' 검색 결과를 가져올 수 없습니다.\n검색 링크: https://search.naver.com/search.naver?query={quote(query)}"


def _search_ddg_lite(query):
    """DuckDuckGo Lite HTML 스크래핑"""
    url = f"https://lite.duckduckgo.com/lite/?q={quote(query)}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    trs = soup.select("tr")
    i = 0
    while i < len(trs) and len(results) < 5:
        link = trs[i].select_one("a.result-link")
        if link:
            title = link.get_text(strip=True)
            snippet = ""
            if i + 1 < len(trs):
                snippet = trs[i + 1].get_text(strip=True)
                if snippet.startswith("http"):
                    snippet = ""
            if title:
                entry = f"**{title}**"
                if snippet and len(snippet) > 10:
                    entry += f"\n{snippet[:200]}"
                results.append(entry)
            i += 3
        else:
            i += 1

    if results:
        return "\n\n".join(results)
    return None


def _search_naver_fallback(query):
    """네이버 검색 폴백"""
    try:
        url = f"https://search.naver.com/search.naver?query={quote(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []

        # 네이버 웹 검색 결과 (sds-comps 기반 새 UI)
        for item in soup.select(".sds-comps-vertical-layout"):
            text = item.get_text(strip=True)
            if 30 < len(text) < 300 and not any(skip in text for skip in ["더보기", "관련문서", "광고", "Keep에"]):
                results.append(text[:200])
            if len(results) >= 5:
                break

        # 구 UI 폴백
        if not results:
            for item in soup.select(".total_group .total_wrap"):
                title_el = item.select_one(".total_tit a")
                desc_el = item.select_one(".total_dsc_wrap")
                if title_el:
                    title = title_el.get_text(strip=True)
                    desc = desc_el.get_text(strip=True) if desc_el else ""
                    results.append(f"**{title}**\n{desc}")
                if len(results) >= 5:
                    break

        # 텍스트 블록 폴백
        if not results:
            for item in soup.select(".api_txt_lines"):
                text = item.get_text(strip=True)
                if len(text) > 20:
                    results.append(text[:200])
                if len(results) >= 5:
                    break

        if results:
            return "\n\n".join(results)

        return f"'{query}' 검색 결과를 파싱할 수 없습니다.\n직접 확인: https://search.naver.com/search.naver?query={quote(query)}"
    except Exception as e:
        return f"검색 실패: {e}"


def get_daily_fortune():
    """오늘의 운세를 반환한다. 같은 날에는 항상 동일한 결과를 보장."""
    zodiacs = ["쥐띠", "소띠", "호랑이띠", "토끼띠", "용띠", "뱀띠",
               "말띠", "양띠", "원숭이띠", "닭띠", "개띠", "돼지띠"]
    fortunes = [
        "오늘은 기분 좋은 일이 생길 거예요.",
        "조금 신중하게 행동하는 게 좋겠어요.",
        "뜻밖의 행운이 찾아옵니다!",
        "주변 사람들과의 관계에 신경 쓰세요.",
        "노력한 만큼 결과가 나오는 날입니다.",
        "잠시 휴식을 취하는 것도 좋아요.",
        "새로운 도전을 하기에 좋은 날입니다.",
        "재물운이 상승하고 있어요.",
        "건강 관리에 유의하세요.",
        "오랜 친구에게 연락이 올 수 있어요."
    ]

    today = datetime.date.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    result = f"**{today_str} 오늘의 운세**\n\n"

    # 날짜 기반 시드로 같은 날은 같은 운세 보장
    day_seed = int(today.strftime("%Y%m%d"))

    for i, z in enumerate(zodiacs):
        rng = random.Random(hash((day_seed, i)))
        f = rng.choice(fortunes)
        result += f"**{z}**: {f}\n"
    return result


def get_exchange_rate(base="USD", target="KRW"):
    """환율 조회"""
    try:
        import requests
        resp = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get("rates", {}).get(target)
            if rate:
                return f"1 {base} = {rate:,.2f} {target}"
        return f"환율 조회 실패: {base}/{target}"
    except Exception as e:
        return f"환율 조회 오류: {e}"
