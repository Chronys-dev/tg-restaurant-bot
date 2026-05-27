from typing import Optional, List
from db import get_connection


def add_restaurant(name: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO restaurants (name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_restaurants() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants")
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]


def get_restaurant_by_id(restaurant_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        row = cursor.fetchone()
        if row:
            return dict(zip([c[0] for c in cursor.description], row))
        return None


def delete_restaurant(restaurant_id: int) -> None:
    """Удаляет ресторан. Прежде обнуляет связь у пользователей, затем удаляет запись ресторана."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Обнуляем привязку пользователей
        cursor.execute("UPDATE users SET restaurant_id = NULL WHERE restaurant_id = ?", (restaurant_id,))
        # Удаляем ресторан
        cursor.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))
        conn.commit()


def update_restaurant(restaurant_id: int, name: str) -> None:
    """Обновляет название ресторана по ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE restaurants SET name = ? WHERE id = ?", (name, restaurant_id))
        conn.commit()
