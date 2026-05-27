from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def build_recipes_kb(recipes: list, max_chars=28, back_callback="menu_root"):
    builder = InlineKeyboardBuilder()

    for recipe in recipes:
        display_name = recipe["name"]
        if len(display_name) > max_chars:
            display_name = display_name[:max_chars-3] + "..."
        
        # Добавляем кнопку блюда
        builder.add(InlineKeyboardButton(
            text=display_name, 
            callback_data=f"recipe_{recipe['id']}"
        ))

    # Указываем, что хотим по 2 кнопки в ряд
    builder.adjust(2)

    # Добавляем кнопку "Назад" в самый низ отдельным рядом
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад", 
        callback_data=back_callback
    ))

    return builder.as_markup()


# Генерация кнопок выбора времени
TIME_OPTIONS = [8, 10, 12, 16, 20, 22]
def time_selection_kb():
    builder = InlineKeyboardBuilder()
    for h in TIME_OPTIONS:
        builder.button(
            text=f"{h}:00",
            callback_data=f"ann_time:{h}"
        )
    # Разбиваем кнопки по 2 в ряду
    builder.adjust(2)
    return builder.as_markup()


def days_of_week_kb():
    builder = InlineKeyboardBuilder()
    days = [
        ("Пн", "1"), ("Вт", "2"), ("Ср", "3"), ("Чт", "4"), 
        ("Пт", "5"), ("Сб", "6"), ("Вс", "7")
    ]
    for text, day_id in days:
        builder.button(text=text, callback_data=f"ann_dayw:{day_id}")
    builder.adjust(4, 3)
    return builder.as_markup()

def days_of_month_kb():
    builder = InlineKeyboardBuilder()
    for d in range(1, 32):
        builder.button(text=str(d), callback_data=f"ann_daym:{d}")
    builder.adjust(7) 
    return builder.as_markup()