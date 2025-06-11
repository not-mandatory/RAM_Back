from datetime import datetime, timezone
from enum import Enum
from flask_login import UserMixin
from app import db

# Define role types using Enum
class Role(Enum):
    ADMIN = 'admin'
    USER = 'user'


class Notification(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    related_id = db.Column(db.String(100))  # For linking to ideas, projects, etc.

    # Relationship
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
    role = db.Column(db.Enum(Role), nullable=False, default=Role.USER)
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
    description = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(200))
    answers = db.relationship('Answer', backref='project', lazy=True)

    users = db.relationship("ProjectUser", back_populates="project", cascade="all, delete-orphan")


    def __repr__(self):
        return f'<Project {self.title}>'

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image_path": self.image_path
            #"answers_count": len(self.answers)  # Include the number of answers, or other relevant fields
        }

class ProjectUser(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_team_lead = db.Column(db.Boolean, default=False)

    project = db.relationship("Project", back_populates="users")










"""
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, nullable=False)

    # Relationship with Answer (one to many)
    answers = db.relationship('Answer', backref='question', lazy=True)

    def __repr__(self):
        return f'<Question {self.id}>'
"""



class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)     # Link to User
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)  # Link to Project

    # Static question fields
    q1 = db.Column(db.Integer, nullable=False)
    q2 = db.Column(db.Integer, nullable=False)
    q3 = db.Column(db.Integer, nullable=False)
    q4 = db.Column(db.Integer, nullable=False)
    q5 = db.Column(db.Integer, nullable=False)  # Last question is a boolean

    def __repr__(self):
        return f'<Answer {self.id}>'


"""
def create_questions():
    # This function is used to create predefined questions in the database
    questions = [
        "Désirabilité : le projet semble-t-il résoudre un problème important ?",
        "Viabilité : le projet a-t-il un Business Model à haut potentiel ?",
        "Faisabilité : le projet semble-t-il réalisable techniquement au sein de la RAM ?",
        "Alignement Corporate : le projet est-il aligné avec la stratégie de la RAM et a-t-il un sponsor prêt à le suivre jusqu'au bout ?",
        "Selon vous le projet doit-il continuer ? (Yes/No)"
    ]

    # Check if questions already exist to avoid duplicates
    if not Question.query.first():  # If no questions exist, add them
        for index, question_text in enumerate(questions, start=1):
            question = Question(text=question_text, order=index)
            db.session.add(question)
        db.session.commit()
"""


