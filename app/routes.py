from flask import render_template, url_for, redirect, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from app.models import User, Project, Answer, Question
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Project, Question, Answer

from flask_jwt_extended import create_access_token

# Admin route to create a project
@app.route('/admin/project/create', methods=['POST'])
#@login_required
def create_project():
    #if current_user.role.value != 'admin':
        #flash('You do not have permission to create projects.', 'danger')
        #return jsonify({"error": "you are not an admin"})

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')

    project = Project(title=title, description=description)
    db.session.add(project)
    db.session.commit()

    return jsonify({'message': 'Project created successfully!'}), 201


# Admin route to get all projects
@app.route('/admin/projects', methods=['GET'])
#@login_required
def admin_projects():
    #if current_user.role.value != 'admin':
        #flash('You do not have permission to view projects.', 'danger')
        #return jsonify({"error": "you are not an admin"})

    projects = Project.query.all()
    return jsonify([project.to_dict() for project in projects])

@app.route('/projects/all', methods=['GET'])
@jwt_required()
def projects_with_evaluation_status():
    user_id = get_jwt_identity()
    projects = Project.query.all()
    response = []

    for project in projects:
        already_evaluated = Answer.query.filter_by(
            user_id=user_id,
            project_id=project.id
        ).first() is not None

        response.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "already_evaluated": already_evaluated
        })

    return jsonify(response)




@app.route('/admin/users', methods=['GET'])
def get_users():

    from app.models import Role  # make sure Role Enum is imported

    users = User.query.filter(User.role != Role.ADMIN).all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value
        } for user in users
    ])

@app.route('/project/<int:project_id>', methods=['GET'])
def get_projectById(project_id):
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return jsonify({"error": "Project not found"}), 404

    return jsonify(project.to_dict()), 200

# Route for normal users to evaluate a project
from flask_jwt_extended import jwt_required, get_jwt_identity



# Set up logger
logger = logging.getLogger(__name__)

@app.route('/evaluate/<int:project_id>', methods=['POST'])
@jwt_required()
def evaluate_project(project_id):
    user_id = get_jwt_identity()
    logger.info(f"Received evaluation request for project ID: {project_id} from user ID: {user_id}")

    existing_answers = Answer.query.filter_by(user_id=user_id, project_id=project_id).first()

    if existing_answers:
        return jsonify({"error": "You have already evaluated this project."}), 409


    try:
        data = request.get_json()
        if not data:
            logger.error(f"Missing JSON data in the request for project ID: {project_id}")
            return jsonify({'error': 'No data provided'}), 400

        answers = data.get('answers')

        if not answers:
            logger.error(f"Missing 'answers' in the request data for project ID: {project_id}")
            return jsonify({'error': 'Answers not provided'}), 400

        if len(answers) != 5:
            logger.error(f"Invalid answers count for project ID: {project_id}. Expected 5 answers, got {len(answers)}.")
            return jsonify({'error': 'Invalid answers count.'}), 400

        # Get the project
        project = Project.query.get_or_404(project_id)
        logger.info(f"Found project ID: {project_id} for evaluation.")

        # Iterate over answers and store them in the database
        for index, answer in enumerate(answers):
            question = Question.query.filter_by(order=index + 1).first()
            if not question:
                logger.error(f"Question not found for index {index + 1} in project ID: {project_id}")
                return jsonify({'error': f"Question not found for index {index + 1}"}), 404

            # Store answer in the database
            answer_entry = Answer(user_id=user_id, question_id=question.id, project_id=project.id, answer=answer)
            db.session.add(answer_entry)
            logger.info(f"Answer for question {index + 1} stored successfully for project ID: {project_id}")

        db.session.commit()
        logger.info(f"Evaluation submitted successfully for project ID: {project_id}.")

        return jsonify({'message': 'Project evaluated successfully!'}), 200

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error during evaluation of project ID: {project_id} - {str(e)}")
        return jsonify({'error': 'An error occurred while processing the evaluation.'}), 500




