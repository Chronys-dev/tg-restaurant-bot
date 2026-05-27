from aiogram import Router, F, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from db import (get_user, get_monthly_goal, get_month_events, get_meeting, set_monthly_goal, 
    set_meeting, add_special_event, get_day_events, get_connection, delete_event, get_day_events_with_ids)
from keyboards import mailing_manage_kb, get_calendar_markup, cancel_kb, CalendarCallback
from permissions import is_owner, is_director_or_deputy
from datetime import datetime

router = Router()


class CalendarStates(StatesGroup):
    waiting_for_meeting_topic = State()   # Ждем тему собрания
    waiting_for_meeting_content = State() # Ждем детали собрания
    waiting_for_event_type = State()    # Выбор типа (инвентаризация и т.д.)
    waiting_for_event_desc = State()     # Ждем описание инвентаризации/уборки
    waiting_for_month_goal = State()     # Ждем цель месяца


# Вход в управление рассылкой
@router.message(F.text == "📢 События и календарь")
async def cmd_mailing_section(message: types.Message):        
    await message.answer(
        "⚙️ <b>Раздел Событий и календаря</b>\n\n"
        "Выберите нужное действие:",
        reply_markup=mailing_manage_kb(),
        parse_mode="HTML"
    )

# ловлю кнопку "назад"
@router.callback_query(F.data == "back_to_mailing_section")
async def back_to_mailing_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ <b>Раздел Событий и календаря</b>\n\n"
        "Выберите нужное действие:",
        reply_markup=mailing_manage_kb(),
        parse_mode="HTML"
    )
@router.callback_query(F.data.startswith("day_"))
async def back_to_day_from_string(callback: types.CallbackQuery):
    date_str = callback.data.replace("day_", "")
    await open_day_card(callback, date_str, callback.from_user.id)



