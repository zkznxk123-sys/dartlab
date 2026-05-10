"""메시징 채널 어댑터 추상 클래스 + 공통 분석 로직."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


def _chunkText(text: str, maxLen: int) -> list[str]:
    """텍스트를 max_len 이하 청크로 분할한다.

    문단(\\n\\n) → 줄(\\n) → 강제 분할 순으로 시도.
    """
    if len(text) <= maxLen:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= maxLen:
            chunks.append(remaining)
            break

        # 문단 경계에서 분할 시도
        cut = remaining.rfind("\n\n", 0, maxLen)
        if cut > 0:
            chunks.append(remaining[:cut])
            remaining = remaining[cut + 2 :]
            continue

        # 줄 경계에서 분할 시도
        cut = remaining.rfind("\n", 0, maxLen)
        if cut > 0:
            chunks.append(remaining[:cut])
            remaining = remaining[cut + 1 :]
            continue

        # 강제 분할
        chunks.append(remaining[:maxLen])
        remaining = remaining[maxLen:]

    return chunks


class ChannelAdapter(ABC):
    """메시징 채널 어댑터 추상 클래스."""

    name: str = "base"
    max_message_length: int = 4000

    @abstractmethod
    async def start(self) -> None:
        """어댑터를 시작한다 (blocking)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """어댑터를 정리한다."""
        ...

    @abstractmethod
    async def sendText(self, channelId: str, text: str) -> None:
        """텍스트 메시지를 전송한다."""
        ...

    async def handleAsk(self, channelId: str, userText: str) -> None:
        """사용자 메시지를 분석하고 응답을 전송한다.

        모든 어댑터가 공유하는 핵심 로직:
        1. AI에 질문 전달 (종목은 AI가 자율 판단)
        2. 응답 청킹 + 전송
        """
        userText = userText.strip()
        if not userText:
            await self.sendText(channelId, "질문을 입력해주세요. 예: 삼성전자 재무분석")
            return

        question = userText
        await self.sendText(channelId, "분석 중...")

        # AI 분석 실행 (blocking → asyncio.to_thread)
        try:
            answer = await asyncio.to_thread(self._runAnalysis, None, question)
        except Exception as exc:  # noqa: BLE001
            logger.exception("분석 실패: %s", exc)
            await self.sendText(channelId, f"분석 중 오류가 발생했습니다: {exc}")
            return

        # 응답 청킹 + 전송
        chunks = _chunkText(answer, self.max_message_length)
        for chunk in chunks:
            await self.sendText(channelId, chunk)

    @staticmethod
    def _runAnalysis(company, question: str) -> str:
        """AI 분석을 실행하고 텍스트를 반환한다 (동기)."""
        from dartlab.ai.kernel import ask

        return ask(question, company=company, stream=False)
