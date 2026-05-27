from typing import Optional, List, Union
from db import get_connection


# ========= СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ =========
def create_user(
    user_id: int,
    full_name: str,
    role: str,
    restaurant_id: Optional[int] = None,
    position: Optional[str] = None,
    real_name: Optional[str] = None,
):
    """Создаёт или обновляет запись пользователя.

    Параметры:
    - user_id: Telegram ID пользователя (PRIMARY KEY)
    - full_name: имя/ник из Telegram (используется как fallback при отсутствии real_name)
    - real_name: реальное имя/ФИО сотрудника (может быть NULL)
    - role: роль пользователя (например: 'director', 'deputy_director', 'user')
    - restaurant_id: привязка к ресторану (опционально)
    - position: должность (для сотрудников ресторана)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO users
            (id, full_name, real_name, role, restaurant_id, position, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, full_name, real_name, role, restaurant_id, position),
        )
        conn.commit()

# ========= ОБНОВЛЕНИЕ РЕАЛЬНОГО ИМЕНИ =========
def update_user_real_name(user_id: int, real_name: str):
    """Обновляет поле `real_name` (реальное имя/ФИО) для пользователя с указанным ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET real_name = ? WHERE id = ?",
            (real_name, user_id),
        )
        conn.commit()

# ========= ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ =========
def get_user(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(zip([c[0] for c in cursor.description], row))


# ========= СПИСОК ПОЛЬЗОВАТЕЛЕЙ =========
def get_users(
    user_id: Optional[Union[int, list[int]]] = None,
    role: Optional[Union[str, list]] = None,
    restaurant_id: Optional[int] = None,
    position: Optional[str] = None,
    is_active: Optional[int] = None,
) -> List[dict]:
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if user_id is not None:
        if isinstance(user_id, list):
            placeholders = ', '.join(['?'] * len(user_id))
            query += f" AND id IN ({placeholders})"
            params.extend(user_id)
        else:
            query += " AND id = ?"
            params.append(user_id)

    if role:
        if isinstance(role, list):
            # Если пришел список: преобразуем в "AND role IN (?, ?, ?)"
            placeholders = ', '.join(['?'] * len(role))
            query += f" AND role IN ({placeholders})"
            params.extend(role)
        else:
            # Если пришла строка
            query += " AND role = ?"
            params.append(role)

    if restaurant_id is not None:
        query += " AND restaurant_id = ?"
        params.append(restaurant_id)

    if position:
        query += " AND position = ?"
        params.append(position)
        
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(is_active)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]


# ========= ИЗМЕНЕНИЕ РОЛИ =========
def update_user_role(user_id: int, new_role: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET role = ?, position = NULL
            WHERE id = ?
            """,
            (new_role, user_id),
        )
        conn.commit()


# ========= НАЗНАЧЕНИЕ ДОЛЖНОСТИ =========
def update_user_position(user_id: int, position: Optional[str]):
    """
    position имеет смысл только для role='user'
    """
    if position not in ("waiter", "cook", "bartender", "admin"):
        position = None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET position = ? WHERE id = ?",
            (position, user_id),
        )
        conn.commit()


# ========= ПРИВЯЗКА К РЕСТОРАНУ =========
def assign_user_to_restaurant(user_id: int, restaurant_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET restaurant_id = ? WHERE id = ?",
            (restaurant_id, user_id),
        )
        conn.commit()


# ========= ПЕРЕВОД В ДРУГОЙ РЕСТОРАН =========
def transfer_user(
    user_id: int,
    new_restaurant_id: int,
):
    """
    Используется:
    - OWNER
    - director
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET restaurant_id = ?
            WHERE id = ?
            """,
            (new_restaurant_id, user_id),
        )
        conn.commit()


# ========= ДЕАКТИВАЦИЯ =========
def deactivate_user(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,),
        )
        conn.commit()

# ========= АКТИВАЦИЯ =========
def activate_user(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()

# ========= ПОЛНОЕ УДАЛЕНИЕ ИЗ СИСТЕМЫ =========
def remove_user_from_system(user_id: int):
    """
    - деактивация
    - отвязка от ресторана
    - сброс роли и должности
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET
                is_active = 0,
                restaurant_id = NULL,
                role = 'user',
                position = NULL
            WHERE id = ?
        """, (user_id,))
        conn.commit()

# ========= СПИСОК ПОЛЬЗОВАТЕЛЕЙ на смене с данными из users =========
def get_users_on_shift(cursor, restaurant_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT 
            u.id,
            u.real_name,
            u.position
        FROM daily_shifts ds
        JOIN users u ON u.id = ds.user_id
        WHERE ds.restaurant_id = ?
        ORDER BY u.position, u.real_name
        """,
        (restaurant_id,)
    )

    rows = cursor.fetchall()
    return [dict(row) for row in rows]
        
# ========= ОЧИСТКА ТАБЛИЦЫ сотрудников на смене =========    
def clear_daily_shifts_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Удаляем все записи из таблицы daily_shifts
        cursor.execute("DELETE FROM daily_shifts")
        conn.commit()
        
