import datetime, calendar
from config import CLIENT
import gspread
from db import get_connection


def get_current_worksheet_title():
    """
    Определяет название вкладки в Google Таблице на основе сегодняшней даты
    """
    today = datetime.datetime.now()

    # Словарь с русскими названиями месяцев
    russian_months = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август", 
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    # Получаем название текущего месяца из словаря
    month_name = russian_months.get(today.month, "Неизвестный месяц")
    last_day = calendar.monthrange(today.year, today.month)[1]

    # Определяем, какая сейчас половина месяца
    if today.day <= 15:
        date_range = "1-15"
    else:
        date_range = f"16-{last_day}"

    # Создаем итоговое название вкладки
    worksheet_title = f"{month_name} {date_range}"
    
    return worksheet_title



SPREADSHEET_NAME = "График Лен95"
QUIZ_TAB_NAME = "TG Polls"

def get_working_staff_for_today():
    """
    Подключается к Google Таблице, определяет сегодняшний день 
    и возвращает список фамилий сотрудников, имеющих запись в ячейке.
    """
    worksheet_title = get_current_worksheet_title()
    try:
        sheet = CLIENT.open(SPREADSHEET_NAME).worksheet(worksheet_title)
        all_values = sheet.get_all_values()

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Ошибка: Таблица '{SPREADSHEET_NAME}' или лист '{worksheet_title}' не найдены.")
        return []
    except Exception as e:
        print(f"Произошла ошибка при доступе к Google Sheets: {e}")
        return []

    if not all_values:
        return []


    today_date_str = datetime.datetime.now().strftime("%d.%m")

    date_row = all_values[0]
    
    # Находим индекс столбца
    today_column_index = -1
    for i in range(3, len(date_row)):
        if date_row[i] == today_date_str:
            today_column_index = i
            break
            
    if today_column_index == -1:
        print(f"Сегодняшняя дата '{today_date_str}' не найдена в расписании.")
        return []

    working_today = []
    
    # Итерируемся по сотрудникам 
    for row in all_values[2:]:
        if len(row) > today_column_index and len(row) > 2:
            last_name = row[1]  # Столбец В
            cell_value = row[today_column_index]            

            if cell_value and cell_value.strip() != "":
                working_today.append(last_name)
                
    return working_today


def import_quiz_questions():
    sheet = CLIENT.open(SPREADSHEET_NAME).worksheet(QUIZ_TAB_NAME)
    rows = sheet.get_all_values()[1:]  # пропускаем заголовок

    inserted_count = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        # Полная очистка таблицы
        cursor.execute("DELETE FROM quiz_session_answers")
        cursor.execute("DELETE FROM quiz_sessions")
        cursor.execute("DELETE FROM quiz_questions")

        cursor.execute("DELETE FROM sqlite_sequence WHERE name='quiz_questions'")

        # Импорт вопросов
        for row in rows:
            if not row or not row[0].strip():
                continue 

            parts = row[0].split("||")
            if len(parts) < 8:
                continue

            category = parts[0].strip()
            question = parts[1].strip()
            option_1 = parts[2].strip()
            option_2 = parts[3].strip()
            option_3 = parts[4].strip()
            option_4 = parts[5].strip()

            try:
                correct_option = int(parts[6].strip())
                if not 1 <= correct_option <= 4:
                    continue
            except ValueError:
                continue

            hint = parts[7].strip() if len(parts) > 7 else None

            cursor.execute("""
                INSERT INTO quiz_questions (
                    category,
                    question,
                    option_1,
                    option_2,
                    option_3,
                    option_4,
                    correct_option,
                    hint
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category,
                question,
                option_1,
                option_2,
                option_3,
                option_4,
                correct_option,
                hint
            ))

            inserted_count += 1

        conn.commit()

    print(f"♻️ Квиз обновлён. Загружено {inserted_count} вопросов.")
