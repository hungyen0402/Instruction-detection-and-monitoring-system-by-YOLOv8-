from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_socketio import SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*", 
                   async_mode='threading',
                   ping_timeout=60,
                   ping_interval=25,
                   logger=True,
                   engineio_logger=True) 