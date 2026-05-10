"""Slack 채널 어댑터 — Socket Mode.

사용:
    dartlab share --slack $BOT_TOKEN --slack-app-token $APP_TOKEN
"""

from __future__ import annotations

import asyncio
import inspect
import logging

from dartlab.channel.adapters.base import ChannelAdapter

logger = logging.getLogger(__name__)


class SlackAdapter(ChannelAdapter):
    """slack-bolt 기반 Slack 어댑터 (Socket Mode)."""

    name = "slack"
    max_message_length = 3000

    def __init__(self, botToken: str, appToken: str):
        self._bot_token = botToken
        self._app_token = appToken
        self._app = None
        self._client = None
        self._handler = None

    async def start(self) -> None:
        """Slack 봇을 Socket Mode로 시작."""
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
        except ImportError as exc:
            raise RuntimeError("Slack 어댑터를 사용하려면:\n  uv pip install slack-bolt") from exc

        app = App(token=self._bot_token)
        self._app = app
        self._client = app.client
        adapter = self

        @app.event("app_mention")
        def onMention(event, _say):
            """onMention — TODO 한국어 동작 설명."""
            text = event.get("text", "")
            # @bot 멘션 제거
            import re

            text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
            channel = event["channel"]

            import asyncio

            asyncio.run(adapter.handleAsk(channel, text))

        @app.event("message")
        def onDm(event, _say):
            """onDm — TODO 한국어 동작 설명."""
            # DM에서는 멘션 없이 바로 처리
            if event.get("channel_type") != "im":
                return
            text = event.get("text", "").strip()
            channel = event["channel"]

            import asyncio

            asyncio.run(adapter.handleAsk(channel, text))

        logger.info("Slack 봇 시작 (Socket Mode)")
        handler = SocketModeHandler(app, self._app_token)
        self._handler = handler
        await asyncio.to_thread(handler.start)

    async def stop(self) -> None:
        """Slack 봇 연결 종료."""
        if self._handler is None:
            return
        close = getattr(self._handler, "close", None)
        if callable(close):
            await asyncio.to_thread(close)
            return

        client = getattr(self._handler, "client", None)
        disconnect = getattr(client, "disconnect", None) if client else None
        if callable(disconnect):
            result = disconnect()
            if inspect.isawaitable(result):
                await result

    async def sendText(self, channelId: str, text: str) -> None:
        """Slack 채널에 텍스트 메시지 전송.

        slack_bolt 동기 클라이언트는 내부 HTTP 호출이라 이벤트 루프 블록.
        asyncio.to_thread로 워커 풀에서 실행 (Discord/Telegram과 동일 패턴).
        """
        if self._client:
            await asyncio.to_thread(
                self._client.chat_postMessage,
                channel=channelId,
                text=text,
            )


def create(*, botToken: str, appToken: str, **kwargs) -> SlackAdapter:
    """SlackAdapter 팩토리."""
    return SlackAdapter(botToken, appToken)
