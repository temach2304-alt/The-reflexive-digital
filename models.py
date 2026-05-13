from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Модель пользователя (педагог или ребенок)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'moderator' или 'user'
    status = db.Column(db.String(50), default='active')  # active, inactive, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    sessions = db.relationship('Session', backref='user', lazy='dynamic')
    chat_history = db.relationship('ChatMessage', backref='user', lazy='dynamic')


class Session(db.Model):
    """Модель сессии - учебное занятие с диалоговыми заданиями"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    context = db.Column(db.Text)  # Контекст сессии из методических материалов
    task_list = db.Column(db.Text)  # JSON список диалоговых заданий
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    materials = db.relationship('Material', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    user_sessions = db.relationship('UserSessionProgress', backref='session', lazy='dynamic', cascade='all, delete-orphan')


class Material(db.Model):
    """Модель загруженных методических материалов"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20))  # pdf, docx, txt, md
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    content_processed = db.Column(db.Boolean, default=False)  # Обработан ли файл для ИИ


class ChatMessage(db.Model):
    """Модель сообщений в чате (история запросов и ответов)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    message_type = db.Column(db.String(20), nullable=False)  # 'user_query' или 'ai_response'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    task_index = db.Column(db.Integer)  # Индекс текущего задания в списке


class UserSessionProgress(db.Model):
    """Прогресс пользователя по сессии"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    current_task_index = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    total_tasks = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed, abandoned
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'session_id', name='unique_user_session'),)