# Route to get all answers for a specific question
@app.route('/answers/question/<int:question_id>', methods=['GET'])
def get_answers_for_question(question_id):
    answers = Answer.query.filter_by(question_id=question_id).all()
    answer_data = [{'user': answer.user.username, 'answer': answer.answer} for answer in answers]
    return jsonify(answer_data)


# Route to get all answers for a specific project
@app.route('/project/<int:project_id>/answers', methods=['GET'])
#@login_required
def get_project_answers(project_id):
    project = Project.query.get_or_404(project_id)

    answers = Answer.query.filter_by(project_id=project.id).all()

    response = []
    for ans in answers:
        response.append({
            "user_id": ans.user_id,
            "question_id": ans.question_id,
            "question_text": ans.question.text,
            "answer": ans.answer
        })

    return jsonify(response)


@app.route('/admin/projects/grouped-evaluations', methods=['GET'])
def grouped_evaluations():
    answers = Answer.query.join(User).join(Project).join(Question).order_by(
        Answer.user_id, Answer.project_id, Question.order
    ).all()

    grouped = {}
    for ans in answers:
        key = (ans.user_id, ans.project_id)
        if key not in grouped:
            grouped[key] = {
                "username": ans.user.username,
                "project_title": ans.project.title,
                "answers": []
            }
        grouped[key]["answers"].append(ans.answer)

    return jsonify(list(grouped.values()))


from sqlalchemy.sql import func

@app.route('/admin/projects/summary', methods=['GET'])
def project_question_analysis():
    projects = Project.query.all()
    response = []

    for project in projects:
        mean_qsts = []
        yes_count = 0
        no_count = 0

        for q_id in range(1, 6):  # assuming 5 questions, last one is boolean
            answers = Answer.query.filter_by(project_id=project.id, question_id=q_id).all()
            values = [a.answer for a in answers]

            if q_id == 5:  # Boolean question
                yes_count = values.count(1)
                no_count = values.count(0)
            else:
                mean = round(sum(values) / len(values), 2) if values else 0
                mean_qsts.append(mean)

        avg_qst = round(sum(mean_qsts) / len(mean_qsts), 2) if mean_qsts else 0

        response.append({
            "project_title": project.title,
            "mean_qsts": mean_qsts,
            "avg_qst": avg_qst,
            "yes_count": yes_count,
            "no_count": no_count
        })

    response.sort(key=lambda x: x["avg_qst"], reverse=True)

    return jsonify(response)




# Route to get all projects and their evaluation (answers)
@app.route('/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    project_data = []
    for project in projects:
        project_answers = []
        for question in Question.query.all():
            answers = Answer.query.filter_by(project_id=project.id, question_id=question.id).all()
            project_answers.append({'question': question.text, 'answers': [answer.answer for answer in answers]})
        project_data.append({'project': project.title, 'evaluations': project_answers})

    return jsonify(project_data)


# Route to register a new user
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    #password = generate_password_hash(data.get('password'))
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already in use."}), 400

    user = User(username=username, email=email, password_hash=password)
    db.session.add(user)
    db.session.commit()

    login_user(user)  # added

    return jsonify({'message': 'User registered successfully!', "email": user.email}), 201


# Route for user login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password_hash = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not user.password_hash == password_hash:
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=str(user.id),  # must be string
        additional_claims={"role": user.role.value}
    )
    return jsonify({"access_token": access_token ,'user_role': user.role.value})

# Route to logout the user
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful!'}), 200


@app.route('/whoami', methods=['GET'])
def whoami():
    if current_user.is_authenticated:
        return jsonify({
            "user_email": current_user.email,
            "is_admin": current_user.is_admin(),
            "current_user.role": current_user.role.value
        })
    else:
        return jsonify({"error": "Not logged in"}), 401
