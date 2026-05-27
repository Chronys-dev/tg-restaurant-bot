from aiogram import Router, F, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import manage_tags_inline_kb
from db import add_tag, delete_tag, get_all_tags
from permissions import is_owner

router = Router()

class TagFSM(StatesGroup):
    waiting_name = State()

# --- ГЛАВНОЕ МЕНЮ ТЕГОВ ---
@router.callback_query(F.data == "adm_tag_main") # Точка входа из главного меню админки
async def tag_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📌 <b>Управление тегами</b>\nВыберите действие:",
        reply_markup=manage_tags_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- ДОБАВЛЕНИЕ ТЕГА ---
@router.callback_query(F.data == "adm_tag_add")
async def start_add_tag(callback: types.CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return await callback.answer("⛔ Нет прав", show_alert=True)
    
    await callback.message.edit_text("📝 Введите название нового тега (например: <i>Острое</i>):", parse_mode="HTML")
    await state.set_state(TagFSM.waiting_name)
    await callback.answer()

@router.message(TagFSM.waiting_name)
async def process_save_tag(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return # Игнорируем команды
    
    tag_name = message.text.strip()
    add_tag(tag_name)
    
    await message.answer(f"✅ Тег «{tag_name}» успешно добавлен!")
    # Возвращаем пользователя в меню тегов
    await message.answer("📌 Управление тегами:", reply_markup=manage_tags_inline_kb())
    await state.clear()

# --- УДАЛЕНИЕ ТЕГА (СПИСОК) ---
@router.callback_query(F.data == "adm_tag_del")
async def list_tags_for_delete(callback: types.CallbackQuery):
    tags = get_all_tags()
    if not tags:
        return await callback.answer("❌ Тегов в базе пока нет", show_alert=True)

    kb = InlineKeyboardBuilder()
    for t in tags:
        # Добавляем эмодзи корзины для наглядности
        kb.row(types.InlineKeyboardButton(
            text=f"🗑 {t['name']}",
            callback_data=f"confirm_tag_del_{t['id']}"
        ))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_tag_main"))

    await callback.message.edit_text("Выберите тег, который нужно УДАЛИТЬ:", reply_markup=kb.as_markup())
    await callback.answer()

# --- ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ---
@router.callback_query(F.data.startswith("confirm_tag_del_"))
async def confirm_tag_delete(callback: types.CallbackQuery):
    tag_id = callback.data.split("_")[-1]
    
    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🔥 Да, удалить", callback_data=f"final_tag_del_{tag_id}"),
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="adm_tag_del")
    )
    
    await callback.message.edit_text("⚠️ Вы уверены? Тег отвяжется от всех блюд!", reply_markup=kb.as_markup())
    await callback.answer()

# --- ФИНАЛЬНОЕ УДАЛЕНИЕ ---
@router.callback_query(F.data.startswith("final_tag_del_"))
async def execute_tag_delete(callback: types.CallbackQuery):
    tag_id = int(callback.data.split("_")[-1])
    delete_tag(tag_id)
    
    await callback.answer("🗑 Тег удалён", show_alert=True)
    # Возвращаемся в список тегов
    await list_tags_for_delete(callback)
