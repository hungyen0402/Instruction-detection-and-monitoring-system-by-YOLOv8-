import os
from dotenv import load_dotenv, find_dotenv
from datetime import timedelta

load_dotenv(find_dotenv()) # tự động tìm và load file .env từ các thư mục cha

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # tắt tính năng theo dõi thay đổi của sql
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # YOLO model settings
    YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'best.pt')  # Sử dụng model đã train
    
    # Alert settings
    ALERT_COOLDOWN = timedelta(seconds=30)  # Default cooldown time between alerts
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    DETECTION_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/detections')
    # __file__ là biến đặc biệt chứa đường dẫn đến file hiện tạitại