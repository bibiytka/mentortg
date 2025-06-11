

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

import config
from main import setup_bot, shutdown_bot
from aiogram import Bot

# Настройка логирования для продакшена
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BotRunner:
    """Класс для управления запуском и перезапуском бота"""
    
    def __init__(self):
        self.bot = None
        self.should_restart = True
        self.restart_count = 0
        self.max_restarts = 10
        
    async def start_bot(self):
        """Запустить бота с обработкой ошибок"""
        try:
            logger.info(f"=== Запуск AI Mentor Bot (попытка {self.restart_count + 1}) ===")
            
            # Создаем бота для уведомлений
            self.bot = Bot(token=config.BOT_TOKEN)
            
            # Уведомляем админов о запуске/перезапуске
            restart_msg = " (перезапуск)" if self.restart_count > 0 else ""
            for admin_id in config.SUPER_ADMINS:
                try:
                    await self.bot.send_message(
                        admin_id,
                        f"🚀 Бот запускается{restart_msg}...\n"
                        f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                        f"🔄 Попытка: {self.restart_count + 1}"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")
            
            # Запускаем основную логику бота
            await setup_bot()
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки (Ctrl+C)")
            self.should_restart = False
            
        except Exception as e:
            logger.error(f"Критическая ошибка бота: {e}", exc_info=True)
            self.restart_count += 1
            
            # Уведомляем админов об ошибке
            if self.bot:
                for admin_id in config.SUPER_ADMINS:
                    try:
                        await self.bot.send_message(
                            admin_id,
                            f"❌ Критическая ошибка бота!\n"
                            f"🐛 Ошибка: {str(e)[:500]}\n"
                            f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                            f"🔄 Попытка перезапуска: {self.restart_count}/{self.max_restarts}"
                        )
                    except Exception:
                        pass
            
            # Проверяем лимит перезапусков
            if self.restart_count >= self.max_restarts:
                logger.error(f"Превышен лимит перезапусков ({self.max_restarts}). Остановка.")
                self.should_restart = False
                
                # Финальное уведомление админов
                if self.bot:
                    for admin_id in config.SUPER_ADMINS:
                        try:
                            await self.bot.send_message(
                                admin_id,
                                f"🛑 Бот остановлен после {self.max_restarts} неудачных попыток.\n"
                                f"Требуется ручное вмешательство."
                            )
                        except Exception:
                            pass
            else:
                # Ждем перед перезапуском
                wait_time = min(60 * self.restart_count, 300)  # Увеличивающаяся задержка, max 5 мин
                logger.info(f"Ожидание {wait_time} секунд перед перезапуском...")
                await asyncio.sleep(wait_time)
        
        finally:
            if self.bot:
                await shutdown_bot(self.bot)
    
    async def run(self):
        """Основной цикл с перезапусками"""
        while self.should_restart:
            await self.start_bot()
            
            if self.should_restart and self.restart_count < self.max_restarts:
                logger.info("Подготовка к перезапуску...")
                await asyncio.sleep(5)  # Короткая пауза между попытками
        
        logger.info("=== Завершение работы AI Mentor Bot ===")

def setup_signal_handlers(runner):
    """Настройка обработчиков сигналов для корректной остановки"""
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}")
        runner.should_restart = False
        
        # Принудительно останавливаем event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
    
    # Обработка сигналов остановки
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # На Windows добавляем обработку Ctrl+Break
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

def check_environment():
    """Проверка окружения перед запуском"""
    logger.info("Проверка окружения...")
    
    # Проверяем наличие .env файла
    env_path = Path('.env')
    if not env_path.exists():
        logger.error("Файл .env не найден! Скопируйте .env.example в .env и заполните данные.")
        return False
    
    # Проверяем обязательные переменные
    required_vars = ['BOT_TOKEN', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        return False
    
    # Проверяем наличие админов
    if not config.ALL_ADMINS:
        logger.warning("Не настроены администраторы! Админ-панель будет недоступна.")
    else:
        logger.info(f"Настроено админов: {len(config.ALL_ADMINS)} (из них супер-админов: {len(config.SUPER_ADMINS)})")
    
    # Создаем необходимые директории
    dirs = ['logs', 'prompts', 'prompts/templates']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ Окружение готово к запуску")
    return True

def main():
    """Главная функция для продакшн запуска"""
    print("🤖 AI Mentor Bot - Production Runner")
    print("=" * 50)
    
    # Проверяем окружение
    if not check_environment():
        sys.exit(1)
    
    # Создаем runner
    runner = BotRunner()
    
    # Настраиваем обработчики сигналов
    setup_signal_handlers(runner)
    
    # Запускаем бота
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"Необработанная ошибка в main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()