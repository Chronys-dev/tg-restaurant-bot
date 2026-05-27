import calendar
from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData




class CalendarCallback(CallbackData, prefix="calendar"):
    action: str  # 'day', 'prev', 'next', 'ignore', 'set_goal'
    year: int
    month: int
    day: int = 0

def get_calendar_markup(restaurant_id: int, year: int, month: int, goal: str, events: dict, can_edit: bool = False):

    
    builder = InlineKeyboardBuilder()    
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Текст над календарем (используем переданный goal)
    header_text = f"📅 <b>{month_names[month-1]} {year}</b>\n\n🎯 {goal}"
    
    # Кнопка-заголовок (неактивная)
    builder.row(InlineKeyboardButton(
        text=f"{month_names[month-1]} {year}", 
        callback_data="ignore"
    ))

    # Дни недели
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="ignore") for d in days_of_week])

   
    # Маппинг иконок
    icons = {
        'inventory': '📦',
        'cleaning': '✨',
        'training': '🎓',
        'birthday': '🎂',
        'general': '⚠️',
        'supplier_order': '🛒'
    }

    # Сетка календаря
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        buttons = []
        for day in week:
            if day == 0:
                buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                # Проверяем наличие событий и добавляем иконку
                day_text = str(day)
                if day in events:
                    # Берем иконку первого типа события
                    main_event = events[day][0]
                    day_text += icons.get(main_event, '📍')
                
                buttons.append(InlineKeyboardButton(
                    text=day_text,
                    callback_data=CalendarCallback(action="day", year=year, month=month, day=day).pack()
                ))
        builder.row(*buttons)

    # Навигация
    builder.row(
        InlineKeyboardButton(text="⬅️", callback_data=CalendarCallback(action="prev", year=year, month=month).pack()),
        InlineKeyboardButton(text="➡️", callback_data=CalendarCallback(action="next", year=year, month=month).pack())
    )
    
    # Кнопки спец. действий (директор, зам, создатель)
    if can_edit:
        builder.row(InlineKeyboardButton(
            text="🎯 Установить цель месяца", 
            callback_data=CalendarCallback(action="set_goal", year=year, month=month).pack()
        ))
        
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_mailing_section"))

    return header_text, builder.as_markup()