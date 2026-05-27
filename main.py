from loader import dp, bot
from db import init_db
import asyncio, logging, sys
from services import setup_scheduler

# Импорт роутеров
from services import morning_report
from routers import (
    admin_main,
    admin_add_recipe,
    admin_edit_recipe,
    admin_edit_materials,
    user_main,
    admin_manage_tags,
    admin_manage_sauces,
    admin_manage_restaurants,
    director_manage_staff,
    user_interactions,
    user_materials,
    close_shift,
    meetings_calendar,
    gratitude,
    quiz_sender,
    announcement,
    search,

)

logging.basicConfig(
    filename='bot_errors.log',       # Имя файла, куда будут писаться логи
    filemode='a',                    # Режим добавления (append), чтобы не перезаписывать файл при каждом запуске
    format='%(asctime)s - %(levelname)s - %(message)s', # Формат сообщения: дата, уровень, сообщение
    level=logging.INFO               # Минимальный уровень логирования (INFO и выше)
)



async def main():
    # Подключаем все роутеры
    dp.include_router(admin_main.router)
    dp.include_router(admin_add_recipe.router)
    dp.include_router(admin_edit_recipe.router)
    dp.include_router(admin_manage_tags.router)
    dp.include_router(admin_manage_sauces.router)
    dp.include_router(admin_manage_restaurants.router)
    dp.include_router(director_manage_staff.router)
    dp.include_router(close_shift.router)
    dp.include_router(meetings_calendar.router)    
    dp.include_router(admin_edit_materials.router)    
    dp.include_router(user_main.router)
    dp.include_router(user_materials.router)
    dp.include_router(user_interactions.router)
    dp.include_router(morning_report.router)
    dp.include_router(gratitude.router) 
    dp.include_router(quiz_sender.router)
    dp.include_router(announcement.router)
    dp.include_router(search.router)
    

    logging.info("Бот запущен...")
    scheduler = setup_scheduler()
    scheduler.start()
    

    
    try:
        init_db()
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:        
        asyncio.run(main())
        
    except (KeyboardInterrupt, SystemExit):        
        logging.info("Бот остановлен вручную.")
        
    except Exception as e:
        logging.exception("Критическая ошибка в основном цикле бота!") 
        sys.exit(1)