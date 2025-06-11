import aiosqlite
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from database.models import CREATE_TABLES_SQL, CREATE_INDEXES_SQL, SAMPLE_DATA_SQL, TestStatus
import config

logger = logging.getLogger(__name__)

async def init_database():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            # Создаем таблицы
            await db.executescript(CREATE_TABLES_SQL)
            await db.executescript(CREATE_INDEXES_SQL)
            
            # Добавляем тестовые данные (только если таблицы пустые)
            cursor = await db.execute("SELECT COUNT(*) FROM content_blocks")
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.executescript(SAMPLE_DATA_SQL)
            
            await db.commit()
            logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ===

async def get_or_create_user(user_id: int, username: str = None, full_name: str = "") -> Dict:
    """Получить или создать пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Проверяем, существует ли пользователь
        cursor = await db.execute(
            "SELECT user_id, username, full_name, last_completed_block_order FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = await cursor.fetchone()
        
        if user:
            # Обновляем данные пользователя
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id)
            )
            await db.commit()
            return {
                "user_id": user[0],
                "username": user[1],
                "full_name": user[2],
                "last_completed_block_order": user[3]
            }
        else:
            # Создаем нового пользователя
            await db.execute(
                "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "last_completed_block_order": 0
            }

async def update_user_progress(user_id: int, completed_block_order: int):
    """Обновить прогресс пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET last_completed_block_order = ? WHERE user_id = ? AND last_completed_block_order < ?",
            (completed_block_order, user_id, completed_block_order)
        )
        await db.commit()

async def get_users_statistics(offset: int = 0, limit: int = 10) -> Tuple[List[Dict], int]:
    """Получить статистику пользователей с пагинацией"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Общее количество пользователей
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # Получаем максимальный порядок блоков
        cursor = await db.execute("SELECT MAX(block_order) FROM content_blocks")
        max_blocks = (await cursor.fetchone())[0] or 0
        
        # Получаем пользователей с их прогрессом
        cursor = await db.execute("""
            SELECT u.user_id, u.username, u.full_name, u.last_completed_block_order,
                   COUNT(DISTINCT ta.block_id) as completed_tests
            FROM users u
            LEFT JOIN test_attempts ta ON u.user_id = ta.user_id AND ta.status = 'completed'
            GROUP BY u.user_id
            ORDER BY u.last_completed_block_order DESC, completed_tests DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        users = []
        async for row in cursor:
            users.append({
                "user_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "last_completed_block_order": row[3],
                "completed_tests": row[4],
                "progress_text": f"Пройдено: {row[4]}/{max_blocks} тестов"
            })
        
        return users, total_users

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КОНТЕНТОМ ===

async def get_content_blocks() -> List[Dict]:
    """Получить все блоки контента"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, title, theory_text, video_file_id, pdf_file_id, block_order FROM content_blocks ORDER BY block_order"
        )
        blocks = []
        async for row in cursor:
            blocks.append({
                "id": row[0],
                "title": row[1],
                "theory_text": row[2],
                "video_file_id": row[3],
                "pdf_file_id": row[4],
                "block_order": row[5]
            })
        return blocks

async def get_content_block(block_id: int) -> Optional[Dict]:
    """Получить конкретный блок контента"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, title, theory_text, video_file_id, pdf_file_id, block_order FROM content_blocks WHERE id = ?",
            (block_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "theory_text": row[2],
                "video_file_id": row[3],
                "pdf_file_id": row[4],
                "block_order": row[5]
            }
        return None

async def update_block_content(block_id: int, **kwargs):
    """Обновить содержимое блока"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        for field, value in kwargs.items():
            if field in ['title', 'theory_text', 'video_file_id', 'pdf_file_id']:
                await db.execute(
                    f"UPDATE content_blocks SET {field} = ? WHERE id = ?",
                    (value, block_id)
                )
        await db.commit()

async def get_theory_for_block(block_id: int) -> Optional[str]:
    """Получить текст теории для блока"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT theory_text FROM content_blocks WHERE id = ?",
            (block_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ВОПРОСАМИ ===

async def get_questions_for_block(block_id: int) -> List[Dict]:
    """Получить все вопросы для блока"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, question_text FROM questions WHERE block_id = ? ORDER BY id",
            (block_id,)
        )
        questions = []
        async for row in cursor:
            questions.append({
                "id": row[0],
                "question_text": row[1]
            })
        return questions

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ТЕСТАМИ ===

async def create_test_attempt(user_id: int, block_id: int) -> int:
    """Создать новую попытку прохождения теста"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO test_attempts (user_id, block_id, status) VALUES (?, ?, ?)",
            (user_id, block_id, TestStatus.IN_PROGRESS)
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_test_attempt(user_id: int) -> Optional[Dict]:
    """Получить активную попытку теста пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT ta.id, ta.block_id, ta.status, cb.title
            FROM test_attempts ta
            JOIN content_blocks cb ON ta.block_id = cb.id
            WHERE ta.user_id = ? AND ta.status = ?
        """, (user_id, TestStatus.IN_PROGRESS))
        
        row = await cursor.fetchone()
        if row:
            return {
                "attempt_id": row[0],
                "block_id": row[1],
                "status": row[2],
                "block_title": row[3]
            }
        return None

