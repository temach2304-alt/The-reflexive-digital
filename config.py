import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///rcp_platform.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки для ИИ-агента
    AI_MODEL_PATH = os.environ.get('AI_MODEL_PATH') or './models'
    VECTOR_STORE_PATH = os.environ.get('VECTOR_STORE_PATH') or './vector_store'
    
    # Максимальный размер загружаемых файлов (в байтах)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    
    # Разрешенные расширения файлов
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md'}
