from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from permissions import is_owner
from db import get_user

# Основное меню
def main_menu_kb(user_id: int):
    user = get_user(user_id)
    owner = is_owner(user_id)
    
    # 1. Проверка доступа
    if not owner and (not user or user.get("is_active") != 1):
        return None

    keyboard = []
    
    # 2. Если вы Владелец — добавляем кнопку Админ-панели в самый верх
    if owner:
        keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])

    # 3. Базовые кнопки — видят все авторизованные
    keyboard.append([
    KeyboardButton(text="📖 Меню"),
    KeyboardButton(text="📚 Учебные материалы")
    ])
    keyboard.append([
    KeyboardButton(text="🗣️ Обратная связь"),
    KeyboardButton(text="👤 Личный кабинет")
    ])
    
    # 4. Если пользователь есть в базе, проверяем его роль
    if user:
        role = user.get("role")
        position = user.get("position", "") 

            
        if position == "admin":
            keyboard.append([KeyboardButton(text="📢 События и календарь")])


        # Кнопки для Шефа / Контент-менеджера
        if role in ["content_maker", "chef"]:
            keyboard.append([KeyboardButton(text="📢 События и календарь")])

        # Кнопки для Директора и Заместителя

        if role in ["director", "deputy_director"]:
            keyboard.append([
                KeyboardButton(text="📢 События и календарь"), 
                KeyboardButton(text="🧑 Управление персоналом")
            ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ===== Рецепты =====
def recipe_inline_kb():
    builder = InlineKeyboardBuilder()
    
    # Кнопки цехов
    builder.row(
        InlineKeyboardButton(text="🍣 Суши-бар", callback_data="dept_sushi"),
        InlineKeyboardButton(text="🔥 Горячий цех", callback_data="dept_kitchen")
    )
    builder.row(
        InlineKeyboardButton(text="🍸 Бар", callback_data="dept_bar"),
        InlineKeyboardButton(text="🔍 Поиск Блюда/Напитка", callback_data="menu_search")
    )
    builder.row(
        InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀❌ Закрыть главное меню⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="close_menu")
    )    
    return builder.as_markup()
    
# ===== Бар =====
def bar_menu_inline_kb():
    builder = InlineKeyboardBuilder()
    

    builder.row(
        InlineKeyboardButton(text="🍹 Коктейли", callback_data="bar_cocktails"),
        InlineKeyboardButton(text="🥤🍋 Лимонады", callback_data="bar_lemonades")
    )
    builder.row(
        InlineKeyboardButton(text="🍷🥂 Вино/Игристое", callback_data="bar_wine"),
        InlineKeyboardButton(text="🍺 Пиво", callback_data="bar_beer")
    )
    builder.row(
        InlineKeyboardButton(text="🥃 Шоты", callback_data="bar_strong"),
        InlineKeyboardButton(text="☕🍵 Чай/Кофе", callback_data="bar_tea_coffee")
    )
    builder.row(
        InlineKeyboardButton(text="🧃👶 Соки/ДМ", callback_data="bar_juices"),
        InlineKeyboardButton(text="🏃‍♂️ Быстрые напитки", callback_data="bar_fast")
    )

    builder.row(InlineKeyboardButton(text="🆕🍸 Новинки Бара", callback_data="new_bar"),
                InlineKeyboardButton(text="🍹 Б/А Коктейли", callback_data="bar_non_alcoholic"))
    builder.row(InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀⬅️ Вернуться в меню⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="menu_root"))
    
    return builder.as_markup()

