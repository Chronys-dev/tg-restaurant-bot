from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import (admin_main_inline_kb, dishes_sauces_admin_kb, manage_recipes_inline_kb, 
    manage_sauces_inline_kb, manage_tags_inline_kb, main_menu_kb)

router = Router()

# ВХОД В АДМИНКУ (из главного меню через Reply кнопку)
@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel_start(message: Message):
    await message.answer(
        "⚙️ <b>ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА</b>\nВыберите раздел для работы:",
        reply_markup=admin_main_inline_kb(),
        parse_mode="HTML"
    )

# ВОЗВРАТ В КОРЕНЬ АДМИНКИ
@router.callback_query(F.data == "adm_main")
async def back_to_admin_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠 <b>УПРАВЛЕНИЕ КОНТЕНТОМ</b>\nВыберите раздел:",
        reply_markup=admin_main_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# Переход в "Блюда и Соусы"
@router.callback_query(F.data == "adm_section_dishes_sauces")
async def go_to_dishes_sauces(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍽 <b>УПРАВЛЕНИЕ КОНТЕНТОМ</b>\nРецепты, соусы и теги:",
        reply_markup=dishes_sauces_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# Кнопка Назад в меню (Reply-кнопка)
@router.message(F.text == "⬅️ Назад в меню")
async def back_to_main_reply(message: Message):
    # Сбрасываем всё и шлем главное меню юзера
    await message.answer(
        "🏠 Главное меню:",
        reply_markup=main_menu_kb(message.from_user.id))



# ПЕРЕХОД В УПРАВЛЕНИЕ БЛЮДАМИ
@router.callback_query(F.data == "adm_section_recipes")
async def admin_manage_recipes(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍽 <b>МЕНЮ БЛЮД</b>\nДобавление, правка или удаление рецептов:",
        reply_markup=manage_recipes_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# ПЕРЕХОД В УПРАВЛЕНИЕ СОУСАМИ
@router.callback_query(F.data == "adm_section_sauces")
async def admin_manage_sauces(callback: CallbackQuery):
    await callback.message.edit_text(
        "🥣 <b>МЕНЮ СОУСОВ</b>\nУправление составами соусов:",
        reply_markup=manage_sauces_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# ПЕРЕХОД В УПРАВЛЕНИЕ ТЕГАМИ
@router.callback_query(F.data == "adm_section_tags")
async def admin_manage_tags(callback: CallbackQuery):
    await callback.message.edit_text(
        "📌 <b>МЕНЮ ТЕГОВ</b>\nУправление поисковыми метками:",
        reply_markup=manage_tags_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# ЗАКРЫТИЕ
@router.callback_query(F.data == "close_admin")
async def close_admin_panel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Панель закрыта")


# Заглушки для конкретных разделов
@router.callback_query(F.data.in_(["study_video", "adm_section_plans", "adm_section_stats", "adm_section_broadcast"]))
async def admin_sections_stub(callback: CallbackQuery):
    sections = {

        "adm_section_plans": "📝 План и Темы",
        "adm_section_stats": "📊 Отчеты и Статистика",
        "adm_section_broadcast": "📣 Рассылка",
        "study_video": "🎬 Учебные видео"

    }
    section_name = sections.get(callback.data, "Раздел")
    await callback.answer(f"Раздел '{section_name}' пока в разработке (Версия 1.1)", show_alert=True)