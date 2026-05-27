from typing import Optional, List
from db import get_connection


def add_shift_report(
    cursor,
    restaurant_id: int, 
    admin_id: int, 
    date: str, 
    problems: Optional[str], 
    cash_percentage: float, 
    fast_drinks_percentage: float, 
    comment: Optional[str]
):

    cursor.execute(
        """
        INSERT INTO shift_reports 
        (restaurant_id, admin_id, date, incidents_log, cash_percentage, fast_drinks_rating, atmosphere_comment) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            restaurant_id, 
            admin_id, 
            date, 
            problems,        
            cash_percentage,
            fast_drinks_percentage,
            comment
        ),
    )

# Получает список отчетов за конкретную дату
def get_shift_reports_for_date(cursor, restaurant_id: int, date: str) -> list[dict]:
    # Убираем внутреннее соединение, используем переданный cursor
    cursor.execute(
        "SELECT * FROM shift_reports WHERE restaurant_id = ? AND date = ?", 
        (restaurant_id, date)
    )
    rows = cursor.fetchall()
    
    # Преобразуем каждую строку sqlite3.Row в обычный словарь Python
    return [dict(row) for row in rows]


def get_shift_report_full(cursor, restaurant_id, date):
    # Соединение с БД и курсор передаются ИЗВНЕ в функцию
    # Мы просто используем переданный курсор для выполнения запроса
    cursor.execute("""
        SELECT r.*, u.real_name as admin_name 
        FROM shift_reports r
        JOIN users u ON r.admin_id = u.id
        WHERE r.restaurant_id = ? AND r.date = ?
        ORDER BY r.created_at DESC LIMIT 1
    """, (restaurant_id, date))
    row = cursor.fetchone()
    return dict(row) if row else None

# Проверяет, существует ли отчет за указанную дату
def shift_report_exists(cursor, restaurant_id: int, date: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM shift_reports
        WHERE restaurant_id = ? AND date = ?
        LIMIT 1
        """,
        (restaurant_id, date)
    )
    return cursor.fetchone() is not None

# Заменяет существующий отчет новым (удаляет старый и добавляет новый)
def replace_shift_report(
    cursor,
    restaurant_id: int,
    admin_id: int,
    date: str,
    problems: Optional[str],
    cash_percentage: float,
    fast_drinks_percentage: float,
    comment: Optional[str]
):
    # Удаляем старый отчет (если был)
    cursor.execute(
        """
        DELETE FROM shift_reports
        WHERE restaurant_id = ? AND date = ?
        """,
        (restaurant_id, date)
    )

    # Вставляем новый
    add_shift_report(
        cursor=cursor,
        restaurant_id=restaurant_id,
        admin_id=admin_id,
        date=date,
        problems=problems,
        cash_percentage=cash_percentage,
        fast_drinks_percentage=fast_drinks_percentage,
        comment=comment
    )