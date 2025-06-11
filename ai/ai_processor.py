import os
import json
import logging
from typing import Optional, Dict, Tuple
from openai import AsyncOpenAI
import config
import aiofiles

logger = logging.getLogger(__name__)

# Глобальная переменная для клиента OpenAI
openai_client = None

def get_openai_client():
    """Получить или создать OpenAI клиент"""
    global openai_client
    if openai_client is None:
        try:
            openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("✅ OpenAI клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации OpenAI клиента: {e}")
            raise
    return openai_client

async def load_prompt_template() -> str:
    """Загрузить шаблон промпта из файла"""
    template_path = os.path.join(config.PROMPTS_DIR, "check_answer_prompt.txt")
    
    try:
        async with aiofiles.open(template_path, 'r', encoding='utf-8') as f:
            return await f.read()
    except FileNotFoundError:
        # Возвращаем базовый шаблон если файл не найден
        logger.warning(f"Файл шаблона {template_path} не найден, используем базовый шаблон")
        return """Ты — эксперт-преподаватель морского дела. Твоя задача — оценить ответ студента.

### Учебный материал по теме:
---
{theory_text}
---

### Задание для проверки:
Вопрос: "{question_text}"
Ответ студента: "{user_answer_text}"

Оцени ответ и дай рекомендацию.

### Формат вывода (ТОЛЬКО JSON):
{{"is_sufficient": boolean, "recommendation": "краткая рекомендация для студента"}}"""

async def build_check_answer_prompt(theory_text: str, question_text: str, user_answer_text: str) -> str:
    """Собрать промпт для проверки ответа"""
    template = await load_prompt_template()
    
    return template.format(
        theory_text=theory_text,
        question_text=question_text,
        user_answer_text=user_answer_text
    )

async def transcribe_voice(voice_file_data: bytes) -> Optional[str]:
    """Распознать голосовое сообщение через Whisper"""
    try:
        client = get_openai_client()
        if client is None:
            logger.warning("⚠️ OpenAI недоступен, голосовые сообщения не поддерживаются")
            return "Извините, распознавание голоса временно недоступно. Напишите ответ текстом."
        
        # Создаем временный файл в памяти
        import io
        voice_file = io.BytesIO(voice_file_data)
        voice_file.name = "voice.ogg"  # OpenAI требует имя файла
        
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=voice_file,
            language="ru"
        )
        
        transcribed_text = response.text.strip()
        logger.info(f"✅ Голос распознан: {transcribed_text[:100]}...")
        return transcribed_text
        
    except Exception as e:
        logger.error(f"❌ Ошибка распознавания голоса: {e}")
        return "Извините, не удалось распознать голосовое сообщение. Попробуйте написать ответ текстом."

async def analyze_answer(theory_text: str, question_text: str, user_answer_text: str) -> Optional[Tuple[bool, str]]:
    """Анализировать ответ пользователя через OpenAI"""
    try:
        client = get_openai_client()
        if client is None:
            # Fallback анализ без OpenAI
            logger.warning("⚠️ OpenAI недоступен, используем базовый анализ")
            return analyze_answer_fallback(user_answer_text)
        
        prompt = await build_check_answer_prompt(theory_text, question_text, user_answer_text)
        
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ты эксперт-преподаватель. Отвечай только в формате JSON."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=config.OPENAI_TEMPERATURE,
            max_tokens=config.OPENAI_MAX_TOKENS
        )
        
        result_text = response.choices[0].message.content.strip()
        logger.info(f"✅ Ответ от OpenAI: {result_text}")
        
        # Парсим JSON ответ
        try:
            result = json.loads(result_text)
            is_sufficient = result.get("is_sufficient", False)
            recommendation = result.get("recommendation", "Рекомендация не предоставлена")
            
            return is_sufficient, recommendation
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON от OpenAI: {e}")
            logger.error(f"Полученный текст: {result_text}")
            
            # Возвращаем базовую рекомендацию если JSON невалидный
            return False, "Рекомендую повторить материал и дать более развернутый ответ."
            
    except Exception as e:
        logger.error(f"❌ Ошибка анализа ответа через OpenAI: {e}")
        # Fallback анализ
        return analyze_answer_fallback(user_answer_text)

def analyze_answer_fallback(user_answer_text: str) -> Tuple[bool, str]:
    """Простой анализ ответа без OpenAI"""
    answer_length = len(user_answer_text.strip())
    
    if answer_length < 10:
        return False, "Ответ слишком короткий. Попробуйте дать более развернутый ответ."
    elif answer_length < 30:
        return False, "Ответ краткий. Рекомендую добавить больше деталей из изученного материала."
    elif answer_length < 100:
        return True, "Хороший ответ! Продолжайте изучение следующих тем."
    else:
        return True, "Отличный развернутый ответ! Вы хорошо усвоили материал."

async def generate_final_report(answers_analysis: list) -> str:
    """Сгенерировать итоговый отчет по тесту"""
    try:
        # Подсчитываем статистику
        total_questions = len(answers_analysis)
        sufficient_answers = sum(1 for analysis in answers_analysis if analysis["is_sufficient"])
        
        # Собираем рекомендации
        recommendations = []
        for i, analysis in enumerate(answers_analysis, 1):
            if not analysis["is_sufficient"]:
                recommendations.append(f"{i}. {analysis['recommendation']}")
        
        # Формируем отчет
        report_parts = [
            f"📊 **Результаты анализа вашего теста:**\n",
            f"✅ Достаточных ответов: {sufficient_answers}/{total_questions}",
            f"📈 Процент успешности: {(sufficient_answers/total_questions)*100:.1f}%\n"
        ]
        
        if recommendations:
            report_parts.append("💡 **Рекомендации для улучшения:**\n")
            report_parts.extend(recommendations)
        else:
            report_parts.append("🎉 **Отличная работа!** Все ваши ответы достаточно полные и правильные!")
        
        report_parts.append("\n📚 Продолжайте изучение следующих тем!")
        
        return "\n".join(report_parts)
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчета: {e}")
        return "📊 Анализ завершен. Рекомендуем повторить изученный материал."