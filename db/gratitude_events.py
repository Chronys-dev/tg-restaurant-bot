import asyncio, sqlite3
from db import get_connection
from datetime import date

# ======== РЕГИСТРАЦИЯ БЛАГОДАРНОСТИ =========
def register_gratitude(
    from_user_id: int,
    to_user_id: int,
    restaurant_id: int,
    category: str,
    shift_date: str | None = None
) -> tuple[bool, str]:
    """
    Регистрирует 'спасибо' в БД и уменьшает лимит отправителя.
    """

    if from_user_id == to_user_id:
        return False, "Нельзя отправить спасибо самому себе."

    if not shift_date:
        shift_date = date.today().strftime("%Y-%m-%d")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем или создаём лимит
            cursor.execute(
                """
                SELECT thanks_week_limit
                FROM user_social_limits
                WHERE user_id = ?
                """,
                (from_user_id,)
            )
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    """
                    INSERT INTO user_social_limits (user_id, thanks_week_limit)
                    VALUES (?, 7)
                    """,
                    (from_user_id,)
                )
                thanks_left = 7
            else:
                thanks_left = row["thanks_week_limit"]

            if thanks_left <= 0:
                return False, "Лимит благодарностей на эту неделю исчерпан."

            # Записываем событие благодарности
            cursor.execute(
                """
                INSERT INTO gratitude_events (
                    from_user_id,
                    to_user_id,
                    category,
                    restaurant_id,
                    shift_date
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    from_user_id,
                    to_user_id,
                    category,
                    restaurant_id,
                    shift_date
                )
            )

            # Уменьшаем лимит
            cursor.execute(
                """
                UPDATE user_social_limits
                SET thanks_week_limit = thanks_week_limit - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (from_user_id,)
            )

            thanks_left_after = thanks_left - 1
            conn.commit()
            return True, (
                "✨ Благодарность успешно отправлена!\n"
                f"Осталось благодарностей на эту неделю: {thanks_left_after}"
            )

    except sqlite3.Error as e:
        return False, f"Ошибка БД: {e}"
    
# ======== СБРОС НЕДЕЛЬНЫХ ЛИМИТОВ БЛАГОДАРНОСТЕЙ =========
def reset_weekly_gratitude_limits():
    """
    Сбрасывает недельный лимит 'спасибо' всем активным пользователям.
    Запускается раз в неделю.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_social_limits (user_id, thanks_week_limit)
                SELECT id, 7
                FROM users
                WHERE is_active = 1
                AND id NOT IN (
                    SELECT user_id FROM user_social_limits
                )
            """)

            cursor.execute("""
                UPDATE user_social_limits
                SET thanks_week_limit = 7,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id IN (
                    SELECT id FROM users WHERE is_active = 1
                )
            """)

            conn.commit()

    except sqlite3.Error as e:
        print(f"[GRATITUDE RESET ERROR] {e}")
        
# ======== АСИНХРОННАЯ ОБЕРТКА ДЛЯ СБРОСА ЛИМИТОВ =========
async def reset_weekly_gratitude_limits_async():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        reset_weekly_gratitude_limits
    )

# ======== ПОЛУЧЕНИЕ ОСТАВШИХСЯ БЛАГОДАРНОСТЕЙ =========    
def get_thanks_left(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT thanks_week_limit
            FROM user_social_limits
            WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()

        if not row:
            return 7

        return row["thanks_week_limit"]
    
# ======== ПОЛУЧЕНИЕ ОБЩЕГО КОЛИЧЕСТВА ПОЛУЧЕННЫХ БЛАГОДАРНОСТЕЙ =========
def get_total_received_thanks(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as total
            FROM gratitude_events
            WHERE to_user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return row["total"] if row else 0
    
# ======== ПОЛУЧЕНИЕ СТАТИСТИКИ ПО БЛАГОДАРНОСТЯМ =========
def get_thanks_stats(user_id: int) -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, COUNT(*) AS count
            FROM gratitude_events
            WHERE to_user_id = ?
            GROUP BY category
            ORDER BY count DESC
        """, (user_id,))

        rows = cursor.fetchall()

    return [
        {
            "category": row["category"],
            "count": row["count"]
        }
        for row in rows
    ]