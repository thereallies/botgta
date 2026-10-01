from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("=== Получение Telegram SESSION_STRING ===")
api_id = int(input("API ID: ").strip())
api_hash = input("API Hash: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nSESSION_STRING:\n")
    print(client.session.save())
    print("\nИщу GTA5RP...")
    found = []
    for d in client.iter_dialogs():
        name = d.name or ""
        username = getattr(d.entity, "username", None)
        if "gta5rp" in name.lower() or (username and "gta5rp" in username.lower()):
            found.append(d)
    if found:
        for d in found:
            username = getattr(d.entity, "username", None)
            suffix = f" | @{username}" if username else ""
            print(f"ID: {d.id} | NAME: {d.name!r}{suffix}")
    else:
        print("GTA5RP по имени не найден. Найдите нужный чат в списке диалогов.")
