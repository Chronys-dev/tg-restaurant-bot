from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import QUIZ_CATEGORIES
from aiogram import Router, F
from aiogram.types import CallbackQuery, PollAnswer
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from db import start_quiz_session, save_quiz_answer, finish_quiz_session
from loader import bot

class QuizStates(StatesGroup):
    choosing_category = State()
    in_progress = State()

router = Router()

# Функция для отправки вопроса квиза
async def send_quiz_question(bot, chat_id: int, question_data: dict):
    options = [
        question_data["option_1"],
        question_data["option_2"],
        question_data["option_3"],
        question_data["option_4"],
    ]
    correct_index = question_data["correct_option"] - 1

    return await bot.send_poll(
        chat_id=chat_id,
        question=question_data["question"],
        options=options,
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False,
        explanation=question_data.get("hint")
    )

# Функция для построения клавиатуры с категориями квизов
def build_quiz_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"quiz_category:{key}")
        for key, label in QUIZ_CATEGORIES.items()
    ]
    # формируем ряды по 2 кнопки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)]
    )
    return keyboard

# --- Хэндлер кнопки "Квизы" в ЛК ---
@router.callback_query(F.data == "lk_quizzes")
async def lk_show_quiz_categories(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QuizStates.choosing_category)
    keyboard = build_quiz_category_keyboard()
    await callback.message.edit_text(
        "🧠 Выберите категорию квиза:",
        reply_markup=keyboard
    )
    await callback.answer()

# Начало квиза - выбор категории
@router.callback_query(F.data.startswith("quiz_category:"))
async def quiz_category_selected(callback: CallbackQuery, state: FSMContext):
    category_key = callback.data.split(":")[1]

    user_id = callback.from_user.id
    chat_id = callback.from_user.id

    total_questions = 20 if category_key == "super" else 10

    # Стартуем квиз-сессию в БД
    session_id, questions_list = start_quiz_session(
        user_id=user_id,
        category=category_key,
        total_questions=total_questions
    )

    if not questions_list:
        await callback.answer("В этой категории пока нет вопросов.", show_alert=True)
        return

    # Сохраняем состояние квиза
    await state.set_state(QuizStates.in_progress)
    await state.update_data(
        session_id=session_id,
        questions_list=questions_list,
        current_question=0
    )

    # Отправляем первый вопрос
    first_question = questions_list[0]

    await send_quiz_question(
        bot=bot,
        chat_id=chat_id,
        question_data=first_question
    )

    await callback.answer()
    
@router.poll_answer()
async def handle_quiz_answer(poll_answer: PollAnswer, state: FSMContext):
    user_id = poll_answer.user.id
    selected_option = poll_answer.option_ids[0] + 1  # 0..3 → 1..4

    data = await state.get_data()
    if not data or "questions_list" not in data:
        return

    session_id = data["session_id"]
    questions = data["questions_list"]
    current_index = data.get("current_question", 0)
    correct_count = data.get("correct_answers", 0)

    current_question = questions[current_index]
    question_id = current_question["id"]
    correct_option = current_question["correct_option"]

    is_correct = int(selected_option == correct_option)

    # Сохраняем ответ в БД
    save_quiz_answer(
        session_id=session_id,
        question_id=question_id,
        selected_option=selected_option,
        is_correct=is_correct
    )

    # Обновляем счётчик правильных ответов в FSM
    if is_correct:
        correct_count += 1
        await state.update_data(correct_answers=correct_count)

    # Проверяем, есть ли следующий вопрос
    next_index = current_index + 1
    if next_index >= len(questions):
        # Завершаем квиз, засчитываем только при ≥80%
        passed = (correct_count / len(questions)) >= 0.8
        finish_quiz_session(session_id, passed)

        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Квиз завершён!</b>\n\n"
                f"Всего вопросов: <b>{len(questions)}</b>\n"
                f"Правильных ответов: <b>{correct_count}</b>\n"
                f"Результат: {'✅ Засчитан' if passed else '❌ Не засчитан'}"
            )
        )

        await state.clear()
        return

    # Сохраняем индекс следующего вопроса в FSM
    await state.update_data(current_question=next_index)

    # Отправляем следующий вопрос
    next_question = questions[next_index]
    await send_quiz_question(
        bot=bot,
        chat_id=user_id,
        question_data=next_question
    )

