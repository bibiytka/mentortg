import re
import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime

def format_user_progress(completed_tests: int, total_tests: int) -> str:
    """Форматировать прогресс пользователя"""
    if total_tests == 0:
        return "Нет доступных тестов"
    
    percentage = (completed_tests / total_tests) * 100
    progress_bar = create_progress_bar(percentage)
    
    return f"{progress_bar} {completed_tests}/{total_tests} ({percentage:.1f}%)"

def create_progress_bar(percentage: float, length: int = 10) -> str:
    """Создать текстовую полосу прогресса"""
    filled = int(length * percentage / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезать текст до максимальной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_text(text: str) -> str:
    """Очистить текст от лишних символов"""
    if not text:
        return ""
    
    # Убираем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Убираем HTML теги если есть
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def validate_text_length(text: str, min_length: int = 1, max_length: int = 1000) -> Tuple[bool, str]:
    """Валидация длины текста"""
    if not text or len(text.strip()) < min_length:
        return False, f"Текст должен содержать минимум {min_length} символов"
    
    if len(text) > max_length:
        return False, f"Текст не должен превышать {max_length} символов"
    
    return True, ""

def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Форматировать дату и время"""
    if format_type == "full":
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    elif format_type == "date":
        return dt.strftime("%d.%m.%Y")
    elif format_type == "time":
        return dt.strftime("%H:%M")
    elif format_type == "short":
        return dt.strftime("%d.%m %H:%M")
    else:
        return str(dt)

def calculate_pagination(total_items: int, items_per_page: int, current_page: int = 1) -> Dict:
    """Рассчитать параметры пагинации"""
    total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
    current_page = max(1, min(current_page, total_pages))
    
    offset = (current_page - 1) * items_per_page
    has_prev = current_page > 1
    has_next = current_page < total_pages
    
    return {
        "total_pages": total_pages,
        "current_page": current_page,
        "offset": offset,
        "has_prev": has_prev,
        "has_next": has_next,
        "items_per_page": items_per_page
    }

def extract_numbers(text: str) -> List[int]:
    """Извлечь все числа из текста"""
    return [int(match) for match in re.findall(r'\d+', text)]

def format_file_size(size_bytes: int) -> str:
    """Форматировать размер файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def create_username_display(username: Optional[str], full_name: str, user_id: int) -> str:
    """Создать отображаемое имя пользователя"""
    if username:
        return f"{full_name} (@{username})"
    return f"{full_name} (ID: {user_id})"

def escape_markdown(text: str) -> str:
    """Экранировать специальные символы Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_test_statistics(total_questions: int, correct_answers: int) -> str:
    """Форматировать статистику теста"""
    if total_questions == 0:
        return "Нет вопросов"
    
    percentage = (correct_answers / total_questions) * 100
    
    if percentage >= 90:
        grade = "Отлично! 🏆"
    elif percentage >= 70:
        grade = "Хорошо! 👍"
    elif percentage >= 50:
        grade = "Удовлетворительно ⚡"
    else:
        grade = "Требует улучшения 📚"
    
    return f"{grade} {correct_answers}/{total_questions} ({percentage:.1f}%)"

def generate_test_report_summary(analysis_results: List[Dict]) -> str:
    """Генерировать краткое резюме отчета теста"""
    if not analysis_results:
        return "Нет данных для анализа"
    
    total = len(analysis_results)
    correct = sum(1 for result in analysis_results if result.get("is_sufficient", False))
    
    percentage = (correct / total) * 100
    
    # Определяем общую оценку
    if percentage >= 80:
        overall = "🎉 Отличная работа!"
    elif percentage >= 60:
        overall = "👍 Хорошие результаты!"
    elif percentage >= 40:
        overall = "⚡ Есть потенциал для улучшения"
    else:
        overall = "📚 Рекомендуется повторить материал"
    
    return f"{overall} Результат: {correct}/{total} ({percentage:.1f}%)"

def sanitize_filename(filename: str) -> str:
    """Очистить имя файла от недопустимых символов"""
    # Заменяем недопустимые символы на подчеркивания
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Убираем лишние пробелы и точки в начале/конце
    filename = filename.strip(' .')
    # Ограничиваем длину
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')
    
    return filename or "unnamed_file"

def parse_callback_data(callback_data: str) -> Dict[str, str]:
    """Парсить callback_data и извлечь параметры"""
    parts = callback_data.split('_')
    
    if len(parts) < 2:
        return {"action": callback_data}
    
    result = {"action": parts[0]}
    
    # Специальная обработка для разных типов callback'ов
    if parts[0] in ["view", "start", "edit", "nav"]:
        if len(parts) >= 3:
            result["object_type"] = parts[1]
            result["object_id"] = parts[2]
    elif parts[0] == "stats":
        if len(parts) >= 3:
            result["page"] = parts[2]
    elif parts[0] == "feedback":
        if len(parts) >= 3:
            result["type"] = parts[1]
            result["attempt_id"] = parts[2]
    
    return result

def create_progress_message(current: int, total: int, action: str = "Обработка") -> str:
    """Создать сообщение с прогрессом"""
    percentage = (current / total) * 100 if total > 0 else 0
    progress_bar = create_progress_bar(percentage, 15)
    
    return f"{action}... {progress_bar} {current}/{total} ({percentage:.1f}%)"