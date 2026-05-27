from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest   
from db import (
    get_users, get_user, create_user, activate_user, deactivate_user, get_restaurant_by_id, remove_user_from_system, 
    assign_user_to_restaurant, update_user_position, update_user_role, update_user_real_name)
from permissions import is_owner, is_director_or_deputy
from loader import bot
import traceback
from keyboards import cancel_kb, POSITIONS_MAP, ROLES_MAP
from typing import Union

router = Router()

# ================= FSM =================
class StaffStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_real_name = State()
    edit_real_name = State()



# ================= МЕНЮ УПРАВЛЕНИЯ ПЕРСОНАЛОМ =================
# Общая функция для инлайн-клавиатуры управления персоналом
def get_staff_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Список персонала", callback_data="staff_list"))
    builder.row(InlineKeyboardButton(text="🧑 Авторизовать по ID", callback_data="staff_authorize"))
    return builder.as_markup()

# Обработка нажатия ПЕРВОЙ реплай-кнопки
@router.message(F.text == "🧑 Управление персоналом")
async def admin_staff_menu(message: Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not (is_owner(uid) or (user and user.get("role") in ["director", "deputy_director"])):
        return

    await message.answer(
        "🧑 <b>УПРАВЛЕНИЕ ПЕРСОНАЛОМ</b>\nВыберите действие:",
        reply_markup=get_staff_inline_kb(), 
        parse_mode="HTML"
    )

# Обработка нажатия инлайн-кнопки "НАЗАД"
@router.callback_query(F.data == "back_to_staff_main")
async def admin_staff_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧑 <b>УПРАВЛЕНИЕ ПЕРСОНАЛОМ</b>\nВыберите действие:",
        reply_markup=get_staff_inline_kb(),
        parse_mode="HTML"
    )

