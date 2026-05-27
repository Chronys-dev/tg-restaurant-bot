from db import get_connection

# Создает или обновляет тему собрания на конкретную дату
def set_meeting(cursor, restaurant_id, date, topic, content=None):
    cursor.execute("""
        INSERT INTO meetings (restaurant_id, date, topic, content)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(restaurant_id, date) DO UPDATE SET
        topic = excluded.topic,
        content = excluded.content
    """, (restaurant_id, date, topic, content))


# Получает данные собрания на дату
def get_meeting(cursor, restaurant_id, date): 
    cursor.execute("SELECT * FROM meetings WHERE restaurant_id = ? AND date = ?", (restaurant_id, date))
    row = cursor.fetchone()
    return dict(row) if row else None
    
# Возвращает словарь {день: [список_типов]} для отрисовки иконок
def get_month_events(restaurant_id, year, month):
    # Формируем маску года-месяца 'YYYY-MM-%'
    date_pattern = f"{year}-{month:02d}-%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, event_type FROM special_events 
            WHERE restaurant_id = ? AND date LIKE ?
        """, (restaurant_id, date_pattern))
        
        events_map = {}
        for row in cursor.fetchall():
            # Извлекаем день из строки 'YYYY-MM-DD'
            day = int(row['date'].split('-')[2])
            if day not in events_map:
                events_map[day] = []
            events_map[day].append(row['event_type'])
        return events_map
    
# Добавить событие
def add_special_event(cursor, restaurant_id, date, event_type, description):
    cursor.execute("""
        INSERT INTO special_events (restaurant_id, date, event_type, description)
        VALUES (?, ?, ?, ?)
    """, (restaurant_id, date, event_type, description))
        
# ======== Цели месяца ========
# Получить
def get_monthly_goal(cursor, restaurant_id, year, month):
    cursor.execute("""
        SELECT goal_text FROM monthly_goals 
        WHERE restaurant_id = ? AND year = ? AND month = ?
    """, (restaurant_id, year, month))
    row = cursor.fetchone()
    return row['goal_text'] if row else "Цель на месяц не установлена"

# Установить цель
def set_monthly_goal(cursor, restaurant_id, year, month, goal_text):
    cursor.execute("""
        INSERT INTO monthly_goals (restaurant_id, year, month, goal_text)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(restaurant_id, year, month) DO UPDATE SET
        goal_text = excluded.goal_text,
        updated_at = CURRENT_TIMESTAMP
    """, (restaurant_id, year, month, goal_text))

# список событий
def get_day_events(cursor, restaurant_id, date):
    cursor.execute("""
        SELECT event_type, description FROM special_events 
        WHERE restaurant_id = ? AND date = ?
    """, (restaurant_id, date))
    return [dict(row) for row in cursor.fetchall()]

# Удалить событие
def delete_event(cursor, restaurant_id: int, event_id: int):
    """Удаляет конкретное событие, проверяя принадлежность к ресторану"""
    cursor.execute(
        "DELETE FROM special_events WHERE id = ? AND restaurant_id = ?",
        (event_id, restaurant_id)
    )

# Вспомогательная функция: получаем события вместе с их ID для кнопок удаления
def get_day_events_with_ids(cursor, restaurant_id, date):
    cursor.execute("""
        SELECT id, event_type, description FROM special_events 
        WHERE restaurant_id = ? AND date = ?
    """, (restaurant_id, date))
    return [dict(row) for row in cursor.fetchall()]

# Сохраняет или обновляет кэшированный текст утренней рассылки 
def save_newsletter_to_cache(user_id: int, post_date: str, message_text: str):  
    with get_connection() as conn:
        cursor = conn.cursor()
        # Используем INSERT OR REPLACE для обработки уникального ограничения (UNIQUE(user_id, post_date))
        cursor.execute("""
            INSERT OR REPLACE INTO morning_posts_cache 
            (user_id, post_date, message_text) VALUES (?, ?, ?)
        """, (user_id, post_date, message_text))
        conn.commit()

# Извлекает кэшированный текст утренней рассылки для конкретного пользователя и даты
def get_cached_newsletter_text(user_id: int, post_date: str) -> str | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message_text FROM morning_posts_cache 
            WHERE user_id = ? AND post_date = ?
        """, (user_id, post_date))
        
        result = cursor.fetchone()
        
        if result:
            # Возвращаем текст сообщения из словаря/кортежа результата
            return result['message_text'] if isinstance(result, dict) else result[0]
        else:
            return None