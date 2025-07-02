"""class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://myadmin:anass%401234@mysql-ram.mysql.database.azure.com:3306/evaluate'
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {"ca": "./DigiCertGlobalRootCA.crt.pem"}
        }
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "jwt-super-secret"


import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
"""


import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL'    )
    # Path to SSL certificate, defaulting to local path but can be overridden by env variable
    MYSQL_SSL_CA = os.environ.get(
        'MYSQL_SSL_CA',
        os.path.join(os.path.dirname(__file__), 'DigiCertGlobalRootCA.crt.pem')
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {"ca": MYSQL_SSL_CA}
        }
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret')

