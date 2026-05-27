from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import manage_sauces_inline_kb
from db.sauces import add_sauce, delete_sauce, get_all_sauces, update_sauce, get_sauce_by_id


router = Router()

class SauceFSM(StatesGroup):
    waiting_name = State()
    choosing_sauce = State()
    edit_menu = State()
    waiting_new_value = State()

# --- ГЛАВНОЕ МЕНЮ СОУСОВ ---
@router.callback_query(F.data == "adm_sauce_main")
async def sauce_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🥣 <b>Управление соусами</b>\nВыберите действие:",
        reply_markup=manage_sauces_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- ДОБАВЛЕНИЕ ---
@router.callback_query(F.data == "adm_sauce_add")
async def start_add_sauce(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введите название нового соуса:")
    await state.set_state(SauceFSM.waiting_name)
    await callback.answer()

@router.message(SauceFSM.waiting_name)
async def process_add_sauce(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return
    sauce_id = add_sauce(message.text.strip())
    await message.answer(f"✅ Соус «{message.text}» добавлен!")
    # Сразу открываем меню этого соуса
    await show_sauce_edit_card(message, sauce_id, state)

# --- РЕДАКТИРОВАНИЕ (ВЫБОР) ---
@router.callback_query(F.data == "adm_sauce_edit")
async def list_sauces_for_edit(callback: types.CallbackQuery, state: FSMContext):
    sauces = get_all_sauces()
    if not sauces:
        return await callback.answer("❌ Соусов нет в БД", show_alert=True)
    
    kb = InlineKeyboardBuilder()
    for s in sauces:
        kb.row(types.InlineKeyboardButton(text=s["name"], callback_data=f"sedit_{s['id']}"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sauce_main"))
    
    await callback.message.edit_text("Выберите соус для редактирования:", reply_markup=kb.as_markup())
    await state.set_state(SauceFSM.choosing_sauce)

# --- ОБРАБОТКА ВЫБОРА КОНКРЕТНОГО СОУСА ---
@router.callback_query(F.data.startswith("sedit_"), SauceFSM.choosing_sauce)
async def process_sauce_selection(callback: types.CallbackQuery, state: FSMContext):
    sauce_id = int(callback.data.split("_")[1])
    await show_sauce_edit_card(callback.message, sauce_id, state)
    await callback.answer()


# --- КАРТОЧКА СОУСА ---
async def show_sauce_edit_card(message: types.Message, sauce_id: int, state: FSMContext):
    sauce = get_sauce_by_id(sauce_id)
    if not sauce:
        return await message.answer("❌ Соус не найден")

    await state.update_data(edit_sauce_id=sauce_id)
    
    # Формируем текст состава для предпросмотра
    ingr_text = "\n".join([f"• {i['name']} {i['weight']}" for i in sauce['ingredients']]) or "не указан"
    
    text = (f"🥣 <b>Соус:</b> {sauce['name']}\n"
            f"⚖️ <b>Выход:</b> {sauce.get('yield_weight') or '—'}\n"
            f"📄 <b>Состав:</b>\n{ingr_text}\n\n"
            f"👨‍🍳 <b>Технология:</b>\n{sauce.get('steps') or '—'}")
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✏️ Название", callback_data="sfield_name"),
           types.InlineKeyboardButton(text="⚖️ Выход", callback_data="sfield_yield_weight"))
    kb.row(types.InlineKeyboardButton(text="🥗 Состав (ТТК)", callback_data="sfield_structure"),
           types.InlineKeyboardButton(text="👨‍🍳 Технология", callback_data="sfield_steps"))
    kb.row(types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"sdel_conf_{sauce_id}"))
    kb.row(types.InlineKeyboardButton(text="🔙 К списку", callback_data="adm_sauce_edit"))
    
    try:
        if message.from_user.is_bot:
            await message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        # На случай, если edit_text невозможен (например, сообщение слишком старое)
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

    await state.set_state(SauceFSM.edit_menu)
    
  

# --- ОБНОВЛЕНИЕ ПОЛЕЙ ---
@router.callback_query(F.data.startswith("sfield_"), SauceFSM.edit_menu)
async def ask_sauce_value(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("sfield_", "")
    await state.update_data(current_field=field)
    
    prompts = {
        "name": "Введите новое название соуса:",
        "yield_weight": "Введите выход соуса (например, 1000г):",
        "steps": "Введите шаги приготовления соуса:",
        "structure": "Пришлите состав (каждый продукт с новой строки).\nПример:\nСметана 100г\nУкроп 5г"
    }
    await callback.message.answer(prompts.get(field, "Введите данные:"))
    await state.set_state(SauceFSM.waiting_new_value)

@router.message(SauceFSM.waiting_new_value)
async def save_sauce_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sid = data['edit_sauce_id']
    field = data['current_field']
    
    # Подготовка данных для твоей функции update_sauce
    update_args = {"sauce_id": sid}
    
    if field == "structure":
        # Используем наш парсер (тот же, что для блюд)
        from routers.admin_edit_recipe import parse_ingredients_text
        update_args["ingredients_data"] = parse_ingredients_text(message.text)
    else:
        # Для полей name, steps, yield_weight
        update_args[field] = message.text.strip()

    update_sauce(**update_args)
    await message.answer("✅ Обновлено!")
    await show_sauce_edit_card(message, sid, state)

# --- УДАЛЕНИЕ ---
@router.callback_query(F.data == "adm_sauce_del") # Быстрый путь удаления из списка
async def list_sauces_for_del(callback: types.CallbackQuery):
    sauces = get_all_sauces()
    kb = InlineKeyboardBuilder()
    for s in sauces:
        kb.row(types.InlineKeyboardButton(text=f"🗑 {s['name']}", callback_data=f"sdel_conf_{s['id']}"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sauce_main"))
    await callback.message.edit_text("Нажмите на соус, чтобы УДАЛИТЬ его:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("sdel_conf_"))
async def confirm_sauce_del(callback: types.CallbackQuery):
    sid = callback.data.split("_")[-1]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔥 Да, удалить", callback_data=f"sdel_final_{sid}"),
           types.InlineKeyboardButton(text="❌ Отмена", callback_data="adm_sauce_main"))
    await callback.message.edit_text("⚠️ Вы уверены? Соус удалится из всех блюд!", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("sdel_final_"))
async def execute_sauce_del(callback: types.CallbackQuery, state: FSMContext):
    sid = int(callback.data.split("_")[-1])
    delete_sauce(sid)
    await callback.answer("🗑 Удалено", show_alert=True)
    await sauce_main_menu(callback, state)
