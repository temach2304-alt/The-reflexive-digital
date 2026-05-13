from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Session, Material, User, UserSessionProgress, ChatMessage
from ai_agent import process_file_content, create_session_context
import json
import os
from datetime import datetime

moderator_bp = Blueprint('moderator', __name__, template_folder='templates')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx', 'txt', 'md'}

@moderator_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'moderator':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    # Получение всех сессий модератора
    sessions = Session.query.filter_by(moderator_id=current_user.id).order_by(Session.created_at.desc()).all()
    
    # Получение всех пользователей и их статусов
    users = User.query.filter_by(role='user').all()
    
    return render_template('moderator_dashboard.html', sessions=sessions, users=users)

@moderator_bp.route('/session/create', methods=['GET', 'POST'])
@login_required
def create_session():
    if current_user.role != 'moderator':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        context = request.form.get('context')
        task_list_json = request.form.get('task_list')
        
        try:
            task_list = json.loads(task_list_json)
        except json.JSONDecodeError:
            flash('Неверный формат списка заданий (должен быть JSON)', 'error')
            return render_template('create_session.html')
        
        session = Session(
            title=title,
            description=description,
            context=context,
            task_list=json.dumps(task_list),
            moderator_id=current_user.id,
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        flash('Сессия успешно создана!', 'success')
        return redirect(url_for('moderator.edit_session', session_id=session.id))
    
    return render_template('create_session.html')

@moderator_bp.route('/session/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(session_id):
    if current_user.role != 'moderator':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    session = Session.query.get_or_404(session_id)
    
    if session.moderator_id != current_user.id:
        flash('У вас нет прав на редактирование этой сессии', 'error')
        return redirect(url_for('moderator.dashboard'))
    
    materials = Material.query.filter_by(session_id=session_id).all()
    
    return render_template('edit_session.html', session=session, materials=materials)

@moderator_bp.route('/session/<int:session_id>/upload', methods=['POST'])
@login_required
def upload_material(session_id):
    if current_user.role != 'moderator':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    session = Session.query.get_or_404(session_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{filename}"
        file_path = os.path.join('uploads', saved_filename)
        
        file.save(file_path)
        
        # Определение типа файла
        file_type = filename.rsplit('.', 1)[1].lower()
        
        # Создание записи в БД
        material = Material(
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            session_id=session_id
        )
        
        db.session.add(material)
        db.session.commit()
        
        # Обработка файла для ИИ-агента
        try:
            content = process_file_content(file_path, file_type)
            create_session_context(session_id, content)
            material.content_processed = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Файл загружен и обработан',
                'material_id': material.id
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Файл загружен, но обработка не удалась: {str(e)}'
            }), 500
    else:
        return jsonify({'error': 'Недопустимый тип файла'}), 400

@moderator_bp.route('/users')
@login_required
def view_users():
    if current_user.role != 'moderator':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    users = User.query.filter_by(role='user').all()
    return render_template('view_users.html', users=users)

@moderator_bp.route('/user/<int:user_id>/status', methods=['POST'])
@login_required
def update_user_status(user_id):
    if current_user.role != 'moderator':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    user = User.query.get_or_404(user_id)
    new_status = request.form.get('status')
    
    if new_status in ['active', 'inactive', 'blocked']:
        user.status = new_status
        db.session.commit()
        flash(f'Статус пользователя {user.username} обновлен', 'success')
    else:
        flash('Неверный статус', 'error')
    
    return redirect(url_for('moderator.view_users'))

@moderator_bp.route('/user/<int:user_id>/history')
@login_required
def view_user_history(user_id):
    if current_user.role != 'moderator':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.get_or_404(user_id)
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.desc()).all()
    
    return render_template('user_history.html', user=user, messages=messages)

@moderator_bp.route('/user/<int:user_id>/progress')
@login_required
def view_user_progress(user_id):
    if current_user.role != 'moderator':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    user = User.query.get_or_404(user_id)
    progress_records = UserSessionProgress.query.filter_by(user_id=user_id).all()
    
    progress_data = []
    for record in progress_records:
        session = Session.query.get(record.session_id)
        progress_data.append({
            'session_title': session.title,
            'current_task': record.current_task_index,
            'total_tasks': record.total_tasks,
            'status': record.status,
            'started_at': record.started_at.isoformat(),
            'completed_at': record.completed_at.isoformat() if record.completed_at else None
        })
    
    return jsonify({'progress': progress_data})
