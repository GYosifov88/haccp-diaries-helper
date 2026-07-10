from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from haccp.bot import handle_message
from haccp.config import get_settings


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("HACCP diary bot is ready. Send a message or photo to log a diary entry.")


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.edited_message or update.message
    if not message:
        return

    sender_name = (
        update.effective_user.full_name
        or update.effective_user.username
        or str(update.effective_user.id)
    )

    if message.photo:
        file = await context.bot.get_file(message.photo[-1].file_id)
        file_bytes = bytes(await file.download_as_bytearray())
        result = handle_message(
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            user_name=sender_name,
            text=message.caption or "",
            input_kind="photo",
            file_bytes=file_bytes,
            file_mime="image/jpeg",
        )
    elif message.document:
        file = await context.bot.get_file(message.document.file_id)
        file_bytes = bytes(await file.download_as_bytearray())
        result = handle_message(
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            user_name=sender_name,
            text=message.caption or "",
            input_kind="document",
            file_bytes=file_bytes,
            file_mime=message.document.mime_type or "application/octet-stream",
        )
    elif message.voice:
        file = await context.bot.get_file(message.voice.file_id)
        file_bytes = bytes(await file.download_as_bytearray())
        result = handle_message(
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            user_name=sender_name,
            text="",
            input_kind="voice",
            file_bytes=file_bytes,
            file_mime="audio/ogg",
        )
    else:
        result = handle_message(
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            user_name=sender_name,
            text=message.text or "",
            input_kind="text",
        )

    reply = "\n".join(result.get("reply_messages", [])) or "Обработих съобщението."
    await message.reply_text(reply)


def build_application(token: str | None = None) -> Application:
    settings = get_settings()
    app = Application.builder().token(token or settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, echo_message))
    return app


def run_bot(token: str | None = None) -> None:
    app = build_application(token)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
