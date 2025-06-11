from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import config
from database.db_functions import is_maintenance_mode

class AuthMiddleware(BaseMiddleware):
    """Middleware для авторизации и проверки режима обслуживания"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        # Проверяем, является ли пользователь админом
        is_admin = user_id in config.ALL_ADMINS
        is_super_admin = user_id in config.SUPER_ADMINS
        
        # Добавляем информацию об админе в данные для обработчиков
        data["is_admin"] = is_admin
        data["is_super_admin"] = is_super_admin
        
        # Проверяем режим обслуживания (не распространяется на админов)
        if not is_admin:
            maintenance = await is_maintenance_mode()
            if maintenance:
                if isinstance(event, Message):
                    await event.answer(
                        "🔧 Бот находится на техническом обслуживании.\n"
                        "Попробуйте позже."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Бот на техническом обслуживании",
                        show_alert=True
                    )
                return  # Прекращаем обработку
        
        # Продолжаем выполнение обработчика
        return await handler(event, data)