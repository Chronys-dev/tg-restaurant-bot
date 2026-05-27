from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os, re, asyncio, traceback
from keyboards import skip_inline_kb, CATEGORY_MAP
from db import add_recipe, get_all_sauces, get_all_tags
from permissions import is_owner
from loader import bot

router = Router()

# ===== FSM состояния =====
class AddRecipe(StatesGroup):
    waiting_categories = State()
    waiting_name = State()
    waiting_price = State()
    waiting_photo = State()
    waiting_short_composition = State()
    waiting_description = State()
    waiting_sauces = State()
    waiting_tags = State()


# =====Выбор категорий=====
@router.callback_query(F.data == "adm_rec_add")
async def start_add_recipe(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("⛔ Недостаточно прав", show_alert=True)
        return

    await state.clear()
    await state.update_data(selected_categories=[])
    await render_category_selection(callback.message, state)
    await state.set_state(AddRecipe.waiting_categories)
    await callback.answer()

async def render_category_selection(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    
    builder = InlineKeyboardBuilder()
    for name, code in CATEGORY_MAP.items():
        status = " ✅" if code in selected else ""
        builder.add(InlineKeyboardButton(text=f"{name}{status}", callback_data=f"sel_cat_{code}"))
    
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ ГОТОВО", callback_data="finish_cat_selection"))
    builder.row(InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="adm_section_recipes"))

    await message.edit_text("<b>ШАГ 1:</b> Выберите категории блюда:", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("sel_cat_"), AddRecipe.waiting_categories)
async def toggle_category(callback: CallbackQuery, state: FSMContext):
    cat_code = callback.data.replace("sel_cat_", "")
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    
    if cat_code in selected: selected.remove(cat_code)
    else: selected.append(cat_code)
    
    await state.update_data(selected_categories=selected)
    await render_category_selection(callback.message, state)
    await callback.answer()

# ===== Переход к Названию =====
@router.callback_query(F.data == "finish_cat_selection", AddRecipe.waiting_categories)
async def finish_categories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("selected_categories"):
        await callback.answer("⚠️ Выберите хотя бы одну категорию!", show_alert=True)
        return

    await callback.message.edit_text("<b>ШАГ 2:</b> Введите название блюда:")
    await state.set_state(AddRecipe.waiting_name)

# ===== Название =====
@router.message(AddRecipe.waiting_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Название: <b>{message.text}</b>\n\n<b>ШАГ 3:</b> Введите цену и КЦ, через пробел:", parse_mode="HTML")
    await state.set_state(AddRecipe.waiting_price)

# ===== Цена =====
@router.message(AddRecipe.waiting_price)
async def enter_price(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # Разделяем текст по пробелу, запятой или слэшу
    prices = re.findall(r'\d+', text)

    if not prices:
        await message.answer("⚠️ Введите цену числом! Например: <code>500</code> или <code>500 450</code> (если есть КЦ)", parse_mode="HTML")
        return

    price = int(prices[0])
    price_red = int(prices[1]) if len(prices) > 1 else None

    # Сохраняем обе цены в FSM
    await state.update_data(price=price, price_red=price_red)

    # Формируем подтверждение для пользователя
    msg_text = f"✅ Цена установлена: <code>{price} ₽</code>"
    if price_red:
        msg_text += f"\n🔴 Красная цена: <code>{price_red} ₽</code>"
    
    await message.answer(f"{msg_text}\n\n<b>ШАГ 4:</b> Пришлите фото:", reply_markup=skip_inline_kb(), parse_mode="HTML")
    await state.set_state(AddRecipe.waiting_photo)
    
    
# ===== Фото =====
@router.message(F.photo, AddRecipe.waiting_photo)
async def enter_photo(message: Message, state: FSMContext):
    # Получаем самый качественный вариант фото (последний в списке)
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Создаем путь для сохранения на диске (например, папка img/recipes/)
    folder = "img/recipes"
    os.makedirs(folder, exist_ok=True)
    local_path = os.path.join(folder, f"{file_id}.jpg")
    
    # Сохраняем в FSM оба параметра
    await state.update_data(
        photo_file_id=file_id,
        photo_path=local_path
    )
    
    # ЗАПУСКАЕМ СКАЧИВАНИЕ В ФОНЕ
    asyncio.create_task(bot.download(photo, destination=local_path))
    
    await message.answer("✅ Фото сохранено в базу и на диск.")
    await ask_short_comp(message, state)

@router.callback_query(F.data == "skip_step", AddRecipe.waiting_photo)
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_path=None)
    await ask_short_comp(callback.message, state)

async def ask_short_comp(message: Message, state: FSMContext):
    await message.answer("<b>ШАГ 5:</b> Введите краткий состав:", reply_markup=skip_inline_kb(), parse_mode="HTML")
    await state.set_state(AddRecipe.waiting_short_composition)

# ===== Краткий состав =====
@router.message(AddRecipe.waiting_short_composition)
async def enter_short_comp(message: Message, state: FSMContext):
    await state.update_data(short_composition=message.text)
    await ask_description(message, state)

@router.callback_query(F.data == "skip_step", AddRecipe.waiting_short_composition)
async def skip_short_comp(callback: CallbackQuery, state: FSMContext):
    await state.update_data(short_composition=None)
    await ask_description(callback.message, state)

async def ask_description(message: Message, state: FSMContext):
    await message.answer("<b>ШАГ 6:</b> Введите описание:", reply_markup=skip_inline_kb(), parse_mode="HTML")
    await state.set_state(AddRecipe.waiting_description)

# ===== Описание и Вопрос про Соусы =====
@router.message(AddRecipe.waiting_description)
async def enter_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await ask_sauce_question(message)

@router.callback_query(F.data == "skip_step", AddRecipe.waiting_description)
async def skip_description(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await ask_sauce_question(callback.message)

async def ask_sauce_question(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="sauces_yes"),
         InlineKeyboardButton(text="❌ Нет", callback_data="sauces_no")]
    ])
    await message.answer("<b>ШАГ 7:</b> Добавить соусы?", reply_markup=kb, parse_mode="HTML")

