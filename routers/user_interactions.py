import os
from aiogram.types import InputMediaPhoto
from aiogram import Router, F, types
import os
import traceback
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import (get_recipe_by_id, get_tags_for_recipe, get_recipe_tech, get_recipe_sauces, 
    get_sauce_by_id)
from keyboards import recipe_inline_kb

router = Router()


# Формирование карточки
def get_recipe_caption(recipe, tags, tech=None):
    # ЗАГОЛОВОК И ЦЕНЫ
    caption = f"🥗 <b>{recipe['name'].upper()}</b>\n"
    
    price = recipe.get("price")
    price_red = recipe.get("price_red")

    if price_red:
        # Если есть красная цена, старую зачеркиваем, новую выделяем
        caption += f"💰 Цена: <b>{price} ₽</b> КЦ: <b>{price_red} ₽</b>"
    elif price:
        # Если красной цены нет, пишем обычную
        caption += f"💰 Цена: <code>{price} ₽</code>"
    
    caption += "\n\n"

    # КРАТКИЙ СОСТАВ И ВЫХОД
    if recipe.get("short_composition"):
        caption += f"<b>Состав:</b> <i>{recipe['short_composition']}</i>\n"
    
    caption += "\n"
    
    # Добавляем выход блюда из ТТК
    if tech and tech.get("yield_weight"):
        caption += f"⚖️ <b>Выход:</b> <code>{tech['yield_weight']}</code>\n"
    
    caption += "\n"

    # 3. РЕЧЕВОЙ МОДУЛЬ (Презентация)
    if recipe.get("presentation_text"):
        caption += f"<b>🗣 РЕЧЕВОЙ МОДУЛЬ:</b>\n<blockquote>{recipe['presentation_text']}</blockquote>\n\n"

    # 4. ТЕГИ
    if tags:
        tags_list = [f"{t['name']}" for t in tags]
        caption += " ".join(tags_list)
        
    return caption


