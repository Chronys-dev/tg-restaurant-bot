import random, sqlite3, datetime
from typing import List, Dict, Tuple
from db import get_connection

def start_quiz_session(user_id: int, category: str, total_questions: int = 10) -> Tuple[int, List[Dict]]:
    """
    Создаёт сессию квиза для пользователя и возвращает список вопросов.
    
    :param user_id: ID пользователя
    :param category: Категория квиза или "super" для супер квиза
    :param total_questions: Количество вопросов в сессии (10 или 20)
    :return: (session_id, questions_list)
    """

    with get_connection() as conn:
        cursor = conn.cursor()

        # --- Получаем пул вопросов ---
        if category == "super":
            cursor.execute("SELECT * FROM quiz_questions")
        else:
            cursor.execute(
                "SELECT * FROM quiz_questions WHERE category = ?",
                (category,)
            )
        all_questions = cursor.fetchall()

        if not all_questions:
            raise ValueError(f"Вопросов в категории '{category}' нет.")

        # --- Случайный выбор вопросов ---
        questions_pool = random.sample(all_questions, min(total_questions, len(all_questions)))

        # --- Создаём сессию ---
        cursor.execute(
            """
            INSERT INTO quiz_sessions (user_id, category, total_questions)
            VALUES (?, ?, ?)
            """,
            (user_id, category, len(questions_pool))
        )
        session_id = cursor.lastrowid

        # --- Создаём пустые ответы для выбранных вопросов ---
        for q in questions_pool:
            cursor.execute(
                """
                INSERT INTO quiz_session_answers (session_id, question_id)
                VALUES (?, ?)
                """,
                (session_id, q["id"])
            )

        conn.commit()

        # --- Формируем список вопросов для вывода пользователю ---
        questions_list = []
        for q in questions_pool:
            questions_list.append({
                "id": q["id"],
                "question": q["question"],
                "option_1": q["option_1"],
                "option_2": q["option_2"],
                "option_3": q["option_3"],
                "option_4": q["option_4"],
                "correct_option": q["correct_option"],
                "hint": q["hint"]
            })

        return session_id, questions_list

# Сохранение ответа пользователя на вопрос квиза
def save_quiz_answer(
    session_id: int,
    question_id: int,
    selected_option: int,
    is_correct: int
) -> None:

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO quiz_session_answers (
                    session_id,
                    question_id,
                    selected_option,
                    is_correct
                )
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                question_id,
                selected_option,
                is_correct
            ))

            conn.commit()

    except sqlite3.Error as e:
        print(f"[DB] Ошибка сохранения ответа квиза: {e}")
        
# Увеличение счётчика правильных ответов в сессии квиза
def increment_quiz_correct(session_id: int) -> None:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE quiz_sessions
                SET correct_answers = correct_answers + 1
                WHERE id = ?
            """, (session_id,))

            conn.commit()

    except sqlite3.Error as e:
        print(f"[DB] Ошибка обновления correct_answers: {e}")
        
# Завершение сессии квиза    
def finish_quiz_session(session_id: int, passed: bool) -> None:
    try:
        finished_at = datetime.datetime.now().isoformat(timespec="seconds")
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE quiz_sessions
                SET finished_at = ?,
                    passed = ?
                WHERE id = ?
            """, (finished_at, int(passed), session_id))

            conn.commit()

    except sqlite3.Error as e:
        print(f"[DB] Ошибка завершения квиза: {e}")
        
# Получение общего количества успешно завершённых квизов пользователем
def get_total_completed_quizzes(user_id: int) -> int:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM quiz_sessions
                WHERE user_id = ? AND passed = 1
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        print(f"[DB] Ошибка получения количества пройденных квизов: {e}")
        return 0

# Получение количества квизов, пройденных без ошибок  
def get_perfect_quizzes_count(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM quiz_sessions
            WHERE user_id = ?
              AND finished_at IS NOT NULL
              AND correct_answers = total_questions
        """, (user_id,))
        
        row = cursor.fetchone()
        return row["cnt"] if row else 0