import logging
import math
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db_functions import (
    get_content_blocks, get_content_block, update_block_content,
    get_users_statistics, is_maintenance_mode, toggle_maintenance_mode,
    get_ai_analytics_data
)
import config
from fsm.states import AdminContent
from utils.keyboards import (
    get_admin_menu_keyboard, get_admin_content_keyboard, get_admin_stats_keyboard,
    get_ai_analytics_keyboard, get_ai_blocks_keyboard, get_back_keyboard
)
from utils.constants import MESSAGES, LIMITS

logger = logging.getLogger(__name__)
router = Router()

# === ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ ===

@router.callback_query(F.data == "menu_admin")
async def show_admin_menu(callback: CallbackQuery, is_admin: bool = False, is_super_admin: bool = False):
    """Показать главное меню админ-панели"""
    if not is_admin:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        maintenance = await is_maintenance_mode()
        
        await callback.message.edit_text(
            MESSAGES["admin_panel"],
            reply_markup=get_admin_menu_keyboard(is_super_admin, maintenance),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_admin_menu: {e}")
        await callback.answer("Ошибка загрузки админ-панели")

# === УПРАВЛЕНИЕ КОНТЕНТОМ ===

@router.callback_query(F.data == "admin_content")
async def show_content_management(callback: CallbackQuery, state: FSMContext):
    """Показать управление контентом"""
    try:
        blocks = await get_content_blocks()
        if not blocks:
            await callback.message.edit_text(
                "⚙️ **Управление контентом**\n\nБлоки контента не найдены.",
                reply_markup=get_back_keyboard("admin"),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Показываем первый блок
        first_block = blocks[0]
        await state.set_state(AdminContent.viewing_block)
        await state.update_data(
            blocks=blocks,
            current_block_index=0
        )
        
        await show_content_block(callback, first_block, 1, len(blocks))
        
    except Exception as e:
        logger.error(f"Ошибка в show_content_management: {e}")
        await callback.answer("Ошибка загрузки контента")

@router.callback_query(F.data.startswith("content_nav_"))
async def navigate_content_blocks(callback: CallbackQuery, state: FSMContext):
    """Навигация между блоками контента"""
    try:
        target_index = int(callback.data.split("_")[-1]) - 1  # Приводим к 0-based индексу
        data = await state.get_data()
        blocks = data.get("blocks", [])
        
        if 0 <= target_index < len(blocks):
            await state.update_data(current_block_index=target_index)
            target_block = blocks[target_index]
            await show_content_block(callback, target_block, target_index + 1, len(blocks))
        else:
            await callback.answer("Блок не найден")
        
    except Exception as e:
        logger.error(f"Ошибка в navigate_content_blocks: {e}")
        await callback.answer("Ошибка навигации")

async def show_content_block(callback: CallbackQuery, block: dict, current: int, total: int):
    """Показать конкретный блок для редактирования"""
    try:
        # Формируем превью блока
        preview_parts = []
        
        if block["theory_text"]:
            preview_parts.append(f"📝 Текст: {len(block['theory_text'])} символов")
        else:
            preview_parts.append("📝 Текст: не задан")
        
        if block["video_file_id"]:
            preview_parts.append("🎥 Видео: загружено")
        else:
            preview_parts.append("🎥 Видео: нет")
        
        if block["pdf_file_id"]:
            preview_parts.append("📄 PDF: загружен")
        else:
            preview_parts.append("📄 PDF: нет")
        
        preview_text = "\n".join(preview_parts)
        
        await callback.message.edit_text(
            MESSAGES["admin_content"].format(
                current=current,
                total=total,
                title=block["title"],
                preview=preview_text
            ),
            reply_markup=get_admin_content_keyboard(block["id"], current, total),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_content_block: {e}")
        await callback.answer("Ошибка отображения блока")

# === РЕДАКТИРОВАНИЕ КОНТЕНТА ===

@router.callback_query(F.data.startswith("content_edit_text_"))
async def edit_content_text(callback: CallbackQuery, state: FSMContext):
    """Редактировать текст блока"""
    try:
        block_id = int(callback.data.split("_")[-1])
        
        await state.set_state(AdminContent.waiting_for_text)
        await state.update_data(editing_block_id=block_id)
        
        await callback.message.edit_text(
            MESSAGES["send_new_text"],
            reply_markup=get_back_keyboard("admin"),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в edit_content_text: {e}")
        await callback.answer("Ошибка редактирования")

@router.callback_query(F.data.startswith("content_edit_video_"))
async def edit_content_video(callback: CallbackQuery, state: FSMContext):
    """Редактировать видео блока"""
    try:
        block_id = int(callback.data.split("_")[-1])
        
        await state.set_state(AdminContent.waiting_for_video)
        await state.update_data(editing_block_id=block_id)
        
        await callback.message.edit_text(
            MESSAGES["send_new_video"],
            reply_markup=get_back_keyboard("admin"),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в edit_content_video: {e}")
        await callback.answer("Ошибка редактирования")

@router.callback_query(F.data.startswith("content_edit_pdf_"))
async def edit_content_pdf(callback: CallbackQuery, state: FSMContext):
    """Редактировать PDF блока"""
    try:
        block_id = int(callback.data.split("_")[-1])
        
        await state.set_state(AdminContent.waiting_for_pdf)
        await state.update_data(editing_block_id=block_id)
        
        await callback.message.edit_text(
            MESSAGES["send_new_pdf"],
            reply_markup=get_back_keyboard("admin"),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в edit_content_pdf: {e}")
        await callback.answer("Ошибка редактирования")

# === ОБРАБОТКА ЗАГРУЗКИ КОНТЕНТА ===

@router.message(AdminContent.waiting_for_text)
async def save_content_text(message: Message, state: FSMContext):
    """Сохранить новый текст блока"""
    try:
        data = await state.get_data()
        block_id = data["editing_block_id"]
        
        if len(message.text) > LIMITS["max_theory_length"]:
            await message.answer(
                f"❌ Текст слишком длинный. Максимум {LIMITS['max_theory_length']} символов."
            )
            return
        
        await update_block_content(block_id, theory_text=message.text)
        
        await message.answer(
            MESSAGES["admin_content_updated"],
            reply_markup=get_back_keyboard("admin")
        )
        
        await state.set_state(AdminContent.viewing_block)
        
    except Exception as e:
        logger.error(f"Ошибка в save_content_text: {e}")
        await message.answer(MESSAGES["error_generic"])

@router.message(AdminContent.waiting_for_video)
async def save_content_video(message: Message, state: FSMContext):
    """Сохранить новое видео блока"""
    try:
        data = await state.get_data()
        block_id = data["editing_block_id"]
        
        if message.video:
            file_id = message.video.file_id
            await update_block_content(block_id, video_file_id=file_id)
            await message.answer("✅ Видео обновлено!")
        else:
            await update_block_content(block_id, video_file_id=None)
            await message.answer("✅ Видео удалено!")
        
        await state.set_state(AdminContent.viewing_block)
        
    except Exception as e:
        logger.error(f"Ошибка в save_content_video: {e}")
        await message.answer(MESSAGES["error_generic"])

@router.message(AdminContent.waiting_for_pdf)
async def save_content_pdf(message: Message, state: FSMContext):
    """Сохранить новый PDF блока"""
    try:
        data = await state.get_data()
        block_id = data["editing_block_id"]
        
        if message.document and message.document.mime_type == "application/pdf":
            file_id = message.document.file_id
            await update_block_content(block_id, pdf_file_id=file_id)
            await message.answer("✅ PDF обновлен!")
        else:
            await update_block_content(block_id, pdf_file_id=None)
            await message.answer("✅ PDF удален!")
        
        await state.set_state(AdminContent.viewing_block)
        
    except Exception as e:
        logger.error(f"Ошибка в save_content_pdf: {e}")
        await message.answer(MESSAGES["error_generic"])

# === СТАТИСТИКА ===

@router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: CallbackQuery):
    """Показать статистику пользователей"""
    try:
        await show_stats_page(callback, page=1)
        
    except Exception as e:
        logger.error(f"Ошибка в show_statistics: {e}")
        await callback.answer("Ошибка загрузки статистики")

@router.callback_query(F.data.startswith("stats_page_"))
async def navigate_stats_pages(callback: CallbackQuery):
    """Навигация по страницам статистики"""
    try:
        page = int(callback.data.split("_")[-1])
        await show_stats_page(callback, page)
        
    except Exception as e:
        logger.error(f"Ошибка в navigate_stats_pages: {e}")
        await callback.answer("Ошибка навигации")

async def show_stats_page(callback: CallbackQuery, page: int):
    """Показать конкретную страницу статистики"""
    try:
        offset = (page - 1) * LIMITS["users_per_page"]
        users, total = await get_users_statistics(offset=offset, limit=LIMITS["users_per_page"])
        
        if not users:
            await callback.message.edit_text(
                "📊 **Статистика пользователей**\n\nПользователи не найдены.",
                reply_markup=get_back_keyboard("admin"),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Формируем текст статистики
        stats_text = []
        
        for i, user in enumerate(users, offset + 1):
            username = f"@{user['username']}" if user['username'] else "без username"
            stats_text.append(f"{i}. {user['full_name']} ({username})")
            stats_text.append(f"   {user['progress_text']}")
        
        total_pages = math.ceil(total / LIMITS["users_per_page"])
        stats_text.append(f"\nСтраница {page}/{total_pages} • Всего: {total}")
        
        await callback.message.edit_text(
            MESSAGES["admin_stats"].format(stats_text="\n".join(stats_text)),
            reply_markup=get_admin_stats_keyboard(
                page, total_pages,
                has_prev=page > 1, has_next=page < total_pages
            ),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_stats_page: {e}")
        await callback.answer("Ошибка загрузки страницы")

# === АНАЛИТИКА ИИ ===

@router.callback_query(F.data == "admin_ai_analytics")
async def show_ai_analytics(callback: CallbackQuery):
    """Показать основную аналитику ИИ"""
    try:
        analytics = await get_ai_analytics_data()
        
        total_feedback = analytics['positive_ratings'] + analytics['negative_ratings']
        feedback_rate = (analytics['positive_ratings'] / total_feedback * 100) if total_feedback > 0 else 0
        
        analytics_text = (
            "📉 **Аналитика ИИ - Обзор**\n\n"
            "🤖 **Общая статистика:**\n"
            f"• Всего анализов: {analytics['total_analyses']}\n"
            f"• Успешных: {analytics['successful_analyses']} ({analytics.get('avg_success_rate', 0):.1f}%)\n"
            f"• Ошибок: {analytics['failed_analyses']}\n\n"
            "👥 **Оценки пользователей:**\n"
            f"• 👍 Положительные: {analytics['positive_ratings']}\n"
            f"• 👎 Отрицательные: {analytics['negative_ratings']}\n"
            f"• 🤷 Без оценки: {analytics['no_ratings']}\n"
            f"• 📈 Удовлетворенность: {feedback_rate:.1f}%\n\n"
            f"📅 **Обновлено:** {analytics['last_updated']}"
        )
        
        await callback.message.edit_text(
            analytics_text,
            reply_markup=get_ai_analytics_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_ai_analytics: {e}")
        
        fallback_text = (
            "📉 **Аналитика ИИ**\n\n"
            "⚠️ **Статус:** Сбор данных...\n\n"
            "💡 **Для получения статистики:**\n"
            "• Пройдите несколько тестов\n"
            "• Оцените ответы ИИ (👍/👎)\n"
            f"📅 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.message.edit_text(
            fallback_text,
            reply_markup=get_back_keyboard("admin"),
            parse_mode="Markdown"
        )
        await callback.answer("Недостаточно данных")

@router.callback_query(F.data == "ai_analytics_blocks")
async def show_blocks_analytics(callback: CallbackQuery):
    """Показать детальную аналитику по блокам"""
    try:
        analytics = await get_ai_analytics_data()
        
        if not analytics['blocks']:
            await callback.answer("Нет данных по блокам", show_alert=True)
            return
        
        blocks_text = ["📊 **Детальная аналитика по блокам:**\n"]
        
        for block in analytics['blocks']:
            if block['total_answers'] > 0:
                total_feedback = block['positive_feedback'] + block['negative_feedback']
                
                blocks_text.append(f"📚 **{block['title']}**")
                blocks_text.append(f"• Тестов: {block['total_tests']}")
                blocks_text.append(f"• Ответов: {block['total_answers']}")
                blocks_text.append(f"• Успешность: {block['success_rate']:.1f}%")
                
                if total_feedback > 0:
                    blocks_text.append(f"• 👍 {block['positive_feedback']} / 👎 {block['negative_feedback']}")
                    blocks_text.append(f"• Удовлетворенность: {block['feedback_rate']:.1f}%")
                else:
                    blocks_text.append("• Оценок пока нет")
                
                blocks_text.append("")
        
        if len(blocks_text) == 1:
            blocks_text.append("Данных пока недостаточно.")
        
        await callback.message.edit_text(
            "\n".join(blocks_text),
            reply_markup=get_ai_blocks_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_blocks_analytics: {e}")
        await callback.answer("Ошибка загрузки данных")

@router.callback_query(F.data == "ai_analytics_best")
async def show_best_feedback(callback: CallbackQuery):
    """Показать блоки с лучшими оценками"""
    try:
        analytics = await get_ai_analytics_data()
        
        best_text = ["👍 **Блоки с лучшими оценками:**\n"]
        
        if analytics['best_feedback_blocks']:
            for i, block in enumerate(analytics['best_feedback_blocks'], 1):
                best_text.append(f"{i}. **{block['title']}**")
                best_text.append(f"   • 👍 {block['positive_feedback']} / 👎 {block['negative_feedback']}")
                best_text.append(f"   • Удовлетворенность: {block['feedback_rate']:.1f}%")
                best_text.append(f"   • Всего тестов: {block['total_tests']}")
                best_text.append("")
        else:
            best_text.append("Пока нет данных для анализа.")
        
        await callback.message.edit_text(
            "\n".join(best_text),
            reply_markup=get_ai_analytics_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_best_feedback: {e}")
        await callback.answer("Ошибка загрузки данных")

@router.callback_query(F.data == "ai_analytics_worst")
async def show_worst_feedback(callback: CallbackQuery):
    """Показать блоки с худшими оценками"""
    try:
        analytics = await get_ai_analytics_data()
        
        worst_text = ["👎 **Блоки требующие улучшения:**\n"]
        
        if analytics['worst_feedback_blocks']:
            for i, block in enumerate(analytics['worst_feedback_blocks'], 1):
                worst_text.append(f"{i}. **{block['title']}**")
                worst_text.append(f"   • 👍 {block['positive_feedback']} / 👎 {block['negative_feedback']}")
                worst_text.append(f"   • Удовлетворенность: {block['feedback_rate']:.1f}%")
                worst_text.append(f"   • Всего тестов: {block['total_tests']}")
                worst_text.append("")
            
            worst_text.append("💡 **Рекомендации:**")
            worst_text.append("• Проверьте качество теории")
            worst_text.append("• Обновите промпты для ИИ")
            worst_text.append("• Улучшите вопросы в тестах")
        else:
            worst_text.append("Нет блоков с плохими оценками.")
        
        await callback.message.edit_text(
            "\n".join(worst_text),
            reply_markup=get_ai_analytics_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_worst_feedback: {e}")
        await callback.answer("Ошибка загрузки данных")

# === НАСТРОЙКИ ===

@router.callback_query(F.data == "admin_maintenance")
async def toggle_maintenance(callback: CallbackQuery, is_super_admin: bool = False):
    """Переключить режим обслуживания"""
    if not is_super_admin:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    try:
        new_state = await toggle_maintenance_mode()
        
        # Обновляем админ-панель
        await callback.message.edit_text(
            MESSAGES["admin_panel"],
            reply_markup=get_admin_menu_keyboard(is_super_admin, new_state),
            parse_mode="Markdown"
        )
        
        status_text = MESSAGES["maintenance_enabled"] if new_state else MESSAGES["maintenance_disabled"]
        await callback.answer(status_text, show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в toggle_maintenance: {e}")
        await callback.answer("Ошибка переключения режима")