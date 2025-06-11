import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from database.db_functions import init_database
from middleware.auth_middleware import AuthMiddleware
from handlers import user_handlers, admin_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def create_directories():
    """Создать необходимые директории"""
    directories = [
        'prompts',
        'prompts/templates',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Директория {directory} создана или уже существует")

async def create_prompt_template():
    """Создать файл шаблона промпта если его нет"""
    template_path = os.path.join(config.PROMPTS_DIR, "check_answer_prompt.txt")
    
    if not os.path.exists(template_path):
        template_content = """Ты — эксперт-преподаватель морского дела и IT-ментор. Твоя задача — оценить ответ студента, основываясь ИСКЛЮЧИТЕЛЬНО на предоставленном ниже учебном материале.

### Учебный материал по теме:
---
{theory_text}
---

### Задание для проверки:
Вопрос: "{question_text}"
Ответ студента: "{user_answer_text}"

### Критерии оценки:
1. Полнота ответа - охватывает ли ответ основные аспекты вопроса
2. Правильность - соответствуют ли факты в ответе учебному материалу
3. Понимание - демонстрирует ли студент понимание темы

### Инструкции:
- Основывайся СТРОГО на предоставленном учебном материале
- Если ответ содержит основную суть, но неполный - считай его достаточным
- Если ответ содержит грубые ошибки или полностью неверен - считай недостаточным
- Рекомендации должны быть конкретными и ссылаться на материал

### Формат вывода (ТОЛЬКО JSON):
{{"is_sufficient": boolean, "recommendation": "краткая рекомендация для студента"}}"""
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        logger.info(f"Создан файл шаблона промпта: {template_path}")

async def setup_bot():
    """Настройка и запуск бота"""
    try:
        # Создаем необходимые директории
        await create_directories()
        
        # Создаем шаблон промпта
        await create_prompt_template()
        
        # Инициализируем базу данных
        logger.info("Инициализация базы данных...")
        await init_database()
        logger.info("База данных успешно инициализирована")
        
        # Создаем бота и диспетчер
        bot = Bot(token=config.BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрируем middleware (ВАЖНО: в правильном порядке!)
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())
        
        # Регистрируем роутеры (ВАЖНО: admin_handlers ПЕРЕД user_handlers для приоритета)
        dp.include_router(admin_handlers.router)
        dp.include_router(user_handlers.router)
        
        logger.info("Бот настроен и готов к запуску")
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"Бот запущен: @{bot_info.username} ({bot_info.full_name})")
        
        # Уведомляем админов о запуске
        for admin_id in config.ALL_ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 **Бот {bot_info.full_name} запущен!**\n\n"
                    f"📊 **Конфигурация:**\n"
                    f"• Супер-админы: {len(config.SUPER_ADMINS)}\n"
                    f"• Админы: {len(config.ADMINS)}\n"
                    f"• Inline интерфейс: ✅\n"
                    f"• AI анализ: ✅\n\n"
                    f"Используйте /start для начала работы.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")
        
        # Запускаем polling
        logger.info("Запуск polling...")
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise

async def shutdown_bot(bot: Bot):
    """Корректное завершение работы бота"""
    try:
        # Уведомляем админов о остановке
        for admin_id in config.ALL_ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    "🔴 **Бот останавливается...**\n\n"
                    f"📅 Время: {asyncio.get_running_loop().time()}"
                )
            except Exception:
                pass  # Игнорируем ошибки при остановке
        
        await bot.session.close()
        logger.info("Бот успешно остановлен")
        
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")

def main():
    """Главная функция"""
    logger.info("=== 🚀 Запуск AI Mentor Bot (Inline Version) ===")
    
    # Проверяем наличие необходимых переменных окружения
    try:
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден")
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не найден")
        
        logger.info("✅ Конфигурация успешно загружена")
        logger.info(f"👑 Супер-админов: {len(config.SUPER_ADMINS)}")
        logger.info(f"🛡️ Админов: {len(config.ADMINS)}")
        logger.info(f"🎨 Интерфейс: Inline")
        
    except Exception as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # Запускаем бота
    try:
        asyncio.run(setup_bot())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        sys.exit(1)
    finally:
        logger.info("=== ✅ Завершение работы AI Mentor Bot ===")

if __name__ == "__main__":
    main()