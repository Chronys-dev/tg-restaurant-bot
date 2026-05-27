from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardButton
import os

from db import add_material, delete_material, get_materials_by_category
from keyboards import MATERIALS_CAT



class AdminMaterials(StatesGroup):
    choosing_category = State() # Выбор категории для добавления
    waiting_for_file = State()  # Ожидание самого файла
    deleting_choose_cat = State()    # Выбор категории для удаления
    deleting_choose_file = State()   # Выбор файла в этой категории
    confirm_delete = State()    # Выбор файла для удаления
    

router = Router()

SAVE_PATH = "materials"  
os.makedirs(SAVE_PATH, exist_ok=True) 


# Главное меню раздела материалов
@router.callback_query(F.data == "adm_section_materials")
async def admin_materials_main(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить материал", callback_data="adm_mat_add"))
    builder.row(InlineKeyboardButton(text="❌ Удалить материал", callback_data="adm_mat_del"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_section_materials"))
    
    await callback.message.edit_text("Управление учебными материалами:", reply_markup=builder.as_markup())

# --- ПРОЦЕСС ДОБАВЛЕНИЯ ---

@router.callback_query(F.data == "adm_mat_add")
async def add_material_start(callback: types.CallbackQuery, state: FSMContext):
    # Рисуем кнопки существующих категорий из вашей БД
    builder = InlineKeyboardBuilder()
    
    for name, slug in MATERIALS_CAT: 
        builder.row(InlineKeyboardButton(text=name, callback_data=f"mat_cat_{slug}"))
    
    await state.set_state(AdminMaterials.choosing_category)
    await callback.message.edit_text("Выберите категорию, в которую добавить файл:", reply_markup=builder.as_markup())

@router.callback_query(AdminMaterials.choosing_category)
async def add_material_file_wait(callback: types.CallbackQuery, state: FSMContext):
    category_slug = callback.data.replace("mat_cat_", "")
    await state.update_data(cat_slug=category_slug)
    
    await state.set_state(AdminMaterials.waiting_for_file)
    await callback.message.edit_text(f"Пришлите файл (Документ, Видео или Фото).\nНазовите его красиво перед отправкой!")

@router.message(AdminMaterials.waiting_for_file)
async def add_material_save(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    category_slug = data['cat_slug']
    
    # 1. Определяем файл
    if message.document:
        file_obj = message.document
        file_type = "doc"
    elif message.video:
        file_obj = message.video
        file_type = "video"
    else:
        await message.answer("❌ Пожалуйста, пришлите именно документ или видео.")
        return

    file_id = file_obj.file_id
    # Для видео file_name может быть пустым, даем стандартное имя
    original_name = getattr(file_obj, 'file_name', f"video_{file_id[:10]}.mp4")
    
    # Формируем путь для сохранения на диск
    # Создаем подпапку категории (например, data/materials/kitchen/)
    cat_dir = os.path.join(SAVE_PATH, category_slug)
    os.makedirs(cat_dir, exist_ok=True)
    
    local_destination = os.path.join(cat_dir, original_name)

    try:
        # Проверяем размер (лимит Telegram Bot API на скачивание — 20 МБ)
        if file_obj.file_size <= 20 * 1024 * 1024:
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, local_destination)
            path_for_db = local_destination
            status_text = f"📂 Сохранен локально: <code>{local_destination}</code>"
        else:
            path_for_db = "CLOUD_ONLY"
            status_text = "☁️ Сохранен только в облаке Telegram (файл > 20МБ)"
        
        # Сохраняем в БД (важно: передаем path_for_db)
        success = add_material(
            category_slug=category_slug,
            title=original_name,
            file_type=file_type,
            tg_file_id=file_id,
            local_path=path_for_db  # Исправлено здесь
        )
        
        if success:
            await message.answer(
                f"✅ Файл успешно обработан!\n\n"
                f"{status_text}\n"
                f"🆔 TG ID: <code>Имеется</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка при записи в базу данных.")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке: {e}")
    
    await state.clear()


# --- ПРОЦЕСС УДАЛЕНИЯ ---
# Выбор категории для удаления
@router.callback_query(F.data == "adm_mat_del")
async def delete_material_select_cat(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    
    for name, slug in MATERIALS_CAT: 
        builder.row(InlineKeyboardButton(text=name, callback_data=f"del_cat_{slug}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_section_materials"))
    
    await state.set_state(AdminMaterials.deleting_choose_cat)
    await callback.message.edit_text("Выберите категорию, из которой нужно удалить файл:", reply_markup=builder.as_markup())

# Выбор конкретного файла в категории
@router.callback_query(AdminMaterials.deleting_choose_cat, F.data.startswith("del_cat_"))
async def delete_material_select_file(callback: types.CallbackQuery, state: FSMContext):
    category_slug = callback.data.replace("del_cat_", "")
    
    # Получаем файлы только этой категории
    materials = get_materials_by_category(category_slug) 
    
    if not materials:
        await callback.answer("В этой категории нет файлов.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    
    # В функции get_materials_by_category запрос должен возвращать (id, title, ...)
    for m_id, title, *etc in materials:
        builder.row(InlineKeyboardButton(text=f"🗑 {title}", callback_data=f"confirm_del_{m_id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_mat_del"))
    
    await state.set_state(AdminMaterials.deleting_choose_file)
    await callback.message.edit_text(f"Выберите файл для удаления:", reply_markup=builder.as_markup())

# 3. Этап: Само удаление
@router.callback_query(AdminMaterials.deleting_choose_file, F.data.startswith("confirm_del_"))
async def delete_material_confirm(callback: types.CallbackQuery, state: FSMContext):
    m_id = callback.data.replace("confirm_del_", "")
    
    if delete_material(m_id):
        await callback.answer("Файл успешно удален из базы", show_alert=True)
        # Возвращаемся в начало раздела материалов
        await state.clear()
        await admin_materials_main(callback) 
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)