import random

# ===== Категории =====
CATEGORY_MAP = {
    "🍹 Коктейли": "bar_cocktails",
    "🍹 Б/А Коктейли": "bar_non_alcoholic",
    "🆕🍸 Новинки Бара": "new_bar",
    "🥤🍋 Лимонады": "bar_lemonades",
    "🍷🥂 Вино/Игристое": "bar_wine",
    "🍺 Пиво": "bar_beer",
    "🥃 Шоты": "bar_strong",
    "☕🍵 Чай/Кофе": "bar_tea_coffee",
    "🧃👶 Соки/ДМ": "bar_juices",
    "🏃‍♂️ Быстрые напитки": "bar_fast",
    
    
    "🍲 Супы": "kitchen_soups",
    "🆕🍽️ Новинки Кухни": "new_kitchen",
    "🍕🍔 Пицца/Бургеры": "kitchen_pizza_burgers",
    "🍛 Горячие блюда": "kitchen_hot",
    "👶 Детское меню": "kitchen_kids",
    "🥗 Салаты": "kitchen_salads",
    "🍰 Десерты": "kitchen_desserts",
    "🍗 Закуски": "kitchen_snacks",
    "🥡 Вок/Поке": "kitchen_wok_poke",
    "🍱 Ланч дня": "lunch_of_the_day",
    
    "🎨 Вдохновение": "sushi_inspiration",
    "🍣 Суши": "sushi_sushi",
    "🥢 Роллы": "sushi_rolls",
    "🔥 Горячие роллы": "sushi_hot_rolls",
    "🍱 Сеты": "sushi_sets",
    "🆕🍣 Новинки Суши": "new_sushi"
}

MATERIALS_CAT = [
        ("🍳 Кухня", "kitchen"),
        ("🍸 Бар", "bar"),
        ("🧑‍💼 Официанты", "waiter"),
        ("🎬 Учебные видео", "video"),
        ("📚 Для админов", "admin"),
        ("📋 Бланки этапов", "stages")
    ]


POSITIONS_MAP = {
    "waiter": "Официант",
    "cook": "Повар",
    "bartender": "Бармен",
    "admin": "Админ ресторана",
    "deputy_director": "Зам. директора"
}

POSITIONS_MAP_ANNO = {
    "waiter": "Официант",
    "cook": "Повар",
    "bartender": "Бармен",
    "admin": "Админ ресторана"    
}

ROLES_MAP = {
    "director": "Директор",
    "deputy_director": "Зам. директора",
    "content_maker": "Контент-мейкер",
    "user": "Сотрудник",
    "chef": "Шеф-повар",
    "regional_manager": "Региональный менеджер"
}


TOPICS = {
    "stoplist": "Стоп-лист",
    "long_wait": "Долгая отдача",
    "quality": "Качество блюд",
    "tech": "Технические поломки",
    "conflict": "Конфликты",
    "order_error": "Ошибки в заказах",
    "no_staff": "Нехватка персонала",
    "bad_comm": "Плохая коммуникация",
    "no_clean_dishes": "Нехватка чистой посуды",
}

THANKS_CATEGORIES = {
    "help": "🤝 Помощь",
    "support": "💛 Поддержка",
    "professionalism": "🎯 Профессионализм",
    "initiative": "🚀 Инициатива",
    "atmosphere": "✨ Атмосфера на смене"
}

QUIZ_CATEGORIES = {
    "hot_kitchen": "🍳 Горячий цех",
    "sushibar": " 🍣Сушибар",
    "bar": "🍹 Бар",
    "service_standards": "🤝 Обслуживание",
    "gastronomy": "🧠 Гастрономический",
    "super": "💎 Супер квиз (20 воп.)"
}

ACHIEVEMENTS = {
    "first_quiz": {
        "title": "Первый шаг",
        "description": "Пройден первый квиз",
        "icon": "🥉"
    },
    "quiz_master": {
        "title": "Эрудит",
        "description": "Пройдено 10 квизов",
        "icon": "🥈"
    },
    "perfect_quiz": {
        "title": "Без ошибок",
        "description": "Пройден квиз на 100%",
        "icon": "🥇"
    }
}

