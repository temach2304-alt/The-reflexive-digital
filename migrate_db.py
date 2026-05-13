"""
Скрипт миграции базы данных для добавления полей rcp_name и rcp_avatar
"""
from models import db
from app import create_app

app = create_app()

with app.app_context():
    # Создаём все таблицы (новые поля будут добавлены автоматически)
    db.create_all()
    print("✅ База данных обновлена!")
    print("Добавлены новые поля в таблицу User:")
    print("  - rcp_name (имя РЦП)")
    print("  - rcp_avatar (аватар РЦП)")
