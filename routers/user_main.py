from aiogram import Router, F, types
import traceback
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from services import get_user_achievements
from db import (get_user, get_recipes, get_thanks_left, get_total_received_thanks, 
    get_total_completed_quizzes, get_thanks_stats
)

from keyboards import (
    main_menu_kb, recipe_inline_kb, kitchen_menu_inline_kb, 
    bar_menu_inline_kb, sushi_menu_inline_kb, material_menu_inline_kb,
    build_recipes_kb, CATEGORY_MAP, THANKS_CATEGORIES
)
from permissions import is_owner
from config import OWNER_ID
from loader import bot


router = Router()

class StartStates(StatesGroup):
    waiting_authorization = State()
    main_menu = State()

class AdminAuthorizeStates(StatesGroup):
    waiting_for_user_id = State()

class FeedbackStates(StatesGroup):
    waiting_for_thanks_target = State()
    waiting_for_thanks_text = State()
    waiting_for_anon_text = State()

# ===== СТАРТ =====
@router.message(Command("start"))
async def start_handler(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    user = get_user(user_id)

    if is_owner(user_id) or (user and user["is_active"] == 1):
        await state.set_state(StartStates.main_menu)

        # Показываем имя: сначала из БД, иначе из профиля Telegram
        if user and user.get("full_name"):
            display_name = user.get("full_name")
        else:
            display_name = msg.from_user.first_name or getattr(msg.from_user, 'username', 'пользователь')

        await msg.answer(f"🌟 Добро пожаловать, {display_name}!", reply_markup=main_menu_kb(user_id))
    else:
        await state.set_state(StartStates.waiting_authorization)
        await msg.answer(
            f"Привет! Вы не авторизованы.\nID: <code>{user_id}</code>\n\nОтправьте этот ID директору.\nПосле авторизации вам откроется меню.",
            parse_mode="HTML"
        )

# ===== ГЛАВНЫЕ РАЗДЕЛЫ (Вызов Inline-меню через Message) =====

@router.message(F.text == "📖 Меню")
async def show_menu(message: Message):
    await message.answer("📂 <b>БАЗА РЕЦЕПТОВ</b>\nВыберите отдел:", 
                         reply_markup=recipe_inline_kb(), parse_mode="HTML")

@router.message(F.text == "📚 Учебные материалы")
async def show_materials(message: Message):
    await message.answer("📖 <b>УЧЕБНЫЙ ЦЕНТР</b>\nВыберите раздел:", 
                         reply_markup=material_menu_inline_kb(message.from_user.id), parse_mode="HTML")


# ===== Обратная связь =====
@router.message(F.text == "🗣️ Обратная связь")
async def feedback_menu(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✨ Сказать спасибо коллеге", callback_data="feedback_thanks"))
    builder.row(InlineKeyboardButton(text="📮 Коробка идей", callback_data="feedback_anon"))

    # дополнительная кнопка для админов ресторана (по должности)
    role = user.get("role")
    position = user.get("position")
    if role in ["director", "deputy_director"] or position == "admin":
        builder.row(InlineKeyboardButton(text="🚀 Закрытие смены", callback_data="feedback_close_shift"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"))
    await message.answer("🗣️ <b>ОБРАТНАЯ СВЯЗЬ</b>\nВыберите действие:", reply_markup=builder.as_markup(), parse_mode="HTML")

# Старт анонимного фидбэка
@router.callback_query(F.data == "feedback_anon")
async def feedback_anon_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_for_anon_text)
    await callback.message.answer(
        "💡 Напишите анонимное сообщение или предложение владельцу:"
    )
    await callback.answer()

# FSM: получение текста
@router.message(FeedbackStates.waiting_for_anon_text)
async def feedback_anon_text(message: Message, state: FSMContext):
    try:
        await bot.send_message(
            OWNER_ID,
            "📩 <b>Анонимное сообщение от сотрудника:</b>\n\n"
            f"{message.text}",
            parse_mode="HTML"
        )
    except Exception:
        print(traceback.format_exc())
        await message.answer(
            "Произошла ошибка при отправке сообщения. Попробуйте позже."
        )
        await state.clear()
        return

    await message.answer(
        "✅ Сообщение отправлено владельцу.\nСпасибо за вашу идею!"
    )
    await state.clear()

# Возврат в корень меню рецептов
@router.callback_query(F.data == "menu_root")
async def back_to_root(callback: CallbackQuery):
    await callback.message.edit_text("📂 <b>БАЗА РЕЦЕПТОВ</b>\nВыберите отдел:", 
                                     reply_markup=recipe_inline_kb(), parse_mode="HTML")
    await callback.answer()

# Переход в Горячий цех
@router.callback_query(F.data == "dept_kitchen")
async def show_kitchen_inline(callback: CallbackQuery):
    await callback.message.edit_text("🍳 <b>ГОРЯЧИЙ ЦЕХ</b>\nВыберите категорию:", 
                                     reply_markup=kitchen_menu_inline_kb(), parse_mode="HTML")
    await callback.answer()

# Переход в Бар
@router.callback_query(F.data == "dept_bar")
async def show_bar_inline(callback: CallbackQuery):
    await callback.message.edit_text("🍸 <b>БАР</b>\nВыберите категорию:", 
                                     reply_markup=bar_menu_inline_kb(), parse_mode="HTML")
    await callback.answer()

# Переход в Суши-бар
@router.callback_query(F.data == "dept_sushi")
async def show_sushi_inline(callback: CallbackQuery):
    await callback.message.edit_text("🍣 <b>СУШИ-БАР</b>\nВыберите категорию:", 
                                     reply_markup=sushi_menu_inline_kb(), parse_mode="HTML")
    await callback.answer()

# ===== ПОДКАТЕГОРИИ (Список блюд) =====

@router.callback_query(F.data.in_(CATEGORY_MAP.values()))
async def subcategory_handler(callback: types.CallbackQuery):

    category_code = callback.data

    recipes = get_recipes(category_code) 

    if recipes:
        # Определяем, куда должна вести кнопка "Назад"
        back_to = "menu_root"
        if category_code.startswith("kitchen_"): back_to = "dept_kitchen"
        elif category_code.startswith("bar_"): back_to = "dept_bar"
        elif category_code.startswith("sushi_"): back_to = "dept_sushi"
        elif category_code.startswith("new_"): back_to = "menu_root"

        # Название категории для заголовка (ищем ключ по значению в словаре)
        category_name = next((k for k, v in CATEGORY_MAP.items() if v == category_code), "Блюда")

        await callback.message.edit_text(
            f"{category_name}\n\n🍽️ <b>Выберите карточку блюда:</b>",
            reply_markup=build_recipes_kb(recipes, back_callback=back_to),
            parse_mode="HTML"
        )
    else:
        await callback.answer(f"В категории {category_code} пока нет рецептов 😔", show_alert=True)
    
    await callback.answer()
    
# Обработчик для кнопки закрытия
@router.callback_query(F.data == "close_menu")
async def close_menu_handler(callback: types.CallbackQuery):
    try:
        # Бот удаляет сообщение, в котором была нажата кнопка
        await callback.message.delete()
    except Exception:

        print(traceback.format_exc())
        await callback.message.edit_reply_markup(reply_markup=None)

    await callback.answer()
  
  
#===============================================================================
# ===== Личный кабинет =====
def build_profile_text(user: dict) -> str:
    name = user.get("real_name") or user.get("full_name") or "Без имени"
    role = user.get("role") or "Сотрудник"
    thanks_balance = get_thanks_left(user["id"])

    total_thanks = get_total_received_thanks(user["id"])
    quizzes_done = get_total_completed_quizzes(user["id"])

    return (
        "👤 <b>Личный кабинет</b>\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Роль: <b>{role}</b>\n"
        f"Спасибо на балансе: <b>{thanks_balance} 💛</b>\n\n"
        "За всё время:\n"
        f"• Получено спасибо: <b>{total_thanks}</b>\n"
        f"• Пройдено квизов: <b>{quizzes_done}</b>"
    )

# ===== Клавиатура ЛК =====
def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🧠 Квизы",callback_data="lk_quizzes")],
                        [InlineKeyboardButton(text="🏆 Ачивки",callback_data="lk_achievements")],
                        [InlineKeyboardButton(text="💛 Благодарности",callback_data="lk_thanks")]])


# ===== Открытие ЛК =====
async def render_profile(
    *,
    user_id: int,
    tg_user,
    send_func,
):
    user = get_user(user_id)

    if not user:
        await send_func(
            "❌ Пользователь не найден. Обратитесь к администратору."
        )
        return

    # Подмешиваем имя из TG
    user["tg_name"] = tg_user.full_name

    text = build_profile_text(user)

    await send_func(
        text,
        reply_markup=profile_keyboard()
    )


@router.message(F.text == "👤 Личный кабинет")
async def open_profile(message: Message):
    await render_profile(
        user_id=message.from_user.id,
        tg_user=message.from_user,
        send_func=message.answer
    )

# ===== Ачивки =====   
@router.callback_query(F.data == "lk_achievements")
async def achievements_menu(callback: CallbackQuery):
    user_id = callback.from_user.id

    achievements = get_user_achievements(user_id)

    text = "<b>🏆 Ваши ачивки</b>\n\n"

    for ach in achievements:
        status = "✅" if ach["completed"] else "🔒"
        text += (
            f"{ach['icon']} <b>{ach['title']}</b> {status}\n"
            f"{ach['description']}\n\n"
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=achievements_keyboard()
    )
    await callback.answer()
    
def achievements_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="lk_profile")]
        ]
    )   

@router.callback_query(F.data == "lk_profile")
async def back_to_profile(callback: CallbackQuery):
    await render_profile(
        user_id=callback.from_user.id,
        tg_user=callback.from_user,
        send_func=callback.message.edit_text
    )

    await callback.answer()
    

def build_thanks_text(stats: list[dict]) -> str:
    if not stats:
        return (
            "💛 <b>Благодарности</b>\n\n"
            "Пока вы не получали благодарностей.\n"
            "Но это вопрос времени 🙂"
        )

    lines = ["💛 <b>Благодарности</b>\n"]

    for item in stats:
        label = THANKS_CATEGORIES.get(item["category"], item["category"])
        lines.append(f"{label}: <b>{item['count']}</b>")

    return "\n".join(lines)

@router.callback_query(F.data == "lk_thanks")
async def open_thanks(callback: CallbackQuery):
    user_id = callback.from_user.id

    stats = get_thanks_stats(user_id)
    text = build_thanks_text(stats)

    await callback.message.edit_text(
        text,
        reply_markup=achievements_keyboard()
    )
    await callback.answer()