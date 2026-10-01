import asyncio
import logging
import os
import re
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
log = logging.getLogger('gta5rp-bridge')

def required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'Не задана переменная окружения: {name}')
    return value

TELEGRAM_BOT_TOKEN = required('TELEGRAM_BOT_TOKEN')
SOURCE_CHAT_ID = int(os.getenv('TELEGRAM_SOURCE_CHAT_ID', '0'))
SOURCE_CHAT_TITLE = os.getenv('TELEGRAM_SOURCE_CHAT_TITLE', 'GTA5RP: бот-помощник').strip().lower()
TIMEZONE_NAME = os.getenv('TIMEZONE', 'Europe/Moscow')
TZ = ZoneInfo(TIMEZONE_NAME)

DISCORD_TOKEN = required('DISCORD_TOKEN')
DISCORD_CHANNEL_RESULTS = int(required('DISCORD_CHANNEL_RESULTS'))
DISCORD_CHANNEL_TIMING = int(required('DISCORD_CHANNEL_TIMING'))
DISCORD_CHANNEL_COPY = int(required('DISCORD_CHANNEL_COPY'))

discord_client = discord.Client(intents=discord.Intents.default())
discord_ready = asyncio.Event()

@discord_client.event
async def on_ready():
    log.info('Discord подключен: %s (%s)', discord_client.user, discord_client.user.id)
    discord_ready.set()

async def get_discord_channel(channel_id):
    channel = discord_client.get_channel(channel_id)
    return channel if channel is not None else await discord_client.fetch_channel(channel_id)

async def send_discord(channel_id, text):
    channel = await get_discord_channel(channel_id)
    for i in range(0, len(text), 2000):
        await channel.send(text[i:i + 2000])

def message_datetime(message):
    dt = message.date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)

def format_dt(dt):
    return dt.strftime('%d.%m.%Y %H:%M')

def source_chat_matches(message):
    chat = message.chat
    if SOURCE_CHAT_ID:
        return chat.id == SOURCE_CHAT_ID
    names = [getattr(chat, 'title', None), getattr(chat, 'first_name', None), getattr(chat, 'last_name', None)]
    full_name = ' '.join(x for x in names if x).strip().lower()
    return full_name == SOURCE_CHAT_TITLE

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.business_message
    if message is None:
        return
    chat = message.chat
    text = (message.text or message.caption or '').strip()
    log.info('BUSINESS MESSAGE | chat_id=%s | chat=%s | text=%r', chat.id, getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or getattr(chat, 'username', None), text[:300])
    if not source_chat_matches(message) or not text:
        return
    lower = text.lower()
    sent_at = message_datetime(message)
    try:
        if 'войну' in lower and re.search(r'\bзабил(?:а|и|о)?\b', lower):
            await send_discord(DISCORD_CHANNEL_COPY, text)
        if 'удерживает' in lower and 'в бою #' in lower:
            await send_discord(DISCORD_CHANNEL_RESULTS, '✅ Выигрыш (deff) - статистика ниже ⬇️')
            await send_discord(DISCORD_CHANNEL_TIMING, f'Следующий дефф {format_dt(sent_at + timedelta(hours=1))} ⚠️')
        elif 'захватывает' in lower and 'в бою #' in lower:
            await send_discord(DISCORD_CHANNEL_RESULTS, '✅ Выигрыш (att) - статистика ниже ⬇️')
            await send_discord(DISCORD_CHANNEL_TIMING, f'Следующая атака {format_dt(sent_at + timedelta(hours=2))} ♻️')
        elif 'проигрывает' in lower and 'в бою #' in lower:
            await send_discord(DISCORD_CHANNEL_RESULTS, '❌ Проигрыш - статистика ниже ⬇️')
    except Exception:
        log.exception('Ошибка обработки business_message')

async def telegram_error(update, context):
    log.error('Telegram error: %s', context.error)

async def main():
    log.info('=== GTA5RP Telegram Business -> Discord ===')
    log.info('Источник: %s', SOURCE_CHAT_ID or SOURCE_CHAT_TITLE)
    log.info('Timezone: %s', TIMEZONE_NAME)
    discord_task = asyncio.create_task(discord_client.start(DISCORD_TOKEN))
    try:
        await asyncio.wait_for(discord_ready.wait(), timeout=60)
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.ALL, handle_update))
        app.add_error_handler(telegram_error)
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=['business_message'])
        log.info('Telegram Business Bot подключен')
        log.info('Мост запущен. Ждем сообщения GTA5RP...')
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop(); await app.stop(); await app.shutdown()
    finally:
        if not discord_client.is_closed():
            await discord_client.close()
        if not discord_task.done():
            discord_task.cancel()
            try: await discord_task
            except asyncio.CancelledError: pass

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
