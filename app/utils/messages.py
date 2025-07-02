
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app import mail, app  # Import the `mail` instance
from flask_mail import Message

def send_welcome_email(user_email, password):
    msg = Message(
        subject="Welcome to Our Platform",
        sender=app.config['MAIL_USERNAME'],  # Use configured email
        recipients=[user_email]
    )
    msg.body = f"""
    Hello,

    Your account has been created.

    Email: {user_email}
    Password: {password}

    Regards,
    The Admin Team
    """
    mail.send(msg)