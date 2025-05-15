import datetime

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object('config.Config')


CORS(app, origins=["http://localhost:3000"], supports_credentials=True)



# Very important for cookies + frontend calls

app.config["JWT_SECRET_KEY"] = "super-secret-key"
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False         # ✅ Only send cookie over HTTPS
app.config["JWT_COOKIE_SAMESITE"] = "Lax"     # ✅ For cross-origin cookies (frontend <> backend)
app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Optional for testing only
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=1)
#app.config["JWT_TOKEN_LOCATION"] = ["headers"]

db = SQLAlchemy(app)
migrate = Migrate(app, db)

jwt = JWTManager(app)

from app import routes, models

