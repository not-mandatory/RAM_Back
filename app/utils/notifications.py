import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from app import db, socketio  # Make sure socketio is initialized in your app
from app.models import User, Notification, Project, Answer

# Set up logger
logger = logging.getLogger(__name__)

# --- Notification Helper Function ---
def create_notification_for_admins(title, message, notification_type="info", related_id=None):
    """Create notifications for all admin users"""
    try:
        admins = User.query.filter_by(role='admin').all()
        notifications_created = []

        for admin in admins:

            notification = Notification(
                user_id=admin.id,
                title=title,
                message=message,
                type=notification_type,
                related_id=str(related_id) if related_id else None
            )
            db.session.add(notification)
            notifications_created.append(notification)

        db.session.commit()
        return notifications_created
    except Exception as e:
        db.session.rollback()
        print(f"Error creating notifications: {e}")
        return []

