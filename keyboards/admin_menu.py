from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_main_inline_kb():
    builder = InlineKeyboardBuilder()
    
    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="🍽 Блюда и Соусы", callback_data="adm_section_dishes_sauces"),
        InlineKeyboardButton(text="🏬 Управление ресторанами", callback_data="adm_section_restaurants")
    )
    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="📚 Учебные материалы", callback_data="adm_section_materials"),
        InlineKeyboardButton(text="📊 Отчеты и Стата", callback_data="adm_section_stats")
    )
    # Третий ряд
    builder.row(
        InlineKeyboardButton(text="🧑 Персонал", callback_data="adm_section_staff"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="adm_section_broadcast")
    )

    builder.row(
        InlineKeyboardButton(text="❌ Закрыть панель", callback_data="close_menu")
    )    
    return builder.as_markup()


def dishes_sauces_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🍽 Управление блюдами", callback_data="adm_section_recipes"),
        InlineKeyboardButton(text="🥣 Управление соусами", callback_data="adm_section_sauces")
    )
    builder.row(
        InlineKeyboardButton(text="📌 Управление тегами", callback_data="adm_section_tags")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_main")
    )    
    return builder.as_markup()
   
def manage_recipes_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="adm_rec_add"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="adm_rec_edit")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_main"))
    
    return builder.as_markup()

def manage_sauces_inline_kb():
    builder = InlineKeyboardBuilder()    
    builder.row(InlineKeyboardButton(text="➕🥣 Добавить соус", callback_data="adm_sauce_add"))
    builder.row(
        InlineKeyboardButton(text="✏️🥣 Редактировать", callback_data="adm_sauce_edit"),
        InlineKeyboardButton(text="🗑🥣 Удалить", callback_data="adm_sauce_del")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_main"))
    
    return builder.as_markup()
  
def manage_tags_inline_kb():
    builder = InlineKeyboardBuilder()    
    builder.row(
        InlineKeyboardButton(text="➕📌 Добавить тег", callback_data="adm_tag_add"),
        InlineKeyboardButton(text="🗑📌 Удалить тег", callback_data="adm_tag_del")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_main"))
    
    return builder.as_markup()


