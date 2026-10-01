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

if not TIMEZONE_NAME or TIMEZONE_NAME.upper() == "TIMEZONE":
    TIMEZONE_NAME = "Europe/Moscow"

try:
    TZ = ZoneInfo(TIMEZONE_NAME)

except ZoneInfoNotFoundError:
    log.exception(
        "Не найден часовой пояс %s. Используем Europe/Moscow.",
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


intents = discord.Intents.default()

discord_client = discord.Client(
    intents=intents
)

discord_ready = asyncio.Event()


# ============================================================
# DISCORD
# ============================================================

@discord_client.event
async def on_ready():

    log.info(
        "============================================"
    )

    log.info(
        "DISCORD ПОДКЛЮЧЕН"
    )

    log.info(
        "Бот: %s",
        discord_client.user,
    )

    log.info(
        "ID: %s",
        discord_client.user.id,
    )

    log.info(
        "Серверов: %s",
        len(discord_client.guilds),
    )

    for guild in discord_client.guilds:
        log.info(
            "Сервер: %s | ID: %s",
            guild.name,
            guild.id,
        )

    log.info(
        "============================================"
    )

    discord_ready.set()


@discord_client.event
async def on_disconnect():

    log.warning(
        "Discord отключился."
    )


@discord_client.event
async def on_resumed():

    log.info(
        "Discord соединение восстановлено."
    )


async def get_discord_channel(channel_id):

    channel = discord_client.get_channel(
        channel_id
    )

    if channel is not None:
        return channel

    log.info(
        "Канал %s не найден в кеше. Запрашиваем Discord API...",
        channel_id,
    )

    return await discord_client.fetch_channel(
        channel_id
    )


async def send_discord(channel_id, text):

    channel = await get_discord_channel(
        channel_id
    )

    if channel is None:
        raise RuntimeError(
            f"Discord канал {channel_id} не найден"
        )

    for i in range(0, len(text), 2000):

        await channel.send(
            text[i:i + 2000]
        )


# ============================================================
# TIME
# ============================================================

def message_datetime(message):

    dt = message.date

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(TZ)


def format_dt(dt):

    return dt.strftime(
        "%d.%m.%Y %H:%M"
    )


# ============================================================
# SOURCE CHAT
# ============================================================

def source_chat_matches(message):

    chat = message.chat

    if SOURCE_CHAT_ID:
        return chat.id == SOURCE_CHAT_ID

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
# TELEGRAM
# ============================================================

async def handle_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

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

    if not source_chat_matches(message):
        log.info(
            "Сообщение проигнорировано: неправильный источник."
        )
        return

    if not text:
        return

    lower = text.lower()

    sent_at = message_datetime(
        message
    )

    try:

        # ====================================================
        # ВОЙНА
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
                "Сообщение отправлено в COPY."
            )

        # ====================================================
        # DEFF
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
                    "Следующий дефф "
                    f"{format_dt(next_deff)} ⚠️"
                ),
            )

        # ====================================================
        # ATTACK
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
                    "Следующая атака "
                    f"{format_dt(next_attack)} ♻️"
                ),
            )

        # ====================================================
        # LOSS
        # ====================================================

        elif (
            "проигрывает" in lower
            and "в бою #" in lower
        ):

            await send_discord(
                DISCORD_CHANNEL_RESULTS,
                "❌ Проигрыш - статистика ниже ⬇️",
            )

    except Exception:

        log.exception(
            "Ошибка обработки business_message"
        )


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

    log.info(
        "Discord token найден: %s",
        bool(DISCORD_TOKEN),
    )

    log.info(
        "Telegram token найден: %s",
        bool(TELEGRAM_BOT_TOKEN),
    )

    # ========================================================
    # DISCORD
    # ========================================================

    discord_task = asyncio.create_task(
        discord_client.start(
            DISCORD_TOKEN
        )
    )

    try:

        log.info(
            "Подключаемся к Discord..."
        )

        try:

            await asyncio.wait_for(
                discord_ready.wait(),
                timeout=60,
            )

        except asyncio.TimeoutError:

            log.error(
                "============================================"
            )

            log.error(
                "DISCORD НЕ ПОДКЛЮЧИЛСЯ ЗА 60 СЕКУНД"
            )

            log.error(
                "Проверяй DISCORD_TOKEN и доступ бота."
            )

            log.error(
                "============================================"
            )

            # Получаем реальную ошибку task
            if discord_task.done():

                try:
                    discord_task.result()

                except Exception:
                    log.exception(
                        "РЕАЛЬНАЯ ОШИБКА DISCORD:"
                    )

            raise RuntimeError(
                "Discord connection timeout"
            )

        # ====================================================
        # TELEGRAM
        # ====================================================

        app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        app.add_handler(
            MessageHandler(
                filters.ALL,
                handle_update,
            )
        )

        app.add_error_handler(
            telegram_error
        )

        await app.initialize()

        await app.start()

        await app.updater.start_polling(
            allowed_updates=[
                "business_message"
            ]
        )

        log.info(
            "============================================"
        )

        log.info(
            "TELEGRAM BUSINESS BOT ПОДКЛЮЧЕН"
        )

        log.info(
            "МОСТ ЗАПУЩЕН"
        )

        log.info(
            "Ждем сообщения GTA5RP..."
        )

        log.info(
            "============================================"
        )

        await asyncio.Event().wait()

    finally:

        log.info(
            "Остановка..."
        )

        if "app" in locals():

            try:

                if app.updater.running:
                    await app.updater.stop()

                await app.stop()
                await app.shutdown()

            except Exception:

                log.exception(
                    "Ошибка остановки Telegram"
                )

        try:

            if not discord_client.is_closed():
                await discord_client.close()

        except Exception:

            log.exception(
                "Ошибка остановки Discord"
            )

        if not discord_task.done():

            discord_task.cancel()

            try:
                await discord_task

            except asyncio.CancelledError:
                pass


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        log.info(
            "Бот остановлен."
        )

    except Exception:

        log.exception(
            "КРИТИЧЕСКАЯ ОШИБКА БОТА"
        )