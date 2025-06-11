# Текстовые сообщения для inline-интерфейса
MESSAGES = {
    # Главное меню
    "main_menu": "🏠 **Главное меню**\n\nДобро пожаловать, {name}!\n\nВыберите действие:",
    
    # Теория
    "theory_menu": "📚 **Теория**\n\nВыберите блок для изучения:",
    "theory_block": "📚 **{title}**\n\n{content}",
    "theory_empty": "📚 **{title}**\n\nМатериалы для этого блока пока не загружены.",
    
    # Тесты
    "tests_menu": "📝 **Тесты**\n\nВыберите тест для прохождения:\n\n💡 Тесты нужно проходить по порядку.",
    "test_locked": "🔒 Этот тест заблокирован.\n\nСначала пройдите предыдущие тесты.",
    
    # Прохождение теста
    "test_started": "🎯 **Тест начался!**\n\nВопрос {current}/{total}:\n\n{question}",
    "test_next_question": "Вопрос {current}/{total}:\n\n{question}",
    "test_completed": "✅ Спасибо, тест завершен!\n\n🤖 Начинаю анализ ваших ответов...",
    "test_analyzing": "🔍 Анализирую ваши ответы... [{current}/{total}]",
    "test_already_active": "⚠️ У вас уже есть активный тест.\n\nИспользуйте команду /continue для продолжения.",
    "test_not_found": "❌ У вас нет незавершенных тестов.",
    "test_continued": "🔄 Продолжаем тест: **{title}**\n\n",
    
    # Админ-панель
    "admin_panel": "👑 **Админ-панель**\n\nВыберите действие:",
    "admin_stats": "📊 **Статистика пользователей**\n\n{stats_text}",
    "admin_content": "⚙️ **Управление контентом**\n\nБлок {current}/{total}: **{title}**\n\n{preview}",
    "admin_content_updated": "✅ Контент успешно обновлен!",
    
    # Системные сообщения
    "maintenance_enabled": "🔧 Режим обслуживания включен",
    "maintenance_disabled": "✅ Режим обслуживания отключен",
    "feedback_thanks": "Спасибо за вашу оценку! 👍",
    "error_generic": "😔 Произошла ошибка. Попробуйте позже.",
    "error_ai": "🤖 Ошибка анализа ИИ. Ваши ответы сохранены.",
    "no_access": "❌ У вас нет доступа к этой функции.",
    
    # Редактирование контента
    "send_new_text": "📝 **Редактирование текста блока**\n\nПришлите новый текст:",
    "send_new_video": "🎥 **Изменение видео**\n\nПришлите новое видео или любой текст для удаления:",
    "send_new_pdf": "📄 **Изменение PDF**\n\nПришлите новый PDF-файл или любой текст для удаления:",
}

# Эмодзи и символы
EMOJI = {
    "home": "🏠",
    "theory": "📚",
    "test": "📝",
    "admin": "👑",
    "back": "🔙",
    "loading": "⏳",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "locked": "🔒",
    "unlocked": "🔓",
    "stats": "📊",
    "ai": "🤖",
    "content": "⚙️",
    "settings": "🛠️"
}

# Лимиты и настройки
LIMITS = {
    "max_answer_length": 1000,
    "max_theory_length": 10000,
    "users_per_page": 10,
    "ai_timeout": 30,
    "blocks_per_page": 5
}