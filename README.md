# GTA5RP Business Bot -> Discord

Вариант без Telegram API ID/API Hash, Telethon и SESSION_STRING.

Схема: Telegram Business -> Business Bot -> business_message -> Python -> Discord.

## Переменные Bothost

```text
TELEGRAM_BOT_TOKEN=токен_из_BotFather
TELEGRAM_SOURCE_CHAT_ID=0
TELEGRAM_SOURCE_CHAT_TITLE=GTA5RP: бот-помощник
DISCORD_TOKEN=токен_Discord_бота
DISCORD_CHANNEL_RESULTS=ID_канала_результатов
DISCORD_CHANNEL_TIMING=ID_канала_тайминга
DISCORD_CHANNEL_COPY=ID_канала_копирования
TIMEZONE=Europe/Moscow
```

Если в логах будет известен ID чата GTA5RP, лучше заменить `TELEGRAM_SOURCE_CHAT_ID=0` на него.

Главный файл Bothost: `bot.py`.

## Логика

`Удерживает ... в бою #` -> `✅ Выигрыш (deff) - статистика ниже ⬇️` + следующий дефф через 1 час.

`Захватывает ... в бою #` -> `✅ Выигрыш (att) - статистика ниже ⬇️` + следующая атака через 2 часа.

`Проигрывает ... в бою #` -> `❌ Проигрыш - статистика ниже ⬇️`.

`забил/забила/забили/забило ... войну` -> полный текст в канал копирования.

Время считается от времени исходного Telegram-сообщения и переводится в `TIMEZONE`.

Не публикуйте `TELEGRAM_BOT_TOKEN` или `DISCORD_TOKEN`.
