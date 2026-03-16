"""crypto_trading 공통 유틸리티 함수"""


def normalize_ticker(ticker: str) -> str:
    """티커 문자열을 Upbit KRW 마켓 형식으로 정규화.

    예: "btc" → "KRW-BTC", "KRW-ETH" → "KRW-ETH"
    """
    ticker = ticker.upper().strip()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    return ticker