async def update_test_attempt_status(attempt_id: int, status: str):
    """Обновить статус попытки теста"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        timestamp_field = "completed_timestamp" if status == TestStatus.COMPLETED else None
        if timestamp_field:
            await db.execute(
                f"UPDATE test_attempts SET status = ?, {timestamp_field} = CURRENT_TIMESTAMP WHERE id = ?",
                (status, attempt_id)
            )
        else:
            await db.execute(
                "UPDATE test_attempts SET status = ? WHERE id = ?",
                (status, attempt_id)
            )
        await db.commit()

async def cancel_test_attempt(user_id: int) -> bool:
    """Отменить активную попытку теста пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Находим активную попытку
        cursor = await db.execute(
            "SELECT id FROM test_attempts WHERE user_id = ? AND status = ?",
            (user_id, TestStatus.IN_PROGRESS)
        )
        attempt = await cursor.fetchone()
        
        if attempt:
            attempt_id = attempt[0]
            # Обновляем статус на "abandoned"
            await db.execute(
                "UPDATE test_attempts SET status = ?, completed_timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                (TestStatus.ABANDONED, attempt_id)
            )
            await db.commit()
            logger.info(f"Тест {attempt_id} отменен для пользователя {user_id}")
            return True
        
        return False

async def save_user_answer(attempt_id: int, question_id: int, answer_text: str):
    """Сохранить ответ пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO user_answers (attempt_id, question_id, user_answer_text) VALUES (?, ?, ?)",
            (attempt_id, question_id, answer_text)
        )
        await db.commit()

async def get_answered_questions_count(attempt_id: int) -> int:
    """Получить количество отвеченных вопросов"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_answers WHERE attempt_id = ?",
            (attempt_id,)
        )
        return (await cursor.fetchone())[0]

async def get_test_answers(attempt_id: int) -> List[Dict]:
    """Получить все ответы для попытки теста"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT ua.id, ua.question_id, ua.user_answer_text, q.question_text, ta.block_id
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            JOIN test_attempts ta ON ua.attempt_id = ta.id
            WHERE ua.attempt_id = ?
            ORDER BY ua.id
        """, (attempt_id,))
        
        answers = []
        async for row in cursor:
            answers.append({
                "answer_id": row[0],
                "question_id": row[1],
                "user_answer_text": row[2],
                "question_text": row[3],
                "block_id": row[4]
            })
        return answers

async def save_ai_analysis(answer_id: int, is_sufficient: bool, recommendation: str):
    """Сохранить результат анализа ИИ"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE user_answers SET ai_verdict_is_sufficient = ?, ai_verdict_recommendation = ? WHERE id = ?",
            (is_sufficient, recommendation, answer_id)
        )
        await db.commit()

async def save_feedback_rating(attempt_id: int, rating: int):
    """Сохранить оценку обратной связи"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE test_attempts SET ai_feedback_rating = ? WHERE id = ?",
            (rating, attempt_id)
        )
        await db.commit()

# === ФУНКЦИИ ДЛЯ НАСТРОЕК СИСТЕМЫ ===

async def get_setting(key: str) -> Optional[str]:
    """Получить настройку системы"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM system_settings WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_setting(key: str, value: str):
    """Установить настройку системы"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        await db.commit()

async def is_maintenance_mode() -> bool:
    """Проверить, включен ли режим обслуживания"""
    value = await get_setting("maintenance_mode")
    return value == "true"

async def toggle_maintenance_mode() -> bool:
    """Переключить режим обслуживания"""
    current = await is_maintenance_mode()
    new_value = "false" if current else "true"
    await set_setting("maintenance_mode", new_value)
    return not current

# === АНАЛИТИКА ИИ ===

