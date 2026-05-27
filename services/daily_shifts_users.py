from datetime import datetime
from db import get_connection, get_users, clear_daily_shifts_table
from .sheets import get_working_staff_for_today
import asyncio, logging



logger = logging.getLogger(__name__)

def update_daily_shifts(staff_from_sheet: list):
    """
    Обновляет таблицу daily_shifts на основе данных из Google Sheets.
    
    staff_from_sheet: список фамилий сотрудников, которые работают сегодня
    """
    if not staff_from_sheet:
        print("Список сотрудников пуст. Пропуск обновления.")
        return

    # Очистка таблицы смен
    clear_daily_shifts_table()

    # Получаем всех активных пользователей из БД
    db_users = get_users(is_active=1)

    # Сопоставление по фамилии
    today_str = datetime.now().strftime("%Y-%m-%d")
    records_to_insert = []

    for user in db_users:
        real_name = user['real_name'].strip()
        if not real_name:
            continue

        # Берем только фамилию
        last_name = real_name.split()[0]

        # Сравниваем с фамилиями из Google Sheets (частичное совпадение)
        for sheet_name in staff_from_sheet:
        # Пропускаем пустые строки
            if not sheet_name or sheet_name.strip() == "":
                continue

            parts = sheet_name.split()
            # Пропускаем строки, где нет хотя бы одного слова (фамилии)
            if len(parts) < 1:
                continue

            sheet_last_name = parts[0].strip()

            if last_name.lower() == sheet_last_name.lower():
                # Совпало — формируем запись для вставки
                records_to_insert.append({
                    'user_id': user['id'],
                    'shift_date': today_str,
                    'restaurant_id': user['restaurant_id']
                })
                break  # нашли совпадение, больше не ищем

    # Вставляем найденных сотрудников в таблицу daily_shifts
    if records_to_insert:
        with get_connection() as conn:
            cursor = conn.cursor()
            for rec in records_to_insert:
                cursor.execute("""
                    INSERT OR IGNORE INTO daily_shifts (user_id, shift_date, restaurant_id)
                    VALUES (?, ?, ?)
                """, (rec['user_id'], rec['shift_date'], rec['restaurant_id']))
            conn.commit()
        
        print(f"Обновлено {len(records_to_insert)} сотрудников на смене.")
        print(f"Список: {[rec['user_id'] for rec in records_to_insert]}")
    else:
        print("Совпадений не найдено. Таблица daily_shifts осталась пустой.")
        

def refresh_daily_shifts():
    """
    Основная функция для обновления сотрудников на смене.
    Парсим Google Sheets
    Сравниваем с БД
    Обновляем таблицу daily_shifts
    """
    # Получаем список сотрудников на смене из Google Sheets 
    staff_today = get_working_staff_for_today()
    
    if not staff_today:
        print("Сегодняшние сотрудники не найдены в Google Sheets.")
        return

    # Передаем список в функцию обновления таблицы
    update_daily_shifts(staff_today)

    print("Таблица daily_shifts успешно обновлена.")
    
async def refresh_daily_shifts_async():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        refresh_daily_shifts
    )
asyncio.run(refresh_daily_shifts_async())