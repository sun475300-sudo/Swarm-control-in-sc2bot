"""
#180: 음성 매매 인터페이스 (Voice Trading Interface) — 스텁

음성 -> 텍스트 -> 명령 파싱 파이프라인의 기본 구조.
실제 음성 인식은 향후 SpeechRecognition / Whisper 통합 예정.
"""
import logging
from datetime import datetime

logger = logging.getLogger("voice_trading")


class VoiceTradeInterface:
    """음성 매매 인터페이스

    음성 입력을 텍스트로 변환하고, 텍스트를 매매 명령으로 파싱하는
    파이프라인 스텁 구현. 실제 음성 인식 엔진은 미연결 상태.
    """

    # 지원 명령어 패턴
    COMMAND_PATTERNS = {
        "buy": ["매수", "사", "buy", "구매"],
        "sell": ["매도", "팔아", "sell", "판매"],
        "hold": ["홀드", "보류", "hold", "대기"],
        "status": ["상태", "현황", "status", "포트폴리오"],
        "cancel": ["취소", "cancel", "중지"],
    }

    def __init__(self):
        """초기화"""
        self._is_listening = False
        self._engine = None  # 음성 인식 엔진 (미연결)
        self._command_history: list = []
        self._supported_languages = ["ko", "en"]
        self._current_language = "ko"
        logger.info("VoiceTradeInterface 초기화 (스텁 모드)")

    def start_listening(self) -> dict:
        """음성 입력 시작 (스텁)

        Returns:
            dict: 리스닝 상태
        """
        self._is_listening = True
        logger.info("음성 인식 시작 (스텁 — 실제 음성 입력 불가)")
        return {
            "status": "stub",
            "listening": True,
            "message": "음성 인식 스텁 모드. 실제 마이크 입력은 지원하지 않습니다.",
            "engine": "none (stub)",
        }

    def stop_listening(self) -> dict:
        """음성 입력 중지 (스텁)

        Returns:
            dict: 리스닝 상태
        """
        self._is_listening = False
        return {"status": "stopped", "listening": False}

    def speech_to_text(self, audio_data: bytes = None) -> str:
        """음성 -> 텍스트 변환 (스텁)

        Args:
            audio_data: 오디오 바이너리 데이터 (스텁에서는 무시)

        Returns:
            str: 변환된 텍스트 (스텁에서는 빈 문자열)
        """
        # 실제 구현 시: SpeechRecognition / Whisper API 호출
        logger.debug("speech_to_text 호출 (스텁 — 빈 결과 반환)")
        return ""

    def parse_command(self, text: str) -> dict:
        """텍스트 -> 매매 명령 파싱

        Args:
            text: 사용자 발화 텍스트

        Returns:
            dict: {
                'action': str,      # buy/sell/hold/status/cancel/unknown
                'ticker': str,      # 종목 코드 (파싱된 경우)
                'amount': float,    # 금액 (파싱된 경우)
                'raw_text': str,    # 원본 텍스트
                'confidence': float # 파싱 신뢰도 (0~1)
            }
        """
        result = {
            "action": "unknown",
            "ticker": "",
            "amount": 0.0,
            "raw_text": text,
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

        if not text:
            return result

        text_lower = text.lower().strip()

        # 명령어 매칭
        for action, keywords in self.COMMAND_PATTERNS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result["action"] = action
                    result["confidence"] = 0.8
                    break
            if result["action"] != "unknown":
                break

        # 종목 코드 추출 시도 (예: "비트코인", "BTC", "KRW-BTC")
        ticker_map = {
            "비트코인": "KRW-BTC", "btc": "KRW-BTC",
            "이더리움": "KRW-ETH", "eth": "KRW-ETH",
            "리플": "KRW-XRP", "xrp": "KRW-XRP",
            "솔라나": "KRW-SOL", "sol": "KRW-SOL",
            "도지": "KRW-DOGE", "doge": "KRW-DOGE",
        }
        for name, ticker in ticker_map.items():
            if name in text_lower:
                result["ticker"] = ticker
                break

        # 금액 추출 시도 (숫자 + 만/원)
        import re
        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*만\s*원?", text_lower)
        if amount_match:
            result["amount"] = float(amount_match.group(1)) * 10000
        else:
            amount_match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*원", text_lower)
            if amount_match:
                result["amount"] = float(amount_match.group(1).replace(",", ""))

        # 명령 기록
        self._command_history.append(result)

        return result

    def process_voice_command(self, audio_data: bytes = None, text: str = None) -> dict:
        """음성 매매 명령 전체 파이프라인 (스텁)

        Args:
            audio_data: 오디오 데이터 (스텁)
            text: 직접 텍스트 입력 (테스트용)

        Returns:
            dict: 파싱된 명령 + 실행 결과
        """
        # Step 1: 음성 -> 텍스트
        if text is None:
            text = self.speech_to_text(audio_data)

        # Step 2: 텍스트 -> 명령
        command = self.parse_command(text)

        # Step 3: 명령 실행 (스텁 — 실제 매매 미수행)
        command["executed"] = False
        command["execution_message"] = "스텁 모드: 실제 매매 미실행"

        return command

    def get_command_history(self) -> list:
        """명령 히스토리 반환"""
        return list(self._command_history)

    def get_status(self) -> dict:
        """인터페이스 상태"""
        return {
            "is_listening": self._is_listening,
            "engine": "stub",
            "language": self._current_language,
            "command_count": len(self._command_history),
            "supported_languages": self._supported_languages,
        }


if __name__ == "__main__":
    vi = VoiceTradeInterface()
    # 테스트: 텍스트 명령 파싱
    test_commands = [
        "비트코인 10만원 매수",
        "이더리움 팔아",
        "포트폴리오 상태",
    ]
    for cmd in test_commands:
        result = vi.process_voice_command(text=cmd)
        print(f"입력: '{cmd}'")
        print(f"  -> action={result['action']}, ticker={result['ticker']}, amount={result['amount']}")
        print()
