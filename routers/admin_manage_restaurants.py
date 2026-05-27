from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import (
    add_restaurant, get_all_restaurants, get_restaurant_by_id, delete_restaurant, update_restaurant,
    assign_user_to_restaurant, update_user_role, get_users )
from permissions import is_owner
from loader import bot
from keyboards import cancel_kb
import traceback

router = Router()


# =========================
# FSM
# =========================

class RestaurantFSM(StatesGroup):
    waiting_for_name = State()
    waiting_for_new_name = State()
    waiting_for_director_id = State()


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

def owner_guard(callback: CallbackQuery) -> bool:
    if not is_owner(callback.from_user.id):
        callback.answer("⛔ Только владелец", show_alert=True)
        return False
    return True





# =========================
# ГЛАВНОЕ МЕНЮ РЕСТОРАНОВ
# =========================

@router.callback_query(F.data == "adm_section_restaurants")
async def restaurants_menu(callback: CallbackQuery):
    if not owner_guard(callback):
        return

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 Список ресторанов", callback_data="rest_list"))
    kb.row(InlineKeyboardButton(text="➕ Добавить ресторан", callback_data="rest_create"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_main"))

    await callback.message.edit_text(
        "🏬 <b>Управление ресторанами</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# СОЗДАНИЕ
# =========================

@router.callback_query(F.data == "rest_create")
async def rest_create_start(callback: CallbackQuery, state: FSMContext):
    if not owner_guard(callback):
        return

    await state.set_state(RestaurantFSM.waiting_for_name)
    await callback.message.answer(
        "Введите название ресторана:",
        reply_markup=cancel_kb("adm_section_restaurants")
    )
    await callback.answer()


@router.message(RestaurantFSM.waiting_for_name)
async def rest_create_finish(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return

    try:
        rest_id = add_restaurant(name)
        await message.answer(f"✅ Ресторан «{name}» создан (ID {rest_id})")
    except Exception:
        print(traceback.format_exc())
        await message.answer("❌ Ошибка при создании ресторана.")
    finally:
        await state.clear()


# =========================
# СПИСОК
# =========================

@router.callback_query(F.data == "rest_list")
async def rest_list(callback: CallbackQuery):
    if not owner_guard(callback):
        return

    rests = get_all_restaurants()
    if not rests:
        await callback.answer("Ресторанов пока нет", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for r in rests:
        kb.row(
            InlineKeyboardButton(
                text=r["name"],
                callback_data=f"rest_detail_{r['id']}"
            )
        )
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_section_restaurants"))

    await callback.message.edit_text("Выберите ресторан:", reply_markup=kb.as_markup())
    await callback.answer()


# =========================
# ДЕТАЛИ
# =========================

@router.callback_query(F.data.startswith("rest_detail_"))
async def rest_detail(callback: CallbackQuery):
    if not owner_guard(callback):
        return

    rest_id = int(callback.data.split("_")[-1])
    rest = get_restaurant_by_id(rest_id)
    if not rest:
        await callback.answer("Ресторан не найден", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👤 Назначить директора", callback_data=f"rest_set_director_{rest_id}"))
    kb.row(InlineKeyboardButton(text="❌ Снять директора", callback_data=f"rest_remove_director_{rest_id}"))
    kb.row(InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rest_rename_{rest_id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"rest_delete_{rest_id}"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="rest_list"))

    await callback.message.edit_text(
        f"<b>{rest['name']}</b>\nID: {rest_id}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# ПЕРЕИМЕНОВАНИЕ
# =========================

@router.callback_query(F.data.startswith("rest_rename_"))
async def rest_rename_start(callback: CallbackQuery, state: FSMContext):
    if not owner_guard(callback):
        return

    rest_id = int(callback.data.split("_")[-1])
    await state.update_data(rest_id=rest_id)
    await state.set_state(RestaurantFSM.waiting_for_new_name)

    await callback.message.answer(
        "Введите новое название ресторана:",
        reply_markup=cancel_kb("rest_list")
    )
    await callback.answer()


@router.message(RestaurantFSM.waiting_for_new_name)
async def rest_rename_finish(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    data = await state.get_data()
    rest_id = data.get("rest_id")

    if not name:
        await message.answer("Название не может быть пустым.")
        return

    try:
        update_restaurant(rest_id, name)
        await message.answer("✅ Название обновлено")
    except Exception:
        print(traceback.format_exc())
        await message.answer("❌ Ошибка при обновлении")
    finally:
        await state.clear()


# =========================
# УДАЛЕНИЕ
# =========================

@router.callback_query(F.data.startswith("rest_delete_"))
async def rest_delete(callback: CallbackQuery):
    if not owner_guard(callback):
        return

    rest_id = int(callback.data.split("_")[-1])
    delete_restaurant(rest_id)

    await callback.message.edit_text("🗑 Ресторан удалён")
    await callback.answer()


# =========================
# ДИРЕКТОР
# =========================

@router.callback_query(F.data.startswith("rest_set_director_"))
async def set_director_start(callback: CallbackQuery, state: FSMContext):
    if not owner_guard(callback):
        return

    rest_id = int(callback.data.split("_")[-1])
    await state.update_data(rest_id=rest_id)
    await state.set_state(RestaurantFSM.waiting_for_director_id)

    await callback.message.answer(
        "Введите Telegram ID директора:",
        reply_markup=cancel_kb("rest_list")
    )
    await callback.answer()


@router.message(RestaurantFSM.waiting_for_director_id)
async def set_director_finish(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Нужен числовой Telegram ID.")
        return

    user_id = int(message.text)
    data = await state.get_data()
    rest_id = data.get("rest_id")


    try:
        restaurant = get_restaurant_by_id(rest_id)
        rest_name = restaurant['name'] if restaurant else f"ID {rest_id}"
        update_user_role(user_id, "director")
        assign_user_to_restaurant(user_id, rest_id)
        
        await message.answer(f"✅ Директор назначен в ресторан <b>«{rest_name}»</b>", parse_mode="HTML")
        
        try:
            await bot.send_message(
                user_id, 
                f"🌟 Поздравляем! Вы назначены директором ресторана <b>«{rest_name}»</b>.\n"
                f"Перезапустите бота (команда /start), чтобы обновить меню управления.",
                parse_mode="HTML"
            )
        except Exception:
            await message.answer("⚠️ Директор назначен в БД, но не смог получить сообщение (возможно, бот заблокирован).")
            
    except Exception:
        print(traceback.format_exc())
        await message.answer("❌ Ошибка при назначении")
    finally:
        await state.clear()

# Удалить директора
@router.callback_query(F.data.startswith("rest_remove_director_"))
async def remove_director(callback: CallbackQuery):
    if not owner_guard(callback):
        return

    rest_id = int(callback.data.split("_")[-1])
    

    users = get_users(role="director", restaurant_id=rest_id)
    
    # Проверяем, что список не пуст
    if not users:
        await callback.answer("Директор не найден", show_alert=True)
        return

    user = users[0]
    update_user_role(user["id"], "user")
    assign_user_to_restaurant(user["id"], None)

    await callback.message.answer("❌ Директор снят")
    await callback.answer()
