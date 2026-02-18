"""
#185: LLM 매매 자문 (LLM Trade Advisor)

시장 데이터를 Claude API에 전달하여 매매 조언을 받는 자문 시스템.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("llm_trade_advisor")


class LLMTradeAdvisor:
    """LLM 기반 매매 자문 시스템

    시장 데이터, 기술 지표, 포트폴리오 상태를 Claude API에 전달하여
    매수/매도/홀드 추천을 받는다.
    """

    SYSTEM_PROMPT = (
        "당신은 암호화폐 트레이딩 전문 어드바이저입니다. "
        "주어진 시장 데이터와 기술 지표를 분석하여 매매 추천을 제공합니다. "
        "반드시 다음 형식으로 응답하세요:\n"
        "1. 추천: BUY / SELL / HOLD 중 하나\n"
        "2. 신뢰도: 0~100 사이 정수\n"
        "3. 근거: 추천 이유 (2~3문장)\n"
        "4. 리스크: 주의사항 (1~2문장)\n\n"
        "투자 원칙:\n"
        "- 리스크 관리를 최우선시\n"
        "- 확실하지 않으면 HOLD 추천\n"
        "- 과도한 레버리지/집중 투자 경고\n"
        "- 시장 변동성 고려"
    )

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        """초기화

        Args:
            api_key: Anthropic API 키 (None이면 환경변수에서 로드)
            model: 사용할 Claude 모델
        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model
        self._advice_history: list = []
        self._max_history = 100
        self._project_root = Path(__file__).parent

    def _call_claude_api(self, prompt: str) -> str:
        """Claude API 호출

        Args:
            prompt: 사용자 프롬프트

        Returns:
            str: Claude 응답 텍스트
        """
        if not self._api_key:
            return "[API 키 미설정] ANTHROPIC_API_KEY 환경변수를 설정하세요."

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except ImportError:
            return self._call_claude_api_raw(prompt)
        except Exception as e:
            logger.error(f"Claude API 호출 실패: {e}")
            return f"[API 오류] {e}"

    def _call_claude_api_raw(self, prompt: str) -> str:
        """anthropic 라이브러리 없이 직접 HTTP 호출"""
        try:
            import urllib.request
            import urllib.error

            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            }
            body = json.dumps({
                "model": self._model,
                "max_tokens": 1024,
                "system": self.SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")

            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["content"][0]["text"]
        except Exception as e:
            logger.error(f"Claude API raw 호출 실패: {e}")
            return f"[API 오류] {e}"

    def _format_market_data(self, market_data: dict) -> str:
        """시장 데이터를 프롬프트용 텍스트로 포맷"""
        lines = ["=== 시장 데이터 ==="]

        if "ticker" in market_data:
            lines.append(f"종목: {market_data['ticker']}")
        if "current_price" in market_data:
            lines.append(f"현재가: {market_data['current_price']:,.0f} KRW")
        if "change_pct" in market_data:
            lines.append(f"24시간 변동률: {market_data['change_pct']:+.2f}%")
        if "volume" in market_data:
            lines.append(f"거래량: {market_data['volume']:,.0f}")
        if "high_24h" in market_data:
            lines.append(f"24시간 고가: {market_data['high_24h']:,.0f} KRW")
        if "low_24h" in market_data:
            lines.append(f"24시간 저가: {market_data['low_24h']:,.0f} KRW")

        # 기술 지표
        indicators = market_data.get("indicators", {})
        if indicators:
            lines.append("\n=== 기술 지표 ===")
            if "rsi" in indicators:
                lines.append(f"RSI(14): {indicators['rsi']:.1f}")
            if "macd" in indicators:
                lines.append(f"MACD: {indicators['macd']:.4f}")
            if "ma_20" in indicators:
                lines.append(f"20일 이동평균: {indicators['ma_20']:,.0f}")
            if "ma_50" in indicators:
                lines.append(f"50일 이동평균: {indicators['ma_50']:,.0f}")
            if "bollinger_upper" in indicators:
                lines.append(f"볼린저 상단: {indicators['bollinger_upper']:,.0f}")
            if "bollinger_lower" in indicators:
                lines.append(f"볼린저 하단: {indicators['bollinger_lower']:,.0f}")

        # 포트폴리오 상태
        portfolio = market_data.get("portfolio", {})
        if portfolio:
            lines.append("\n=== 포트폴리오 ===")
            if "total_krw" in portfolio:
                lines.append(f"총 자산: {portfolio['total_krw']:,.0f} KRW")
            if "current_holding" in portfolio:
                lines.append(f"현재 보유량: {portfolio['current_holding']}")
            if "avg_buy_price" in portfolio:
                lines.append(f"평균 매수가: {portfolio['avg_buy_price']:,.0f} KRW")
            if "unrealized_pnl_pct" in portfolio:
                lines.append(f"미실현 수익률: {portfolio['unrealized_pnl_pct']:+.2f}%")

        return "\n".join(lines)

    def _parse_advice_response(self, response: str) -> dict:
        """Claude 응답을 구조화된 딕셔너리로 파싱"""
        result = {
            "recommendation": "HOLD",
            "confidence": 50,
            "rationale": "",
            "risk_warning": "",
            "raw_response": response,
        }

        response_upper = response.upper()

        # 추천 파싱
        if "BUY" in response_upper and "SELL" not in response_upper:
            result["recommendation"] = "BUY"
        elif "SELL" in response_upper and "BUY" not in response_upper:
            result["recommendation"] = "SELL"
        else:
            # 더 정밀한 파싱
            import re
            rec_match = re.search(r"추천\s*[:：]\s*(BUY|SELL|HOLD)", response, re.IGNORECASE)
            if rec_match:
                result["recommendation"] = rec_match.group(1).upper()

        # 신뢰도 파싱
        import re
        conf_match = re.search(r"신뢰도\s*[:：]\s*(\d+)", response)
        if conf_match:
            result["confidence"] = min(100, max(0, int(conf_match.group(1))))

        # 근거 파싱
        rationale_match = re.search(r"근거\s*[:：]\s*(.+?)(?=리스크|$)", response, re.DOTALL)
        if rationale_match:
            result["rationale"] = rationale_match.group(1).strip()

        # 리스크 파싱
        risk_match = re.search(r"리스크\s*[:：]\s*(.+?)$", response, re.DOTALL)
        if risk_match:
            result["risk_warning"] = risk_match.group(1).strip()

        return result

    def get_trade_advice(self, market_data: dict) -> dict:
        """매매 자문 요청

        Args:
            market_data: 시장 데이터 딕셔너리
                {
                    'ticker': str,
                    'current_price': float,
                    'change_pct': float,
                    'volume': float,
                    'indicators': { 'rsi': float, 'macd': float, ... },
                    'portfolio': { 'total_krw': float, ... },
                }

        Returns:
            dict: {
                'recommendation': 'BUY' | 'SELL' | 'HOLD',
                'confidence': int (0~100),
                'rationale': str,
                'risk_warning': str,
                'raw_response': str,
                'timestamp': str,
                'ticker': str,
            }
        """
        prompt = self._format_market_data(market_data)
        prompt += "\n\n위 데이터를 분석하여 매매 추천을 제공해주세요."

        logger.info(f"LLM 매매 자문 요청: {market_data.get('ticker', 'N/A')}")

        response_text = self._call_claude_api(prompt)
        advice = self._parse_advice_response(response_text)
        advice["timestamp"] = datetime.now().isoformat()
        advice["ticker"] = market_data.get("ticker", "N/A")

        # 히스토리 기록
        self._advice_history.append(advice)
        if len(self._advice_history) > self._max_history:
            self._advice_history = self._advice_history[-self._max_history:]

        return advice

    def get_advice_history(self) -> list:
        """자문 히스토리 반환"""
        return list(self._advice_history)

    def get_summary(self) -> dict:
        """자문 통계 요약"""
        if not self._advice_history:
            return {"total_advices": 0, "buy_count": 0, "sell_count": 0, "hold_count": 0}

        buy_count = sum(1 for a in self._advice_history if a["recommendation"] == "BUY")
        sell_count = sum(1 for a in self._advice_history if a["recommendation"] == "SELL")
        hold_count = sum(1 for a in self._advice_history if a["recommendation"] == "HOLD")
        avg_confidence = sum(a["confidence"] for a in self._advice_history) / len(self._advice_history)

        return {
            "total_advices": len(self._advice_history),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "avg_confidence": round(avg_confidence, 1),
            "last_advice": self._advice_history[-1] if self._advice_history else None,
        }


if __name__ == "__main__":
    advisor = LLMTradeAdvisor()

    # 테스트 데이터
    test_data = {
        "ticker": "KRW-BTC",
        "current_price": 135_000_000,
        "change_pct": -2.5,
        "volume": 15_000_000_000,
        "high_24h": 140_000_000,
        "low_24h": 133_000_000,
        "indicators": {
            "rsi": 35.2,
            "macd": -500000,
            "ma_20": 137_000_000,
            "ma_50": 132_000_000,
        },
        "portfolio": {
            "total_krw": 10_000_000,
            "current_holding": 0.05,
            "avg_buy_price": 130_000_000,
            "unrealized_pnl_pct": 3.85,
        },
    }

    print("=== LLM Trade Advisor Test ===")
    advice = advisor.get_trade_advice(test_data)
    print(f"Recommendation: {advice['recommendation']}")
    print(f"Confidence: {advice['confidence']}%")
    print(f"Rationale: {advice['rationale']}")
    print(f"Risk: {advice['risk_warning']}")
