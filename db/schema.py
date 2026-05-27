import os
from db import get_connection
from config import DATABASE_PATH

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")      
        cursor = conn.cursor()

 
        
        # ===== БЛЮДА =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER,
            price_red INTEGER,           
            photo_path TEXT,
            photo_file_id TEXT,
            short_composition TEXT,
            presentation_text TEXT
        )
        """)
        
        # ===== КАТЕГОРИИ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_categories (
            recipe_id INTEGER NOT NULL,
            category_code TEXT NOT NULL,
            PRIMARY KEY (recipe_id, category_code),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        """)

        # ===== ТЕХНОЛОГИЯ (ТТК) =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_tech (
            recipe_id INTEGER PRIMARY KEY,            
            steps TEXT,
            yield_weight TEXT,            
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        """)

        # ===== КОМПОНЕНТЫ БЛЮДА =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_structure_simple (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            item_name TEXT,
            item_weight TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        """)



        #===== СОУСЫ / ЗАГОТОВКИ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sauces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            steps TEXT,
            yield_weight TEXT
        )
        """)

        # ===== СОСТАВ СОУСОВ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sauce_structure_simple (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sauce_id INTEGER,
            item_name TEXT,
            item_weight TEXT,
            FOREIGN KEY (sauce_id) REFERENCES sauces(id) ON DELETE CASCADE
        )
        """)
        
        # ===== СВЯЗЬ БЛЮДА И СОУСОВ (КАКИЕ СОУСЫ ИДУТ К БЛЮДУ) =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_sauces (
            recipe_id INTEGER,
            sauce_id INTEGER,
            PRIMARY KEY (recipe_id, sauce_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (sauce_id) REFERENCES sauces(id) ON DELETE CASCADE
        )
        """)
                
        # ===== ТЕГИ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_tags (
            recipe_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (recipe_id, tag_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """)

        # Учебные материалы
        # Таблица категорий 
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE  -- 'kitchen', 'bar', 'waiter', 'video', 'admin', 'stages'
        )
        """)

        # Таблица материалов
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            title TEXT NOT NULL,       -- Название для кнопки
            file_type TEXT,            -- 'pdf', 'word', 'excel', 'video'
            tg_file_id TEXT,           -- ID файла в Telegram
            local_path TEXT,           -- Путь к файлу на диске
            description TEXT,          -- Короткое описание (опционально, удобно для видео)
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        );
        """)
                
        # ===== РЕСТОРАНЫ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        
        # ===== ПОЛЬЗОВАТЕЛИ =====        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, -- telegram_id
            full_name TEXT,
            real_name TEXT,
            role TEXT NOT NULL CHECK (
                role IN ('director', 'deputy_director', 'content_maker', 'user', 'chef', 'regional_manager')
            ),
            restaurant_id INTEGER,
            position TEXT CHECK (
                position IN ('waiter', 'cook', 'bartender', 'admin') OR position IS NULL
            ),
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
        """)

        # ===== СОТРУДНИКИ НА СМЕНЕ СЕГОДНЯ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shift_date TEXT NOT NULL, -- Дата смены в формате YYYY-MM-DD
            restaurant_id INTEGER NOT NULL, -- ID ресторана (для удобства фильтрации)
            FOREIGN KEY (user_id) REFERENCES users(id), -- Ссылка на таблицу users
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            UNIQUE(user_id, shift_date) -- Гарантирует, что сотрудник не задвоится в смене за день
        )
        """)

        # ===== КАЛЕНДАРЬ СОБРАНИЙ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,            
            date DATE UNIQUE,
            topic TEXT,
            content TEXT,
            UNIQUE(restaurant_id, date),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        )
        """)

        # ===== КАЛЕНДАРЬ СОБЫТИЙ=====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS special_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            date DATE NOT NULL,                  
            event_type TEXT,            -- 'inventory', 'cleaning', 'training'
            description TEXT,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        )
        """)

        # ===== Цели месяца =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            goal_text TEXT,             
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(restaurant_id, year, month),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        )
        """)

        # ===== ОТЧЕТЫ О ЗАКРЫТИИ СМЕН =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shift_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            
            -- Новые поля для аналитики:
            cash_percentage REAL,       -- Процент наличной выручки (0.0 до 100.0)
            fast_drinks_rating REAL,    -- Рейтинг "быстрых напитков" (0.0 до 100.0)

            incidents_log TEXT,         -- Инциденты/косяки за смену
            atmosphere_comment TEXT,    -- Комментарий по атмосфере/проблемам

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
        """)
        
        # ===== КЭШ СООБЩЕНИЙ С ОТЧЕТОМ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS morning_posts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_date TEXT NOT NULL, -- Дата рассылки в формате YYYY-MM-DD
            message_text TEXT NOT NULL, -- Полный текст сообщения с HTML форматированием
            UNIQUE(user_id, post_date) -- Гарантирует уникальность записи для пользователя и дня
        )
        """)
                
        # ===== ЛИМИТЫ ПО "СПАСИБО" =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_social_limits (
            user_id INTEGER PRIMARY KEY,
            thanks_week_limit INTEGER NOT NULL DEFAULT 7,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        
        # ===== СОБЫТИЯ БЛАГОДАРНОСТЕЙ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gratitude_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            restaurant_id INTEGER NOT NULL,
            shift_date TEXT NOT NULL,
            FOREIGN KEY (from_user_id) REFERENCES users(id),
            FOREIGN KEY (to_user_id) REFERENCES users(id)
        )
        """)
        
        # ===== ВИКТОРИНЫ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            option_1 TEXT NOT NULL,
            option_2 TEXT NOT NULL,
            option_3 TEXT NOT NULL,
            option_4 TEXT NOT NULL,
            correct_option INTEGER NOT NULL CHECK(correct_option BETWEEN 1 AND 4),
            hint TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # ===== СЕССИИ ВИКТОРИН =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            total_questions INTEGER NOT NULL DEFAULT 10,
            correct_answers INTEGER NOT NULL DEFAULT 0,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME,
            passed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        
        # ===== ОТВЕТЫ ВИКТОРИН =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_session_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option INTEGER,
            is_correct INTEGER,
            answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES quiz_sessions(id),
            FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
        )
        """)
        
        #===== ОБЪЯВЛЕНИЯ =====
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_by INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL CHECK (
                type IN ('one_time', 'daily', 'weekly', 'monthly')
            ),
            send_date TEXT,                            -- YYYY-MM-DD (для one_time)
            send_time TEXT,                            -- HH:MM (для всех типов)
            day_of_week INTEGER,                       -- 0–6 (weekly, APScheduler)
            day_of_month INTEGER,                     -- 1–31 (monthly)

            roles TEXT NOT NULL,
            positions TEXT,

            is_active INTEGER DEFAULT 1,               -- 0 = выключено
            last_sent_at TEXT,                         -- для аналитики / отладки

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
        """)
        
                        
        # ===== ВЕРСИЯ СХЕМЫ БАЗЫ ДАННЫХ =====        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
        """)        
         
     
        conn.commit()
        
