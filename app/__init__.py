import datetime

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
from flask_mail import Mail




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

load_dotenv()
import boto3
app.config['AWS_ACCESS_KEY_ID'] = os.environ.get('AWS_ACCESS_KEY_ID')
app.config['AWS_SECRET_ACCESS_KEY'] = os.environ.get('AWS_SECRET_ACCESS_KEY')
app.config['AWS_S3_BUCKET_NAME'] = os.environ.get('AWS_S3_BUCKET_NAME') # This is your BUCKET
app.config['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.example.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)



s3 = boto3.client(
    "s3",
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION']
)

# Now, define BUCKET using the loaded config
# This BUCKET variable will be imported or accessed in your routes.py
BUCKET = app.config['AWS_S3_BUCKET_NAME']



db = SQLAlchemy(app)
migrate = Migrate(app, db)

jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000", logger=True,  # Enable detailed logging
                   engineio_logger=True)

from app import routes, models, socket_events

