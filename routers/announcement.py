from aiogram import Router, F
from typing import Union
from datetime import datetime, timedelta
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from db import create_announcement
from keyboards import POSITIONS_MAP_ANNO, time_selection_kb, days_of_week_kb, days_of_month_kb
from services import send_one_time_announcement

router = Router()

class AnnouncementFSM(StatesGroup):
    type = State()
    message = State()
    send_time = State()
    send_date = State()
    day_of_week = State()
    day_of_month = State()
    positions = State()
    confirm = State()


# Клавиатура для выбора позиций
def positions_kb(selected_positions: list):
    builder = InlineKeyboardBuilder()
    for slug, name in POSITIONS_MAP_ANNO.items():
        check = "✅ " if slug in selected_positions else ""
        builder.button(text=f"{check}{name}", callback_data=f"ann_pos:{slug}")
    builder.button(text="➡️ Далее", callback_data="ann_pos_done")
    builder.adjust(1)
    return builder.as_markup()

# Клавиатура для выбора типа объявления
def announcement_type_kb():
    kb = InlineKeyboardBuilder()

    kb.add(InlineKeyboardButton(text="📌 Разовая", callback_data="ann_type:one_time"),
        InlineKeyboardButton(text="🔁 Ежедневная", callback_data="ann_type:daily"),
        InlineKeyboardButton(text="📆 Еженедельная", callback_data="ann_type:weekly"),
        InlineKeyboardButton(text="🗓 Ежемесячная", callback_data="ann_type:monthly"),)
    kb.adjust(2)
    return kb.as_markup()



# ===== ИНИЦИАЛИЗАЦИЯ ТАБЛИЦЫ ОБЪЯВЛЕНИЙ =====  
# Выбор типа рассылки

@router.callback_query(F.data == "adm_make_announcement")
async def start_announcement(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 Создание объявления\n\nВыбери тип рассылки:",
        reply_markup=announcement_type_kb()
    )
    await state.set_state(AnnouncementFSM.type)
    await callback.answer()


@router.callback_query(F.data.startswith("ann_type"), AnnouncementFSM.type)
async def set_type(call: CallbackQuery, state: FSMContext):
    ann_type = call.data.split(":")[1]
    await state.update_data(type=ann_type, positions=[])
    await call.message.edit_text(
        "👥 Выбери должности для рассылки:", 
        reply_markup=positions_kb([])
    )
    await state.set_state(AnnouncementFSM.positions)
    await call.answer()
    

# Мультивыбор должностей
@router.callback_query(F.data.startswith("ann_pos:"), AnnouncementFSM.positions)
async def toggle_position(call: CallbackQuery, state: FSMContext):
    pos = call.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("positions", [])

    if pos in selected:
        selected.remove(pos)
    else:
        selected.append(pos)

    await state.update_data(positions=selected)
    await call.message.edit_reply_markup(reply_markup=positions_kb(selected))
    await call.answer()


# 3. Переход к тексту после выбора должностей
@router.callback_query(F.data == "ann_pos_done", AnnouncementFSM.positions)
async def positions_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("positions"):
        return await call.answer("⚠️ Выбери хотя бы одну должность!", show_alert=True)

    await call.message.edit_text("✏️ Введи текст сообщения:")
    await state.set_state(AnnouncementFSM.message)
    await call.answer()

# 4. Текст получен
@router.message(AnnouncementFSM.message)
async def set_message(message: Message, state: FSMContext, bot=None):
    # Сохраняем текст в state
    await state.update_data(message=message.text)

    # Получаем данные **после обновления**
    data = await state.get_data()
    ann_type = data.get("type")
    positions = data.get("positions", [])

    if ann_type == "one_time":
        restaurant_id = 1  # <-- тут реально нужно взять restaurant_id из state или пользователя
        await send_one_time_announcement(
            bot=bot,
            restaurant_id=restaurant_id,
            message=message.text,  # используем **message.text**, а не data["message"]
            positions=positions
        )
        await message.answer("✅ Сообщение отправлено.")
        await state.clear()
    else:
        # Для остальных типов идем на выбор времени
        await message.answer("⏰ Выбери время отправки:", reply_markup=time_selection_kb())
        await state.set_state(AnnouncementFSM.send_time)

# 5. Время получено -> Логика по типам
@router.callback_query(F.data.startswith("ann_time:"), AnnouncementFSM.send_time)
async def set_time(call: CallbackQuery, state: FSMContext):
    hour = call.data.split(":")[1]
    await state.update_data(send_time=f"{hour.zfill(2)}:00")

    data = await state.get_data()
    ann_type = data.get("type")

    if ann_type == "daily":
        await show_confirm(call, state)
    elif ann_type == "weekly":
        await call.message.edit_text("📅 Выбери день недели:", reply_markup=days_of_week_kb())
        await state.set_state(AnnouncementFSM.day_of_week)
    elif ann_type == "monthly":
        await call.message.edit_text("📅 Выбери число месяца:", reply_markup=days_of_month_kb())
        await state.set_state(AnnouncementFSM.day_of_month)

# 6. Обработка дат/дней
@router.callback_query(
    F.data.startswith("ann_day"), 
    AnnouncementFSM.day_of_week, 
    AnnouncementFSM.day_of_month
)
async def set_days(call: CallbackQuery, state: FSMContext):
    val = int(call.data.split(":")[1])
    if "dayw" in call.data:
        await state.update_data(day_of_week=val)
    else:
        await state.update_data(day_of_month=val)
    await show_confirm(call, state)

@router.message(AnnouncementFSM.send_date)
async def set_date(message: Message, state: FSMContext):
    await state.update_data(send_date=message.text)
    await show_confirm(message, state)

# 7. Предпросмотр и подтверждение
async def show_confirm(event: Union[Message, CallbackQuery], state: FSMContext):
    data = await state.get_data()
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="ann_final_confirm")
    kb.button(text="❌ Отмена", callback_data="ann_cancel")

    pos_names = ", ".join([POSITIONS_MAP_ANNO[p] for p in data['positions']])
    text = (
        f"📋 **ПРЕДПРОСМОТР**\n\n"
        f"Тип: {data['type']}\n"
        f"Должности: {pos_names}\n"
        f"Время: {data.get('send_time', '—')}\n"
        f"Текст: {data['message']}"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.set_state(AnnouncementFSM.confirm)

# 8. Сохранение
@router.callback_query(F.data == "ann_final_confirm", AnnouncementFSM.confirm)
async def save_to_db(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    roles = ["deputy_director", "director"]
    rest_id = 1  #ДОБАВИТЬ ЛОГИКУ ПОЛУЧЕНИЯ restaurant_id
        
    create_announcement(
    created_by=call.from_user.id,
    restaurant_id=rest_id,
    message=data.get("message"),
    type=data.get("type"),
    roles=roles,
    positions=data.get("positions"),
    send_time=data.get("send_time"),
    send_date=data.get("send_date"),
    day_of_week=data.get("day_of_week"),
    day_of_month=data.get("day_of_month"),
)

    await call.message.edit_text("✅ Рассылка сохранена и будет отправлена по расписанию.")
    await state.clear()