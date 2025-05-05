from app import app, db
from app.models import User, Answer, Question, Project, create_questions

with app.app_context():
    db.create_all()  # This will create all the tables based on your models
    print("Tables created successfully!")

    create_questions()