# ================= СПИСОК ПЕРСОНАЛА =================
@router.callback_query(F.data == "staff_list")
async def staff_list(callback: CallbackQuery):
    uid = callback.from_user.id
    author = get_user(uid)
    rest_id = author.get("restaurant_id") if author else None

    if not rest_id:
        return await callback.answer("Ресторан не найден", show_alert=True)

    users = get_users(restaurant_id=rest_id)
    builder = InlineKeyboardBuilder()

    for u in users:
        if u['id'] == uid: continue  # Пропускаем себя
        
        name = u.get('real_name') or u.get('full_name') or f"ID: {u['id']}"
        status = "✅" if u.get("is_active") == 1 else "⏳"
        
        # Кнопка ведет в карточку сотрудника
        builder.row(InlineKeyboardButton(
            text=f"{status} {name}", 
            callback_data=f"st_card_{u['id']}")
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_staff_main"))
    await callback.message.edit_text("📋 <b>Выберите сотрудника:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")



# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ОТОБРАЖЕНИЯ КАРТОЧКИ
async def display_staff_card(event: Union[CallbackQuery, Message], target_id: int):
    u = get_user(target_id)
    if not u:
        if isinstance(event, CallbackQuery):
            await event.answer("Сотрудник не найден")
        return

    # Формируем данные и текст
    raw_pos = u.get("position")
    human_pos = POSITIONS_MAP.get(raw_pos, raw_pos or "—")
    human_role = ROLES_MAP.get(u.get("role"), u.get("role") or "—")   
    status_text = "Активен ✅" if u.get("is_active") == 1 else "Деактивирован ❌"
    
    text = (
        f"👤 <b>Карточка сотрудника</b>\n\n"
        f"<b>ID:</b> <code>{u['id']}</code>\n"
        f"<b>ФИО:</b> {u.get('real_name') or '—'}\n"
        f"<b>TG Имя:</b> {u.get('full_name') or '—'}\n"
        f"<b>Роль:</b> {human_role}\n"
        f"<b>Должность:</b> {human_pos}\n"
        f"<b>Статус:</b> {status_text}"
    )

    # Формируем кнопки  ❌
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Изменить ФИО", callback_data=f"st_edit_name_{target_id}"))
    builder.row(InlineKeyboardButton(text="🛠 Изменить Должность", callback_data=f"st_edit_pos_{target_id}"))
    
    if u.get("is_active") == 1:
        builder.row(InlineKeyboardButton(text="🔒 Деактивировать", callback_data=f"st_status_0_{target_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🔓 Активировать", callback_data=f"st_status_1_{target_id}"))
        
    builder.row(InlineKeyboardButton(text="❌ Удалить пользователя", callback_data=f"st_remove_user_{target_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data="staff_list"))

    # Логика отправки/редактирования
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        # Если пришло текстовое сообщение, отправляем новое
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

# ================= КАРТОЧКА СОТРУДНИКА =================
@router.callback_query(F.data.startswith("st_card_"))
async def staff_card_handler(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[-1])
    await display_staff_card(callback, target_id)
    await callback.answer() # Отвечаем на колбэк здесь


# ================= ИЗМЕНЕНИЕ СТАТУСА АКТИВНОСТИ =================
@router.callback_query(F.data.startswith("st_status_"))
async def process_status_change(callback: CallbackQuery):
    _, _, action, target_id = callback.data.split("_", maxsplit=3)
    target_id = int(target_id)

    try:
        if action == "1":
            activate_user(target_id)
            await callback.answer("✅ Сотрудник активирован")
        else:
            deactivate_user(target_id)
            await callback.answer("🔒 Сотрудник деактивирован")
        await display_staff_card(callback, target_id) 

    except Exception:
        print(traceback.format_exc())
        await callback.answer("❌ Ошибка при изменении статуса", show_alert=True)


# ================= АВТОРИЗАЦИЯ ПО ID =================
@router.callback_query(F.data == "staff_authorize")
async def start_authorize_by_id(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_director_or_deputy(uid) and not is_owner(uid):
        await callback.answer("⛔ У вас нет прав для авторизации пользователей.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="staff_cancel"))

    await state.set_state(StaffStates.waiting_for_user_id)
    await callback.message.answer(
        "Отправьте Telegram ID пользователя (число), которого нужно авторизовать.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(StaffStates.waiting_for_user_id)
async def handle_authorize_id(message: Message, state: FSMContext):
    text = message.text.strip()

    # Проверка на числовой ID
    if not text.isdigit():
        await message.answer(
            "⚠️ Пожалуйста, пришлите корректный числовой Telegram ID.",
            reply_markup=cancel_kb("staff_cancel") # Кнопка отмены, если ошибся
        )
        return

    target_id = int(text)

    try:
        # Пытаемся получить данные пользователя из TG
        try:
            chat = await bot.get_chat(target_id)
            full_name = " ".join(filter(None, (chat.first_name, getattr(chat, 'last_name', None)))) 
            full_name = full_name or getattr(chat, 'username', None) or "Неизвестно"
        except Exception:
            full_name = "Неизвестно"

        await state.update_data(target_id=target_id, target_name=full_name)

        # Собираем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"staff_confirm_{target_id}"))
        builder.row(*cancel_kb("staff_cancel").inline_keyboard[0])

        await message.answer(
            f"👤 <b>Пользователь найден:</b>\n"
            f"Имя: <code>{full_name}</code>\n"
            f"ID: <code>{target_id}</code>\n\n"
            f"Подтверждаете авторизацию?",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error in handle_authorize_id: {e}")
        await message.answer("❌ Ошибка при поиске пользователя. Проверьте ID.")
        await state.clear()


@router.callback_query(F.data == "staff_cancel")
async def staff_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        try:
            await callback.message.edit_text("Отмена авторизации.", reply_markup=None)
        except Exception:
            pass
        await callback.answer("Отменено", show_alert=True)
    except Exception:
        print(traceback.format_exc())
        await callback.answer("Ошибка при отмене", show_alert=True)


# ================= ПОДТВЕРЖДЕНИЕ АВТОРИЗАЦИИ =================
@router.callback_query(F.data.startswith("staff_confirm_"))
async def staff_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_director_or_deputy(uid) and not is_owner(uid):
        await callback.answer("⛔ У вас нет прав для авторизации пользователей.", show_alert=True)
        return

    try:
        target_id = int(callback.data.split("_")[2])
        data = await state.get_data()
        target_name = data.get("target_name") if data else None

        existing = get_user(target_id)
        if existing:
            activate_user(target_id)
            created_msg = f"✅ Пользователь с ID {target_id} ({target_name}) активирован."
        else:
            create_user(target_id, target_name or "Неизвестно", role="user")
            created_msg = f"✅ Пользователь с ID {target_id} ({target_name}) создан и активирован."

        await callback.message.edit_text(created_msg, reply_markup=None)

        # Назначаем ресторан сотруднику (если директор или зам)
        author = get_user(uid)
        if author and author.get("role") in ("director", "deputy_director"):
            rest_id = author.get("restaurant_id")
            restaurant = get_restaurant_by_id(rest_id) 
            rest_name = restaurant['name'] if restaurant else f"ID {rest_id}" #Получаем название ресторана
            
            if rest_id:
                assign_user_to_restaurant(target_id, rest_id)

                # Запрашиваем ФИО
                await state.update_data(target_id=target_id, target_rest_id=rest_id)
                await state.set_state(StaffStates.waiting_for_real_name)

                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="staff_cancel"))
                await callback.message.answer(
                    f"Пользователь назначен в ресторан <b>«{rest_name}»</b>. Пожалуйста, отправьте реальное имя (ФИО) пользователя.",
                    reply_markup=builder.as_markup()
                )

    except Exception:
        print(traceback.format_exc())
        await callback.answer("Ошибка при подтверждении авторизации.", show_alert=True)
        await state.clear()


# ================= ВВОД ФИО И ВЫБОР ДОЛЖНОСТИ =================
@router.message(StaffStates.waiting_for_real_name)
async def handle_real_name_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
  
    if len(text) < 2:
        await message.answer("⚠️ Пожалуйста, введите корректное ФИО (минимум 2 символа).")
        return

    data = await state.get_data()
    target_id = data.get("target_id")

    if not target_id:
        await message.answer("❌ Ошибка: пользователь не найден в памяти. Начните сначала.")
        await state.clear()
        return

    try:
        # Обновляем имя в БД
        update_user_real_name(target_id, text)
        
        # Генерируем кнопки должностей
        builder = InlineKeyboardBuilder()
        positions = [
            ("Официант", "waiter"),
            ("Повар", "cook"),
            ("Бармен", "bartender"),
            ("Админ ресторана", "admin"),
            ("Зам. директора", "deputy_director")
        ]
        
        for name, code in positions:
            builder.row(InlineKeyboardButton(
                text=name, 
                callback_data=f"staff_setpos_{target_id}_{code}")
            )

        builder.attach(InlineKeyboardBuilder.from_markup(cancel_kb("staff_cancel")))

        await message.answer(
            f"✅ ФИО установлено: <b>{text}</b>\n\n"
            f"Теперь выберите должность для сотрудника:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error updating real name: {e}")
        await message.answer("❌ Произошла техническая ошибка при сохранении имени.")
        await state.clear()


# ================= НАЗНАЧЕНИЕ ДОЛЖНОСТИ / РОЛИ =================
@router.callback_query(F.data.startswith("staff_setpos_"))
async def staff_setpos(callback: CallbackQuery):
    try:
        _, _, target_id, pos_code = callback.data.split("_", maxsplit=3)
        target_id = int(target_id)

        if pos_code == "deputy_director":
            # РОЛЬ
            update_user_role(target_id, "deputy_director")
            # ДОЛЖНОСТЬ всегда NULL
            update_user_position(target_id, None)

            msg_text = (
                f"✅ Пользователь <code>{target_id}</code> назначен "
                f"<b>заместителем директора</b>"
            )
            notify_text = (
                "🌟 Вас назначили <b>заместителем директора</b>. "
                "Перезапустите бота (/start) для обновления меню."
            )
        else:
            # Обычный сотрудник
            update_user_role(target_id, "user")
            update_user_position(target_id, pos_code)

            human_pos = POSITIONS_MAP.get(pos_code, pos_code)
            msg_text = (
                f"✅ Должность сотрудника <code>{target_id}</code> обновлена "
                f"на: <b>{human_pos}</b>"
            )
            notify_text = f"📋 Вам назначена должность: <b>{human_pos}</b>"

        await callback.message.edit_text(
            msg_text,
            reply_markup=cancel_kb("staff_list"),
            parse_mode="HTML"
        )

        try:
            await bot.send_message(target_id, notify_text, parse_mode="HTML")
        except Exception:
            pass

        await callback.answer("Готово")

    except Exception:
        print(traceback.format_exc())
        await callback.answer("❌ Ошибка при назначении должности", show_alert=True)


# --- Нажата кнопка "Изменить ФИО" в карточке ---
@router.callback_query(F.data.startswith("st_edit_name_"))
async def edit_staff_name_start(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[-1])
    
    await state.update_data(target_id=target_id)
    await state.set_state(StaffStates.edit_real_name)
    
    await callback.message.answer(
        f"📝 Введите новое ФИО для сотрудника <code>{target_id}</code>:",
        reply_markup=cancel_kb(f"st_card_{target_id}"), # Кнопка отмены вернет в карточку
        parse_mode="HTML"
    )
    await callback.answer()

# --- Обработка введенного текста ---
@router.message(StaffStates.edit_real_name)
async def handle_edit_real_name_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    
    if len(text) < 2:
        await message.answer("⚠️ ФИО слишком короткое. Введите корректные данные.")
        return

    data = await state.get_data()
    target_id = data.get("target_id")

    try:
        # Обновляем в БД
        update_user_real_name(target_id, text)
        await message.answer(f"✅ ФИО обновлено на: <b>{text}</b>", parse_mode="HTML")
        
        # Вызываем универсальную функцию карточки, передавая ей объект message и ID
        await display_staff_card(message, target_id=target_id)

    except Exception as e:
        print(f"Error: {e}")
        await message.answer("❌ Ошибка при сохранении.")
    
    await state.clear()

# --- Нажата кнопка "Изменить Должность" в карточке ---
@router.callback_query(F.data.startswith("st_edit_pos_"))
async def edit_staff_position_start(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[-1])
    
    builder = InlineKeyboardBuilder()
    # Собираем кнопки
    for code, name in POSITIONS_MAP.items():
        builder.row(InlineKeyboardButton(
            text=name, 
            callback_data=f"staff_edit_setpos_{target_id}_{code}")
        )

    # Добавляем кнопку возврата (отмены)
    builder.attach(InlineKeyboardBuilder.from_markup(cancel_kb(f"st_card_{target_id}")))

    await callback.message.edit_text(
        f"🛠 Выберите новую должность для <code>{target_id}</code>:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Обработка выбора новой должности ---
@router.callback_query(F.data.startswith("staff_edit_setpos_"))
async def process_set_position(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_", maxsplit=4)
        target_id = int(parts[3])
        pos_code = parts[4]

        # Логика обновления Роли и Должности
        if pos_code == "deputy_director":
            update_user_role(target_id, "deputy_director")
            update_user_position(target_id, None)
            notif = "🌟 Вас назначили <b>заместителем директора</b>."
        else:
            update_user_role(target_id, "user")
            update_user_position(target_id, pos_code)
            h_pos = POSITIONS_MAP.get(pos_code, pos_code)
            notif = f"📋 Вам назначена должность: <b>{h_pos}</b>"

        # Уведомляем сотрудника
        try:
            await bot.send_message(target_id, notif, parse_mode="HTML")
        except: pass
        
        await callback.answer("✅ Должность обновлена")

        # АВТОМАТИЧЕСКИЙ ВОЗВРАТ
        await display_staff_card(callback, target_id)

    except Exception:
        print(traceback.format_exc())
        await callback.answer("❌ Ошибка обновления", show_alert=True)

    finally:
        await state.clear()
        
# Удалить пользователя
@router.callback_query(F.data.startswith("st_remove_user_"))
async def remove_user_start(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[-1])

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ Да, удалить",
        callback_data=f"st_remove_ask_{target_id}"
    ))
    builder.attach(InlineKeyboardBuilder.from_markup(cancel_kb(f"st_card_{target_id}")))

    try:
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить сотрудника <code>{target_id}</code>?",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass
    await callback.answer()

# Подтверждение удаления
@router.callback_query(F.data.startswith("st_remove_ask_"))
async def confirm_remove_user(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[-1])

    try:
        remove_user_from_system(target_id)
        await callback.answer("✅ Пользователь удален")
        # Возвращаемся к списку сотрудников
        await staff_list(callback)
    except Exception as e:
        print(f"Error removing user: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)