import json
from db import get_connection

def init_announcements_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_by INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            type TEXT NOT NULL CHECK (
                type IN ('one_time', 'daily', 'weekly', 'monthly')
            ),

            send_date TEXT,        -- YYYY-MM-DD (one_time)
            send_time TEXT,        -- HH:MM

            day_of_week INTEGER,   -- 0-6 (weekly)
            day_of_month INTEGER,  -- 1-31 (monthly)

            roles TEXT NOT NULL,   -- JSON: ["waiter","admin"]
            positions TEXT,        -- JSON или NULL

            is_active INTEGER DEFAULT 1,
            last_sent_at TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
        """)
        
# ===== СОЗДАНИЕ ОБЪЯВЛЕНИЯ =====
def create_announcement(
    *,
    created_by: int,
    restaurant_id: int,
    message: str,
    type: str,
    roles: list[str],
    send_time: str,
    send_date: str | None = None,
    day_of_week: int | None = None,
    day_of_month: int | None = None,
    positions: list[str] | None = None,
):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO announcements (
            created_by,
            restaurant_id,
            message,
            type,
            send_date,
            send_time,
            day_of_week,
            day_of_month,
            roles,
            positions
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            created_by,
            restaurant_id,
            message,
            type,
            send_date,
            send_time,
            day_of_week,
            day_of_month,
            json.dumps(roles, ensure_ascii=False),
            json.dumps(positions, ensure_ascii=False) if positions else None
        ))
        return cursor.lastrowid
    
# ===== ПОЛУЧЕНИЕ АКТИВНЫХ ОБЪЯВЛЕНИЙ =====
def get_active_announcements(type: str | None = None) -> list[dict]:
    query = "SELECT * FROM announcements WHERE is_active = 1"
    params = []

    if type:
        query += " AND type = ?"
        params.append(type)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = []
        for row in rows:
            data = dict(row)
            data["roles"] = json.loads(data["roles"])
            data["positions"] = json.loads(data["positions"]) if data["positions"] else None
            result.append(data)

        return result
    
#==== ДЕАКТИВАЦИЯ ОБЪЯВЛЕНИЯ =====
def deactivate_announcement(announcement_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE announcements SET is_active = 0 WHERE id = ?",
            (announcement_id,)
        )
        
#==== ОБНОВЛЕНИЕ ВРЕМЕНИ ПОСЛЕДНЕЙ РАССЫЛКИ =====
def mark_announcement_sent(announcement_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE announcements SET last_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (announcement_id,)
        )
        
# ===== ФУНКЦИЯ ПОЛУЧЕНИЯ ПОЛУЧАТЕЛЕЙ ОБЪЯВЛЕНИЯ =====
def get_announcement_audience(
    *,
    restaurant_id: int,
    positions: list[str],
) -> list[dict]:

    # автоматически добавляем зама директора
    roles = ["deputy_director", "director"]

    placeholders = ",".join(["?"] * len(positions))

    query = f"""
    SELECT * FROM users
    WHERE restaurant_id = ?
      AND is_active = 1
      AND (
            position IN ({placeholders})
            OR role IN ({",".join(["?"] * len(roles))})
          )
    """

    params = [restaurant_id]
    params.extend(positions)
    params.extend(roles)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
