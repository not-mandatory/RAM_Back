from datetime import datetime, timezone
from enum import Enum
from flask_login import UserMixin
from app import db
from datetime import datetime, timezone
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

# Define role types using Enum
class Role(Enum):
    ADMIN = 'admin'
    ÉVALUATEUR = 'évaluateur'


from sqlalchemy.sql import func

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')
    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    related_id = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'related_id': self.related_id
        }

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.ÉVALUATEUR)
    position = db.Column(db.String(255), nullable=False)
    direction = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Define the relationship with Answer
    answers = db.relationship('Answer', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def is_admin(self):
        return self.role == Role.ADMIN


class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable = False, default='pending')  # 'pending', 'approved', 'rejected'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='ideas')





class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200))
    category = db.Column(db.String(255), nullable=False)

    answers = db.relationship('Answer', backref='project', lazy=True)
    users = db.relationship("ProjectUser", back_populates="project", cascade="all, delete-orphan")


    def __repr__(self):
        return f'<Project {self.title}>'

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image_path": self.image_path,
            "category": self.category
            #"answers_count": len(self.answers)  # Include the number of answers, or other relevant fields
        }

class ProjectUser(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_team_lead = db.Column(db.Boolean, default=False)

    project = db.relationship("Project", back_populates="users")












# app/models.py (excerpt)
from datetime import datetime, timezone # Import timezone

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    q1 = db.Column(db.Integer, nullable=False)
    q2 = db.Column(db.Integer, nullable=False)
    q3 = db.Column(db.Integer, nullable=False)
    q4 = db.Column(db.Integer, nullable=False)
    q5 = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)

    # Add this new column:
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Answer {self.id}>'





