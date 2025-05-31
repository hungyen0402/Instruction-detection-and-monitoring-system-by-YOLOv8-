from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

from models import User

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 