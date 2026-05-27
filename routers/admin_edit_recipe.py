import os, re, asyncio
from typing import List, Dict
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loader import bot
from permissions import is_owner
from keyboards import admin_main_inline_kb, CATEGORY_MAP
from db import (
    get_recipes, get_recipe_by_id, update_recipe, delete_recipe,
    get_recipe_tech, search_recipes_by_name, get_connection,
    get_all_sauces, get_recipe_sauces, set_recipe_sauces,
    get_all_tags, get_tags_for_recipe, set_recipe_tags
)

router = Router()

# FSM состояния
class EditRecipe(StatesGroup):
    waiting_method = State()
    waiting_search_query = State()
    waiting_categories = State()
    waiting_recipe_choice = State()
    main_edit_menu = State()
    waiting_new_value = State()
    waiting_yield_weight = State()
    waiting_selection = State()
    waiting_category_edit = State()
    waiting_sauce_selection = State()
    waiting_tag_selection = State()
    
    
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def parse_ingredients_text(text: str) -> List[Dict[str, str]]:

    ingredients = []
    for line in text.strip().split('\n'):
        if not line.strip(): continue
        # Пытаемся отделить название от веса (например, 'Лосось 100г' или 'Соль по вкусу')
        match = re.match(r"^(.*?)\s*(\d+[гк мл]+|[\d\.,/]+.+)$", line.strip())
        if match:
            ingredients.append({"item_name": match.group(1).strip(), "item_weight": match.group(2).strip()})
        else:
            ingredients.append({"item_name": line.strip(), "item_weight": "по вкусу"})
    return ingredients

# Универсальная клавиатура для соусов/тегов с галочками
def build_multi_select_kb(items: list, selected_ids: list, prefix: str):

    kb = InlineKeyboardBuilder()
    for item in items:
        is_sel = item['id'] in selected_ids
        kb.row(types.InlineKeyboardButton(
            text=f"{'✅' if is_sel else '☑️'} {item['name']}",
            callback_data=f"{prefix}_{item['id']}"
        ))
    kb.row(types.InlineKeyboardButton(text="💾 Сохранить", callback_data=f"{prefix}_done"))
    return kb.as_markup()

# ЛОГИКА ПОИСКА И ВЫБОРА
@router.callback_query(F.data == "adm_rec_edit")
async def start_edit_recipe(callback: types.CallbackQuery, state: FSMContext):

    if not is_owner(callback.from_user.id): 
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔍 Найти по названию", callback_data="method_search"))
    kb.row(types.InlineKeyboardButton(text="📂 Выбрать по категории", callback_data="method_cats"))

    await callback.message.edit_text(
        "Как найти блюдо для редактирования?", 
        reply_markup=kb.as_markup()
    )
    
    await state.set_state(EditRecipe.waiting_method)
    await callback.answer()

