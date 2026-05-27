from datetime import datetime
from loader import bot
from db import (
    get_active_announcements, get_announcement_audience,
    mark_announcement_sent,
    deactivate_announcement,
)
import asyncio
import logging



# ===== ФУНКЦИЯ РАССЫЛКИ РАЗОВОГО ОБЪЯВЛЕНИЯ =====
async def send_one_time_announcement(
    *,
    bot,
    restaurant_id: int,
    message: str,
    positions: list[str]
):
    recipients = get_announcement_audience(
        restaurant_id=restaurant_id,
        positions=positions
    )

    if not recipients:
        print("⚠️ Нет получателей для рассылки")
        return

    for user in recipients:
        chat_id = user["id"]

        if not chat_id:
            print("⚠️ У пользователя нет telegram_id:", user)
            continue

        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"❌ Не отправлено {chat_id}: {e}")



async def run_announcements_async():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.date()

    announcements = get_active_announcements()

    for ann in announcements:
        try:
            ann_type = ann["type"]

            # --- ПРОВЕРКА ВРЕМЕНИ ---
            if ann["send_time"] != current_time:
                continue

            if ann_type == "one_time":
                if not ann["send_date"]:
                    continue
                # Преобразуем дату в объект datetime
                send_date = datetime.strptime(ann["send_date"], "%d.%m.%Y").date()
                if send_date != today:
                    continue

            elif ann_type == "daily":
                pass  # только время

            elif ann_type == "weekly":
                if ann["day_of_week"] is None:
                    continue
                if ann["day_of_week"] != now.weekday():
                    continue

            elif ann_type == "monthly":
                if ann["day_of_month"] is None:
                    continue
                if ann["day_of_month"] != now.day:
                    continue

            # --- АНТИ-ДУБЛЬ ---
            if ann["last_sent_at"]:
                last_sent = datetime.fromisoformat(ann["last_sent_at"])
                if last_sent.date() == today and ann_type != "one_time":
                    continue

            # --- ПОЛУЧАТЕЛИ ---
            recipients = get_announcement_audience(
                restaurant_id=ann["restaurant_id"],
                positions=ann.get("positions") or []
            )

            if not recipients:
                logging.warning(f"⚠️ Нет получателей для рассылки объявления ID={ann['id']}")
                continue

            # --- РАССЫЛКА ---
            for user in recipients:
                chat_id = user.get("id")
                if not chat_id:
                    continue
                try:
                    await bot.send_message(
                        chat_id,
                        f"📢 <b>Объявление</b>\n\n{ann['message']}",
                        parse_mode="HTML"
                    )
                except Exception:
                    logging.exception(f"❌ Не удалось отправить объявление ID={ann['id']} пользователю {chat_id}")

            # --- ОБНОВЛЕНИЕ СОСТОЯНИЯ ---
            mark_announcement_sent(ann["id"])

            # Разовая рассылка — сразу деактивируем
            if ann_type == "one_time":
                deactivate_announcement(ann["id"])

        except Exception:
            logging.exception(f"Ошибка рассылки объявления ID={ann.get('id')}")