# ===== Кухня =====
def kitchen_menu_inline_kb():
    builder = InlineKeyboardBuilder()


    builder.row(
        InlineKeyboardButton(text="🍛 Горячие блюда", callback_data="kitchen_hot"),
        InlineKeyboardButton(text="🍕🍔 Пицца/Бургеры", callback_data="kitchen_pizza_burgers")
    )
    builder.row(
        InlineKeyboardButton(text="🍲 Супы", callback_data="kitchen_soups"),
        InlineKeyboardButton(text="👶 Детское меню", callback_data="kitchen_kids")
    )
    builder.row(
        InlineKeyboardButton(text="🥗 Салаты", callback_data="kitchen_salads"),
        InlineKeyboardButton(text="🍰 Десерты", callback_data="kitchen_desserts")
    )
    builder.row(
        InlineKeyboardButton(text="🍗 Закуски", callback_data="kitchen_snacks"),
        InlineKeyboardButton(text="🥡 Вок/Поке", callback_data="kitchen_wok_poke")
    )

    builder.row(
        InlineKeyboardButton(text="🆕🍽️ Новинки Кухни", callback_data="new_kitchen"),
        InlineKeyboardButton(text="🍱 Ланч дня", callback_data="lunch_of_the_day")        
    )

    builder.row(InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀⬅️ Вернуться в меню⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="menu_root"))
    
    return builder.as_markup()

# ===== Суши =====
def sushi_menu_inline_kb():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎨 Вдохновение", callback_data="sushi_inspiration"),
        InlineKeyboardButton(text="🔥 Горячие роллы", callback_data="sushi_hot_rolls")
    )
    builder.row(
        InlineKeyboardButton(text="🥢 Роллы", callback_data="sushi_rolls"),
        InlineKeyboardButton(text="🍣 Суши", callback_data="sushi_sushi")
    )
    builder.row(
        InlineKeyboardButton(text="🍱 Сеты", callback_data="sushi_sets"),
        InlineKeyboardButton(text="🆕🍣 Новинки", callback_data="new_sushi")
    )
    
    builder.row(InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀⬅️ Вернуться в меню⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="menu_root"))
    
    return builder.as_markup()

# ===== Учебные материалы =====
def material_menu_inline_kb(user_id: int | None = None):
    builder = InlineKeyboardBuilder()

    # Определяем доступы по роли/должности
    role = None
    position = None
    try:
        if user_id is not None:
            user = get_user(user_id)
            if user:
                role = user.get("role")
                position = user.get("position")
    except Exception:
        pass

    # Все видят эти разделы
    builder.row(
        InlineKeyboardButton(text="🍳 Кухня", callback_data="study_kitchen"),
        InlineKeyboardButton(text="🍸 Бар", callback_data="study_bar")
        )
    builder.row(
            InlineKeyboardButton(text="🧑‍💼 Официанты", callback_data="study_waiter"),
            InlineKeyboardButton(text="🎬 Учебные видео", callback_data="study_video")
        )

    # Раздел для админов доступен директорам, контентмейкеру, шефу и администраторам по должности
    if role in ["director", "deputy_director", "content_maker", "chef"] or position == "admin":
        builder.row(
            InlineKeyboardButton(text="📚 Для админов", callback_data="study_admin"),
            InlineKeyboardButton(text="📋 Бланки этапов", callback_data="study_stages")
        )

    builder.row(InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀⬅️ Вернуться в меню⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="menu_root"))

    return builder.as_markup()
 
# ===== Календарь и рассылка ===== 
def mailing_manage_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗓 Календарь", callback_data="adm_manage_calendar"))
    builder.row(InlineKeyboardButton(text="📣 Сделать объявление", callback_data="adm_make_announcement"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_root"))
    return builder.as_markup()
    
# ===== Кнопка Назад =====   
def back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu_root"))
    return builder.as_markup()

# ===== Кнопка Пропустить ===== 
def skip_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_step"))
    return builder.as_markup()

# ===== Кнопки поиска =====
def search_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 По названию", callback_data="search_name"),
        InlineKeyboardButton(text="📌 По тегу", callback_data="search_tag")
    )
    builder.row(        
        InlineKeyboardButton(text="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⬅️ Вернуться в меню⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", callback_data="menu_root"))
    return builder.as_markup()

# ===== Кнопки после поиска =====
def search_result_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Искать снова", callback_data="search_name"),
        InlineKeyboardButton(text="⬅️ Вернуться в меню", callback_data="menu_root")
    )
    return builder.as_markup()

def cancel_kb(back_cb: str):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))
    return kb.as_markup()