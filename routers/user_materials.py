from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from db import get_materials_by_category, get_material_by_id
from keyboards import material_menu_inline_kb
import os


router = Router()

# Главное меню учебных материалов
@router.callback_query(F.data == "menu_materials")
async def main_material_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📚 Выберите раздел обучения:",
        reply_markup=material_menu_inline_kb(callback.from_user.id)
    )

# 1. Отображение списка файлов в выбранной категории
@router.callback_query(F.data.startswith("study_"))
async def show_category_materials(callback: types.CallbackQuery):
    # Отрезаем префикс, чтобы получить slug (например, 'kitchen')
    category_slug = callback.data.replace("study_", "")
    
    materials = get_materials_by_category(category_slug)
    
    if not materials:
        await callback.answer("В этом разделе пока нет материалов.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    
    for m_id, title, f_type, tg_id in materials:
        # Подбираем иконку по типу файла
        icon = "📄"
        if f_type == "video": icon = "🎬"
        elif ".pdf" in title.lower(): icon = "📕"
        elif ".xls" in title.lower(): icon = "📗"
        
        # Кнопка с ID файла в callback_data
        builder.row(types.InlineKeyboardButton(
            text=f"{icon} {title}", 
            callback_data=f"download_file_{m_id}")
        )
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_materials"))

    await callback.message.edit_text(
        f"📚 Выберите материал для скачивания:",
        reply_markup=builder.as_markup()
    )

# 2. Обработка нажатия на конкретный файл (Скачивание)
@router.callback_query(F.data.startswith("download_file_"))
async def send_material_file(callback: types.CallbackQuery):
    material_id = callback.data.replace("download_file_", "")
    material = get_material_by_id(material_id)
    
    if not material:
        await callback.answer("Файл не найден в базе данных.", show_alert=True)
        return

    title, tg_file_id, local_path = material
    
    await callback.answer("Отправляю файл...")

    try:
        # Пытаемся отправить через Telegram File ID (самый быстрый способ 2026)
        if tg_file_id:
            await callback.message.answer_document(
                document=tg_file_id,
                caption=f"✅ Файл: {title}"
            )
        # Если ID нет, но есть путь на диске — отправляем локально
        elif local_path and os.path.exists(local_path):
            file = FSInputFile(local_path, filename=title)
            await callback.message.answer_document(
                document=file,
                caption=f"✅ Файл: {title}"
            )
        else:
            await callback.message.answer("❌ Ошибка: файл физически отсутствует.")
            
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось отправить файл. Ошибка: {e}")