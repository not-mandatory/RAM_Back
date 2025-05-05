"""from app import app, db
from app.models import User, Answer, Question, Project, create_questions, Role

with app.app_context():
    # Create a new admin user
    new_admin = User(username='_user',email = 'a@ad.com', password_hash='cure_password')
    db.session.add(new_admin)
    db.session.commit()
"""
from flask_cors import CORS
 # or CORS(app, origins="http://localhost:3000") if you want to restrict

from cors_config import *

from app import app



if __name__ == "__main__":
    app.run(debug=True)



"""
"scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
"""
