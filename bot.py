import asyncio
import logging
import os
import re
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters


# ============================================================
# НАСТРОЙКА
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("gta5rp-bridge")


def required(name):
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Не задана переменная окружения: {name}"
        )

    return value.strip()


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = required("TELEGRAM_BOT_TOKEN")

SOURCE_CHAT_ID = int(
    os.getenv("TELEGRAM_SOURCE_CHAT_ID", "0")
)

SOURCE_CHAT_TITLE = os.getenv(
    "TELEGRAM_SOURCE_CHAT_TITLE",
    "GTA5RP: бот-помощник",
).strip().lower()


# ============================================================
# TIMEZONE
# ============================================================

TIMEZONE_NAME = os.getenv(
    "TIMEZONE",
    "Europe/Moscow",
).strip()

# Защита от старого неправильного значения:
# TIMEZONE=TIMEZONE
if not TIMEZONE_NAME or TIMEZONE_NAME.upper() == "TIMEZONE":
    log.warning(
        "Переменная TIMEZONE задана неправильно: %r. "
        "Используем Europe/Moscow.",
        TIMEZONE_NAME,
    )

    TIMEZONE_NAME = "Europe/Moscow"


try:
    TZ = ZoneInfo(TIMEZONE_NAME)

except ZoneInfoNotFoundError:
    log.exception(
        "Часовой пояс '%s' не найден. "
        "Используем Europe/Moscow.",
        TIMEZONE_NAME,
    )

    TIMEZONE_NAME = "Europe/Moscow"
    TZ = ZoneInfo(TIMEZONE_NAME)


# ============================================================
# DISCORD
# ============================================================

DISCORD_TOKEN = required("DISCORD_TOKEN")

DISCORD_CHANNEL_RESULTS = int(
    required("DISCORD_CHANNEL_RESULTS")
)

DISCORD_CHANNEL_TIMING = int(
    required("DISCORD_CHANNEL_TIMING")
)

DISCORD_CHANNEL_COPY = int(
    required("DISCORD_CHANNEL_COPY")
)


discord_client = discord.Client(
    intents=discord.Intents.default()
)

discord_ready = asyncio.Event()


# ============================================================
# DISCORD EVENTS
# ============================================================

@discord_client.event
async def on_ready():
    log.info(
        "Discord подключен: %s (%s)",
        discord_client.user,
        discord_client.user.id,
    )

    discord_ready.set()


async def get_discord_channel(channel_id):
    channel = discord_client.get_channel(channel_id)

    if channel is not None:
        return channel

    return await discord_client.fetch_channel(channel_id)


async def send_discord(channel_id, text):
    channel = await get_discord_channel(channel_id)

    if channel is None:
        raise RuntimeError(
            f"Discord канал {channel_id} не найден"
        )

    # Discord ограничивает сообщение 2000 символами.
    for i in range(0, len(text), 2000):
        await channel.send(text[i:i + 2000])


# ============================================================
# TIME / DATE
# ============================================================

def message_datetime(message):
    dt = message.date

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(TZ)


def format_dt(dt):
    return dt.strftime("%d.%m.%Y %H:%M")


# ============================================================
# TELEGRAM SOURCE CHECK
# ============================================================

def source_chat_matches(message):
    chat = message.chat

    # Если указан конкретный ID чата —
    # используем именно его.
    if SOURCE_CHAT_ID:
        return chat.id == SOURCE_CHAT_ID

    # Иначе проверяем название.
    names = [
        getattr(chat, "title", None),
        getattr(chat, "first_name", None),
        getattr(chat, "last_name", None),
    ]

    full_name = " ".join(
        x for x in names if x
    ).strip().lower()

    return full_name == SOURCE_CHAT_TITLE


# ============================================================
# TELEGRAM MESSAGE HANDLER
# ============================================================

