"""
ИИ-агент (Рефлексивная Цифровая Персона)

Этот модуль отвечает за:
1. Обработку загруженных файлов (PDF, DOCX, TXT, MD)
2. Создание векторного хранилища для контекста сессий
3. Генерацию ответов на основе контекста и истории диалога
4. Адаптацию вопросов на основе предыдущих ответов пользователя
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime

# Глобальные хранилища для сессионных данных
session_contexts = {}  # session_id -> context_data
user_sessions = {}  # (user_id, session_id) -> conversation_history


def process_file_content(file_path: str, file_type: str) -> str:
    """
    Извлечение текста из загруженных файлов
    
    Args:
        file_path: Путь к файлу
        file_type: Тип файла (pdf, docx, txt, md)
    
    Returns:
        Извлеченный текст из файла
    """
    content = ""
    
    try:
        if file_type == 'txt' or file_type == 'md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        elif file_type == 'pdf':
            content = extract_pdf_content(file_path)
        
        elif file_type == 'docx':
            content = extract_docx_content(file_path)
        
        return content
    
    except Exception as e:
        raise Exception(f"Ошибка обработки файла {file_path}: {str(e)}")


def extract_pdf_content(file_path: str) -> str:
    """Извлечение текста из PDF файла"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except ImportError:
        # Если PyPDF2 не установлен, возвращаем заглушку
        return "[PDF контент - требуется установка PyPDF2]"
    except Exception as e:
        return f"[Ошибка чтения PDF: {str(e)}]"


def extract_docx_content(file_path: str) -> str:
    """Извлечение текста из DOCX файла"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except ImportError:
        return "[DOCX контент - требуется установка python-docx]"
    except Exception as e:
        return f"[Ошибка чтения DOCX: {str(e)}]"


def create_session_context(session_id: int, content: str) -> Dict:
    """
    Создание контекста сессии на основе загруженных материалов
    
    Args:
        session_id: ID сессии
        content: Текст из загруженных файлов
    
    Returns:
        Словарь с данными контекста
    """
    context_data = {
        'session_id': session_id,
        'content': content,
        'created_at': datetime.utcnow().isoformat(),
        'chunks': split_content_into_chunks(content)
    }
    
    session_contexts[session_id] = context_data
    
    # Здесь можно добавить интеграцию с векторным хранилищем (ChromaDB)
    # для семантического поиска по контексту
    
    return context_data


def split_content_into_chunks(content: str, chunk_size: int = 500) -> List[str]:
    """Разбиение контента на чанки для обработки"""
    chunks = []
    words = content.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        
        if current_length >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def initialize_session_for_user(user_id: int, session_id: int, context: str) -> Dict:
    """
    Инициализация сессии для конкретного пользователя
    
    Args:
        user_id: ID пользователя
        session_id: ID сессии
        context: Контекст сессии
    
    Returns:
        Данные инициализированной сессии
    """
    session_key = (user_id, session_id)
    
    user_sessions[session_key] = {
        'conversation_history': [],
        'context': context,
        'started_at': datetime.utcnow().isoformat(),
        'current_task_index': 0
    }
    
    return user_sessions[session_key]


def get_ai_response(
    user_id: int,
    session_id: int,
    user_message: str,
    current_task: Dict,
    task_index: int
) -> Dict:
    """
    Генерация ответа ИИ-агента на сообщение пользователя
    
    Args:
        user_id: ID пользователя
        session_id: ID сессии
        user_message: Сообщение от пользователя
        current_task: Текущее задание
        task_index: Индекс текущего задания
    
    Returns:
        Словарь с ответом и метаданными
    """
    session_key = (user_id, session_id)
    
    # Получение или создание истории сессии
    if session_key not in user_sessions:
        user_sessions[session_key] = {
            'conversation_history': [],
            'context': '',
            'started_at': datetime.utcnow().isoformat(),
            'current_task_index': task_index
        }
    
    session_data = user_sessions[session_key]
    
    # Добавление сообщения пользователя в историю
    session_data['conversation_history'].append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.utcnow().isoformat(),
        'task_index': task_index
    })
    
    # Генерация ответа (здесь должна быть интеграция с LLM)
    response = generate_reflective_response(
        user_message=user_message,
        current_task=current_task,
        conversation_history=session_data['conversation_history'],
        context=session_data.get('context', '')
    )
    
    # Добавление ответа ИИ в историю
    session_data['conversation_history'].append({
        'role': 'assistant',
        'content': response['text'],
        'timestamp': datetime.utcnow().isoformat(),
        'task_index': task_index
    })
    
    return {
        'response': response['text'],
        'task_completed': response['task_completed'],
        'metadata': {
            'task_index': task_index,
            'reflection_depth': response.get('reflection_depth', 'basic')
        }
    }


def generate_reflective_response(
    user_message: str,
    current_task: Dict,
    conversation_history: List[Dict],
    context: str
) -> Dict:
    """
    Генерация рефлексивного ответа на основе задачи и истории диалога
    
    Это основная функция ИИ-агента, которая должна:
    1. Анализировать ответ пользователя
    2. Оценивать глубину рефлексии
    3. Формулировать следующий вопрос или обратную связь
    4. Определять, выполнено ли текущее задание
    
    В продакшене здесь должна быть интеграция с локальной LLM
    (Ollama, LM Studio, или другая модель)
    """
    
    # Эвристическая логика для демонстрации
    # В реальной системе здесь будет вызов LLM
    
    task_description = current_task.get('description', '')
    task_goal = current_task.get('goal', '')
    
    # Анализ длины ответа как простой метрики вовлеченности
    response_length = len(user_message.strip())
    
    # Простая эвристика для определения завершенности задания
    task_completed = response_length > 50  # Минимальная длина ответа
    
    # Генерация ответа
    if response_length < 20:
        response_text = f"""Я вижу, что ваш ответ довольно краткий. 
