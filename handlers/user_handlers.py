import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InputFile
from aiogram.exceptions import TelegramBadRequest 

from database.db_functions import (
    get_or_create_user, get_content_blocks, get_content_block,
    get_questions_for_block, create_test_attempt, get_active_test_attempt,
    save_user_answer, get_answered_questions_count, save_feedback_rating,
    cancel_test_attempt
)
from fsm.states import Test
from utils.keyboards import (
    get_main_menu_keyboard, get_theory_menu_keyboard, get_theory_view_keyboard,
    get_tests_menu_keyboard, get_test_feedback_keyboard, get_back_keyboard,
    get_active_test_keyboard, get_test_in_progress_keyboard
)
from utils.constants import MESSAGES, EMOJI
from ai.ai_processor import transcribe_voice
from ai.background_tasks import create_background_task

logger = logging.getLogger(__name__)
router = Router()

# === ГЛАВНОЕ МЕНЮ ===

@router.message(Command("start"))
async def cmd_start(message: Message, is_admin: bool = False):
    """Команда /start - показать главное меню"""
    try:
        # Регистрируем пользователя
        await get_or_create_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        # Отправляем главное меню
        await message.answer(
            MESSAGES["main_menu"].format(name=message.from_user.full_name),
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer(MESSAGES["error_generic"])

@router.callback_query(F.data == "menu_main")
async def show_main_menu(callback: CallbackQuery, is_admin: bool = False):
    """Показать главное меню"""
    try:
        # Всегда отправляем новое сообщение для главного меню
        await callback.message.delete()
        await callback.message.answer(
            MESSAGES["main_menu"].format(name=callback.from_user.full_name),
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_main_menu: {e}")
        # Если не удалось удалить, пробуем редактировать
        try:
            await callback.message.edit_text(
                MESSAGES["main_menu"].format(name=callback.from_user.full_name),
                reply_markup=get_main_menu_keyboard(is_admin=is_admin),
                parse_mode="Markdown"
            )
            await callback.answer()
        except Exception:
            await callback.answer("Ошибка загрузки меню")

# === ТЕОРИЯ ===

@router.callback_query(F.data == "menu_theory")
async def show_theory_menu(callback: CallbackQuery):
    """Показать меню теории"""
    try:
        blocks = await get_content_blocks()
        
        if not blocks:
            message_text = "📚 **Теория**\n\nБлоки теории пока не добавлены."
            keyboard = get_back_keyboard("main")
        else:
            message_text = MESSAGES["theory_menu"]
            keyboard = get_theory_menu_keyboard(blocks)
        
        # Всегда отправляем новое сообщение для меню теории
        await callback.message.delete()
        await callback.message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_theory_menu: {e}")
        # Если не удалось удалить, пробуем редактировать
        try:
            blocks = await get_content_blocks()
            if not blocks:
                await callback.message.edit_text(
                    "📚 **Теория**\n\nБлоки теории пока не добавлены.",
                    reply_markup=get_back_keyboard("main"),
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text(
                    MESSAGES["theory_menu"],
                    reply_markup=get_theory_menu_keyboard(blocks),
                    parse_mode="Markdown"
                )
            await callback.answer()
        except Exception:
            await callback.answer("Ошибка загрузки теории")

@router.callback_query(F.data.startswith("theory_view_"))
async def view_theory(callback: CallbackQuery, state: FSMContext):
    """Просмотр конкретного блока теории (текст + медиа в одном сообщении)"""
    try:
        block_id = int(callback.data.split("_")[-1])
        block = await get_content_block(block_id)

        if not block:
            await callback.answer("Блок не найден", show_alert=True)
            return

        # Подготавливаем содержимое блока
        text_part = block["theory_text"] or "Материалы для этого блока пока не загружены."
        
        # Ограничиваем длину caption (лимит Telegram - 1024 символа)
        max_caption_length = 950  # Оставляем место для заголовка
        if len(text_part) > max_caption_length:
            text_part = text_part[:max_caption_length] + "..."
        
        caption = MESSAGES["theory_block"].format(
            title=block["title"],
            content=text_part
        )

        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Определяем тип контента и отправляем соответствующее сообщение
        keyboard = get_theory_view_keyboard(block_id)
        
        if block["video_file_id"]:
            # Отправляем видео с текстом в caption
            new_message = await callback.message.answer_video(
                video=block["video_file_id"],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        elif block["pdf_file_id"]:
            # Отправляем PDF с текстом в caption
            new_message = await callback.message.answer_document(
                document=block["pdf_file_id"],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # Отправляем только текст если нет медиа
            new_message = await callback.message.answer(
                caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        # Сохраняем информацию о сообщении в состоянии для корректной навигации
        await state.update_data(
            last_theory_message_id=new_message.message_id,
            last_theory_message_type="media" if (block["video_file_id"] or block["pdf_file_id"]) else "text"
        )
        
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка в view_theory: {e}")
        await callback.answer("Ошибка загрузки блока")

@router.callback_query(F.data == "menu_theory_back")
async def back_to_theory_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню теории"""
    try:
        # Получаем блоки теории
        blocks = await get_content_blocks()
        
        # Удаляем текущее сообщение (неважно какого типа)
        await callback.message.delete()
        
        # Отправляем новое сообщение с меню теории
        if not blocks:
            await callback.message.answer(
                "📚 **Теория**\n\nБлоки теории пока не добавлены.",
                reply_markup=get_back_keyboard("main"),
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                MESSAGES["theory_menu"],
                reply_markup=get_tests_menu_keyboard(blocks),
                parse_mode="Markdown"
            )
        
        # Очищаем данные состояния
        await state.update_data(
            last_theory_message_id=None,
            last_theory_message_type=None
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в back_to_theory_menu: {e}")
        await callback.answer("Ошибка загрузки меню")

# === ТЕСТЫ ===

@router.callback_query(F.data == "menu_tests")
async def show_tests_menu(callback: CallbackQuery):
    """Показать меню тестов"""
    try:
        # Получаем пользователя и его прогресс
        user = await get_or_create_user(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        blocks = await get_content_blocks()
        
        if not blocks:
            await callback.message.edit_text(
                "📝 **Тесты**\n\nТесты пока не добавлены.",
                reply_markup=get_back_keyboard("main"),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            MESSAGES["tests_menu"],
            reply_markup=get_tests_menu_keyboard(blocks, user["last_completed_block_order"]),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в show_tests_menu: {e}")
        await callback.answer("Ошибка загрузки тестов")

@router.callback_query(F.data.startswith("test_locked_"))
async def test_locked(callback: CallbackQuery):
    """Заблокированный тест"""
    await callback.answer(MESSAGES["test_locked"], show_alert=True)

@router.callback_query(F.data.startswith("test_start_"))
async def start_test(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начать тест с проверкой активного теста (учёт сообщений с медиа)"""
    try:
        block_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id

        # Проверяем активный тест
        active_test = await get_active_test_attempt(user_id)
        if active_test:
            # Сохраняем block_id нового теста для использования после отмены
            await state.update_data(pending_test_block_id=block_id)

            message_text = (
                f"⚠️ **У вас есть незавершенный тест**\n\n"
                f"Тест: {active_test['block_title']}\n\n"
                f"Что вы хотите сделать?"
            )
            keyboard = get_active_test_keyboard(active_test)

            # Безопасное обновление сообщения: пытаемся отредактировать,
            # при неудаче (медиа-сообщение) — удаляем и отправляем заново.
            try:
                await callback.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except TelegramBadRequest:
                # Нельзя редактировать сообщение (скорее всего содержит медиа)
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )

            await callback.answer()
            return

        # Если активного теста нет, запускаем новый
        await start_new_test(callback, state, bot, block_id)

    except Exception as e:
        logger.error(f"Ошибка в start_test: {e}")
        await callback.answer("Ошибка запуска теста")

async def start_new_test(callback: CallbackQuery, state: FSMContext, bot: Bot, block_id: int):
    """Начать новый тест (вспомогательная функция)"""
    try:
        user_id = callback.from_user.id
        
        # Получаем вопросы
        questions = await get_questions_for_block(block_id)
        if not questions:
            await callback.answer("Вопросы не найдены", show_alert=True)
            return
        
        # Создаем попытку
        attempt_id = await create_test_attempt(user_id, block_id)
        
        # Устанавливаем FSM
        await state.set_state(Test.in_progress)
        await state.update_data(
            attempt_id=attempt_id,
            block_id=block_id,
            questions=questions,
            current_question_index=0,
            test_message_id=callback.message.message_id,
            pending_test_block_id=None  # Очищаем pending test
        )
        
        # Показываем первый вопрос
        first_question = questions[0]
        await callback.message.edit_text(
            MESSAGES["test_started"].format(
                current=1,
                total=len(questions),
                question=first_question["question_text"]
            ),
            reply_markup=get_test_in_progress_keyboard(),
            parse_mode="Markdown"
        )
        
        await callback.answer("Тест начался! Отвечайте текстом или голосом.")
        
    except Exception as e:
        logger.error(f"Ошибка в start_new_test: {e}")
        await callback.answer("Ошибка запуска теста")

@router.callback_query(F.data == "test_continue")
async def continue_test_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Продолжить активный тест"""
    try:
        user_id = callback.from_user.id
        
        active_test = await get_active_test_attempt(user_id)
        if not active_test:
            await callback.answer("Активный тест не найден", show_alert=True)
            return
        
        attempt_id = active_test["attempt_id"]
        block_id = active_test["block_id"]
        
        questions = await get_questions_for_block(block_id)
        answered_count = await get_answered_questions_count(attempt_id)
        
        if answered_count >= len(questions):
            # Удаляем текущее сообщение и отправляем новое
            await callback.message.delete()
            await callback.message.answer(
                "❓ Вы уже ответили на все вопросы. Ожидайте результаты.",
                reply_markup=get_back_keyboard("tests"),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Восстанавливаем FSM
        await state.set_state(Test.in_progress)
        await state.update_data(
            attempt_id=attempt_id,
            block_id=block_id,
            questions=questions,
            current_question_index=answered_count
        )
        
        # Показываем следующий вопрос
        next_question = questions[answered_count]
        
        # Удаляем текущее сообщение (которое может содержать медиа)
        await callback.message.delete()
        
        # Отправляем новое сообщение с тестом
        new_message = await callback.message.answer(
            MESSAGES["test_continued"].format(title=active_test["block_title"]) +
            MESSAGES["test_next_question"].format(
                current=answered_count + 1,
                total=len(questions),
                question=next_question["question_text"]
            ),
            reply_markup=get_test_in_progress_keyboard(),
            parse_mode="Markdown"
        )
        
        # Сохраняем ID нового сообщения для обновления
        await state.update_data(test_message_id=new_message.message_id)
        
        await callback.answer("Продолжаем тест!")
        
    except Exception as e:
        logger.error(f"Ошибка в continue_test_callback: {e}")
        await callback.answer("Ошибка продолжения теста")

@router.callback_query(F.data == "test_cancel_and_new")
async def cancel_and_start_new(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отменить текущий тест и начать новый"""
    try:
        user_id = callback.from_user.id
        
        # Отменяем активный тест
        cancelled = await cancel_test_attempt(user_id)
        if not cancelled:
            await callback.answer("Не удалось отменить тест", show_alert=True)
            return
        
        # Получаем block_id нового теста
        data = await state.get_data()
        block_id = data.get("pending_test_block_id")
        
        if not block_id:
            # Если по какой-то причине нет pending test, возвращаемся к списку тестов
            # Удаляем текущее сообщение, которое может содержать медиа
            await callback.message.delete()
            # Отправляем новое сообщение с меню тестов
            await callback.message.answer(
                MESSAGES["tests_menu"],
                reply_markup=get_tests_menu_keyboard(await get_content_blocks(), 0),
                parse_mode="Markdown"
            )
            return
        
        # Получаем вопросы
        questions = await get_questions_for_block(block_id)
        if not questions:
            await callback.answer("Вопросы не найдены", show_alert=True)
            return
        
        # Создаем попытку
        attempt_id = await create_test_attempt(user_id, block_id)
        
        # Устанавливаем FSM
        await state.set_state(Test.in_progress)
        await state.update_data(
            attempt_id=attempt_id,
            block_id=block_id,
            questions=questions,
            current_question_index=0,
            pending_test_block_id=None  # Очищаем pending test
        )
        
        # Удаляем текущее сообщение (которое может содержать медиа)
        await callback.message.delete()
        
        # Показываем первый вопрос в новом сообщении
        first_question = questions[0]
        new_message = await callback.message.answer(
            MESSAGES["test_started"].format(
                current=1,
                total=len(questions),
                question=first_question["question_text"]
            ),
            reply_markup=get_test_in_progress_keyboard(),
            parse_mode="Markdown"
        )
        
        # Сохраняем ID нового сообщения
        await state.update_data(test_message_id=new_message.message_id)
        
        await callback.answer("Тест начался! Отвечайте текстом или голосом.")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_and_start_new: {e}")
        await callback.answer("Ошибка при отмене теста")

@router.callback_query(F.data == "test_cancel_current")
async def cancel_current_test(callback: CallbackQuery, state: FSMContext):
    """Отменить текущий тест во время прохождения"""
    try:
        user_id = callback.from_user.id
        
        # Отменяем активный тест
        cancelled = await cancel_test_attempt(user_id)
        
        # Очищаем состояние
        await state.clear()
        
        if cancelled:
            await callback.message.edit_text(
                "❌ **Тест отменен**\n\n"
                "Вы можете начать новый тест или вернуться к изучению теории.",
                reply_markup=get_back_keyboard("tests"),
                parse_mode="Markdown"
            )
            await callback.answer("Тест отменен")
        else:
            await callback.answer("Не удалось отменить тест", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_current_test: {e}")
        await callback.answer("Ошибка при отмене теста")

# === ОТМЕНА ТЕСТА ===

@router.message(Command("cancel"))
async def cancel_test_command(message: Message, state: FSMContext):
    """Отменить текущий тест через команду /cancel"""
    try:
        # Проверяем, есть ли активное состояние теста
        current_state = await state.get_state()
        if current_state != Test.in_progress:
            await message.answer("У вас нет активного теста для отмены.")
            return
        
        user_id = message.from_user.id
        
        # Отменяем активный тест
        cancelled = await cancel_test_attempt(user_id)
        
        # Очищаем состояние
        await state.clear()
        
        if cancelled:
            await message.answer(
                "❌ **Тест отменен**\n\n"
                "Вы можете начать новый тест или вернуться к изучению теории.\n\n"
                "Используйте /start для возврата в главное меню.",
                parse_mode="Markdown"
            )
        else:
            await message.answer("Не удалось отменить тест.")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_test_command: {e}")
        await message.answer(MESSAGES["error_generic"])

# === ПРОХОЖДЕНИЕ ТЕСТА ===

@router.message(Test.in_progress)
async def process_test_answer(message: Message, state: FSMContext, bot: Bot):
    """Обработка ответа в тесте"""
    try:
        data = await state.get_data()
        attempt_id = data["attempt_id"]
        questions = data["questions"]
        current_index = data["current_question_index"]
        test_message_id = data["test_message_id"]
        
        # Получаем текст ответа
        answer_text = ""
        if message.text:
            answer_text = message.text[:1000]
        elif message.voice:
            # Распознаем голос
            voice_file = await bot.get_file(message.voice.file_id)
            voice_data = await bot.download_file(voice_file.file_path)
            
            transcribed = await transcribe_voice(voice_data.read())
            if transcribed:
                answer_text = transcribed[:1000]
            else:
                await message.answer("😔 Не удалось распознать голос. Попробуйте еще раз.")
                return
        else:
            await message.answer("📝 Отправьте текст или голосовое сообщение.")
            return
        
        # Сохраняем ответ
        current_question = questions[current_index]
        await save_user_answer(attempt_id, current_question["id"], answer_text)
        
        # Удаляем сообщение с ответом пользователя
        try:
            await message.delete()
        except Exception:
            pass
        
        # Следующий вопрос
        next_index = current_index + 1
        
        if next_index < len(questions):
            # Есть еще вопросы
            await state.update_data(current_question_index=next_index)
            next_question = questions[next_index]
            
            # Обновляем сообщение с тестом
            await bot.edit_message_text(
                MESSAGES["test_next_question"].format(
                    current=next_index + 1,
                    total=len(questions),
                    question=next_question["question_text"]
                ),
                chat_id=message.chat.id,
                message_id=test_message_id,
                reply_markup=get_test_in_progress_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Тест завершен
            await bot.edit_message_text(
                MESSAGES["test_completed"],
                chat_id=message.chat.id,
                message_id=test_message_id,
                parse_mode="Markdown"
            )
            
            await state.clear()
            
            # Запускаем анализ
            create_background_task(bot, message.from_user.id, attempt_id)
        
    except Exception as e:
        logger.error(f"Ошибка в process_test_answer: {e}")
        await message.answer(MESSAGES["error_generic"])

@router.message(Command("continue"))
async def continue_test(message: Message, state: FSMContext, bot: Bot):
    """Продолжить незавершенный тест через команду"""
    try:
        user_id = message.from_user.id
        
        active_test = await get_active_test_attempt(user_id)
        if not active_test:
            await message.answer(MESSAGES["test_not_found"])
            return
        
        attempt_id = active_test["attempt_id"]
        block_id = active_test["block_id"]
        
        questions = await get_questions_for_block(block_id)
        answered_count = await get_answered_questions_count(attempt_id)
        
        if answered_count >= len(questions):
            await message.answer("❓ Вы уже ответили на все вопросы. Ожидайте результаты.")
            return
        
        # Восстанавливаем FSM
        await state.set_state(Test.in_progress)
        await state.update_data(
            attempt_id=attempt_id,
            block_id=block_id,
            questions=questions,
            current_question_index=answered_count
        )
        
        # Показываем следующий вопрос
        next_question = questions[answered_count]
        test_message = await message.answer(
            MESSAGES["test_continued"].format(title=active_test["block_title"]) +
            MESSAGES["test_next_question"].format(
                current=answered_count + 1,
                total=len(questions),
                question=next_question["question_text"]
            ),
            reply_markup=get_test_in_progress_keyboard(),
            parse_mode="Markdown"
        )
        
        # Сохраняем ID сообщения для обновления
        await state.update_data(test_message_id=test_message.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка в continue_test: {e}")
        await message.answer(MESSAGES["error_generic"])

# === ОБРАТНАЯ СВЯЗЬ ===

@router.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(callback: CallbackQuery):
    """Обработка оценки результатов теста"""
    try:
        parts = callback.data.split("_")
        feedback_type = parts[1]  # "positive" or "negative"
        attempt_id = int(parts[2])
        
        rating = 1 if feedback_type == "positive" else -1
        await save_feedback_rating(attempt_id, rating)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"✅ **Спасибо за оценку!**\n\n{MESSAGES['feedback_thanks']}\n\nВы можете продолжить изучение других тем.",
            reply_markup=get_back_keyboard("main"),
            parse_mode="Markdown"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_feedback: {e}")
        await callback.answer("Ошибка сохранения оценки")

# === ОБРАБОТЧИК НЕИЗВЕСТНЫХ CALLBACK ===

@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback"""
    logger.warning(f"Неизвестный callback: {callback.data}")
    await callback.answer("Неизвестная команда", show_alert=True)