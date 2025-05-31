from flask import Flask
from config import Config
from extensions import db, login_manager, mail, socketio
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Set up login manager
    login_manager.login_view = 'bp.login'
    
    # Import models after db is initialized
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes import bp
    app.register_blueprint(bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize SocketIO after all other initializations
    socketio.init_app(app, 
                     cors_allowed_origins="*",
                     async_mode='threading',
                     logger=True,
                     engineio_logger=True)
    
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, 
                debug=True,
                host='0.0.0.0',
                port=5000,
                use_reloader=False)  # Disable reloader to prevent duplicate connections