# ===== Соусы =====
@router.callback_query(F.data == "sauces_no")
async def no_sauces(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sauce_ids=[])
    await ask_tags(callback.message, state)

@router.callback_query(F.data == "sauces_yes")
async def yes_sauces(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sauce_ids=[])
    await render_sauce_selection(callback.message, state)
    await state.set_state(AddRecipe.waiting_sauces)

async def render_sauce_selection(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("sauce_ids", [])
    all_sauces = get_all_sauces()
    builder = InlineKeyboardBuilder()
    
    for sauce in all_sauces:
        s_id = sauce["id"]
        s_name = sauce["name"]        
        status = " ✅" if s_id in selected else ""
        builder.add(InlineKeyboardButton(
            text=f"{s_name}{status}", 
            callback_data=f"sel_sauce_{s_id}"
        ))
        
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ ГОТОВО", callback_data="finish_sauces"))
    await message.edit_text("Выберите соусы:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("sel_sauce_"), AddRecipe.waiting_sauces)
async def toggle_sauce(callback: CallbackQuery, state: FSMContext):
    sid = int(callback.data.replace("sel_sauce_", ""))
    data = await state.get_data()
    selected = data.get("sauce_ids", [])
    if sid in selected: selected.remove(sid)
    else: selected.append(sid)
    await state.update_data(sauce_ids=selected)
    await render_sauce_selection(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "finish_sauces", AddRecipe.waiting_sauces)
async def finish_sauces(callback: CallbackQuery, state: FSMContext):
    await ask_tags(callback.message, state)

# ===== Теги =====
async def ask_tags(message: Message, state: FSMContext):
    await state.update_data(tag_ids=[])
    await render_tag_selection(message, state)
    await state.set_state(AddRecipe.waiting_tags)

async def render_tag_selection(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("tag_ids", [])
    all_tags = get_all_tags()
    builder = InlineKeyboardBuilder()
    
    for tag in all_tags:
        t_id = tag["id"]
        t_name = tag["name"]
        status = " ✅" if t_id in selected else ""
        builder.add(InlineKeyboardButton(text=f"{t_name}{status}", callback_data=f"sel_tag_{t_id}"))
        
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="💾 СОХРАНИТЬ", callback_data="finalize"))
    await message.edit_text("Выберите теги:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("sel_tag_"), AddRecipe.waiting_tags)
async def toggle_tag(callback: CallbackQuery, state: FSMContext):
    tid = int(callback.data.replace("sel_tag_", ""))
    data = await state.get_data()
    selected = data.get("tag_ids", [])
    if tid in selected: selected.remove(tid)
    else: selected.append(tid)
    await state.update_data(tag_ids=selected)
    await render_tag_selection(callback.message, state)
    await callback.answer()

# ===== ФИНАЛЬНОЕ СОХРАНЕНИЕ =====
@router.callback_query(F.data == "finalize", AddRecipe.waiting_tags)
async def finalize_recipe_logic(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    try:
        
        new_id = add_recipe(
            name=data["name"],
            price=data.get("price"),
            price_red=data.get("price_red"),
            photo_path=data.get("photo_path"),
            photo_file_id=data.get("photo_file_id"),
            short_composition=data.get("short_composition"),
            presentation_text=data.get("description"),
            categories=data.get("selected_categories"), 
            sauce_ids=data.get("sauce_ids", []),
            tag_ids=data.get("tag_ids", [])
        )
        
        await state.clear() 

        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Наполнить ТТК (Граммовки)", callback_data=f"edit_ttk_{new_id}")],
            [InlineKeyboardButton(text="👨‍🍳 Описать технологию", callback_data=f"edit_tech_{new_id}")],
            [InlineKeyboardButton(text="🏠 В главное меню админки", callback_data="adm_main")]
        ])

        await callback.message.edit_text(
            f"✅ Блюдо <b>«{data['name']}»</b> успешно создано!\n"
            f"ID в базе: <code>{new_id}</code>\n\n"
            f"Маркетинговая часть готова. Теперь вы можете перейти к технической части (ТТК) или вернуться в меню.",
            reply_markup=kb,
            parse_mode="HTML"
        )

    except Exception as e:
        # Логируем полную трассировку, чтобы было проще отладить проблему
        print(traceback.format_exc())
        await callback.message.answer("❌ Ошибка при сохранении. Подробности в логах.")
    
    await callback.answer()