Для развития рефлексии важно подробнее раскрыть свои мысли. 

Попробуйте ответить на вопрос: 
- Что именно вы почувствовали в этой ситуации?
- Какие мысли у вас возникли?
- Как это связано с вашим предыдущим опытом?

{task_description}"""
        reflection_depth = 'shallow'
        task_completed = False
    
    elif response_length < 100:
        response_text = f"""Спасибо за ваш ответ! Вы затронули важные моменты.

Давайте углубимся еще немного:
- Почему вы считаете это важным?
- Как это влияет на ваше понимание ситуации?
- Какие альтернативные точки зрения вы можете рассмотреть?

Продолжайте размышлять над: {task_goal}"""
        reflection_depth = 'moderate'
        task_completed = False
    
    else:
        response_text = f"""Отличная работа! Ваш ответ показывает глубокое размышление.

Вы хорошо проанализировали ситуацию, отметив важные аспекты.
{generate_specific_feedback(user_message, task_goal)}

{'Переходим к следующему заданию!' if task_completed else 'Продолжайте в том же духе!'}"""
        reflection_depth = 'deep'
        task_completed = True
    
    return {
        'text': response_text,
        'task_completed': task_completed,
        'reflection_depth': reflection_depth
    }


def generate_specific_feedback(user_message: str, task_goal: str) -> str:
    """Генерация специфической обратной связи на основе ответа пользователя"""
    
    # Ключевые слова для анализа
    reflection_keywords = [
        'потому что', 'думаю', 'чувствую', 'понял', 'осознал',
        'важно', 'значит', 'связь', 'причина', 'следствие'
    ]
    
    found_keywords = [kw for kw in reflection_keywords if kw in user_message.lower()]
    
    if len(found_keywords) >= 3:
        return f"Вы использовали рефлексивные формулировки ({', '.join(found_keywords[:3])}), что показывает глубокий уровень самоанализа."
    elif len(found_keywords) >= 1:
        return f"Хорошо, что вы отмечаете такие аспекты как '{found_keywords[0]}'. Это помогает развивать рефлексию."
    else:
        return "Попробуйте использовать больше рефлексивных формулировок: 'я думаю', 'я чувствую', 'я понимаю'."


def get_conversation_summary(user_id: int, session_id: int) -> Dict:
    """Получение сводки по сессии пользователя"""
    session_key = (user_id, session_id)
    
    if session_key not in user_sessions:
        return {'error': 'Сессия не найдена'}
    
    session_data = user_sessions[session_key]
    
    return {
        'started_at': session_data['started_at'],
        'message_count': len(session_data['conversation_history']),
        'history': session_data['conversation_history']
    }
