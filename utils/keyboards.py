from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

# === ГЛАВНОЕ МЕНЮ ===

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню с inline кнопками"""
    buttons = [
        [InlineKeyboardButton(text="📚 Теория", callback_data="menu_theory")],
        [InlineKeyboardButton(text="📝 Тесты", callback_data="menu_tests")]
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === ТЕОРИЯ ===

def get_theory_menu_keyboard(blocks: List[Dict]) -> InlineKeyboardMarkup:
    """Меню выбора блоков теории"""
    buttons = []
    
    for block in blocks:
        buttons.append([
            InlineKeyboardButton(
                text=block["title"],
                callback_data=f"theory_view_{block['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_theory_view_keyboard(block_id: int) -> InlineKeyboardMarkup:
    """Клавиатура просмотра теории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать тест", callback_data=f"test_start_{block_id}")],
        [InlineKeyboardButton(text="🔙 К списку блоков", callback_data="menu_theory")]
    ])

# === ТЕСТЫ ===

def get_tests_menu_keyboard(blocks: List[Dict], user_progress: int = 0) -> InlineKeyboardMarkup:
    """Меню выбора тестов"""
    buttons = []
    
    for block in blocks:
        if block["block_order"] <= user_progress + 1:
            # Доступный тест
            text = f"✅ {block['title']}" if block["block_order"] <= user_progress else block["title"]
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"test_start_{block['id']}"
                )
            ])
        else:
            # Заблокированный тест
            buttons.append([
                InlineKeyboardButton(
                    text=f"🔒 {block['title']}",
                    callback_data=f"test_locked_{block['id']}"
                )
            ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_feedback_keyboard(attempt_id: int) -> InlineKeyboardMarkup:
    """Клавиатура оценки результатов теста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Полезно", callback_data=f"feedback_positive_{attempt_id}"),
            InlineKeyboardButton(text="👎 Бесполезно", callback_data=f"feedback_negative_{attempt_id}")
        ],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")]
    ])

def get_active_test_keyboard(active_test: Dict) -> InlineKeyboardMarkup:
    """Клавиатура для выбора действия с активным тестом"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"➡️ Продолжить тест '{active_test['block_title']}'", 
            callback_data="test_continue"
        )],
        [InlineKeyboardButton(
            text="🗑️ Отменить и начать новый", 
            callback_data="test_cancel_and_new"
        )],
        [InlineKeyboardButton(text="🔙 Назад к тестам", callback_data="menu_tests")]
    ])

def get_test_in_progress_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время прохождения теста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить тест", callback_data="test_cancel_current")]
    ])

# === АДМИН-ПАНЕЛЬ ===

def get_admin_menu_keyboard(is_super_admin: bool = False, maintenance_mode: bool = False) -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    buttons = [
        [InlineKeyboardButton(text="⚙️ Управление контентом", callback_data="admin_content")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📉 Аналитика ИИ", callback_data="admin_ai_analytics")]
    ]
    
    if is_super_admin:
        maintenance_text = "🛠️ Режим: ВКЛ" if maintenance_mode else "🛠️ Режим: ВЫКЛ"
        buttons.append([
            InlineKeyboardButton(text=maintenance_text, callback_data="admin_maintenance")
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_content_keyboard(block_id: int, current: int, total: int) -> InlineKeyboardMarkup:
    """Клавиатура управления контентом"""
    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data=f"content_edit_text_{block_id}")],
        [InlineKeyboardButton(text="🎥 Изменить видео", callback_data=f"content_edit_video_{block_id}")],
        [InlineKeyboardButton(text="📄 Изменить PDF", callback_data=f"content_edit_pdf_{block_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить блок", callback_data=f"content_delete_{block_id}")]
    ]
    
    # Навигация
    nav_buttons = []
    if current > 1:
        prev_id = current - 1
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"content_nav_{prev_id}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current}/{total}", callback_data="content_current"))
    
    if current < total:
        next_id = current + 1
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"content_nav_{next_id}"))
    
    if len(nav_buttons) > 1:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔙 Админ-панель", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_stats_keyboard(current_page: int, total_pages: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Клавиатура статистики с пагинацией"""
    buttons = []
    
    # Навигация по страницам
    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"stats_page_{current_page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="stats_current"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"stats_page_{current_page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔙 Админ-панель", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === АНАЛИТИКА ИИ ===

def get_ai_analytics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура аналитики ИИ"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Детально по блокам", callback_data="ai_analytics_blocks")],
        [
            InlineKeyboardButton(text="👍 Лучшие", callback_data="ai_analytics_best"),
            InlineKeyboardButton(text="👎 Худшие", callback_data="ai_analytics_worst")
        ],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_ai_analytics")],
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="menu_admin")]
    ])

def get_ai_blocks_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура детальной аналитики по блокам"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К аналитике ИИ", callback_data="admin_ai_analytics")]
    ])

# === СИСТЕМНЫЕ ===

def get_back_keyboard(destination: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура возврата"""
    destinations = {
        "main": ("🔙 Главное меню", "menu_main"),
        "theory": ("🔙 К теории", "menu_theory"),
        "tests": ("🔙 К тестам", "menu_tests"),
        "admin": ("🔙 Админ-панель", "menu_admin"),
        "stats": ("🔙 К статистике", "admin_stats"),
        "analytics": ("🔙 К аналитике", "admin_ai_analytics")
    }
    
    text, callback = destinations.get(destination, ("🔙 Назад", "menu_main"))
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)]
    ])

def get_confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_content")
        ]
    ])