# Вход в календарь
@router.callback_query(F.data == "adm_manage_calendar")
async def open_calendar_cmd(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    user = get_user(uid)
    
    if not user:
        await callback.answer("❌ Профиль не найден", show_alert=True)
        return

    rest_id = user.get("restaurant_id")
    is_admin = is_owner(uid) or is_director_or_deputy(uid)
    
    # Берем текущую дату
    now = datetime.now()
    
    # 1. Открываем соединение для получения цели
    with get_connection() as conn:
        cursor = conn.cursor()
        goal = get_monthly_goal(cursor, rest_id, now.year, now.month)
    
    # 2. Получаем иконки событий
    events = get_month_events(rest_id, now.year, now.month)
    
    # Генерируем клавиатуру и текст
    header_text, kb = get_calendar_markup(
        rest_id, 
        now.year, 
        now.month, 
        goal, 
        events, 
        can_edit=is_admin
    )
    
    try:
        await callback.message.edit_text(
            header_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        # Если сообщение не изменилось (например, повторный клик), просто закрываем уведомление
        await callback.answer()

# Обработчик навигации
@router.callback_query(CalendarCallback.filter(F.action.in_(["prev", "next"])))
async def process_calendar_nav(callback: types.CallbackQuery, callback_data: CalendarCallback):
    uid = callback.from_user.id
    user = get_user(uid)
    
    if not user:
        await callback.answer("❌ Ошибка профиля")
        return

    rest_id = user.get("restaurant_id")
    is_admin = is_owner(uid) or is_director_or_deputy(uid)
    
    m, y = callback_data.month, callback_data.year
    
    # Логика переключения месяца
    if callback_data.action == "next":
        m += 1
        if m > 12: 
            m = 1
            y += 1
    else:
        m -= 1
        if m < 1: 
            m = 12
            y -= 1
        
    # --- РАБОТА С БД ---
    # Получаем цель через курсор
    with get_connection() as conn:
        cursor = conn.cursor()
        goal = get_monthly_goal(cursor, rest_id, y, m)
    
    # 2. Получаем иконки
    events = get_month_events(rest_id, y, m)
    
    # Генерируем новый интерфейс
    header_text, kb = get_calendar_markup(rest_id, y, m, goal, events, can_edit=is_admin)
    
    try:
        await callback.message.edit_text(
            header_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception:
        # Игнорируем ошибку "message is not modified", если пользователь слишком быстро кликает
        await callback.answer()

# Нажатие на день
@router.callback_query(CalendarCallback.filter(F.action == "day"))
async def handle_day_click(callback: types.CallbackQuery, callback_data: CalendarCallback):
    date_str = f"{callback_data.year}-{callback_data.month:02d}-{callback_data.day:02d}"

    await open_day_card(callback, date_str, callback.from_user.id)

async def open_day_card(event: types.Message | types.CallbackQuery, date_str: str, uid: int):

    user = get_user(uid)
    if not user:
        # Отправляем сообщение об ошибке, если пользователя нет
        if isinstance(event, types.CallbackQuery):
            await event.answer("❌ Профиль не найден.")
            await event.message.edit_text("❌ Ошибка: пользователь не идентифицирован.")
        return

    rest_id = user.get("restaurant_id")

    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем данные из БД
        meeting = get_meeting(cursor, rest_id, date_str)
        day_events = get_day_events(cursor, rest_id, date_str) 
        text = f"📅 <b>Карточка дня: {date_str}</b>\n\n"
        
        # Тема собрания
        topic = meeting['topic'] if meeting else "<i>не заполнена</i>"
        text += f"📝 <b>Тема:</b> {topic}\n\n"

        if day_events:
            text += "<b>События дня:</b>\n"
            icons = {'inventory': '📦', 'cleaning': '✨', 'training': '🎓', 'birthday': '🎂', 'general': '⚠️'}
            for ev in day_events:
                icon = icons.get(ev['event_type'], '📍')
                text += f"{icon} {ev['description']}\n"
        else:
            text += "💎 Спец. событий не запланировано.\n"

        builder = InlineKeyboardBuilder()
        

        # Кнопка "Подробности собрания" (только если есть сценарий)
        if meeting and meeting.get('content'):
            builder.row(InlineKeyboardButton(text="📜 Подробности собрания", callback_data=f"view_content_{date_str}"))

        # ПРОВЕРКА ПРАВ: Кнопки редактирования только для руководства
        if is_owner(uid) or (user and user.get("role") in ["director", "deputy_director"]):
            # Первая строка: работа с темой и сценарием
            builder.row(
                InlineKeyboardButton(text="✏️ Тема", callback_data=f"edit_meet_{date_str}"),
                InlineKeyboardButton(text="📜 Сценарий", callback_data=f"edit_cont_{date_str}")
            )
            # Вторая строка: добавление событий
        builder.row(
            InlineKeyboardButton(text="📦 Добавить событие", callback_data=f"add_event_{date_str}"),
            InlineKeyboardButton(text="🗑 Удалить событие", callback_data=f"del_ev_list_{date_str}")
            )
        
        # Кнопка назад доступна всем
        builder.row(InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="adm_manage_calendar"))


        # Отправка/редактирование сообщения
        try:
            if isinstance(event, types.Message):
                await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
            else:
                await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception:
            if isinstance(event, types.CallbackQuery):
                await event.answer("Сообщение не изменено.")


# Вывод подробностей (Сценария)
@router.callback_query(F.data.startswith("view_content_"))
async def view_meeting_content(callback: types.CallbackQuery):
    date_str = callback.data.replace("view_content_", "")
    uid = callback.from_user.id
    
    user = get_user(uid)
    if not user:
        return await callback.answer("Ошибка профиля", show_alert=True)
        
    rest_id = user['restaurant_id']

    # Открываем соединение для получения данных
    with get_connection() as conn:
        cursor = conn.cursor()
        meeting = get_meeting(cursor, rest_id, date_str)
    
    if not meeting or not meeting.get('content'):
        return await callback.answer("Сценарий не заполнен", show_alert=True)
        
    text = f"📜 <b>Сценарий собрания на {date_str}</b>\n\n{meeting['content']}"
    
    builder = InlineKeyboardBuilder()
    # Кнопка возврата к карточке дня
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"day_{date_str}"))
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.answer()


# Редактирование цели месяца
@router.callback_query(CalendarCallback.filter(F.action == "set_goal"))
async def start_set_goal(callback: types.CallbackQuery, callback_data: CalendarCallback, state: FSMContext):
    # Проверяем права еще раз для безопасности
    if not (is_owner(callback.from_user.id) or is_director_or_deputy(callback.from_user.id)):
        await callback.answer("⛔ У вас нет прав", show_alert=True)
        return

    # Сохраняем год и месяц, для которых ставим цель
    await state.update_data(goal_year=callback_data.year, goal_month=callback_data.month)    
    await state.set_state(CalendarStates.waiting_for_month_goal)
    
    # Месяцы для текста
    m_names = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
    month_name = m_names[callback_data.month - 1]

    await callback.message.answer(
        f"🎯 <b>Установка цели на {month_name} {callback_data.year}</b>\n\n"
        "Введите текст цели (одним сообщением). Например:\n"
        "<i>«Поднять выручку по бару на 10% и сократить списания»</i>",
        reply_markup=cancel_kb(back_cb="adm_manage_calendar"),
        parse_mode="HTML"
    )
    await callback.answer()

