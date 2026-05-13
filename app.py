from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Добавление кастомного фильтра для JSON
    @app.template_filter('from_json')
    def from_json_filter(value):
        import json
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    # Инициализация расширений
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Настройка папок
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('vector_store', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    
    # Регистрация маршрутов
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from moderator_routes import moderator_bp
    app.register_blueprint(moderator_bp, url_prefix='/moderator')
    
    from user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'moderator':
                return redirect(url_for('moderator.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