@router.callback_query(F.data == "method_search", EditRecipe.waiting_method)
async def ask_search_query(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название блюда (можно часть):")
    await state.set_state(EditRecipe.waiting_search_query)

@router.message(EditRecipe.waiting_search_query)
async def process_search(message: types.Message, state: FSMContext):
    recipes = search_recipes_by_name(message.text)
    if not recipes:
        return await message.answer("❌ Ничего не найдено. Попробуйте другое название:")
    
    kb = InlineKeyboardBuilder()
    for r in recipes:
        kb.row(types.InlineKeyboardButton(text=r["name"], callback_data=f"select_{r['id']}"))
    
    await message.answer(f"Результаты поиска по '{message.text}':", reply_markup=kb.as_markup())
    await state.set_state(EditRecipe.waiting_recipe_choice)

@router.callback_query(F.data == "method_cats", EditRecipe.waiting_method)
async def show_category_selector(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_categories=[])
    kb = InlineKeyboardBuilder()
    for name, cat_id in CATEGORY_MAP.items():
        kb.row(types.InlineKeyboardButton(text=name, callback_data=f"ecat_{cat_id}"))
    kb.row(types.InlineKeyboardButton(text="✅ Показать блюда", callback_data="ecat_done"))
    
    await callback.message.edit_text("Выберите одну или несколько категорий:", reply_markup=kb.as_markup())
    await state.set_state(EditRecipe.waiting_categories)

@router.callback_query(F.data.startswith("ecat_"), EditRecipe.waiting_categories)
async def handle_category_click(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_categories", [])

    # 1. Если нажали "Готово" — собираем и выводим блюда
    if callback.data == "ecat_done":
        if not selected: 
            return await callback.answer("❌ Выберите хотя бы одну категорию!", show_alert=True)
        
        # Собираем блюда без дубликатов (используем ID как ключ)
        all_recipes = {}
        for cat_code in selected:
            found = get_recipes(cat_code)
            for r in found:
                all_recipes[r['id']] = r
        
        if not all_recipes:
            return await callback.answer("❌ В выбранных категориях пусто", show_alert=True)
        
        kb = InlineKeyboardBuilder()
        # Сортируем по алфавиту для удобства
        sorted_recipes = sorted(all_recipes.values(), key=lambda x: x['name'])
        for r in sorted_recipes:
            kb.row(types.InlineKeyboardButton(text=r["name"], callback_data=f"select_{r['id']}"))
        
        await callback.message.edit_text("Выберите блюдо для редактирования:", reply_markup=kb.as_markup())
        await state.set_state(EditRecipe.waiting_recipe_choice)
        return

    # 2. Логика переключения (Toggle)
    # Используем replace, чтобы корректно получить длинные коды типа 'bar_cocktails'
    cat_id = callback.data.replace("ecat_", "")
    
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.append(cat_id)
    
    await state.update_data(selected_categories=selected)
    
    # 3. Обновляем клавиатуру (ставим/убираем ✅)
    kb = InlineKeyboardBuilder()
    for name, code in CATEGORY_MAP.items():
        is_sel = code in selected
        kb.row(types.InlineKeyboardButton(
            text=f"{'✅ ' if is_sel else ''}{name}", 
            callback_data=f"ecat_{code}"
        ))
    kb.row(types.InlineKeyboardButton(text="✅ Показать блюда", callback_data="ecat_done"))
    
    # Редактируем только разметку, чтобы сообщение не мерцало
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer()

# ===== ГЛАВНОЕ МЕНЮ РЕДАКТИРОВАНИЯ БЛЮДА =====
# Функция для отрисовки карточки блюда после любых изменений
async def refresh_edit_menu(message: types.Message, recipe_id: int, state: FSMContext):

    recipe = get_recipe_by_id(recipe_id)
    tech = get_recipe_tech(recipe_id)
    short_comp = recipe.get('short_composition') or "Не указан"
    
    await state.update_data(recipe_id=recipe_id)
    
    status_ttk = "✅ Заполнена" if tech else "❌ Не заполнена"
    text = (
        f"📍 <b>Редактирование:</b> {recipe['name']}\n"
        f"💰 Цена: {recipe['price']}₽\n"
        f"📝 <b>Краткий состав:</b> <i>{short_comp}</i>\n"
        f"📋 ТТК: {status_ttk}\n\n"
        f"<i>Выберите раздел для изменения:</i>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✏ Название", callback_data="edt_name"),
           types.InlineKeyboardButton(text="💰 Цена", callback_data="edt_price"))
    kb.row(types.InlineKeyboardButton(text="🖼 Фото", callback_data="edt_photo_path"),
           types.InlineKeyboardButton(text="📄 Состав ТТК", callback_data="edt_ingredients_data"))
    kb.row(types.InlineKeyboardButton(text="👨‍🍳 Технология", callback_data="edt_steps"),
           types.InlineKeyboardButton(text="📜 Речевой модуль", callback_data="edt_presentation_text"))
    kb.row(types.InlineKeyboardButton(text="🥣 Соусы", callback_data="mng_sauces"),
           types.InlineKeyboardButton(text="📌 Теги", callback_data="mng_tags"))
    kb.row(types.InlineKeyboardButton(text="📝 Краткий состав", callback_data="edt_short_composition"),        
           types.InlineKeyboardButton(text="📂 Изменить категории", callback_data="mng_categories"))
    kb.row(types.InlineKeyboardButton(text="🗑 Удалить блюдо", callback_data=f"del_confirm_{recipe_id}"),
           types.InlineKeyboardButton(text="⬅️ Выход", callback_data="back_to_menu"))

    
    
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.set_state(EditRecipe.main_edit_menu)

@router.callback_query(F.data.startswith("select_"), EditRecipe.waiting_recipe_choice)
async def open_recipe_card(callback: types.CallbackQuery, state: FSMContext):
    recipe_id = int(callback.data.split("_")[1])
    await refresh_edit_menu(callback.message, recipe_id, state)
    await callback.answer()

# ===== ОБРАБОТКА ИЗМЕНЕНИЙ (UPDATE) =====

@router.callback_query(F.data.startswith("edt_"), EditRecipe.main_edit_menu)
async def ask_new_value(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edt_", "")
    await state.update_data(current_field=field)
    
    prompts = {
        "name": "Введите новое название блюда:",
        "price": "Введите новую цену (только цифры):",
        "photo_path": "Пришлите новое фото блюда:",
        "short_composition": "Введите краткий состав для меню (через запятую):\nПример: <i>Лосось, авокадо, рис, нори</i>",
        "ingredients_data": "Пришлите состав (каждый продукт с новой строки).\nПример:\nКурица 100г\nСоус 30мл",
        "steps": "Пришлите пошаговую инструкцию приготовления:",
        "presentation_text": "Введите новый речевой модуль (описание):"
    }
    await callback.message.answer(prompts.get(field, "Введите данные:"))
    await state.set_state(EditRecipe.waiting_new_value)

@router.message(EditRecipe.waiting_new_value)
async def save_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data['current_field']
    recipe_id = data['recipe_id']
    
    args = {"recipe_id": recipe_id}
    
    if field == "price":
        prices = re.findall(r'\d+', message.text)
        if not prices: return await message.answer("❌ Ошибка! Введите число.")
        args["price"] = int(prices[0])
        if len(prices) > 1:
            args["price_red"] = int(prices[1])
        
    elif field == "ingredients_data":
        args["ingredients_data"] = parse_ingredients_text(message.text)
        update_recipe(**args)
        
        await message.answer("✅ Состав сохранен!\n\n<b>Теперь введите выход блюда</b> (например: 250 г):", parse_mode="HTML")
        await state.set_state(EditRecipe.waiting_yield_weight)
        return
    
    elif field == "photo_path":
        if not message.photo: 
            return await message.answer("❌ Пришлите именно фото!")
        
        photo = message.photo[-1]
        folder = "img/recipes"
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{photo.file_id}.jpg")
        
        # Скачиваем в фоне
        asyncio.create_task(bot.download(photo, destination=path))
        
        # Передаем ОБА параметра в CRUD
        args["photo_path"] = path
        args["photo_file_id"] = photo.file_id
    else:
        args[field] = message.text

    update_recipe(**args)
    
    await message.answer("✅ Сохранено!")
    await refresh_edit_menu(message, recipe_id, state)

# Прием веса выхода
@router.message(EditRecipe.waiting_yield_weight)
async def save_yield_weight_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    recipe_id = data['recipe_id']
    
    # Сохраняем вес через существующий КРУД
    update_recipe(recipe_id=recipe_id, yield_weight=message.text)
    
    await message.answer(f"✅ Выход блюда (<code>{message.text}</code>) сохранен!", parse_mode="HTML")
    await state.set_state(EditRecipe.main_edit_menu) 
    await refresh_edit_menu(message, recipe_id, state)

# Хендлер ТТК из создания блюда
@router.callback_query(F.data.startswith("edit_ttk_"))
async def start_filling_ttk(callback: types.CallbackQuery, state: FSMContext):
    recipe_id = int(callback.data.split("_")[-1])
    
    await state.update_data(recipe_id=recipe_id, current_field="ingredients_data")
    
    await callback.message.answer(
        "<b>Шаг 1 из 2:</b> Пришлите состав блюда (Продукт Вес) построчно:", 
        parse_mode="HTML"
    )
    await state.set_state(EditRecipe.waiting_new_value)
    await callback.answer()


@router.callback_query(F.data == "mng_categories", EditRecipe.main_edit_menu)
async def manage_recipe_categories(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    recipe_id = data['recipe_id']
    
    # Получаем текущие коды категорий этого блюда напрямую из БД

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category_code FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
        # Извлекаем только значения (строки кодов)
        current_categories = [row[0] for row in cursor.fetchall()]

    # Формируем список для клавиатуры на основе CATEGORY_MAP
    all_cats_list = [{"id": code, "name": name} for name, code in CATEGORY_MAP.items()]
    
    # Генерируем клавиатуру
    kb = build_multi_select_kb(all_cats_list, current_categories, "mcat")
    
    await callback.message.answer(
        "Выберите категории, в которых должно отображаться блюдо:", 
        reply_markup=kb
    )
    # Сохраняем временный список выбранных кодов в FSM
    await state.update_data(temp_selected_cats=current_categories)
    await state.set_state(EditRecipe.waiting_category_edit)
    await callback.answer()

@router.callback_query(F.data.startswith("mcat_"), EditRecipe.waiting_category_edit)
async def toggle_recipe_category(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("temp_selected_cats", [])
    recipe_id = data['recipe_id']
    
    # Получаем код категории из callback_data (все что после mcat_)
    cat_code = callback.data.replace("mcat_", "")

    # Если нажата кнопка "Готово"
    if cat_code == "done":

        update_recipe(recipe_id=recipe_id, categories=selected)
        
        await callback.message.answer("✅ Категории успешно обновлены!")

        return await refresh_edit_menu(callback.message, recipe_id, state)

    # Логика "галочки": если код уже в списке — удаляем, если нет — добавляем
    if cat_code in selected:
        selected.remove(cat_code)
    else:
        selected.append(cat_code)


    await state.update_data(temp_selected_cats=selected)
    
    # Перерисовываем только клавиатуру (чтобы сообщение не прыгало)
    all_cats_list = [{"id": code, "name": name} for name, code in CATEGORY_MAP.items()]
    kb = build_multi_select_kb(all_cats_list, selected, "mcat")
    
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()



# ===== УПРАВЛЕНИЕ СОУСАМИ =====

@router.callback_query(F.data == "mng_sauces", EditRecipe.main_edit_menu)
async def manage_sauces(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr_ids = [s['id'] for s in get_recipe_sauces(data['recipe_id'])]
    kb = build_multi_select_kb(get_all_sauces(), curr_ids, "msauce")
    await callback.message.answer("Выберите соусы для этого блюда:", reply_markup=kb)
    await state.update_data(temp_selected=curr_ids)
    await state.set_state(EditRecipe.waiting_sauce_selection)

@router.callback_query(F.data.startswith("msauce_"), EditRecipe.waiting_sauce_selection)
async def toggle_sauce(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('temp_selected', [])
    
    parts = callback.data.split("_")
    if len(parts) < 2: return
    action = parts[1]
    
    if action == "done":
        set_recipe_sauces(data['recipe_id'], selected)
        await state.set_state(EditRecipe.main_edit_menu)
        await callback.message.answer("✅ Список соусов обновлен")        
        return await refresh_edit_menu(callback.message, data['recipe_id'], state)
    
    try:
        sid = int(action)
        if sid in selected: selected.remove(sid)
        else: selected.append(sid)
        
        await state.update_data(temp_selected=selected)
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=build_multi_select_kb(get_all_sauces(), selected, "msauce")
        )
    except ValueError:
        await callback.answer("Ошибка данных")

# ===== УПРАВЛЕНИЕ ТЕГАМИ =====

@router.callback_query(F.data == "mng_tags", EditRecipe.main_edit_menu)
async def manage_tags(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    recipe_id = data['recipe_id']
    
    # Получаем текущие ID тегов блюда
    curr_tags = [t['id'] for t in get_tags_for_recipe(recipe_id)]
    # Получаем вообще все существующие теги в базе
    all_tags = get_all_tags()
    
    # Строим клавиатуру с префиксом "mtag"
    kb = build_multi_select_kb(all_tags, curr_tags, "mtag")
    
    await callback.message.answer("Выберите теги для этого блюда:", reply_markup=kb)
    # Сохраняем временный список в стейт (используем уникальный ключ, чтобы не пересекаться с соусами)
    await state.update_data(temp_selected_tags=curr_tags)
    await state.set_state(EditRecipe.waiting_tag_selection)
    await callback.answer()

@router.callback_query(F.data.startswith("mtag_"), EditRecipe.waiting_tag_selection)
async def toggle_tag(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('temp_selected_tags', [])
    recipe_id = data['recipe_id']
    
    # Извлекаем то, что идет после "mtag_"
    action = callback.data.replace("mtag_", "")
    
    if action == "done":
        # Сохраняем итоговый список в БД
        set_recipe_tags(recipe_id, selected)
        await callback.message.answer("✅ Список тегов обновлен")
        await state.set_state(EditRecipe.main_edit_menu)
        return await refresh_edit_menu(callback.message, recipe_id, state)
    
    # Переключение (Toggle)
    tag_id = int(action)
    if tag_id in selected:
        selected.remove(tag_id)
    else:
        selected.append(tag_id)
    
    await state.update_data(temp_selected_tags=selected)
    
    # Обновляем только кнопки
    kb = build_multi_select_kb(get_all_tags(), selected, "mtag")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()



# ===== УДАЛЕНИЕ =====

@router.callback_query(F.data.startswith("del_confirm_"))
async def delete_recipe_ask(callback: types.CallbackQuery):
    rid = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔥 Да, удалить навсегда", callback_data=f"del_final_{rid}"))
    kb.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu"))
    await callback.message.answer("⚠️ Вы уверены? Это удалит ТТК, соусы и теги этого блюда!", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("del_final_"))
async def delete_recipe_execute(callback: types.CallbackQuery, state: FSMContext):
    rid = int(callback.data.split("_")[2])
    delete_recipe(rid)
    await callback.message.answer("🗑 Блюдо успешно удалено.", reply_markup=admin_main_inline_kb())
    await state.clear()

@router.callback_query(F.data == "back_to_menu")
async def exit_edit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Редактирование завершено.", reply_markup=admin_main_inline_kb())