# Отправка карточки блюда
@router.callback_query(F.data.startswith("recipe_"))
async def recipe_card_callback(callback: types.CallbackQuery):
    recipe_id = int(callback.data.split("_")[-1])
    recipe = get_recipe_by_id(recipe_id)
    
    if not recipe:
        return await callback.answer("Ошибка: Блюдо не найдено", show_alert=True)

    tech = get_recipe_tech(recipe_id)
    tags = get_tags_for_recipe(recipe_id)
    sauces = get_recipe_sauces(recipe_id)
    caption = get_recipe_caption(recipe, tags, tech)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚖️ ТТК", callback_data=f"show_ttk_{recipe_id}"))
    if sauces:
        for sauce in sauces:
            builder.row(InlineKeyboardButton(text=f"🥫 {sauce['name']}", 
                                           callback_data=f"show_sauce_{sauce['id']}_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list"))

    file_id = recipe.get("photo_file_id")
    local_path = recipe.get("photo_path")

    # Решаем, какой объект медиа подготовить
    photo_to_send = None
    if file_id:
        photo_to_send = file_id
    elif local_path:
        # Отправляем локальный файл только если он существует
        if os.path.exists(local_path):
            photo_to_send = FSInputFile(local_path)
        else:
            # Локальный файл ещё не скачан — падаём back to text mode
            print(f"Local photo not found: {local_path}")
            photo_to_send = None

    try:
        # СЛУЧАЙ 1: У блюда ЕСТЬ фото
        if photo_to_send:
            # Если текущее сообщение УЖЕ с фото — просто меняем медиа (эффект переключения)
            if callback.message.photo:
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=photo_to_send, caption=caption, parse_mode="HTML"),
                    reply_markup=builder.as_markup()
                )
            else:
                # Если старое сообщение было текстом (например, список) — шлем фото (не удаляем старое сообщение)
                await callback.message.answer_photo(
                    photo=photo_to_send, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML"
                )
        # СЛУЧАЙ 2: У блюда НЕТ фото
        else:
            if callback.message.photo:
                # Если текущее было с фото, а новое без — шлём текст и убираем кнопки у старого сообщения
                await callback.message.answer(caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    print(traceback.format_exc())
            else:
                # Если оба текстовые — просто редактируем текст (бесшовно)
                await callback.message.edit_text(caption, reply_markup=builder.as_markup(), parse_mode="HTML")

    except Exception as e:
        # Логируем трассировку для отладки, затем шлём сообщение заново
        print(traceback.format_exc())
        await callback.message.answer(caption, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer()
    

# Вкладка ТТК
@router.callback_query(F.data.startswith("show_ttk_"))
async def show_recipe_ttk_handler(callback: types.CallbackQuery):
    recipe_id = int(callback.data.split("_")[-1])
    recipe = get_recipe_by_id(recipe_id)
    tech = get_recipe_tech(recipe_id)
    
    if not tech:
        return await callback.answer("⚠️ ТТК не заполнена", show_alert=True)

    ingr_lines = []
    for i in tech['ingredients']:
        name = i['name'].strip()
        weight = i['weight'].strip()
        ingr_lines.append(f"• {name}  —  <b>{weight}</b>")

    ingredients_text = "\n".join(ingr_lines)
    
    ttk_caption = (
        f"<b>⚖️ ТТК: {recipe['name'].upper()}</b>\n"
        f"───────────────\n"
        f"<b>🛒 СОСТАВ:</b>\n"
        f"{ingredients_text}\n\n"
        f"<b>⚖️ ВЫХОД:</b> <b>{tech.get('yield_weight', '—')}</b>\n"
        f"───────────────\n"
        f"<b>👨‍🍳 ТЕХНОЛОГИЯ:</b>\n<i>{tech.get('steps', '—')}</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📄 Вернуться к описанию", callback_data=f"recipe_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list"))

    if callback.message.photo:
        # Лимит подписи к фото - 1024 символа
        if len(ttk_caption) <= 1024:
            await callback.message.edit_caption(
                caption=ttk_caption, 
                reply_markup=builder.as_markup(), 
                parse_mode="HTML"
            )
        else:
            # Если ТТК слишком длинная, заменяем фото на текст (убираем медиа)
            await callback.message.answer(ttk_caption, reply_markup=builder.as_markup(), parse_mode="HTML")
            # Не удаляем старое сообщение — убираем кнопки, чтобы не путать пользователя
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                print(traceback.format_exc())
    else:
        await callback.message.edit_text(text=ttk_caption, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("show_sauce_"))
async def show_sauce_info_handler(callback: types.CallbackQuery):
    # Данные приходят в формате show_sauce_{sauce_id}_{recipe_id}
    parts = callback.data.split("_")
    sauce_id = int(parts[2])
    recipe_id = int(parts[3])
    
    # Получаем данные о соусе
    sauce = get_sauce_by_id(sauce_id) 
    
    if not sauce:
        return await callback.answer("⚠️ Информация о соусе не найдена", show_alert=True)

    # Формируем текст состава соуса
    ingr_lines = [f"• {i['name']}: <b>{i['weight']}</b>" for i in sauce['ingredients']]
    ingredients_text = "\n".join(ingr_lines) if ingr_lines else "<i>Состав не указан</i>"
    
    sauce_text = (
        f"<b>🥣: {sauce['name']}</b>\n\n"
        f"<b>🛒 Состав:</b>\n{ingredients_text}\n\n"
        f"<b>⚖️ Выход:</b> {sauce.get('yield_weight', '—')}\n\n"
        f"<b>👨‍🍳 Технология:</b>\n{sauce.get('steps', '—')}"
    )

    # Клавиатура для возврата обратно в карточку блюда
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="📄 Вернуться к блюду", 
        callback_data=f"recipe_{recipe_id}"
    ))
    builder.row(types.InlineKeyboardButton(
        text="⬅️ Назад к списку", 
        callback_data="back_to_list"
    ))

    # Редактируем текущее сообщение (с фото или без)
    try:
        if callback.message.photo:
            # Проверка лимита 1024 символа
            if len(sauce_text) > 1024:
                await callback.message.answer(sauce_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                await callback.answer()
            else:
                await callback.message.edit_caption(
                    caption=sauce_text, 
                    reply_markup=builder.as_markup(), 
                    parse_mode="HTML"
                )
        else:
            await callback.message.edit_text(
                text=sauce_text, 
                reply_markup=builder.as_markup(), 
                parse_mode="HTML"
            )
    except Exception as e:
        print(traceback.format_exc())
        await callback.message.answer(sauce_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer()


# Кнопка ⬅️ Назад    
@router.callback_query(F.data == "back_to_list")
async def back_to_categories_simple(callback: types.CallbackQuery):
    # Убираем кнопки с текущего сообщения (если возможно) и отправляем новое меню
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        print(traceback.format_exc())

    # Отправляем новое чистое сообщение с выбором цехов
    await callback.message.answer(
        "📂 <b>БАЗА РЕЦЕПТОВ</b>\nВыберите интересующий вас отдел:",
        reply_markup=recipe_inline_kb(),
        parse_mode="HTML"
    )

    await callback.answer()