# Сохранение и автоматический возврат в календарь
@router.message(CalendarStates.waiting_for_month_goal)
async def save_monthly_goal_text(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден.")
        return
        
    rest_id = user.get("restaurant_id")
    
    # Получаем год и месяц из состояния FSM
    data = await state.get_data()
    year = data.get("goal_year")
    month = data.get("goal_month")
    
    # Если данные в FSM потерялись берем текущие
    if not year or not month:
        now = datetime.now()
        year, month = now.year, now.month
    
    new_goal_text = message.text.strip()

    # --- РАБОТА С БД ---
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Сохраняем новую цель (передаем 5 аргументов)
        set_monthly_goal(cursor, rest_id, year, month, new_goal_text)
        conn.commit()
        
        # Сразу получаем актуальную цель из базы для отрисовки
        goal = get_monthly_goal(cursor, rest_id, year, month)
    
    # Очищаем состояние после успешного сохранения
    await state.clear()
    
    # Получаем иконки событий 
    events = get_month_events(rest_id, year, month)
    
    # Подготавливаем данные для интерфейса
    is_admin = is_owner(uid) or is_director_or_deputy(uid)
    header_text, kb = get_calendar_markup(rest_id, year, month, goal, events, can_edit=is_admin)
    
    # Отправляем подтверждение и новый календарь
    await message.answer("✅ Цель сохранена!")
    await message.answer(header_text, reply_markup=kb, parse_mode="HTML")


# Нажали "✏️ Тема"
@router.callback_query(F.data.startswith("edit_meet_"))
async def start_edit_topic(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("edit_meet_", "")
    await state.update_data(edit_date=date_str)
    await state.set_state(CalendarStates.waiting_for_meeting_topic)
    
    await callback.message.answer(
        f"✍️ <b>Введите ТЕМУ собрания на {date_str}:</b>\n"
        "Краткий заголовок (например: <i>Правило последней спины</i>)",
        reply_markup=cancel_kb(back_cb="adm_manage_calendar"),
        parse_mode="HTML"
    )
    await callback.answer()

# Нажали "📜 Сценарий"
@router.callback_query(F.data.startswith("edit_cont_"))
async def start_edit_content(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("edit_cont_", "")
    await state.update_data(edit_date=date_str)
    await state.set_state(CalendarStates.waiting_for_meeting_content)
    
    await callback.message.answer(
        f"✍️ <b>Введите СЦЕНАРИЙ собрания на {date_str}:</b>\n"
        "Подробный план, задачи и фокусы дня.",
        reply_markup=cancel_kb(back_cb="adm_manage_calendar"),
        parse_mode="HTML"
    )
    await callback.answer()

# Сохранение ТЕМЫ
@router.message(CalendarStates.waiting_for_meeting_topic)
async def save_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    date_str = data['edit_date']
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден.")
        return
        
    rest_id = user.get("restaurant_id")

    # Открываем соединение
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Получаем текущие данные
            current = get_meeting(cursor, rest_id, date_str)
            content = current['content'] if current else None

            set_meeting(cursor, rest_id, date_str, message.text, content)
            conn.commit()
            
        except Exception as e:
            await message.answer(f"❌ Ошибка при сохранении в БД: {e}")
            return
    
    await message.answer(f"✅ Тема на {date_str} сохранена!")
    await state.clear()
    
    # Возвращаем пользователя в карточку дня
    await open_day_card(message, date_str, uid)

# Сохранение СЦЕНАРИЯ
@router.message(CalendarStates.waiting_for_meeting_content)
async def save_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    date_str = data['edit_date']
    uid = message.from_user.id
    
    user = get_user(uid)
    if not user:
        await message.answer("❌ Ошибка: профиль не найден.")
        return
        
    rest_id = user.get("restaurant_id")

    # Открываем ОДНО соединение для чтения и последующей записи
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # 1. Получаем текущие данные
            current = get_meeting(cursor, rest_id, date_str)
            
            # Если запись уже есть, берем старую тему, иначе ставим заглушку
            topic = current['topic'] if current else "Без темы"
            
            # 2. Сохраняем сценарий
            set_meeting(cursor, rest_id, date_str, topic, message.text)
            
            # 3. Фиксируем изменения
            conn.commit()
            
            await message.answer(f"✅ Сценарий на {date_str} сохранен!")
            
        except Exception as e:
            await message.answer(f"❌ Ошибка при сохранении сценария: {e}")
            return # Прерываем, если база выдала ошибку
    
    await state.clear()
    # Возвращаемся к карточке дня
    await open_day_card(message, date_str, uid)

# Обработка возврата
@router.callback_query(F.data.startswith("open_day_"))
async def back_to_day_card(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    date_str = callback.data.replace("open_day_", "")
    await open_day_card(callback, date_str, callback.from_user.id)
   
# Добавить событие
@router.callback_query(F.data.startswith("add_event_"))
async def start_add_event(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("add_event_", "")
    await state.update_data(edit_date=date_str)
    
    builder = InlineKeyboardBuilder()
    # Маппинг для кнопок
    types_map = {
        "inventory": "📦 Инвентаризация",
        "cleaning": "✨ Генуборка",
        "training": "🎓 Обучение",
        "birthday": "🎂 День рождения",
        "general": "⚠️ Другое",
        "supplier_order": "🛒 Заказ"
    }
    
    for k, v in types_map.items():
        builder.row(InlineKeyboardButton(text=v, callback_data=f"evtype_{k}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"open_day_{date_str}"))
    
    await state.set_state(CalendarStates.waiting_for_event_type)
    await callback.message.edit_text(
        f"📅 <b>Добавление события на {date_str}</b>\nВыберите категорию:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    
# выбор типа и переход к описанию
@router.callback_query(F.data.startswith("evtype_"), CalendarStates.waiting_for_event_type)
async def process_event_type(callback: types.CallbackQuery, state: FSMContext):
    event_type = callback.data.replace("evtype_", "")
    await state.update_data(selected_type=event_type)
    
    data = await state.get_data()
    date_str = data['edit_date']
    
    await state.set_state(CalendarStates.waiting_for_event_desc)
    await callback.message.edit_text(
        f"✍️ <b>Введите описание для события на {date_str}:</b>\n"
        f"Например: <i>'Инвентаризация алкоголя'</i>",
        reply_markup=cancel_kb(back_cb=f"add_event_{date_str}"),
        parse_mode="HTML"
    )

# сохранение описания в БД
@router.message(CalendarStates.waiting_for_event_desc)
async def save_special_event(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        await message.answer("❌ Ошибка: профиль не найден.")
        return
        
    rest_id = user.get("restaurant_id")
    
    # Достаем данные, накопленные в FSM
    data = await state.get_data()
    date_str = data.get('edit_date')
    event_type = data.get('selected_type')
    
    if not date_str or not event_type:
        await message.answer("❌ Ошибка данных. Попробуйте добавить событие заново.")
        await state.clear()
        return

    # --- РАБОТА С БД ---
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Передаем 5 аргументов: cursor, rest_id, дата, тип, описание
            add_special_event(
                cursor=cursor, 
                restaurant_id=rest_id, 
                date=date_str, 
                event_type=event_type, 
                description=message.text.strip()
            )
            
            # Фиксируем изменения в базе
            conn.commit()
            
        await message.answer(f"✅ Событие на {date_str} успешно добавлено!")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при сохранении в базу: {e}")
        return

    # Очищаем состояние и возвращаемся в карточку дня
    await state.clear()
    await open_day_card(message, date_str, uid)

# Удалить событие
# Получаем список событий
@router.callback_query(F.data.startswith("del_ev_list_"))
async def list_events_for_delete(callback: types.CallbackQuery):
    date_str = callback.data.replace("del_ev_list_", "")
    uid = callback.from_user.id
    user = get_user(uid) # Получаем данные юзера, чтобы знать restaurant_id

    with get_connection() as conn:
        cursor = conn.cursor()
        events = get_day_events_with_ids(cursor, user["restaurant_id"], date_str)

    if not events:
        await callback.answer("На этот день нет событий", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    
    types_map = {
        "inventory": "📦", "cleaning": "✨", "training": "🎓", 
        "birthday": "🎂", "general": "⚠️", "supplier_order": "🛒 Заказ"
    }

    for ev in events:
        icon = types_map.get(ev['event_type'], "🔹")
        desc = ev['description'][:20] + "..." if len(ev['description']) > 20 else ev['description']
        builder.row(InlineKeyboardButton(
            text=f"❌ {icon} {desc}", 
            callback_data=f"confirm_del_ev_{ev['id']}_{date_str}"
        ))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"open_day_{date_str}"))

    await callback.message.edit_text(
        f"🗑 <b>Выберите событие для удаления на {date_str}:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# Окончательное удаление
@router.callback_query(F.data.startswith("confirm_del_ev_"))
async def process_delete_event(callback: types.CallbackQuery):
    # Извлекаем id и дату
    data_parts = callback.data.split("_")
    
    try:
        event_id = int(data_parts[3])
        date_str = data_parts[4]
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка структуры данных", show_alert=True)
        return
    
    uid = callback.from_user.id
    user = get_user(uid)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            delete_event(cursor, user["restaurant_id"], event_id)

        await callback.answer("✅ Событие удалено")        

        # Вызываем функцию отрисовки карточки
        await open_day_card(callback, date_str, uid)

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