STICKERS_COLLECTION = {
    "super": [
        "CAACAgIAAxkBAAEQOKtpY87SPhoizv0t3UVsoAGGUq9D3gACDgYAAtJaiAE5YXnAD_BKGjgE",
        "CAACAgQAAxkBAAEQOK1pY89VFuWViupZyi1WOsMIE9o3hAACuQADS2nuEIlbeQlz_kbbOAQ",
        "CAACAgIAAxkBAAEQOK9pY89u4NSS89m5VJEP1Pryco9MPAACBBUAAnrwQEpGmLybrR9udzgE",
        "CAACAgQAAxkBAAEQOLFpY8-BU6veSFUaIxJhizILgMBhJgACjxAAAgvviVO1ton_7TxcaDgE",
        "CAACAgIAAxkBAAEQOLNpY8-mWrTA-R95KzEE6lqvueSEDAACiQIAAladvQqhVs0CITIOPTgE",
        "CAACAgIAAxkBAAEQOLVpY8_beW0eN0qtlejgBIC_w_xicgACqxIAAsrtSEhyK3vHAwcKczgE",
        "CAACAgIAAxkBAAEQOLdpY8_uDwABVg_0fxrdC8G2QkMKxjcAAkQTAAIWWklI0B-Czv8lIy04BA",
        "CAACAgIAAxkBAAEQM1lpX9ZAptWGyQ1u0Z2RsYLX3YlY3AACKAADDkfHKGqXGl2kLmEoOAQ",
        "CAACAgIAAxkBAAEQPDtpZpG_ozOYKWNyrMfYkkxoIZH9lwACF1AAAt-ZCUnDXulhLPr4GzgE",
    ],
    "good": [
        "CAACAgIAAxkBAAEQOLtpY9FazziwKXF5-LoUzKXdKFjz6gACCwADDkfHKKig9PrirOHBOAQ",
        "CAACAgIAAxkBAAEQOL1pY9F39Ma22tGqm1ruIGKj8yvZ_gACKgYAAtJaiAHX5pR2ThC37zgE",
        "CAACAgIAAxkBAAEQOL9pY9GFkYis-WVkzxam4nXKf7qbpAACEgYAAtJaiAH3r7K1PEN3dDgE",
        "CAACAgIAAxkBAAEQOMFpY9GVEb2UX7lR0ZN1BYVx2qNmKAACfgIAAladvQpBYnRfUWys5DgE",
        "CAACAgIAAxkBAAEQOMNpY9G3LiMiP5dS3JyflOHTn_75CAAC2xwAApidqUjmAAFlTGcefRw4BA",
        "CAACAgIAAxkBAAEQOMVpY9HFDFm7DwYr78QQ_OpJMxSDugAC0iMAAulVBRgR5I0Cv1pWvDgE",
        "CAACAgIAAxkBAAEQOMdpY9H57r4FS_2w49BLR6PQUuxdrQACJgMAArVx2gY-GQuL5xwZQDgE",
    ],
    "support": [
        "CAACAgIAAxkBAAEQOMlpY9IeuDiL9VFXjyEPzQr8wjGo2gACKQADDkfHKDgROvRoHiGFOAQ", 
        "CAACAgIAAxkBAAEQONFpY9LTEugkCvJYjeuoTWFpMaxEcQACgwQAAsxUSQllj8X9R9oK0zgE", 
        "CAACAgIAAxkBAAEQONdpY9MiwItW6Hu5TGAH6zlwwmyyhgAClxgAAtIAATlKiiaampFkk484BA",
        "CAACAgIAAxkBAAEQONtpY9OmuepvStxqcwSmq3AFxYEZqAACBwADwDZPE0hhd1MIpyLHOAQ",
        "CAACAgIAAxkBAAEQOOVpY9SKOSNJcYGkJM8AAaVD8kl3XCIAAqMnAAIDuDhIIGyDiDI9qek4BA",
        "CAACAgIAAxkBAAEQOOdpY9S3qiEZw0BGIV4ZlyL7ujfX4gACgQkAAhhC7ggdrAXA26gH7DgE",
    ],
    "kudos": [
        "CAACAgIAAxkBAAEQOLtpY9FazziwKXF5-LoUzKXdKFjz6gACCwADDkfHKKig9PrirOHBOAQ", 
        "CAACAgIAAxkBAAEQOL1pY9F39Ma22tGqm1ruIGKj8yvZ_gACKgYAAtJaiAHX5pR2ThC37zgE", 
        "CAACAgIAAxkBAAEQOLNpY8-mWrTA-R95KzEE6lqvueSEDAACiQIAAladvQqhVs0CITIOPTgE",
        "CAACAgIAAxkBAAEQOKtpY87SPhoizv0t3UVsoAGGUq9D3gACDgYAAtJaiAE5YXnAD_BKGjgE",
        "CAACAgIAAxkBAAEQQW1paoG9jESHIll9Y7VZsyQPXXb8OgACDwADDkfHKCnIXzw4qLKjOAQ",
        "CAACAgIAAxkBAAEQQW9paoHgOU0okzo6DRj06L67fIbBVAAC-wUAAtJaiAEK_F4c8hn9yzgE",
        "CAACAgQAAxkBAAEQQXNpaoIT22gAAWzEKQrK1J7fuQyswCkAArkAA0tp7hCJW3kJc_5G2zgE",
        "CAACAgIAAxkBAAEQQXVpaoI-7m-nXUQtGudvWEWkrLeEYwAChQkAAhhC7giKfFqZOBzASzgE",
        "CAACAgIAAxkBAAEQQXlpaoJ5B7d84kiNPJyeTzblk48ybAACzBMAApofyEhgXH8zd2teojgE",
        "CAACAgIAAxkBAAEQQXtpaoKzP8Gd0-gyUMzEK2mYtrGTsAACfQQAAsxUSQnK6DiyVWk87TgE",
    ]
}

# Возвращает случайный ID стикера из выбранной категории
def get_random_sticker(category: str) -> str:
    return random.choice(STICKERS_COLLECTION.get(category, STICKERS_COLLECTION["good"]))