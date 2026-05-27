from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from db import get_connection, get_all_tags, get_tag_by_id
from keyboards import build_recipes_kb, search_inline_kb, search_result_kb
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

class SearchStates(StatesGroup):
    waiting_for_name = State()


    
# Выбор типа поиска (Вызывается из меню или по кнопке Поиск)
@router.callback_query(F.data == "menu_search")
async def select_search_type(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔎 <b>КАК БУДЕМ ИСКАТЬ?</b>\nВыберите удобный вариант:",
        reply_markup=search_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработка кнопок
@router.callback_query(F.data == "search_name")
async def search_by_name_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_name)
    await callback.message.edit_text("⌨️ Введите название блюда (или его часть):")
    await callback.answer()


# ЛОГИКА ПОИСКА ПО НАЗВАНИЮ
@router.message(SearchStates.waiting_for_name)
async def process_search_name(message: types.Message, state: FSMContext):
    query = message.text.lower().strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name FROM recipes 
            WHERE lower(name) LIKE ? LIMIT 10
        """, (f"%{query}%",))
        recipes = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    if recipes:
        await message.answer(
            f"🔎 <b>Результаты по запросу «{query}»:</b>",
            reply_markup=build_recipes_kb(recipes, back_callback="menu_search"),
            parse_mode="HTML"
        )
        await state.clear() # Выходим из режима поиска
    else:
        await message.answer(
            f"Ничего не найдено по запросу «{query}» 😔",
            reply_markup=search_result_kb() # Кнопка "Искать снова"
        )

# ЛОГИКА ПОИСКА ПО ТЕГУ
@router.callback_query(F.data == "search_tag")
async def show_all_tags_search(callback: types.CallbackQuery):

    tags = get_all_tags()
    
    if not tags:
        return await callback.answer("В базе еще нет тегов", show_alert=True)

    kb = InlineKeyboardBuilder()
    # Распределяем теги по 2 в ряд
    for i in range(0, len(tags), 2):
        row_buttons = []
        # Берем текущий тег
        tag1 = tags[i]
        row_buttons.append(types.InlineKeyboardButton(
            text=f"{tag1['name']}", 
            callback_data=f"stag_{tag1['id']}"
        ))
        # Проверяем, есть ли следующий тег для пары
        if i + 1 < len(tags):
            tag2 = tags[i+1]
            row_buttons.append(types.InlineKeyboardButton(
                text=f"{tag2['name']}", 
                callback_data=f"stag_{tag2['id']}"
            ))
        kb.row(*row_buttons)

    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_search"))
    
    await callback.message.edit_text(
        "Выберите тег для поиска блюд:", 
        reply_markup=kb.as_markup()
    )
    await callback.answer()
    
@router.callback_query(F.data.startswith("stag_"))
async def process_tag_selection(callback: types.CallbackQuery):
    tag_id = int(callback.data.split("_")[-1])
    
    # Получаем имя тега для заголовка
    tag_info = get_tag_by_id(tag_id) 
    tag_name = tag_info['name'] if tag_info else "выбранному тегу"

    # Получаем блюда (используем твою логику запроса)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.name 
            FROM recipes r
            JOIN recipe_tags rt ON r.id = rt.recipe_id
            WHERE rt.tag_id = ?
        """, (tag_id,))
        recipes = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    if recipes:
        # Используем функцию сборки клавиатуры блюд
        await callback.message.edit_text(
            f"<b>Блюда с тегом «{tag_name}»:</b>",
            reply_markup=build_recipes_kb(recipes, back_callback="search_tag"),
            parse_mode="HTML"
        )
    else:
        await callback.answer(f"К тегу «{tag_name}» пока не привязаны блюда", show_alert=True)