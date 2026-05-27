
from typing import Optional, List, Dict
from db import get_connection


# Добавить новый рецепт блюда
def add_recipe(
    name: str,
    price: int | None = None,
    price_red: int | None = None,
    photo_path: str | None = None,
    photo_file_id: str | None = None,
    short_composition: str | None = None,
    presentation_text: str | None = None,
    categories: list[str] | None = None,
    steps: str | None = None, 
    yield_weight: str | None = None, 
    sauce_ids: list[int] | None = None,
    tag_ids: list[int] | None = None
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()

        # Основная инфа блюда
        cursor.execute("""
            INSERT INTO recipes (name, price, price_red, photo_path, photo_file_id, short_composition, presentation_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, price, price_red, photo_path, photo_file_id, short_composition, presentation_text))
        recipe_id = cursor.lastrowid

        # Категории
        if categories:
            cursor.executemany("INSERT INTO recipe_categories (recipe_id, category_code) VALUES (?, ?)",
                               [(recipe_id, cat) for cat in categories])
        
        # ТТК
        cursor.execute("""
            INSERT INTO recipe_tech (recipe_id, steps, yield_weight) 
            VALUES (?, ?, ?)
        """, (recipe_id, steps, yield_weight))

        # Соусы
        if sauce_ids:
            cursor.executemany("INSERT INTO recipe_sauces (recipe_id, sauce_id) VALUES (?, ?)",
                               [(recipe_id, sid) for sid in sauce_ids])

        # Теги
        if tag_ids:
            cursor.executemany("INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
                               [(recipe_id, tid) for tid in tag_ids])

        conn.commit()
        return recipe_id

# Добавить новые категории блюда
def add_recipe_categories(recipe_id: int, categories: list[str]):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO recipe_categories (recipe_id, category_code)
            VALUES (?, ?)
        """, [
            (recipe_id, category)
            for category in categories
        ])
        conn.commit()


# Получить карту блюда по ID
def get_recipe_by_id(recipe_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(zip([c[0] for c in cursor.description], row))

# Получить все карты блюд в категории
def get_recipes(category_code: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*
            FROM recipes r
            JOIN recipe_categories rc ON r.id = rc.recipe_id
            WHERE rc.category_code = ?
        """, (category_code,))
        
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]

# Получить все карты блюд по тегу
def get_recipes_by_tag(tag_id: int) -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*
            FROM recipes r
            JOIN recipe_tags rt ON r.id = rt.recipe_id
            WHERE rt.tag_id = ?
        """, (tag_id,))
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]

# Найти карты блюд по названию
def search_recipes_by_name(query: str) -> List[dict]:
    search_term = f"%{query.strip().lower()}%"    
    with get_connection() as conn:
        cursor = conn.cursor()               
        cursor.execute("SELECT * FROM recipes WHERE name LIKE ?", (search_term,))
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("SELECT * FROM recipes WHERE name LIKE ?", (f"%{query.strip().capitalize()}%",))
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

def get_recipe_tech(recipe_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Получаем текстовые поля
        cursor.execute("SELECT steps, yield_weight FROM recipe_tech WHERE recipe_id = ?", (recipe_id,))
        tech_row = cursor.fetchone()
        
        if not tech_row:
            return None

        # 2. Получаем ингредиенты
        cursor.execute("""
            SELECT item_name, item_weight 
            FROM recipe_structure_simple
            WHERE recipe_id = ?
        """, (recipe_id,))
        
        ingredients_list = [
            {"name": row[0], "weight": row[1]} 
            for row in cursor.fetchall()
        ]

        return {
            "steps": tech_row[0] if tech_row[0] else "Инструкция не заполнена.",
            "yield_weight": tech_row[1] if tech_row[1] else "Не указан.",
            "ingredients": ingredients_list
        }


def update_recipe(
    recipe_id: int,
    name: Optional[str] = None,
    price: Optional[int] = None,
    price_red: Optional[int] = None,
    photo_path: Optional[str] = None,
    photo_file_id: Optional[str] = None,
    short_composition: Optional[str] = None,
    presentation_text: Optional[str] = None,
    categories: Optional[List[str]] = None,
    steps: Optional[str] = None,
    yield_weight: Optional[str] = None,
    ingredients_data: Optional[List[Dict[str, str]]] = None,
    sauce_ids: Optional[List[int]] = None,
    tag_ids: Optional[List[int]] = None
):
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ОБНОВЛЯЕМ ОСНОВНЫЕ ПОЛЯ (таблица recipes)
        fields = []
        values = []

        main_updates = [
            ("name", name), ("price", price), ("price_red", price_red), ("photo_path", photo_path),
            ("photo_file_id", photo_file_id), ("short_composition", short_composition), 
            ("presentation_text", presentation_text)
        ]
        
        for field, val in main_updates:
            if val is not None:
                fields.append(f"{field} = ?")
                values.append(val)

        if fields:
            values.append(recipe_id)
            cursor.execute(f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values)

        # ОБНОВЛЯЕМ ТЕХНОЛОГИЮ (таблица recipe_tech)
        cursor.execute("INSERT OR IGNORE INTO recipe_tech (recipe_id) VALUES (?)", (recipe_id,))
        
        tech_fields = []
        tech_values = []
        
        # ВЫХОД БЛЮДА
        for field, val in [("steps", steps), ("yield_weight", yield_weight)]:
             if val is not None:
                tech_fields.append(f"{field} = ?")
                tech_values.append(val)
        
        if tech_fields:
            tech_values.append(recipe_id)
            cursor.execute(f"UPDATE recipe_tech SET {', '.join(tech_fields)} WHERE recipe_id = ?", tech_values)

        # ОБНОВЛЯЕМ КАТЕГОРИИ
        if categories is not None:
            cursor.execute("DELETE FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
            cursor.executemany(
                "INSERT INTO recipe_categories (recipe_id, category_code) VALUES (?, ?)",
                [(recipe_id, cat) for cat in categories]
            )

        # ОБНОВЛЯЕМ СОСТАВ (ингредиенты: item_name, item_weight)
        if ingredients_data is not None:
            cursor.execute("DELETE FROM recipe_structure_simple WHERE recipe_id = ?", (recipe_id,))
            cursor.executemany(
                "INSERT INTO recipe_structure_simple (recipe_id, item_name, item_weight) VALUES (?, ?, ?)",
                [(recipe_id, ing['item_name'], ing['item_weight']) for ing in ingredients_data]
            )

        # ОБНОВЛЯЕМ СОУСЫ
        if sauce_ids is not None:
            cursor.execute("DELETE FROM recipe_sauces WHERE recipe_id = ?", (recipe_id,))
            cursor.executemany(
                "INSERT INTO recipe_sauces (recipe_id, sauce_id) VALUES (?, ?)",
                [(recipe_id, sid) for sid in sauce_ids]
            )

        # ОБНОВЛЯЕМ ТЕГИ
        if tag_ids is not None:
            cursor.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,))
            cursor.executemany(
                "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
                [(recipe_id, tid) for tid in tag_ids]
            )

        conn.commit()


# УДАЛИТЬ БЛЮДО
def delete_recipe(recipe_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        conn.commit()


        