async def get_ai_analytics_data() -> dict:
    """Получить детальную аналитику по работе ИИ с разбивкой по блокам"""
    try:
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            analytics = {}
            
            # === ОБЩАЯ СТАТИСТИКА ===
            
            # Общая статистика анализов
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN ai_verdict_is_sufficient IS NOT NULL THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN ai_verdict_is_sufficient IS NULL THEN 1 ELSE 0 END) as failed
                FROM user_answers
            """)
            row = await cursor.fetchone()
            analytics['total_analyses'] = row[0] or 0
            analytics['successful_analyses'] = row[1] or 0
            analytics['failed_analyses'] = row[2] or 0
            
            # Оценки пользователей (лайки/дизлайки)
            cursor = await db.execute("""
                SELECT 
                    SUM(CASE WHEN ai_feedback_rating = 1 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN ai_feedback_rating = -1 THEN 1 ELSE 0 END) as negative,
                    SUM(CASE WHEN ai_feedback_rating IS NULL THEN 1 ELSE 0 END) as no_rating
                FROM test_attempts 
                WHERE status = 'completed'
            """)
            row = await cursor.fetchone()
            analytics['positive_ratings'] = row[0] or 0
            analytics['negative_ratings'] = row[1] or 0
            analytics['no_ratings'] = row[2] or 0
            
            # Качество анализа ИИ
            cursor = await db.execute("""
                SELECT 
                    SUM(CASE WHEN ai_verdict_is_sufficient = 1 THEN 1 ELSE 0 END) as sufficient,
                    SUM(CASE WHEN ai_verdict_is_sufficient = 0 THEN 1 ELSE 0 END) as insufficient
                FROM user_answers 
                WHERE ai_verdict_is_sufficient IS NOT NULL
            """)
            row = await cursor.fetchone()
            sufficient = row[0] or 0
            insufficient = row[1] or 0
            total_analyzed = sufficient + insufficient
            
            analytics['sufficient_answers'] = sufficient
            analytics['insufficient_answers'] = insufficient
            analytics['avg_success_rate'] = (sufficient / total_analyzed * 100) if total_analyzed > 0 else 0
            
            # === ДЕТАЛЬНАЯ СТАТИСТИКА ПО БЛОКАМ ===
            
            cursor = await db.execute("""
                SELECT 
                    cb.id,
                    cb.title,
                    cb.block_order,
                    COUNT(DISTINCT ta.id) as total_tests,
                    COUNT(ua.id) as total_answers,
                    SUM(CASE WHEN ua.ai_verdict_is_sufficient = 1 THEN 1 ELSE 0 END) as sufficient_answers,
                    SUM(CASE WHEN ua.ai_verdict_is_sufficient = 0 THEN 1 ELSE 0 END) as insufficient_answers,
                    SUM(CASE WHEN ta.ai_feedback_rating = 1 THEN 1 ELSE 0 END) as positive_feedback,
                    SUM(CASE WHEN ta.ai_feedback_rating = -1 THEN 1 ELSE 0 END) as negative_feedback,
                    SUM(CASE WHEN ta.ai_feedback_rating IS NULL THEN 1 ELSE 0 END) as no_feedback
                FROM content_blocks cb
                LEFT JOIN questions q ON cb.id = q.block_id
                LEFT JOIN user_answers ua ON q.id = ua.question_id AND ua.ai_verdict_is_sufficient IS NOT NULL
                LEFT JOIN test_attempts ta ON ua.attempt_id = ta.id AND ta.status = 'completed'
                GROUP BY cb.id, cb.title, cb.block_order
                ORDER BY cb.block_order
            """)
            
            blocks_analytics = []
            async for row in cursor:
                block_data = {
                    'block_id': row[0],
                    'title': row[1],
                    'block_order': row[2],
                    'total_tests': row[3] or 0,
                    'total_answers': row[4] or 0,
                    'sufficient_answers': row[5] or 0,
                    'insufficient_answers': row[6] or 0,
                    'positive_feedback': row[7] or 0,
                    'negative_feedback': row[8] or 0,
                    'no_feedback': row[9] or 0,
                    'success_rate': 0,
                    'feedback_rate': 0
                }
                
                # Рассчитываем проценты
                if block_data['total_answers'] > 0:
                    block_data['success_rate'] = (block_data['sufficient_answers'] / block_data['total_answers']) * 100
                
                total_feedback = block_data['positive_feedback'] + block_data['negative_feedback']
                if total_feedback > 0:
                    block_data['feedback_rate'] = (block_data['positive_feedback'] / total_feedback) * 100
                
                blocks_analytics.append(block_data)
            
            analytics['blocks'] = blocks_analytics
            
            # === ЛУЧШИЕ И ХУДШИЕ БЛОКИ ===
            
            # Блоки с лучшим фидбеком
            best_feedback_blocks = sorted(
                [b for b in blocks_analytics if b['positive_feedback'] + b['negative_feedback'] > 0],
                key=lambda x: x['feedback_rate'],
                reverse=True
            )[:3]
            
            # Блоки с худшим фидбеком  
            worst_feedback_blocks = sorted(
                [b for b in blocks_analytics if b['positive_feedback'] + b['negative_feedback'] > 0],
                key=lambda x: x['feedback_rate']
            )[:3]
            
            analytics['best_feedback_blocks'] = best_feedback_blocks
            analytics['worst_feedback_blocks'] = worst_feedback_blocks
            analytics['last_updated'] = datetime.now().strftime('%d.%m.%Y %H:%M')
            
            return analytics
            
    except Exception as e:
        logger.error(f"Ошибка в get_ai_analytics_data: {e}")
        # Возвращаем пустую аналитику в случае ошибки
        return {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'positive_ratings': 0,
            'negative_ratings': 0,
            'no_ratings': 0,
            'sufficient_answers': 0,
            'insufficient_answers': 0,
            'avg_success_rate': 0,
            'blocks': [],
            'best_feedback_blocks': [],
            'worst_feedback_blocks': [],
            'last_updated': 'Ошибка загрузки'
        }