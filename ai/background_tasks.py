import asyncio
import logging
from typing import List, Dict
from aiogram import Bot
from ai.ai_processor import analyze_answer, generate_final_report
from database.db_functions import (
    get_test_answers, 
    get_theory_for_block, 
    save_ai_analysis, 
    update_test_attempt_status,
    update_user_progress,
    get_content_block
)
from database.models import TestStatus
from utils.keyboards import get_test_feedback_keyboard

logger = logging.getLogger(__name__)

async def run_ai_analysis_and_notify(bot: Bot, user_id: int, attempt_id: int):
    """Фоновая задача для анализа ответов ИИ и уведомления пользователя"""
    try:
        # Обновляем статус попытки на "анализируется"
        await update_test_attempt_status(attempt_id, TestStatus.ANALYZING)
        
        # Получаем все ответы пользователя
        answers = await get_test_answers(attempt_id)
        if not answers:
            logger.error(f"Не найдены ответы для attempt_id {attempt_id}")
            return
        
        total_questions = len(answers)
        block_id = answers[0]["block_id"]
        
        # Получаем теорию для блока
        theory_text = await get_theory_for_block(block_id)
        if not theory_text:
            logger.error(f"Не найдена теория для block_id {block_id}")
            return
        
        # Отправляем начальное сообщение с индикатором прогресса
        progress_message = await bot.send_message(
            user_id,
            f"🔍 Анализирую ваши ответы... [0/{total_questions}]"
        )
        
        # Анализируем каждый ответ
        analysis_results = []
        
        for i, answer in enumerate(answers):
            try:
                # Обновляем прогресс
                await bot.edit_message_text(
                    f"🔍 Анализирую ваши ответы... [{i+1}/{total_questions}]",
                    chat_id=user_id,
                    message_id=progress_message.message_id
                )
                
                # Анализируем ответ через ИИ
                analysis_result = await analyze_answer(
                    theory_text=theory_text,
                    question_text=answer["question_text"],
                    user_answer_text=answer["user_answer_text"]
                )
                
                if analysis_result:
                    is_sufficient, recommendation = analysis_result
                    
                    # Сохраняем результат анализа в БД
                    await save_ai_analysis(
                        answer_id=answer["answer_id"],
                        is_sufficient=is_sufficient,
                        recommendation=recommendation
                    )
                    
                    analysis_results.append({
                        "question_text": answer["question_text"],
                        "user_answer_text": answer["user_answer_text"],
                        "is_sufficient": is_sufficient,
                        "recommendation": recommendation
                    })
                    
                    logger.info(f"✅ Анализ ответа {i+1}/{total_questions} завершен")
                else:
                    # Если анализ не удался, сохраняем базовую рекомендацию
                    await save_ai_analysis(
                        answer_id=answer["answer_id"],
                        is_sufficient=False,
                        recommendation="Рекомендую изучить материал более подробно."
                    )
                    
                    analysis_results.append({
                        "question_text": answer["question_text"],
                        "user_answer_text": answer["user_answer_text"],
                        "is_sufficient": False,
                        "recommendation": "Рекомендую изучить материал более подробно."
                    })
                    
                    logger.warning(f"⚠️ Анализ ответа {i+1}/{total_questions} не удался")
                
                # Небольшая задержка чтобы не перегружать API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Ошибка анализа ответа {i+1}: {e}")
                # Продолжаем с базовой рекомендацией
                analysis_results.append({
                    "question_text": answer["question_text"],
                    "user_answer_text": answer["user_answer_text"],
                    "is_sufficient": False,
                    "recommendation": "Произошла ошибка анализа. Рекомендую повторить материал."
                })
        
        # Генерируем итоговый отчет
        final_report = await generate_final_report(analysis_results)
        
        # Обновляем сообщение с итоговым отчетом
        await bot.edit_message_text(
            final_report,
            chat_id=user_id,
            message_id=progress_message.message_id,
            reply_markup=get_test_feedback_keyboard(attempt_id),
            parse_mode="Markdown"
        )
        
        # Обновляем статус попытки на "завершен"
        await update_test_attempt_status(attempt_id, TestStatus.COMPLETED)
        
        # Обновляем прогресс пользователя если тест пройден успешно
        block = await get_content_block(block_id)
        if block:
            sufficient_count = sum(1 for result in analysis_results if result["is_sufficient"])
            success_rate = sufficient_count / total_questions if total_questions > 0 else 0
            
            # Считаем тест пройденным если >= 70% правильных ответов
            if success_rate >= 0.7:
                await update_user_progress(user_id, block["block_order"])
                logger.info(f"✅ Пользователь {user_id} успешно прошел блок {block['block_order']}")
        
        logger.info(f"✅ Анализ теста для attempt_id {attempt_id} завершен успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в фоновой задаче анализа: {e}")
        
        try:
            # Отправляем сообщение об ошибке пользователю
            await bot.send_message(
                user_id,
                "😔 Произошла ошибка при анализе ваших ответов.\n"
                "Ваши ответы сохранены. Попробуйте пройти тест позже."
            )
            
            # Обновляем статус на "ошибка"
            await update_test_attempt_status(attempt_id, TestStatus.FAILED)
            
        except Exception as notify_error:
            logger.error(f"❌ Ошибка отправки уведомления об ошибке: {notify_error}")

def create_background_task(bot: Bot, user_id: int, attempt_id: int):
    """Создать фоновую задачу для анализа"""
    task = asyncio.create_task(
        run_ai_analysis_and_notify(bot, user_id, attempt_id)
    )
    
    # Добавляем обработку исключений в задачу
    def handle_task_exception(task):
        try:
            exception = task.exception()
            if exception:
                logger.error(f"❌ Необработанная ошибка в фоновой задаче: {exception}")
        except asyncio.InvalidStateError:
            pass  # Задача еще выполняется
    
    task.add_done_callback(handle_task_exception)
    return task