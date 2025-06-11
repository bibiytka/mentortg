# Константы для статусов тестов
class TestStatus:
    IN_PROGRESS = "in_progress"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"

# SQL запросы для создания таблиц
CREATE_TABLES_SQL = """
-- Таблица блоков контента
CREATE TABLE IF NOT EXISTS content_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    theory_text TEXT,
    video_file_id TEXT NULL,
    pdf_file_id TEXT NULL,
    block_order INTEGER UNIQUE NOT NULL
);

-- Таблица вопросов
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    FOREIGN KEY (block_id) REFERENCES content_blocks (id) ON DELETE CASCADE
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NULL,
    full_name TEXT NOT NULL,
    last_completed_block_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица попыток прохождения тестов
CREATE TABLE IF NOT EXISTS test_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    block_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress',
    attempt_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_timestamp DATETIME NULL,
    ai_feedback_rating INTEGER NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (block_id) REFERENCES content_blocks (id) ON DELETE CASCADE
);

-- Таблица ответов пользователей
CREATE TABLE IF NOT EXISTS user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    user_answer_text TEXT NOT NULL,
    ai_verdict_is_sufficient BOOLEAN NULL,
    ai_verdict_recommendation TEXT NULL,
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
);

-- Таблица настроек системы
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Вставляем начальные настройки
INSERT OR IGNORE INTO system_settings (key, value) VALUES ('maintenance_mode', 'false');
"""

# Индексы для производительности
CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_test_attempts_user_status ON test_attempts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_answers_attempt ON user_answers(attempt_id);
CREATE INDEX IF NOT EXISTS idx_questions_block ON questions(block_id);
CREATE INDEX IF NOT EXISTS idx_content_blocks_order ON content_blocks(block_order);
"""

# Начальные данные для тестирования
SAMPLE_DATA_SQL = """
-- Добавляем тестовые блоки контента
INSERT OR IGNORE INTO content_blocks (id, title, theory_text, block_order) VALUES 
(1, 'Блок 1 - Сухогруз', 
'Сухогруз - это тип судна, предназначенный для перевозки сухих грузов, таких как уголь, зерно, руда. Основными характеристиками являются большие грузовые трюмы и палубные краны для самопогрузки/выгрузки. Сухогрузы классифицируются по размеру: Handysize (10,000-35,000 тонн), Handymax (35,000-60,000 тонн), Panamax (60,000-80,000 тонн), Capesize (свыше 100,000 тонн).', 
1),

(2, 'Блок 2 - Рефрижераторный контейнер', 
'Рефрижераторный контейнер (reefer) - специализированный контейнер с системой охлаждения для перевозки скоропортящихся грузов. Оборудован компрессорной установкой, системой циркуляции воздуха и автоматическим контролем температуры. Температурный диапазон: от -30°C до +30°C. Требует подключения к судовой электросети мощностью 460V.', 
2),

(3, 'Блок 3 - Танкер', 
'Танкер - судно для перевозки жидких грузов (нефть, нефтепродукты, химикаты, сжиженный газ). Основные типы: нефтяные танкеры, химовозы, газовозы. Конструктивные особенности: двойной корпус, система инертных газов, специальные насосы и трубопроводы. Классификация по размеру: от малых (до 25,000 тонн) до супертанкеров (свыше 320,000 тонн).', 
3);

-- Добавляем тестовые вопросы
INSERT OR IGNORE INTO questions (block_id, question_text) VALUES 
(1, 'Что такое сухогруз и каково его основное назначение?'),
(1, 'Перечислите основные типы сухогрузов по размеру'),
(1, 'Какие характерные особенности конструкции имеют сухогрузы?'),

(2, 'Что такое рефрижераторный контейнер и для чего он используется?'),
(2, 'Какой температурный диапазон поддерживают рефрижераторные контейнеры?'),
(2, 'Какие технические требования предъявляются к подключению рефконтейнеров?'),

(3, 'Дайте определение танкера и опишите его назначение'),
(3, 'Перечислите основные типы танкеров'),
(3, 'Какие конструктивные особенности характерны для танкеров?');
"""