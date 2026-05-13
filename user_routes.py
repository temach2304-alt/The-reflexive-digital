from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, stream_with_context
from flask_login import login_required, current_user
from models import db, Session, UserSessionProgress, ChatMessage
from ai_agent import get_ai_response, initialize_session_for_user
import json
from datetime import datetime

user_bp = Blueprint('user', __name__, template_folder='templates')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'user':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    # Получение активных сессий
    active_sessions = Session.query.filter_by(is_active=True).all()
    
    # Получение прогресса пользователя по сессиям
    user_progress = UserSessionProgress.query.filter_by(user_id=current_user.id).all()
    
    session_progress_map = {up.session_id: up for up in user_progress}
    
    return render_template('user_dashboard.html', 
                         sessions=active_sessions, 
                         session_progress=session_progress_map)

@user_bp.route('/session/<int:session_id>/start', methods=['POST'])
@login_required
def start_session(session_id):
    session = Session.query.get_or_404(session_id)
    
    if not session.is_active:
        return jsonify({'error': 'Сессия не активна'}), 400
    
    # Проверка, есть ли уже прогресс
    existing_progress = UserSessionProgress.query.filter_by(
        user_id=current_user.id, 
        session_id=session_id
    ).first()
    
    if existing_progress:
        if existing_progress.status == 'completed':
            return jsonify({'error': 'Вы уже завершили эту сессию'}), 400
        return redirect(url_for('user.chat_session', session_id=session_id))
    
    # Инициализация сессии для пользователя
    task_list = json.loads(session.task_list)
    progress = UserSessionProgress(
        user_id=current_user.id,
        session_id=session_id,
        current_task_index=0,
        total_tasks=len(task_list),
        status='in_progress'
    )
    
    db.session.add(progress)
    db.session.commit()
    
    # Инициализация контекста для ИИ-агента
    initialize_session_for_user(current_user.id, session_id, session.context)
    
    return redirect(url_for('user.chat_session', session_id=session_id))

@user_bp.route('/session/<int:session_id>/chat')
@login_required
def chat_session(session_id):
    session = Session.query.get_or_404(session_id)
    
    progress = UserSessionProgress.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).first_or_404()
    
    if progress.status == 'completed':
        flash('Вы завершили эту сессию', 'info')
        return redirect(url_for('user.dashboard'))
    
    # Получение текущего задания
    task_list = json.loads(session.task_list)
    current_task_index = progress.current_task_index
    
    if current_task_index >= len(task_list):
        # Все задания выполнены
        progress.status = 'completed'
        progress.completed_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('user.session_complete', session_id=session_id))
    
    current_task = task_list[current_task_index]
    
    # Получение истории чата для этой сессии
    chat_history = ChatMessage.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    return render_template('chat_session.html', 
                         session=session, 
                         current_task=current_task,
                         task_index=current_task_index,
                         total_tasks=len(task_list),
                         chat_history=chat_history)

@user_bp.route('/session/<int:session_id>/message', methods=['POST'])
@login_required
def send_message(session_id):
    session = Session.query.get_or_404(session_id)
    
    progress = UserSessionProgress.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).first_or_404()
    
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    # Получаем данные РЦП пользователя
    user_rcp_name = current_user.rcp_name or "Помощник"
    user_rcp_avatar = current_user.rcp_avatar or "🦉"
    
    # Сохранение сообщения пользователя
    user_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        message_type='user_query',
        content=user_message,
        task_index=progress.current_task_index
    )
    db.session.add(user_msg)
    
    # Получение ответа от ИИ-агента
    task_list = json.loads(session.task_list)
    current_task = task_list[progress.current_task_index]
    
    try:
        ai_response = get_ai_response(
            user_id=current_user.id,
            session_id=session_id,
            user_message=user_message,
            current_task=current_task,
            task_index=progress.current_task_index,
            user_rcp_name=user_rcp_name,
            user_rcp_avatar=user_rcp_avatar
        )
        
        # Сохранение ответа ИИ
        ai_msg = ChatMessage(
            user_id=current_user.id,
            session_id=session_id,
            message_type='ai_response',
            content=ai_response['response'],
            task_index=progress.current_task_index
        )
        db.session.add(ai_msg)
        
        # Обновление прогресса если задание выполнено
        if ai_response.get('task_completed', False):
            progress.current_task_index += 1
            progress.completed_tasks = progress.current_task_index
            
            if progress.current_task_index >= len(task_list):
                progress.status = 'completed'
                progress.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'response': ai_response['response'],
            'task_completed': ai_response.get('task_completed', False),
            'next_task': task_list[progress.current_task_index] if progress.current_task_index < len(task_list) else None,
            'progress': {
                'current': progress.current_task_index,
                'total': len(task_list)
            },
            'rcp_info': {
                'name': user_rcp_name,
                'avatar': user_rcp_avatar
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/session/<int:session_id>/complete')
@login_required
def session_complete(session_id):
    session = Session.query.get_or_404(session_id)
    
    progress = UserSessionProgress.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).first_or_404()
    
    if progress.status != 'completed':
        return redirect(url_for('user.chat_session', session_id=session_id))
    
    # Получение всей истории чата
    chat_history = ChatMessage.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    return render_template('session_complete.html', 
                         session=session, 
                         progress=progress,
                         chat_history=chat_history)

@user_bp.route('/history')
@login_required
def history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id)\
                                .order_by(ChatMessage.timestamp.desc()).all()
    return render_template('user_history.html', messages=messages)
