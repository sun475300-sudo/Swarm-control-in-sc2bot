"""
JARVIS 확장 기능 패키지
기존 7개 카테고리 + OpenClaw 통합 8개 카테고리

카테고리 (기존):
  1. AI/대화 강화       (ai_features)
  2. 코인/금융 확장     (finance_features)
  3. SC2 봇 강화        (sc2_features)
  4. 시스템/유틸리티    (system_features)
  5. 생산성/일정        (productivity_features)
  6. 엔터테인먼트      (entertainment_features)
  7. 보안/관리          (security_features)

카테고리 (OpenClaw 통합):
  8.  정보/검색         (openclaw_info)
  9.  금융 분석         (openclaw_finance)
  10. 문서 생성         (openclaw_documents)
  11. 미디어 생성       (openclaw_media)
  12. 소셜/통신         (openclaw_social)
  13. 개발/시스템       (openclaw_dev)
  14. 브라우저 자동화   (openclaw_browser)
  15. Cron 자동화       (openclaw_cron)
"""

from __future__ import annotations

import logging
from typing import Optional
from discord.ext import commands

logger = logging.getLogger("jarvis.features")

ALL_COGS = [
    "jarvis_features.ai_features",
    "jarvis_features.finance_features",
    "jarvis_features.sc2_features",
    "jarvis_features.system_features",
    "jarvis_features.productivity_features",
    "jarvis_features.entertainment_features",
    "jarvis_features.security_features",
    # OpenClaw Integration
    "jarvis_features.openclaw_info",
    "jarvis_features.openclaw_finance",
    "jarvis_features.openclaw_documents",
    "jarvis_features.openclaw_media",
    "jarvis_features.openclaw_social",
    "jarvis_features.openclaw_dev",
    "jarvis_features.openclaw_browser",
    "jarvis_features.openclaw_cron",
]


async def load_all_features(bot: commands.Bot) -> list[str]:
    """모든 확장 기능 Cog를 로드한다.

    Returns:
        성공적으로 로드된 모듈 이름 리스트.
    """
    loaded = []
    for cog_path in ALL_COGS:
        try:
            await bot.load_extension(cog_path)
            loaded.append(cog_path)
            logger.info(f"✓ {cog_path} 로드 완료")
        except Exception as e:
            logger.warning(f"✗ {cog_path} 로드 실패: {e}")
    return loaded
