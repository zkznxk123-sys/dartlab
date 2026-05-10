"""Telegram 채널 어댑터 — polling 기반.

사용:
    dartlab share --telegram $BOT_TOKEN
"""

from __future__ import annotations

import asyncio
import logging

from dartlab.channel.adapters.base import ChannelAdapter

logger = logging.getLogger(__name__)


class TelegramAdapter(ChannelAdapter):
    """python-telegram-bot 기반 Telegram 어댑터."""

    name = "telegram"
    max_message_length = 4096

    def __init__(self, token: str):
        self._token = token
        self._app = None
        self._stop_event = None

    async def start(self) -> None:
        """Telegram 봇을 polling 모드로 시작."""
        try:
            from telegram import Update
            from telegram.ext import (
                ApplicationBuilder,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )
        except ImportError as exc:
            raise RuntimeError("Telegram 어댑터를 사용하려면:\n  uv pip install python-telegram-bot") from exc

        app = ApplicationBuilder().token(self._token).build()
        self._app = app
        self._stop_event = asyncio.Event()

        adapter = self

        async def onStart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """/start command handler — 사용 안내 메시지 전송."""
            if update.effective_chat:
                await adapter.sendText(
                    str(update.effective_chat.id),
                    "DartLab 분석 봇입니다.\n사용법: /ask 삼성전자 배당 분석\n또는 바로 메시지를 보내세요.",
                )

        async def onAsk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """/ask command handler — args 를 DartLab 분석으로 위임."""
            if update.effective_chat and context.args:
                text = " ".join(context.args)
                await adapter.handleAsk(str(update.effective_chat.id), text)
            elif update.effective_chat:
                await adapter.sendText(
                    str(update.effective_chat.id),
                    "사용법: /ask 삼성전자 배당 분석",
                )

        async def onMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """일반 메시지 handler — / 로 시작하지 않으면 DartLab 분석으로 위임."""
            if update.effective_chat and update.message and update.message.text:
                text = update.message.text.strip()
                if text.startswith("/"):
                    return
                await adapter.handleAsk(str(update.effective_chat.id), text)

        app.add_handler(CommandHandler("start", onStart))
        app.add_handler(CommandHandler("ask", onAsk))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onMessage))

        logger.info("Telegram 봇 시작 (polling)")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Telegram 봇 종료 및 updater 정리."""
        if self._stop_event is not None and not self._stop_event.is_set():
            self._stop_event.set()
        if self._app:
            if self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def sendText(self, channelId: str, text: str) -> None:
        """Telegram 채팅방에 텍스트 메시지 전송."""
        if self._app:
            await self._app.bot.send_message(chat_id=channelId, text=text)


def create(*, token: str, **kwargs) -> TelegramAdapter:
    """TelegramAdapter 팩토리."""
    return TelegramAdapter(token)
