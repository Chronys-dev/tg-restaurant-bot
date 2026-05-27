
from typing import Optional, List, Dict
from db import get_connection


# Добавить соус
def add_sauce(
    name: str, 
    ingredients_data: list[dict] | None = None
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Создаем сам соус
        cursor.execute(
            "INSERT INTO sauces (name) VALUES (?)",
            (name,)
        )
        sauce_id = cursor.lastrowid

        if ingredients_data:
            cursor.executemany("""
                INSERT INTO sauce_structure_simple (sauce_id, item_name, item_weight)
                VALUES (?, ?, ?)
            """, [
                (sauce_id, ing['item_name'], ing['item_weight']) 
                for ing in ingredients_data
            ])

        conn.commit()
        return sauce_id

# Получение соусов для конкретного блюда
def get_recipe_sauces(recipe_id: int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        # 1. Получаем список соусов, привязанных к конкретному блюду
        cursor.execute("""
            SELECT s.id, s.name, s.steps, s.yield_weight
            FROM sauces s
            JOIN recipe_sauces rs ON rs.sauce_id = s.id
            WHERE rs.recipe_id = ?
        """, (recipe_id,))
        
        sauces = []
        for row in cursor.fetchall():
            sauce_id, sauce_name, steps, yield_weight = row
            
            # 2. Для каждого соуса подтягиваем его состав из правильной таблицы (sauce_structure_simple)
            cursor.execute("""
                SELECT item_name, item_weight
                FROM sauce_structure_simple
                WHERE sauce_id = ?
            """, (sauce_id,))
            
            ingredients = [
                {"name": r[0], "weight": r[1]} 
                for r in cursor.fetchall()
            ]
            
            sauces.append({
                "id": sauce_id,
                "name": sauce_name,
                "steps": steps,
                "yield_weight": yield_weight,
                "ingredients": ingredients
            })
            
        return sauces

# Получить список всех соусов
def get_all_sauces() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM sauces ORDER BY name")
        rows = cursor.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]

# Получить соус по ID
def get_sauce_by_id(sauce_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        # Получаем основные данные
        cursor.execute("SELECT id, name, steps, yield_weight FROM sauces WHERE id = ?", (sauce_id,))
        row = cursor.fetchone()
        if not row: return None
        
        sauce = dict(zip([c[0] for c in cursor.description], row))
        
        # Получаем состав
        cursor.execute("SELECT item_name, item_weight FROM sauce_structure_simple WHERE sauce_id = ?", (sauce_id,))
        sauce['ingredients'] = [{"name": r[0], "weight": r[1]} for r in cursor.fetchall()]
        
        return sauce


# Обновление данных соуса
def update_sauce(
    sauce_id: int, 
    name: Optional[str] = None, 
    steps: Optional[str] = None,
    yield_weight: Optional[str] = None,
    ingredients_data: Optional[List[Dict]] = None
):
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Обновляем основные поля таблицы sauces
        fields = []
        values = []
        
        for field, val in [
            ("name", name), 
            ("steps", steps), 
            ("yield_weight", yield_weight)
        ]:
            if val is not None:
                fields.append(f"{field} = ?")
                values.append(val)

        if fields:
            values.append(sauce_id)
            cursor.execute(f"UPDATE sauces SET {', '.join(fields)} WHERE id = ?", values)

        # 2. Обновляем состав (ТТК соуса) в sauce_structure_simple
        if ingredients_data is not None:
            # Удаляем старый состав по корректному имени таблицы
            cursor.execute("DELETE FROM sauce_structure_simple WHERE sauce_id = ?", (sauce_id,))
            
            # Записываем новый состав (item_name, item_weight)
            cursor.executemany("""
                INSERT INTO sauce_structure_simple (sauce_id, item_name, item_weight)
                VALUES (?, ?, ?)
            """, [
                (sauce_id, ing['item_name'], ing['item_weight']) 
                for ing in ingredients_data
            ])

        conn.commit()

# Отвязать соус
def detach_sauce_from_recipe(recipe_id: int, sauce_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM recipe_sauces
            WHERE recipe_id = ? AND sauce_id = ?
        """, (recipe_id, sauce_id))
        conn.commit()

#Привязать соус
def set_recipe_sauces(recipe_id: int, sauce_ids: list[int]):
    with get_connection() as conn:
        cursor = conn.cursor()
        # Удаляем старые привязки
        cursor.execute("DELETE FROM recipe_sauces WHERE recipe_id = ?", (recipe_id,))
        # Массовая вставка новых
        if sauce_ids:
            cursor.executemany(
                "INSERT INTO recipe_sauces (recipe_id, sauce_id) VALUES (?, ?)",
                [(recipe_id, sid) for sid in sauce_ids]
            )
        conn.commit()
        
#Удалить соус
def delete_sauce(sauce_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Привязки к блюдам и ингредиенты соуса удалятся САМИ по каскаду.
        cursor.execute("DELETE FROM sauces WHERE id = ?", (sauce_id,))
        conn.commit()