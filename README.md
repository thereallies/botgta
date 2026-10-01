# GTA5RP Telegram -> Discord Bridge

Схема: ваш Telegram-аккаунт -> приватный чат `GTA5RP: бот-помощник` -> Telethon -> Discord Bot.

## Что делает

- `Удерживает ... в бою #` -> `✅ Выигрыш (deff) - статистика ниже ⬇️` + `Следующий дефф DD.MM.YYYY HH:MM ⚠️` (+1 час)
- `Захватывает ... в бою #` -> `✅ Выигрыш (att) - статистика ниже ⬇️` + `Следующая атака DD.MM.YYYY HH:MM ♻️` (+2 часа)
- `Проигрывает ... в бою #` -> `❌ Проигрыш - статистика ниже ⬇️`
- `забил/забила/забили/забило` + `войну` -> копирует исходное сообщение целиком в отдельный Discord-канал.

Время берется из timestamp исходного сообщения Telegram и переводится в `TIMEZONE` (по умолчанию `Europe/Moscow`), а не берется с сервера.

## 1. Получить Telegram API ID / Hash

Откройте https://my.telegram.org/apps и создайте API application.

## 2. Получить SESSION_STRING локально

На компьютере:

```bash
pip install telethon
python setup_telegram.py
```

Скрипт попросит номер/код Telegram и, если включен, пароль 2FA. Затем покажет `SESSION_STRING` и попробует найти чат GTA5RP и его ID.

**SESSION_STRING — секрет. Не публикуйте его и не коммитьте в Git.**

## 3. Создать Discord Bot

Создайте обычного Discord-бота и добавьте его на сервер. Дайте ему доступ к трем нужным каналам и право `Send Messages`.

Получите:
- Discord Bot Token
- ID канала результатов
- ID канала тайминга
- ID канала копирования войн

## 4. Bothost

Загрузите проект в Git и создайте Python-бота на Bothost. Главный файл: `bot.py`.

Добавьте Environment Variables:

```text
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
SESSION_STRING=...
TELEGRAM_SOURCE_CHAT_ID=...

DISCORD_TOKEN=...
DISCORD_CHANNEL_RESULTS=...
DISCORD_CHANNEL_TIMING=...
DISCORD_CHANNEL_COPY=...

TIMEZONE=Europe/Moscow
```

После деплоя запускается только `bot.py`. `setup_telegram.py` нужен один раз локально для получения сессии.

## 5. Ожидаемый лог

```text
Discord: вошли как MyBot (...)
Telegram: вошли как username (...)
Источник найден: GTA5RP: бот-помощник
Мост запущен. Ждем новые сообщения...
```

## Важно

Не добавляйте `.env` или `SESSION_STRING` в публичный репозиторий. Если строка сессии утекла, завершите Telegram-сессию и создайте новую.
