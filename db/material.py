from db import get_connection
from keyboards import MATERIALS_CAT


# Добавляет материал в базу
def add_material(category_slug, title, file_type, tg_file_id=None, local_path=None, description=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем ID категории по её слагу (kitchen, bar и т.д.)
        cursor.execute("SELECT id FROM categories WHERE slug = ?", (category_slug,))
        row = cursor.fetchone()
        
        if not row:
            # Если в базе нет, ищем название в списке MATERIALS_CAT
            name_from_dict = next((name for name, slug in MATERIALS_CAT if slug == category_slug), category_slug)
            cursor.execute("INSERT INTO categories (name, slug) VALUES (?, ?)", (name_from_dict, category_slug))
            category_id = cursor.lastrowid
            
        else:
            category_id = row[0]        
                
        cursor.execute("""
            INSERT INTO materials (category_id, title, file_type, tg_file_id, local_path, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category_id, title, file_type, tg_file_id, local_path, description))
        
        conn.commit()
        return True

# Удаляет материал по его ID
def delete_material(material_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        conn.commit()
        return cursor.rowcount > 0

# Получает список всех материалов в категории для меню
def get_materials_by_category(category_slug):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.title, m.file_type, m.tg_file_id 
            FROM materials m
            JOIN categories c ON m.category_id = c.id
            WHERE c.slug = ?
        """, (category_slug,))
        return cursor.fetchall()
 
# Получает данные конкретного файла для отправки 
def get_material_by_id(material_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, tg_file_id, local_path FROM materials WHERE id = ?", (material_id,))
        return cursor.fetchone()