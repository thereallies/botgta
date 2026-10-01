import asyncio
import logging
import os
import re
from datetime import timedelta
from zoneinfo import ZoneInfo

import discord
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("gta5rp-bridge")

def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения: {name}")
    return value

TELEGRAM_API_ID = int(required("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = required("TELEGRAM_API_HASH")
SESSION_STRING = required("SESSION_STRING")
TELEGRAM_SOURCE_CHAT_ID = int(required("TELEGRAM_SOURCE_CHAT_ID"))

DISCORD_TOKEN = required("DISCORD_TOKEN")
CHANNEL_RESULTS = int(required("DISCORD_CHANNEL_RESULTS"))
CHANNEL_TIMING = int(required("DISCORD_CHANNEL_TIMING"))
CHANNEL_COPY = int(required("DISCORD_CHANNEL_COPY"))

TIMEZONE_NAME = os.getenv("TIMEZONE", "Europe/Moscow")
TZ = ZoneInfo(TIMEZONE_NAME)

tg = TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
intents = discord.Intents.default()
dc = discord.Client(intents=intents)
discord_ready = asyncio.Event()

@dc.event
async def on_ready():
    log.info("Discord: вошли как %s (%s)", dc.user, dc.user.id)
    discord_ready.set()

async def get_channel(channel_id: int):
    channel = dc.get_channel(channel_id)
    return channel if channel is not None else await dc.fetch_channel(channel_id)

async def send_discord(channel_id: int, text: str):
    channel = await get_channel(channel_id)
    if len(text) <= 2000:
        await channel.send(text)
        return
    for i in range(0, len(text), 2000):
        await channel.send(text[i:i + 2000])

def message_time(message):
    dt = message.date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TZ)

def fmt(dt):
    return dt.strftime("%d.%m.%Y %H:%M")

async def process_message(event):
    text = (event.raw_text or "").strip()
    if not text:
        return
    lower = text.lower()
    sent_at = message_time(event.message)
    try:
        # Сообщения вида: "Ваша организация забила ... войну ..."
        if "войну" in lower and re.search(r"\bзабил(?:а|и|о)?\b", lower):
            await send_discord(CHANNEL_COPY, text)
            log.info("WAR COPY: %s", text[:150])

        if "удерживает" in lower and "в бою #" in lower:
            await send_discord(CHANNEL_RESULTS, "✅ Выигрыш (deff) - статистика ниже ⬇️")
            next_time = sent_at + timedelta(hours=1)
            await send_discord(CHANNEL_TIMING, f"Следующий дефф {fmt(next_time)} ⚠️")
            log.info("DEFF: %s -> %s", fmt(sent_at), fmt(next_time))

        elif "захватывает" in lower and "в бою #" in lower:
            await send_discord(CHANNEL_RESULTS, "✅ Выигрыш (att) - статистика ниже ⬇️")
            next_time = sent_at + timedelta(hours=2)
            await send_discord(CHANNEL_TIMING, f"Следующая атака {fmt(next_time)} ♻️")
            log.info("ATT: %s -> %s", fmt(sent_at), fmt(next_time))

        elif "проигрывает" in lower and "в бою #" in lower:
            await send_discord(CHANNEL_RESULTS, "❌ Проигрыш - статистика ниже ⬇️")
            log.info("LOSS: %s", fmt(sent_at))
    except Exception:
        log.exception("Ошибка обработки сообщения")

@tg.on(events.NewMessage(chats=TELEGRAM_SOURCE_CHAT_ID))
async def on_new_message(event):
    await process_message(event)

async def main():
    log.info("Источник Telegram chat ID: %s", TELEGRAM_SOURCE_CHAT_ID)
    log.info("Часовой пояс: %s", TIMEZONE_NAME)
    discord_task = asyncio.create_task(dc.start(DISCORD_TOKEN))
    try:
        await discord_ready.wait()
        await tg.start()
        me = await tg.get_me()
        log.info("Telegram: вошли как %s (%s)", getattr(me, "username", None) or getattr(me, "first_name", None), me.id)
        entity = await tg.get_entity(TELEGRAM_SOURCE_CHAT_ID)
        log.info("Источник найден: %s", getattr(entity, "username", None) or getattr(entity, "first_name", None) or getattr(entity, "title", None))
        log.info("Мост запущен. Ждем новые сообщения...")
        await tg.run_until_disconnected()
    finally:
        if tg.is_connected():
            await tg.disconnect()
        if not discord_task.done():
            discord_task.cancel()
            try:
                await discord_task
            except asyncio.CancelledError:
                pass
        if not dc.is_closed():
            await dc.close()

if __name__ == "__main__":
    asyncio.run(main())