async def handle_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # Нас интересуют именно сообщения,
    # полученные через Telegram Business.
    message = update.business_message

    if message is None:
        return

    chat = message.chat

    text = (
        message.text
        or message.caption
        or ""
    ).strip()

    log.info(
        "BUSINESS MESSAGE | chat_id=%s | chat=%s | text=%r",
        chat.id,
        (
            getattr(chat, "title", None)
            or getattr(chat, "first_name", None)
            or getattr(chat, "username", None)
        ),
        text[:300],
    )

    # Игнорируем сообщения не из нужного чата.
    if not source_chat_matches(message):
        log.info(
            "Сообщение проигнорировано: другой чат."
        )
        return

    # Игнорируем сообщения без текста.
    if not text:
        return

    lower = text.lower()

    sent_at = message_datetime(message)

    try:

        # ====================================================
        # КОПИРОВАНИЕ СООБЩЕНИЙ ПРО ВОЙНУ
        # ====================================================

        if (
            "войну" in lower
            and re.search(
                r"\bзабил(?:а|и|о)?\b",
                lower,
            )
        ):
            await send_discord(
                DISCORD_CHANNEL_COPY,
                text,
            )

            log.info(
                "Сообщение о войне отправлено "
                "в канал COPY."
            )

        # ====================================================
        # DEFF / УДЕРЖИВАЕТ
        # ====================================================

        if (
            "удерживает" in lower
            and "в бою #" in lower
        ):

            await send_discord(
                DISCORD_CHANNEL_RESULTS,
                "✅ Выигрыш (deff) - статистика ниже ⬇️",
            )

            next_deff = (
                sent_at
                + timedelta(hours=1)
            )

            await send_discord(
                DISCORD_CHANNEL_TIMING,
                (
                    f"Следующий дефф "
                    f"{format_dt(next_deff)} ⚠️"
                ),
            )

            log.info(
                "DEFF: следующий дефф %s",
                format_dt(next_deff),
            )

        # ====================================================
        # ATTACK / ЗАХВАТЫВАЕТ
        # ====================================================

        elif (
            "захватывает" in lower
            and "в бою #" in lower
        ):

            await send_discord(
                DISCORD_CHANNEL_RESULTS,
                "✅ Выигрыш (att) - статистика ниже ⬇️",
            )

            next_attack = (
                sent_at
                + timedelta(hours=2)
            )

            await send_discord(
                DISCORD_CHANNEL_TIMING,
                (
                    f"Следующая атака "
                    f"{format_dt(next_attack)} ♻️"
                ),
            )

            log.info(
                "ATTACK: следующая атака %s",
                format_dt(next_attack),
            )

        # ====================================================
        # ПРОИГРЫШ
        # ====================================================

        elif (
            "проигрывает" in lower
            and "в бою #" in lower
        ):

            await send_discord(
                DISCORD_CHANNEL_RESULTS,
                "❌ Проигрыш - статистика ниже ⬇️",
            )

            log.info(
                "Зафиксирован проигрыш."
            )

    except Exception:
        log.exception(
            "Ошибка обработки business_message"
        )


# ============================================================
# TELEGRAM ERROR HANDLER
# ============================================================

async def telegram_error(
    update,
    context,
):
    log.error(
        "Telegram error: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    log.info(
        "============================================"
    )

    log.info(
        "=== GTA5RP Telegram Business -> Discord ==="
    )

    log.info(
        "============================================"
    )

    log.info(
        "Источник: %s",
        SOURCE_CHAT_ID or SOURCE_CHAT_TITLE,
    )

    log.info(
        "Timezone: %s",
        TIMEZONE_NAME,
    )

    # --------------------------------------------------------
    # Запускаем Discord
    # --------------------------------------------------------

    discord_task = asyncio.create_task(
        discord_client.start(DISCORD_TOKEN)
    )

    try:

        log.info(
            "Ожидаем подключение Discord..."
        )

        await asyncio.wait_for(
            discord_ready.wait(),
            timeout=60,
        )

        log.info(
            "Discord готов."
        )

        # ----------------------------------------------------
        # Telegram Application
        # ----------------------------------------------------

        app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        # Обрабатываем все типы Telegram updates,
        # но внутри handle_update берём только
        # business_message.
        app.add_handler(
            MessageHandler(
                filters.ALL,
                handle_update,
            )
        )

        app.add_error_handler(
            telegram_error
        )

        # ----------------------------------------------------
        # Запуск Telegram
        # ----------------------------------------------------

        await app.initialize()

        await app.start()

        await app.updater.start_polling(
            allowed_updates=[
                "business_message"
            ]
        )

        log.info(
            "Telegram Business Bot подключен."
        )

        log.info(
            "Мост запущен. Ждем сообщения GTA5RP..."
        )

        # Бесконечно держим процесс запущенным.
        await asyncio.Event().wait()

    finally:

        log.info(
            "Останавливаем бота..."
        )

        # ----------------------------------------------------
        # Telegram shutdown
        # ----------------------------------------------------

        try:
            if "app" in locals():

                if app.updater.running:
                    await app.updater.stop()

                await app.stop()
                await app.shutdown()

        except Exception:
            log.exception(
                "Ошибка при остановке Telegram"
            )

        # ----------------------------------------------------
        # Discord shutdown
        # ----------------------------------------------------

        try:

            if not discord_client.is_closed():
                await discord_client.close()

        except Exception:
            log.exception(
                "Ошибка при остановке Discord"
            )

        # ----------------------------------------------------
        # Discord task
        # ----------------------------------------------------

        if not discord_task.done():

            discord_task.cancel()

            try:
                await discord_task

            except asyncio.CancelledError:
                pass


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        log.info(
            "Бот остановлен вручную."
        )

    except Exception:
        log.exception(
            "Критическая ошибка запуска бота."
        )