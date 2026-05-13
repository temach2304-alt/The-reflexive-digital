from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.status != 'active':
                flash('Ваш аккаунт не активен. Обратитесь к модератору.', 'error')
                return render_template('login.html')
            
            login_user(user)
            next_page = request.args.get('next')
            
            if user.role == 'moderator':
                return redirect(next_page or url_for('moderator.dashboard'))
            else:
                return redirect(next_page or url_for('user.dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')  # 'moderator' или 'user'
        
        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')
        
        # Создание нового пользователя
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('auth.login'))
