from datetime import timedelta, date
import asyncio
from loader import bot
from db import (get_connection, get_shift_report_full, get_day_events, save_newsletter_to_cache,
    get_meeting, get_users, get_cached_newsletter_text, get_users_on_shift)
from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery
from keyboards import TOPICS

router = Router()


# Собираем и кэшируем утреннюю рассылку для всех активных пользователей
def build_and_cache_morning_newsletter(post_date: date):
    today_str = post_date.strftime("%Y-%m-%d")
    yesterday_str = (post_date - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_str = (post_date + timedelta(days=1)).strftime("%Y-%m-%d")

    icons = {
        'inventory': '📦',
        'cleaning': '✨',
        'training': '🎓',
        'birthday': '🎂',
        'general': '⚠️',
        'supplier_order': '🛒'
    }

    with get_connection() as conn:
        cursor = conn.cursor()

        # Получаем все активные рестораны
        cursor.execute("SELECT id, name FROM restaurants WHERE is_active = 1")
        restaurants = [dict(row) for row in cursor.fetchall()]

        for rest in restaurants:
            rest_id = rest['id']
            rest_name = rest['name']

            # Получаем данные для рассылки
            report = get_shift_report_full(cursor, rest_id, yesterday_str)
            meeting_today = get_meeting(cursor, rest_id, today_str)
            events_today = get_day_events(cursor, rest_id, today_str)
            events_tomorrow = get_day_events(cursor, rest_id, tomorrow_str)
            staff_today = get_users_on_shift(cursor, rest_id)
            
            # Получатели
            directors = get_users(
                role=['director', 'deputy_director'],
                restaurant_id=rest_id,
                is_active=1
            )
            admins = get_users(
                position='admin',
                restaurant_id=rest_id,
                is_active=1
            )
            recipients = {u['id'] for u in directors + admins}

            # Формируем текст сообщения
            msg = f"☀️ <b>Доброе утро, {rest_name}!</b>\n Итоги за вчерашний день:\n\n"

            if report:
                msg += f"👤 Админ: <b>{report['admin_name']}</b>\n"
                msg += f"💰 Нал: <b>{report['cash_percentage']}%</b>\n"
                msg += f"🍹 Быстрые Напитки: <b>{report['fast_drinks_rating']}%</b>\n"
                

                if report['incidents_log'] and report['incidents_log'] != 'Нет проблем':
                    keys = [k.strip() for k in report['incidents_log'].split(',') if k.strip()]
                    problems = [TOPICS.get(k, k) for k in keys]
                    msg += "⚠️ Проблемы:\n"
                    for p in problems:
                        msg += f"• {p}\n"
                    
                if report.get('atmosphere_comment'):
                    msg += f"📝 Комментарий администратора:\n{report['atmosphere_comment']}\n"
            else:
                msg += "❌ Отчет за вчера не найден.\n"

            msg += "\n"

            topic = meeting_today['topic'] if meeting_today else "<i>не установлена</i>"
            msg += f"📝 <b>Тема сегодняшнего собрания:</b>\n<code>{topic}</code>\n"

            if events_today:
                msg += "\n📍 <b>События на сегодня:</b>\n"
                for ev in events_today:
                    icon = icons.get(ev['event_type'], '📍')
                    msg += f"{icon} {ev['description']}\n"

            if events_tomorrow:
                msg += "\n⏳ <b>Завтра планируется:</b>\n"
                for ev in events_tomorrow:
                    msg += f"• {ev['description']}\n"
                    
            if staff_today:
                msg += f"\n👥 <b>Сегодня на смене: {len(staff_today)}</b> сотрудников.\n"
                for user in staff_today:
                    msg += f"• {user['real_name']}\n"         
                
            # Сохраняем текст в кэш для каждого пользователя
            for user_id in recipients:
                save_newsletter_to_cache(
                    user_id=user_id,
                    post_date=today_str,
                    message_text=msg
                )
                

# Отправляет кэшированные утренние рассылки всем пользователям
async def send_cached_morning_newsletters():
    post_date_str = date.today().strftime("%Y-%m-%d")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, message_text FROM morning_posts_cache WHERE post_date = ?", (post_date_str,))
        rows = cursor.fetchall()

    for row in rows:
        user_id = row['user_id']
        text = row['message_text']

        with get_connection() as conn:
            cursor = conn.cursor()
            # Узнаем, к какому ресторану привязан юзер
            cursor.execute("SELECT restaurant_id FROM users WHERE id = ?", (user_id,))
            res = cursor.fetchone()
            rest_id = res['restaurant_id'] if res else None

            if rest_id:
                meeting_today = get_meeting(cursor, rest_id, post_date_str)
                kb = InlineKeyboardBuilder()
                
                if meeting_today and meeting_today.get('content'):
                    # Передаем минимум данных: тип:ресторан:дата
                    # user_id не передаем, он и так есть в callback.from_user.id
                    kb.row(InlineKeyboardButton(
                        text="📜 Сценарий собрания",
                        callback_data=f"view_script:{rest_id}:{post_date_str}"
                    ))

                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=kb.as_markup() if meeting_today else None,
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(0.05)
                except Exception as e:
                    print(f"Ошибка отправки {user_id}: {e}")

# Показывает полный контент собрания по кнопке "📜 Сценарий собрания".
@router.callback_query(F.data.startswith("view_script:"))
async def view_meeting_script_handler(callback: CallbackQuery):
    # Распаковываем только 3 значения
    _, rest_id_str, post_date_str = callback.data.split(":")
    rest_id = int(rest_id_str)

    with get_connection() as conn:
        cursor = conn.cursor()
        meeting = get_meeting(cursor, rest_id, post_date_str)

    if meeting and meeting.get("content"):
        kb = InlineKeyboardBuilder()
        # В кнопку "Назад" тоже передаем только самое важное
        kb.row(InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"back_news:{rest_id}:{post_date_str}"
        ))

        await callback.message.edit_text(
            text=f"📜 <b>Сценарий собрания:</b>\n\n{meeting['content']}",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Сценарий не найден", show_alert=True)


# Хэндлер для кнопки "Назад"
@router.callback_query(F.data.startswith("back_news:"))
async def back_to_newsletter_handler(callback: CallbackQuery):
    _, rest_id_str, post_date_str = callback.data.split(":")
    user_id = callback.from_user.id # Берем ID юзера прямо из телеграма
    
    text = get_cached_newsletter_text(user_id, post_date_str)
    
    if not text:
        await callback.answer("Ошибка: сообщение не найдено в кэше", show_alert=True)
        return

    # Рисуем кнопку сценария обратно
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="📜 Сценарий собрания",
        callback_data=f"view_script:{rest_id_str}:{post_date_str}"
    ))

    await callback.message.edit_text(
        text=text,
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    
async def daily_morning_newsletter_job():
    today = date.today()
    
    print(f"[{today}] Начинаю подготовку рассылки...")
    # 1. Сначала строим кэш
    build_and_cache_morning_newsletter(today)
    
    # 2. Сразу после этого запускаем отправку
    print(f"[{today}] Кэш готов, начинаю отправку...")
    await send_cached_morning_newsletters()
    print(f"[{today}] Рассылка завершена.")