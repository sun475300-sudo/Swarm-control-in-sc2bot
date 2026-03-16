
import requests
import feedparser
import random
import datetime
import logging
from datetime import datetime as dt

logger = logging.getLogger("morning_helper")

# Coordinate mapping for major Korean cities
CITY_COORDS = {
    "서울": {"lat": 37.5665, "lon": 126.9780},
    "광주": {"lat": 35.1595, "lon": 126.8526},
    "부산": {"lat": 35.1796, "lon": 129.0756},
    "대구": {"lat": 35.8714, "lon": 128.6014},
    "인천": {"lat": 37.4563, "lon": 126.7052},
    "대전": {"lat": 36.3504, "lon": 127.3845},
    "울산": {"lat": 35.5384, "lon": 129.3114},
    "제주": {"lat": 33.4996, "lon": 126.5312}
}

def get_weather(city_name="서울"):
    """
    Open-Meteo API (Free, No Key) to get current weather.
    """
    try:
        coords = CITY_COORDS.get(city_name, CITY_COORDS["서울"])
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current_weather": "true",
            "timezone": "auto"
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Weather timeout for {city_name}")
            return {"error": "날씨 조회 시간 초과", "city": city_name}
        except requests.exceptions.ConnectionError:
            logger.error(f"Weather connection error for {city_name}")
            return {"error": "날씨 서비스 연결 실패", "city": city_name}
        except requests.exceptions.HTTPError as e:
            logger.error(f"Weather HTTP error for {city_name}: {e}")
            return {"error": f"날씨 API 오류: {e}", "city": city_name}

        data = res.json()
        cw = data.get("current_weather", {})
        temp = cw.get("temperature")
        code = cw.get("weathercode")

        # WMO Weather interpretation codes (simplified)
        condition = "맑음"
        icon = "☀️"
        advice = "좋은 하루 되세요!"

        if code in [0]: condition, icon = "맑음", "☀️"
        elif code in [1, 2, 3]: condition, icon = "구름 조금", "🌤️"
        elif code in [45, 48]: condition, icon = "안개", "🌫️"
        elif code in [51, 53, 55, 61, 63, 65]: condition, icon = "비", "🌧️"
        elif code in [71, 73, 75, 77]: condition, icon = "눈", "❄️"
        elif code in [95, 96, 99]: condition, icon = "뇌우", "⚡"

        if temp <= 0: advice = "날씨가 춥습니다. 따뜻하게 입으세요! 🧥"
        elif temp >= 30: advice = "폭염 주의! 수분 섭취를 잊지 마세요. 💧"
        elif "비" in condition: advice = "우산을 챙기세요! ☂️"

        return {
            "temp": temp,
            "condition": condition,
            "icon": icon,
            "advice": advice,
            "city": city_name
        }
    except Exception as e:
        logger.error(f"Weather Error: {e}")

    return None

def get_google_news(limit=3):
    """
    Google News RSS Feed for Korea (Technology/General)
    """
    try:
        # RSS URL for Korea - Top Stories
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "JARVIS-Bot/1.0"},
        )

        if feed.bozo and not feed.entries:
            return [f"뉴스 피드 파싱 실패"]

        headlines = []
        for entry in feed.entries[:limit]:
            source = entry.source.title if hasattr(entry, 'source') and hasattr(entry.source, 'title') else "Google News"
            headlines.append(f"[{source}] {entry.title}")

        return headlines if headlines else ["뉴스를 가져올 수 없습니다."]
    except Exception as e:
        logger.error(f"News Error: {e}")
        return [f"뉴스 조회 실패: {e}"]

def get_fortune(birth_year=1995):
    """
    Deterministic daily fortune based on date hash.
    """
    zodiacs = {
        0: "원숭이", 1: "닭", 2: "개", 3: "돼지", 4: "쥐", 5: "소", 
        6: "호랑이", 7: "토끼", 8: "용", 9: "뱀", 10: "말", 11: "양"
    }
    zodiac_name = zodiacs[birth_year % 12]
    
    # Deterministic seed based on date + birth_year (고유하게)
    today_str = dt.now().strftime("%Y%m%d")
    seed_val = hash((today_str, birth_year))
    # Bug fix #11: Use local RNG instance instead of poisoning global random.seed()
    rng = random.Random(seed_val)

    stars = "⭐" * rng.randint(3, 5)
    colors = ["빨강", "파랑", "초록", "노랑", "보라", "검정", "흰색", "황금색"]
    lucky_color = rng.choice(colors)

    advices = [
        "오늘은 활발한 에너지가 넘치는 하루입니다.",
        "조금 신중하게 행동하는 것이 좋습니다.",
        "뜻밖의 행운이 찾아올 수 있습니다.",
        "주변 사람들과의 소통이 중요한 날입니다.",
        "새로운 도전을 시작하기 좋은 날입니다.",
        "잠시 휴식을 취하며 재충전하세요.",
        "과거의 노력이 결실을 맺는 날입니다."
    ]

    return {
        "zodiac": zodiac_name,
        "stars": stars,
        "advice": rng.choice(advices),
        "color": lucky_color,
        "desc": f"{zodiac_name}띠인 당신, {stars} 행운이 함께합니다."
    }

if __name__ == "__main__":
    print(get_weather("광주"))
    print(get_google_news())
    print(get_fortune(1995))
