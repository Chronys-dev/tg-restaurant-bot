from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import get_user, get_connection, shift_report_exists, replace_shift_report
from keyboards import TOPICS, get_random_sticker
from aiogram.exceptions import TelegramBadRequest
import traceback



router = Router()


class CloseShiftStates(StatesGroup):
    waiting_for_problems = State()
    waiting_for_cash_percent = State()
    waiting_for_drinks_rating = State()
    waiting_for_comment = State()

def can_close_shift(user: dict) -> bool:
    return (
        user.get("role") in ["director", "deputy_director"]
        or user.get("position") == "admin"
    )

def get_shift_date() -> str:
    now = datetime.now()
    if 0 <= now.hour < 6:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


@router.callback_query(F.data == "feedback_close_shift")
async def close_shift_start(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)

    if not user or not can_close_shift(user):
        await callback.answer("⛔ У вас нет прав.", show_alert=True)
        return

    shift_date = get_shift_date()

    # Проверяем, есть ли уже отчет
    with get_connection() as conn:
        cursor = conn.cursor()
        exists = shift_report_exists(
            cursor,
            restaurant_id=user["restaurant_id"],
            date=shift_date
        )

    if exists:
        await callback.answer(
            "⚠️ Отчёт за эту смену уже существует.\n"
            "При повторном закрытии смены он будет перезаписан.",
            show_alert=True
        )

    await state.set_state(CloseShiftStates.waiting_for_problems)

    topics_items = list(TOPICS.items())
    builder = InlineKeyboardBuilder()

    for i in range(0, len(topics_items), 2):
        row = []
        for j in (0, 1):
            if i + j < len(topics_items):
                key, label = topics_items[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"close_topic_{key}"
                    )
                )
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="close_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="close_cancel"),
    )

    await callback.message.answer(
        "Выберите проблемные темы (можно несколько):\n"
        "✨ <b>Если проблем не было, просто нажмите ✅ Готово</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("close_topic_"))
async def close_topic_toggle(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("close_topic_", "")
    state_data = await state.get_data()
    selected = state_data.get("selected_topics", [])
    topics_items = list(TOPICS.items())
    
    if key in selected:
        selected.remove(key)
    else:
        selected.append(key)
    await state.update_data(selected_topics=selected)

    builder = InlineKeyboardBuilder()
    for i in range(0, len(topics_items), 2):
        row = []
        for j in (0, 1):
            if i + j < len(topics_items):
                k, label = topics_items[i + j]
                display = ("✅ " + label) if k in selected else label
                row.append(InlineKeyboardButton(text=display, callback_data=f"close_topic_{k}"))
        builder.row(*row)

    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="close_done"), InlineKeyboardButton(text="❌ Отмена", callback_data="close_cancel"))

    try:
        # Пытаемся обновить клавиатуру
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except TelegramBadRequest as e:
        if "message is not modified" in e.message:
            # Если данные те же самые — просто подтверждаем колбэк, чтобы убрать "часики"
            await callback.answer()
        else:
            # Если ошибка другая — пробрасываем её дальше
            raise e
    except Exception:
        # Если сообщение вообще пропало (например, удалено) — отправляем новое
        await callback.message.answer(
            "Выберите проблемные темы (можно несколько):\n"
            "✨ <b>Если проблем не было, просто нажмите ✅ Готово</b>", 
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    await callback.answer()

# Подтверждение проблем
@router.callback_query(F.data == "close_done")
async def close_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data() or {}
    selected = data.get("selected_topics") or []
    
    # Если темы выбраны — переводим ключи в строку, если нет — пишем "Проблем нет"
    if selected:
        problems_str = ", ".join(selected)
    else:
        problems_str = "no_problems" # Специальный маркер для идеальной смены
    
    await state.update_data(problems=problems_str)
    
    # Переходим к следующему шагу — % налички
    await state.set_state(CloseShiftStates.waiting_for_cash_percent)
    
    # Меняем текст в зависимости от того, были ли проблемы
    if problems_str == "no_problems":
        msg_text = "✨ <b>Отлично, смена без происшествий!</b>\n\nТеперь введите % наличной выручки:"
    else:
        msg_text = "💰 <b>Темы зафиксированы.</b>\n\nВведите % наличной выручки:"
        
    await callback.message.edit_text(msg_text, parse_mode="HTML")
    await callback.answer()

# Ждем % налички
@router.message(CloseShiftStates.waiting_for_cash_percent)
async def process_cash_percent(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    
    try:
        cash_val = float(text)
        if not (0 <= cash_val <= 100):
            return await message.answer("❌ Процент должен быть от 0 до 100. Попробуйте еще раз:")
        
        await state.update_data(cash_percentage=cash_val)
        
        # Реакция на высокий % налички
        feedback = ""
        if cash_val >= 25:
            feedback = "⭐ <b>Отличный показатель по наличке! Так держать!</b>\n\n"
        
        await state.set_state(CloseShiftStates.waiting_for_drinks_rating)
        await message.answer(
            f"{feedback}☕ <b>Рейтинг быстрых напитков</b>\n"
            "Введите % быстрых напитков.\n",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Введите число (процент наличной выручки). Например: 25.5")

# Ждем % быстрых напитков
@router.message(CloseShiftStates.waiting_for_drinks_rating)
async def process_drinks_percent(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    
    try:
        drinks_val = float(text)
        if not (0 <= drinks_val <= 100):
            return await message.answer("❌ Процент должен быть от 0 до 100. Попробуйте еще раз:")
        
        await state.update_data(fast_drinks_percentage=drinks_val)
        
        # Реакция на высокий % быстрых напитков (цель 35%)
        feedback = ""
        if drinks_val >= 35:
            feedback = "☕ <b>Ого! Продажи напитков на высоте. Настоящее мастерство!</b>\n\n"
        elif drinks_val >= 30:
            feedback = "👍 <b>Хороший результат по напиткам, почти у цели!</b>\n\n"
        
        await state.set_state(CloseShiftStates.waiting_for_comment)
        await message.answer(
            f"{feedback}📝 <b>Комментарий администратора по смене:</b>\n"
            "Расскажите подробнее, как прошел день, были ли важные моменты?",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Введите число (процент быстрых напитков). Например: 36.2")

@router.message(CloseShiftStates.waiting_for_comment)
async def close_shift_final(message: Message, state: FSMContext):
    data = await state.get_data()
    user = get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Профиль не найден.")
        return

    shift_date = get_shift_date()

    problems = data.get("problems", "")
    if problems and problems != "no_problems":
        problem_keys = [k.strip() for k in problems.split(',') if k.strip()]
    else:
        problem_keys = []
        
    cash = data.get("cash_percentage", 0)
    drinks = data.get("fast_drinks_percentage", 0)
    comment = message.text.strip()

    score = sum([
        not problem_keys,
        cash >= 25,
        drinks >= 35
    ])

    if score == 3:
        category = "super"
        result = "🚀 <b>ОТЛИЧНАЯ СМЕНА! Ты молодец!</b>"
    elif score >= 1:
        category = "good"
        result = "✅ <b>Смена закрыта успешно!</b>"
    else:
        category = "support"
        result = "❤️ <b>Смена была непростой. Спасибо за работу.</b>"

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            replace_shift_report(
                cursor=cursor,
                restaurant_id=user["restaurant_id"],
                admin_id=message.from_user.id,
                date=shift_date,
                problems=", ".join(problem_keys) if problem_keys else "Нет проблем",
                cash_percentage=cash,
                fast_drinks_percentage=drinks,
                comment=comment
            )

        sticker = get_random_sticker(category)
        if sticker:
            await message.answer_sticker(sticker)

        await message.answer(result, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения: {e}")

    await state.clear()

@router.callback_query(F.data == "close_cancel")
async def close_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        try:
            await callback.message.edit_text("Отменено", reply_markup=None)
        except Exception:
            pass
        await callback.answer("Отменено", show_alert=True)
    except Exception:
        print(traceback.format_exc())
        await callback.answer("Ошибка при отмене", show_alert=True)


