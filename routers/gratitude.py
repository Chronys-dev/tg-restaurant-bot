from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards import THANKS_CATEGORIES, get_random_sticker
from db import get_user, get_users_on_shift, register_gratitude, get_connection, get_thanks_left
from loader import bot

router = Router()

class GratitudeStates(StatesGroup):
    choosing_colleague = State()
    choosing_category = State()
    
# --- ВЫБОР СОТРУДНИКА ДЛЯ БЛАГОДАРНОСТИ ---
@router.callback_query(F.data == "feedback_thanks")
async def gratitude_choose_colleague(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)

    if not user or not user.get("restaurant_id"):
        await callback.answer("Вы не привязаны к ресторану.", show_alert=True)
        return

    with get_connection() as conn:
        cursor = conn.cursor()

        # Получаем сотрудников на смене через cursor
        staff_today = get_users_on_shift(
            cursor=cursor,
            restaurant_id=user["restaurant_id"]
        )

    # Убираем самого пользователя
    staff_today = [
        u for u in staff_today
        if u["id"] != user["id"]
    ]

    if not staff_today:
        await callback.answer(
            "Сегодня на смене нет других сотрудников.",
            show_alert=True
        )
        return

    buttons = [
        InlineKeyboardButton(
            text=u["real_name"],
            callback_data=f"gratitude_to:{u['id']}"
        )
        for u in staff_today
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    )

    await state.set_state(GratitudeStates.choosing_colleague)

    await callback.message.edit_text(
        "✨ Кого вы хотите поблагодарить?",
        reply_markup=keyboard
    )
    await callback.answer()

# --- ОБРАБОТКА ВЫБОРА СОТРУДНИКА ---
@router.callback_query(
    GratitudeStates.choosing_colleague,
    F.data.startswith("gratitude_to:")
)
async def gratitude_colleague_selected(callback: CallbackQuery, state: FSMContext):
    to_user_id = int(callback.data.split(":")[1])

    # Сохраняем выбранного сотрудника в FSM
    await state.update_data(to_user_id=to_user_id)

    # Меняем состояние на выбор категории
    await state.set_state(GratitudeStates.choosing_category)

    # Подготавливаем кнопки для выбора категории
    buttons = [
        InlineKeyboardButton(
            text=label,
            callback_data=f"gratitude_cat:{key}"
        )
        for key, label in THANKS_CATEGORIES.items()
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)]
    )

    await callback.message.edit_text(
        "✨ За что вы хотите сказать спасибо?",
        reply_markup=keyboard
    )

    await callback.answer()
    
# --- ФИНАЛИЗАЦИЯ БЛАГОДАРНОСТИ ---
@router.callback_query(
    GratitudeStates.choosing_category,
    F.data.startswith("gratitude_cat:")
)
async def gratitude_finalize(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    from_user = get_user(callback.from_user.id)

    to_user_id = data["to_user_id"]
    category_key = callback.data.split(":")[1]
    category_label = THANKS_CATEGORIES.get(category_key)

    # ПОЛУЧАЕМ РАНДОМНЫЙ СТИКЕР
    category = "kudos"
    sticker_to_send = get_random_sticker(category)

    if not category_label:
        await callback.answer("Ошибка категории.", show_alert=True)
        return
    
    to_user = get_user(to_user_id)
    to_name = to_user["real_name"] if to_user else f"ID {to_user_id}"

    # Регистрируем благодарность
    success, error = register_gratitude(
        from_user_id=from_user["id"],
        to_user_id=to_user_id,
        category=category_key,
        restaurant_id=from_user["restaurant_id"]
    )

    if not success:
        await callback.answer(error or "Не удалось отправить спасибо.", show_alert=True)
        await state.clear()
        return

    thanks_left = get_thanks_left(from_user["id"])
    
    
    # Сообщение отправителю
    await callback.message.edit_text(
        f"🙏 <b>Спасибо отправлено!</b>\n\n"
        f"👤 Получатель: <b>{to_name}</b>\n"
        f"📌 Категория: <b>{category_label}</b>\n\n"
        f"✨ Осталось благодарностей на этой неделе: <b>{thanks_left}</b>"
    )

    # Сообщение получателю + стикер
    try:
        await bot.send_sticker(
            to_user_id,
            sticker=sticker_to_send
        )

        await bot.send_message(
            to_user_id,
            f"💛 Коллега сказал вам спасибо!\n\n"
            f"<b>{category_label}</b>"
        )
    except Exception:
        pass  # человек мог заблокировать бота

    await callback.answer()
    await state.clear()