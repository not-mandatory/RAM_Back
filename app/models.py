from enum import Enum
from flask_login import UserMixin
from app import db

# Define role types using Enum
class Role(Enum):
    ADMIN = 'admin'
    USER = 'user'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.USER)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Define the relationship with Answer
    answers = db.relationship('Answer', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def is_admin(self):
        return self.role == Role.ADMIN





class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(200))
    answers = db.relationship('Answer', backref='project', lazy=True)

    def __repr__(self):
        return f'<Project {self.title}>'

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description
            #"answers_count": len(self.answers)  # Include the number of answers, or other relevant fields
        }

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, nullable=False)

    # Relationship with Answer (one to many)
    answers = db.relationship('Answer', backref='question', lazy=True)

    def __repr__(self):
        return f'<Question {self.id}>'




class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)  # Link to Question
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)  # Link to Project
    answer = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Answer {self.id}>'


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



