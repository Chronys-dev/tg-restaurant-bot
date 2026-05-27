
from typing import Optional, List
from db import get_connection

# Добавление нового тега
def add_tag(name: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tags (name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return cursor.lastrowid

# Получить список всех тегов
def get_all_tags() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags")
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]

# Получить тег по ID
def get_tag_by_id(tag_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = cursor.fetchone()
        if row:
            return dict(zip([c[0] for c in cursor.description], row))
        return None

# Получение тегов для конкретного блюда
def get_tags_for_recipe(recipe_id: int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name
            FROM tags t
            JOIN recipe_tags rt ON rt.tag_id = t.id
            WHERE rt.recipe_id = ?
        """, (recipe_id,))
        rows = cursor.fetchall()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]

def detach_tag_from_recipe(recipe_id: int, tag_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM recipe_tags
            WHERE recipe_id = ? AND tag_id = ?
        """, (recipe_id, tag_id))
        conn.commit()
        
# Привязать тег
def set_recipe_tags(recipe_id: int, tag_ids: list[int]):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,))
        for tid in tag_ids:
            cursor.execute(
                "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
                (recipe_id, tid)
            )
        conn.commit()       

# Удаление тега
def delete_tag(tag_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipe_tags WHERE tag_id = ?", (tag_id,))
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        conn.commit()
