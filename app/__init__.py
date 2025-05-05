from flask import Flask
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

jwt = JWTManager(app)

from app import routes, models

@login_manager.user_loader
def load_user(user_id):

    from app.models import User
    return User.query.get(int(user_id))
