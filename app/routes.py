import os
import uuid

from flask import render_template, url_for, redirect, request, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, s3, BUCKET

from app.models import User, Project, Answer, ProjectUser, Idea
import logging
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from app import db
from app.models import Project, Answer
import json


from flask import request, jsonify



from flask import request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_cors import cross_origin

from app.utils.notifications import create_notification_for_admins, logger

from app.utils.messages import send_welcome_email

@app.route("/admin/project/create", methods=["POST"])
def create_project():
    title = request.form.get("title")
    description = request.form.get("description")
    team_leader_id = request.form.get("team_leader_id")
    team_member_ids_raw = request.form.get("team_member_ids")
    category = request.form.get("category")

    image_file = request.files.get('image')
    image_url = request.form.get('imageUrl')
    s3_url = None

    if image_file:
        extension = os.path.splitext(image_file.filename)[1]
        s3_filename = f'project_images/{uuid.uuid4()}{extension}'

        # --- Use the imported BUCKET variable ---
        if not BUCKET: # Add a final check just in case
            current_app.logger.error("AWS_S3_BUCKET_NAME is not set in .env or app configuration.")
            return jsonify({"error": "S3 bucket name not configured"}), 500

        try:
            s3.upload_fileobj(
                image_file,
                BUCKET, # This should now be a string from your .env
                s3_filename,
                ExtraArgs={"ContentType": image_file.content_type}
            )
            s3_url = f'https://{BUCKET}.s3.amazonaws.com/{s3_filename}'
        except Exception as e:
            current_app.logger.error(f"Error uploading file to S3: {e}")
            return jsonify({"error": f"Failed to upload image to S3: {str(e)}"}), 500


    elif image_url:
        s3_url = image_url

    if not title or not team_leader_id:
        return jsonify({"error": "Title and team_leader_id are required"}), 400

    try:
        team_member_ids = json.loads(team_member_ids_raw) if team_member_ids_raw else []
    except json.JSONDecodeError: # More specific error handling
        return jsonify({"error": "Invalid team_member_ids format"}), 400

    all_user_ids = [team_leader_id] + team_member_ids
    users = User.query.filter(User.id.in_(all_user_ids)).all()
    user_map = {user.id: user for user in users}

    if len(users) != len(set(all_user_ids)):
        return jsonify({"error": "One or more user IDs are invalid"}), 400

    project = Project(title=title, description=description, image_path=s3_url, category = category)
    db.session.add(project)
    db.session.flush()

    leader = user_map[int(team_leader_id)]
    db.session.add(ProjectUser(
        project_id=project.id,
        user_id=leader.id,
        is_team_lead=True
    ))

    for member_id in team_member_ids:
        member = user_map[member_id]
        db.session.add(ProjectUser(
            project_id=project.id,
            user_id=member.id,
            is_team_lead=False
        ))

    db.session.commit()

    return jsonify({"message": "Project created successfully", "id": project.id}), 201



from flask import request, jsonify, current_app
import os
import uuid
import json
from urllib.parse import urlparse
import boto3

# --- AWS S3 SETUP ---
s3 = boto3.client('s3')
BUCKET = os.environ.get("AWS_S3_BUCKET_NAME")

def delete_s3_file(s3_url, bucket):
    """Delete a file from S3 given its full URL."""
    parsed = urlparse(s3_url)
    key = parsed.path.lstrip('/')
    s3.delete_object(Bucket=bucket, Key=key)

@app.route("/api/project/update/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # --- Get fields from form data (for FormData requests) ---
    title = request.form.get("title")
    description = request.form.get("description")
    team_leader_id = request.form.get("teamLeadId")
    team_members_raw = request.form.get("teamMembers")
    category = request.form.get("category")

    image_file = request.files.get('image')
    image_url = request.form.get('imageUrl')
    remove_image = request.form.get("removeImage")
    s3_url = None

    previous_image = project.image_path

    # --- IMAGE HANDLING ---
    if remove_image == "true":
        # Remove image from S3 if it was previously uploaded
        if previous_image and BUCKET and "s3.amazonaws.com" in previous_image:
            try:
                delete_s3_file(previous_image, BUCKET)
            except Exception as e:
                current_app.logger.error(f"Error deleting file from S3: {e}")
        project.image_path = None

    elif image_file:
        extension = os.path.splitext(image_file.filename)[1]
        s3_filename = f'project_images/{uuid.uuid4()}{extension}'
        if not BUCKET:
            current_app.logger.error("AWS_S3_BUCKET_NAME is not set.")
            return jsonify({"error": "S3 bucket name not configured"}), 500
        try:
            s3.upload_fileobj(
                image_file,
                BUCKET,
                s3_filename,
                ExtraArgs={"ContentType": image_file.content_type}
            )
            s3_url = f'https://{BUCKET}.s3.amazonaws.com/{s3_filename}'
            # If there was a previous image, delete it
            if previous_image and "s3.amazonaws.com" in previous_image:
                try:
                    delete_s3_file(previous_image, BUCKET)
                except Exception as e:
                    current_app.logger.error(f"Error deleting file from S3: {e}")
            project.image_path = s3_url
        except Exception as e:
            current_app.logger.error(f"Error uploading file to S3: {e}")
            return jsonify({"error": f"Failed to upload image to S3: {str(e)}"}), 500

    elif image_url:
        project.image_path = image_url

    # --- UPDATE PROJECT FIELDS ---
    if title: project.title = title
    if description: project.description = description
    if category: project.category = category

    # --- TEAM HANDLING ---
    try:
        team_member_ids = json.loads(team_members_raw) if team_members_raw else []
        team_member_ids = [m['userId'] if isinstance(m, dict) else int(m) for m in team_member_ids]
    except Exception:
        return jsonify({"error": "Invalid teamMembers format"}), 400

    if team_leader_id:
        all_user_ids = [int(team_leader_id)] + team_member_ids
        users = User.query.filter(User.id.in_(all_user_ids)).all()
        user_map = {user.id: user for user in users}
        if len(users) != len(set(all_user_ids)):
            return jsonify({"error": "One or more user IDs are invalid"}), 400

        # Remove old team assignments
        ProjectUser.query.filter_by(project_id=project.id).delete()
        db.session.flush()

        # Add new team leader
        leader = user_map[int(team_leader_id)]
        db.session.add(ProjectUser(
            project_id=project.id,
            user_id=leader.id,
            is_team_lead=True
        ))

        # Add new team members
        for member_id in team_member_ids:
            if member_id == int(team_leader_id):
                continue
            member = user_map[member_id]
            db.session.add(ProjectUser(
                project_id=project.id,
                user_id=member.id,
                is_team_lead=False
            ))

    db.session.commit()
    return jsonify({"message": "Project updated", "id": project.id}), 200


# Admin route to get all projects
from flask import request, jsonify
# Assuming Project, User, ProjectUser, and db are imported from your app setup
from app import app, db # Assuming app and db are defined in app.py
from app.models import Project, User, ProjectUser # Assuming your models are here

@app.route("/admin/projects", methods=["GET"])
def get_projects():
    # Fetch all projects
    projects = Project.query.all()
    output = []

    for project in projects:
        project_users_data = []

        # Query for ProjectUser entries related to the current project
        # and eagerly load the associated User object by joining ProjectUser with User
        project_users = db.session.query(ProjectUser, User).\
                        join(User, ProjectUser.user_id == User.id).\
                        filter(ProjectUser.project_id == project.id).\
                        all() # This returns tuples of (ProjectUser, User)

        for pu, user in project_users:
            # 'pu' is the ProjectUser instance (for is_team_lead)
            # 'user' is the User instance (for username, position, direction)
            project_users_data.append({
                "name": user.username,        # Fetched from the joined User table
                "position": user.position,    # Fetched from the joined User table
                "direction": user.direction,  # Fetched from the joined User table
                "is_team_lead": pu.is_team_lead, # Fetched from the ProjectUser table
            })

        output.append({
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "image_path": project.image_path,
            "category": project.category,
            "users": project_users_data # This now contains the complete user details
        })


    return jsonify(output)






@app.route('/projects/all', methods=['GET'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
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
            "already_evaluated": already_evaluated,
            "image_path": project.image_path
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
            "role": user.role.value,
            "position": user.position,
            "direction": user.direction,
            "createdAt": user.created_at
        } for user in users
    ])


"""
@app.route('/api/idea/submit', methods=['POST'])
@jwt_required()
def submit_idea():
    data = request.get_json()
    description = data.get("description")
    title = data.get("title")
    category = data.get("category")
    user_id = get_jwt_identity()

    if not description or not title or not category:
        return jsonify({"error": "Title, description, and category are required."}), 400

    try:
        # Create and save the idea
        new_idea = Idea(
            title=title,
            description=description,
            category=category,
            status='pending',
            user_id=user_id
        )
        db.session.add(new_idea)
        db.session.flush()  # Get the ID without committing

        # Get user info for notification
        user = User.query.get(user_id)

        # Create notifications for all admins
        notifications = create_notification_for_admins(
            title="Nouvelle idée soumise",
            message = f"{user.username} has submitted a new idea: '{title}'",
            notification_type="info",
            related_id=new_idea.id
        )

        db.session.commit()


        # Send real-time notification to admin room
        socketio.emit('new_notification', {


            'title': 'Nouvelle idée soumise',
            "id": notifications[0].id if notifications else None,
            'message': f"{user.username} submitted a new idea: '{title}'",
            'type': 'info',
            'idea_id': new_idea.id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'

        }, room='admin_room')

        return jsonify({
            "message": "Idea submitted successfully",
            "idea_id": new_idea.id,
            "status": "success"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to submit idea",
            "details": str(e)
        }), 500

"""




@app.route('/api/project/<int:project_id>/comments', methods=['GET'])
# @project_bp.route('/api/project/<int:project_id>/comments', methods=['GET']) # If using Blueprint
def get_project_comments(project_id):
    # First, check if the project actually exists
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404


    answers = Answer.query.filter_by(project_id=project_id)

    if not answers:
        return jsonify({"comments": []}), 200 # Return empty list if no comments found

    comments_data = []
    for answer in answers:

        if answer.comment:
            comment_entry = {
                "id": answer.id,
                "username": "user", # <--- This is the key you requested
                "project_id": answer.project_id,
                "comment": answer.comment,
                "created_at": answer.created_at.isoformat() + 'Z' # Format datetime to ISO 8601 with Z for UTC
            }
            comments_data.append(comment_entry)

    return jsonify({"comments": comments_data}), 200








@app.route('/api/comments/all', methods=['GET'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_all_comments_with_details():
    # Query all Answer records
    # Eager load related User and Project objects for efficiency (prevents N+1 queries)
    all_comments = db.session.query(Answer, User, Project).\
                   join(User, Answer.user_id == User.id).\
                   join(Project, Answer.project_id == Project.id).\
                   order_by(Answer.created_at.desc()).\
                   all()

    if not all_comments:
        return jsonify({"comments": []}), 200 # Return empty list if no comments found

    comments_data = []
    for answer, user, project in all_comments:
        comment_entry = {
            "username": user.username,        # The user's username    # Include project ID
            "project_name": project.title,    # The project's title
            "comment": answer.comment,        # The comment text itself
            "created_at": answer.created_at # ISO 8601 format with UTC indicator
        }
        comments_data.append(comment_entry)

    return jsonify({"comments": comments_data}), 200








@app.route('/evaluate/<int:project_id>', methods=['POST'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def evaluate_project(project_id):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    logger.info(f"Received evaluation request for project ID: {project_id} from user ID: {user_id}")

    existing_answer_record = Answer.query.filter_by(user_id=user_id, project_id=project_id).first()
    if existing_answer_record:
        logger.warning(f"User {user_id} has already evaluated project {project_id}.")
        return jsonify({"error": "You have already evaluated this project."}), 409

    try:
        data = request.get_json()
        if not data:
            logger.error(f"Missing JSON data in the request for project ID: {project_id}")
            return jsonify({'error': 'No data provided'}), 400

        q1_answer = data.get('q1')
        q2_answer = data.get('q2')
        q3_answer = data.get('q3')
        q4_answer = data.get('q4')
        q5_answer = data.get('q5')
        comment = data.get('comment')

        if any(val is None for val in [q1_answer, q2_answer, q3_answer, q4_answer, q5_answer]):
            logger.error(f"Missing one or more question answers (q1-q5) in request for project ID: {project_id}")
            return jsonify({'error': 'All answers (q1-q5) are required.'}), 400

        rating_questions = [q1_answer, q2_answer, q3_answer, q4_answer]
        for idx, rating in enumerate(rating_questions):
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                logger.error(f"Invalid rating for q{idx + 1}: {rating} for project ID: {project_id}.")
                return jsonify({'error': f'Answer for q{idx + 1} must be an integer between 1 and 5.'}), 400

        if not isinstance(q5_answer, int) or not (0 <= q5_answer <= 1):
            logger.error(f"Invalid value for q5: {q5_answer} for project ID: {project_id}. Must be 0 or 1.")
            return jsonify({'error': 'Answer for q5 must be 0 or 1.'}), 400

        project = Project.query.get_or_404(project_id)
        logger.info(f"Found project ID: {project_id} for evaluation.")

        answer_entry = Answer(
            user_id=user_id,
            project_id=project.id,
            q1=q1_answer,
            q2=q2_answer,
            q3=q3_answer,
            q4=q4_answer,
            q5=q5_answer,
            comment = comment
        )
        db.session.add(answer_entry)
        db.session.commit()
        logger.info(f"Evaluation submitted successfully for project ID: {project_id} by user {user_id}.")

        # --- CREATE NOTIFICATION (ONLY ONCE) ---
        notification_title = "Nouvelle évaluation de projet"
        notification_message = f"Le projet '{project.title}' a été évalué par l'utilisateur '{current_user.username}'."
        #notification_message = f"The project '{project.title}' has been evaluated by the user '{current_user.username}'."
        # Create notification in database
        notification = create_notification_for_admins(
            title=notification_title,
            message=notification_message,
            notification_type="info",
            related_id=project.id
        )

        # --- EMIT REAL-TIME SOCKET.IO EVENT TO ADMINS (ONLY ONCE) ---
        logger.info(f"Emitting notification to admin_room for project {project.id}")
        socketio.emit(
            "new_notification",
            {
                "id": notification[0].id if notification else None,
                "title": notification_title,
                "message": notification_message,
                "type": "info",
                "project_id": project.id,
                "timestamp": notification[0].created_at.isoformat() if notification[0].created_at else None,# Changed from idea_id to project_id

            },
            room="admin_room"
        )

        return jsonify({'message': 'Project evaluated successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during evaluation of project ID: {project_id} - {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred while processing the evaluation.'}), 500



# Route to get all answers for a specific question



# Route to get all answers for a specific project
@app.route('/project/<int:project_id>/answers', methods=['GET'])
#@login_required # Uncomment if you want to restrict access to logged-in users
def get_project_answers(project_id):
    # First, check if the project exists. If not, return 404.
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    # Query for all Answer records related to this project_id
    # We join with the User model to fetch the username of the person who evaluated.
    answers_with_users = db.session.query(Answer, User).\
                         join(User, Answer.user_id == User.id).\
                         filter(Answer.project_id == project_id).\
                         all()

    response = []
    if not answers_with_users:
        # If the project exists but has no evaluations yet
        return jsonify(response), 200 # Return an empty list for no answers

    for ans, user in answers_with_users:
        # 'ans' is the Answer instance
        # 'user' is the User instance (from the joined User table)
        response.append({
            "answer_id": ans.id,      # Include the answer record ID
            "user_id": ans.user_id,
            "username": user.username, # Get username from the joined User table
            "q1": ans.q1,             # Directly access the static question columns
            "q2": ans.q2,
            "q3": ans.q3,
            "q4": ans.q4,
            "q5": ans.q5
        })

    return jsonify(response)

@app.route('/admin/projects/grouped-evaluations', methods=['GET'])
def grouped_evaluations():
    # Query all Answer records.
    # We join with User to get the evaluator's username.
    # We join with Project to get the project's title.
    # The 'Question' join is removed as the model no longer exists.
    answers_with_details = db.session.query(Answer, User, Project).\
                           join(User, Answer.user_id == User.id).\
                           join(Project, Answer.project_id == Project.id).\
                           order_by(Answer.user_id, Answer.project_id).\
                           all()

    # This list will hold the final structured evaluations.
    # Since each 'Answer' record now contains all five static questions (q1-q5),
    # and your /evaluate endpoint prevents multiple Answer records for the same
    # user-project combination, each entry in 'answers_with_details' corresponds
    # to one complete evaluation.
    grouped_evaluations_list = []

    for ans, user, project in answers_with_details:
        grouped_evaluations_list.append({
            "user_id": ans.user_id,          # ID of the user who evaluated
            "username": user.username,       # Username from the User table
            "project_id": ans.project_id,    # ID of the project evaluated
            "project_title": project.title,  # Title from the Project table
            "answers": [                     # All five answers for this evaluation as an array
                ans.q1,
                ans.q2,
                ans.q3,
                ans.q4,
                ans.q5
            ]
        })

    return jsonify(grouped_evaluations_list)


from sqlalchemy.sql import func
@app.route('/admin/projects/summary', methods=['GET'])
def project_question_analysis():
    # Fetch all projects from the database
    projects = Project.query.all()
    response = []

    for project in projects:
        # Retrieve all answer records associated with the current project
        project_answers = Answer.query.filter_by(project_id=project.id).all()

        # Initialize lists to store the values for each question across all evaluations for this project
        q1_values = []
        q2_values = []
        q3_values = []
        q4_values = []
        q5_values = [] # This will store 0s or 1s for the "boolean" question

        # Populate the value lists from each answer record for the current project
        for ans in project_answers:
            q1_values.append(ans.q1)
            q2_values.append(ans.q2)
            q3_values.append(ans.q3)
            q4_values.append(ans.q4)
            q5_values.append(ans.q5) # Assuming q5 is an Integer (0 or 1)

        # --- Calculate Means for Questions 1-4 ---
        mean_qsts = []
        # Iterate through the lists of values for the first four questions
        for values_list in [q1_values, q2_values, q3_values, q4_values]:
            if values_list: # Ensure there are answers before calculating the mean to avoid ZeroDivisionError
                mean = round(sum(values_list) / len(values_list), 2)
                mean_qsts.append(mean)
            else:
                mean_qsts.append(0.0) # Append 0 if no answers for this specific question

        # --- Calculate Yes/No Counts for Question 5 ---
        yes_count = 0
        no_count = 0
        if q5_values: # Ensure there are answers for q5
            yes_count = q5_values.count(1) # Count occurrences of '1'
            no_count = q5_values.count(0)  # Count occurrences of '0'

        # --- Calculate the overall average of the means for questions 1-4 ---
        # This gives a single average score for the project based on the rating questions.
        avg_qst = round(sum(mean_qsts) / len(mean_qsts), 2) if mean_qsts else 0.0

        # Append the calculated summary for the current project to the response list
        response.append({
            "project_id": project.id,        # Include project ID for clear identification
            "project_title": project.title,
            "mean_qsts": mean_qsts,          # A list of mean scores for Q1, Q2, Q3, Q4
            "avg_qst": avg_qst,              # The overall average of those means
            "yes_count": yes_count,          # Count of 'yes' (1) answers for Q5
            "no_count": no_count             # Count of 'no' (0) answers for Q5
        })

    # Sort the projects by their overall average score (avg_qst) in descending order
    response.sort(key=lambda x: x["avg_qst"], reverse=True)

    return jsonify(response)




# Route to get all projects and their evaluation (answers)


"""
# Route to register a new user
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    #password = generate_password_hash(data.get('password'))
    password = data.get('password')
    position = data.get('position')
    direction = data.get('direction')

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already in use."}), 400

    user = User(username=username, email=email, password_hash=password, position = position, direction = direction)
    db.session.add(user)
    db.session.commit()

    login_user(user)  # added

    return jsonify({'message': 'User registered successfully!', "email": user.email}), 201

@app.route('/project/<int:project_id>', methods=['GET'])
def get_projectById(project_id):
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return jsonify({"error": "Project not found"}), 404

    return jsonify(project.to_dict()), 200
"""
# Route for normal users to evaluate a project
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/api/user/<int:user_id>', methods=['GET'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Adjust the fields as needed for your frontend
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "position": user.position,
        "direction": user.direction,
        "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
    }
    return jsonify(user_data), 200





@app.route("/projects/<int:project_id>/team", methods=["GET"])
def get_project_team(project_id):
    # Query ProjectUser entries for the given project_id
    # and join with the User table to get user details
    project_users_with_details = db.session.query(ProjectUser, User).\
                                 join(User, ProjectUser.user_id == User.id).\
                                 filter(ProjectUser.project_id == project_id).\
                                 all()

    if not project_users_with_details:
        # Check if the project itself exists, or if there are truly no users
        # It's better to distinguish between "project not found" and "no team"
        project_exists = Project.query.get(project_id)
        if not project_exists:
            return jsonify({"error": "Project not found"}), 404
        else:
            return jsonify({"team_leader": None, "team_members": []}), 200 # Project exists, but no team assigned

    team_leader = None
    team_members = []

    for pu, user in project_users_with_details:
        # 'pu' is the ProjectUser instance
        # 'user' is the User instance (from the joined User table)
        user_info = {
            "id": user.id, # Often useful to include the user's ID
            "name": user.username,     # Get username from the User table
            "position": user.position, # Get position from the User table
            "direction": user.direction, # Get direction from the User table
        }
        if pu.is_team_lead:
            team_leader = user_info
        else:
            team_members.append(user_info)

    return jsonify({
        "team_leader": team_leader,
        "team_members": team_members
    }), 200



from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Project, ProjectUser, User, db # Assuming your models are structured like this

@app.route('/project/<int:project_id>', methods=['GET'])
def get_project_details(project_id):
    # First, try to fetch the project itself
    project = Project.query.get(project_id)

    # If the project doesn't exist, return a 404 error
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Convert project details to a dictionary
    project_details = project.to_dict()

    # Now, fetch the team associated with this project
    project_users_with_details = db.session.query(ProjectUser, User).\
                                 join(User, ProjectUser.user_id == User.id).\
                                 filter(ProjectUser.project_id == project_id).\
                                 all()

    team_leader = None
    team_members = []

    # Iterate through the fetched project users to identify the leader and members
    for pu, user in project_users_with_details:
        user_info = {
            "id": user.id,
            "username": user.username,
            "position": user.position,
            "direction": user.direction,
            "is_team_lead": pu.is_team_lead # Useful to explicitly state this
        }
        if pu.is_team_lead:
            team_leader = user_info
        else:
            team_members.append(user_info)

    # Add the team information to the project details dictionary
    project_details["team"] = {
        "team_leader": team_leader,
        "team_members": team_members
    }

    # Return the complete project details, including team information
    return jsonify(project_details), 200






# Route for user login







@app.route('/api/login', methods=['POST'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def login():
    data = request.get_json()
    email = data.get("email")
    password_hash = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not user.password_hash == password_hash:
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role.value}
    )

    response = jsonify({
        "msg": "Login successful",
        "user_role": user.role.value,
        # OK to return role or other metadata
        "username": user.username,
        "email": user.email

    })

    set_access_cookies(response, access_token)  # ✅ Secure, HttpOnly, SameSite=None, etc.

    return response, 200


@app.route('/api/verify-token', methods=['GET'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def verify_token():
    try:
        # Verify the JWT token from cookies
        verify_jwt_in_request(locations=["cookies"])

        # If we get here, the JWT is valid
        current_user_id = get_jwt_identity()
        claims = get_jwt()

        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "authenticated": True,
            "userId": current_user_id,
            "user_role": claims.get("role", "user"),
            "name": user.username,
            "email": user.email
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 401



@app.route('/api/idea/analyze', methods=['POST'])
#@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def analyze_idea():
    """Analyze idea and suggest category without saving to database"""
    data = request.get_json()
    description = data.get("description")
    title = data.get("title")


    if not description or not title:
        return jsonify({"error": "Title and description are required."}), 400

    try:
        # Run classification to get suggested category
        predicted_category = classify(description)

        return jsonify({
            "suggestedCategory": predicted_category,
            "status": "success"
        })

    except Exception as e:
        return jsonify({
            "error": "Failed to analyze idea",
            "details": str(e)
        }), 500







from flask import jsonify
from flask_jwt_extended import unset_jwt_cookies

@app.route('/logout', methods=['POST'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def logout():
    response = jsonify({"msg": "Logged out"})
    unset_jwt_cookies(response)
    return response, 200





@app.route('/api/admin/ideas', methods=['GET'])
def get_all_ideas():
    ideas = Idea.query.all()

    ideas_data = []
    for idea in ideas:
        ideas_data.append({
            "id": idea.id,
            "title": idea.title,
            "description": idea.description,
            "category": idea.category,
            "status": idea.status,
            "created_at": idea.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "submitted_by": idea.user.username
        })

    return jsonify(ideas_data), 200









@app.route('/api/idea/<int:idea_id>', methods=['GET'])

def get_idea_by_id(idea_id):
    from app.models import Idea

    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({"error": "Idea not found"}), 404

    return jsonify({
        "id": idea.id,
        "title": idea.title,
        "description": idea.description,
        "category": idea.category,
        "submitted_by": idea.user.username,
        "created_at": idea.created_at
    }), 200







@app.route('/api/ideas/<int:idea_id>/approve', methods=['POST'])
def approve_idea(idea_id):
    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({'error': 'Idea not found'}), 404

    if idea.status == 'Approved':
        return jsonify({'message': 'Idea is already approved'}), 200

    idea.status = 'Approved'
    db.session.commit()
    return jsonify({'message': 'Idea approved successfully', 'id': idea.id, 'status': idea.status}), 200








@app.route('/api/admin/import-users', methods=['POST'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def import_users():
    users = request.get_json() or []
    created = []
    errors = []
    for data in users:
        # Check for duplicates
        if User.query.filter((User.username == data['username']) | (User.email == data['email'])).first():
            errors.append({'username': data['username'], 'email': data['email'], 'error': 'Duplicate'})
            continue
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=data['password'],
            position=data.get('position', ''),
            direction=data.get('direction', ''),
        )
        db.session.add(user)
        created.append({'username': data['username'], 'email': data['email']})
    db.session.commit()
    return jsonify({'created': created, 'errors': errors}), 201


# Add these imports to your existing routes.py
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from datetime import datetime
from app import app, db, socketio
from app.models import Idea, User, Notification






@app.route('/api/notifications', methods=['GET'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_notifications():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    try:
        notifications = Notification.query.filter_by(user_id=user_id) \
            .order_by(Notification.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()

        return jsonify({
            'notifications': [n.to_dict() for n in notifications.items],
            'total': notifications.total,
            'unread_count': unread_count
        })
    except Exception as e:
        return jsonify({"error": "Failed to fetch notifications", "details": str(e)}), 500


# Mark notification as read
@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def mark_notification_read(notification_id):
    user_id = get_jwt_identity()

    try:
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()

        if not notification:
            return jsonify({"error": "Notification not found"}), 404

        notification.is_read = True
        db.session.commit()

        return jsonify({"message": "Notification marked as read"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to mark notification as read", "details": str(e)}), 500


# Mark all notifications as read
@app.route('/api/notifications/read-all', methods=['PUT'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def mark_all_notifications_read():
    user_id = get_jwt_identity()

    try:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()

        return jsonify({"message": "All notifications marked as read"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to mark all notifications as read", "details": str(e)}), 500


# Test notification endpoint (for development)
@app.route('/api/test-notification', methods=['POST'])
@jwt_required()
def test_notification():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != 'admin':
        return jsonify({"error": "Admin access required"}), 403

    try:
        # Create test notifications
        create_notification_for_admins(
            title="Test Notification",
            message="This is a test notification to verify the system is working",
            notification_type="info"
        )

        # Send real-time test notification
        socketio.emit('new_notification', {
            'title': 'Test Notification',
            'message': 'This is a test notification to verify the system is working',
            'type': 'info',
            'timestamp': datetime.utcnow().isoformat()
        }, room='admin_room')

        return jsonify({"message": "Test notification sent successfully"})
    except Exception as e:
        return jsonify({"error": "Failed to send test notification", "details": str(e)}), 500






@app.route('/api/user/evaluations', methods=['GET'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_user_evaluations():
    user_id = get_jwt_identity()
    logger.info(f"Fetching evaluations for user ID: {user_id}")

    # Query all Answer records for the current user, joining with Project to get project details
    user_evaluations = db.session.query(Answer, Project).\
                       join(Project, Answer.project_id == Project.id).\
                       filter(Answer.user_id == user_id).\
                       order_by(Answer.created_at.desc()).\
                       all()

    evaluations_list = []
    for ans, project in user_evaluations:
        # Convert q5 (Integer 0/1) from backend to Boolean for frontend
        q5_boolean = bool(ans.q5)

        evaluations_list.append({
            "id": str(ans.id), # Convert integer ID to string
            "projectId": str(project.id), # Convert integer Project ID to string
            "projectName": project.title,
            "date": ans.created_at.isoformat() if ans.created_at else None, # Format datetime to ISO string
            "ratings": {
                "q1": ans.q1,
                "q2": ans.q2,
                "q3": ans.q3,
                "q4": ans.q4,
                "q5": q5_boolean,
            },
        })

    logger.info(f"Successfully fetched {len(evaluations_list)} evaluations for user ID: {user_id}.")
    # Return the list of evaluations directly
    return jsonify(evaluations_list), 200



@app.route('/api/user/evaluations/<int:evaluation_id>', methods=['GET'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_single_user_evaluation(evaluation_id):
    user_id = get_jwt_identity()
    logger.info(f"Fetching evaluation {evaluation_id} for user ID: {user_id}")

    # Query the Answer record, ensuring it belongs to the authenticated user
    # and join with Project to get its title
    evaluation_record = db.session.query(Answer, Project).\
                                join(Project, Answer.project_id == Project.id).\
                                filter(Answer.id == evaluation_id, Answer.user_id == user_id).\
                                first()

    if not evaluation_record:
        logger.warning(f"Evaluation {evaluation_id} not found or does not belong to user {user_id}.")
        return jsonify({"error": "Evaluation not found or unauthorized."}), 404

    ans, project = evaluation_record

    # Convert q5 (Integer 0/1) from backend to Boolean for frontend
    q5_boolean = bool(ans.q5)

    response_data = {
        "id": str(ans.id),
        "projectId": str(project.id),
        "projectName": project.title,
        "date": ans.created_at.isoformat() if ans.created_at else None, # Use created_at
        "ratings": {
            "q1": ans.q1,
            "q2": ans.q2,
            "q3": ans.q3,
            "q4": ans.q4,
            "q5": q5_boolean,
        },
    }

    logger.info(f"Successfully fetched evaluation {evaluation_id} for user {user_id}.")
    # Return as an object with 'evaluation' key, matching your frontend's `data.evaluation`
    return jsonify({"evaluation": response_data}), 200








logger = logging.getLogger(__name__)

@app.route('/api/user/evaluations/<int:evaluation_id>', methods=['PUT'])
@jwt_required()
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def update_user_evaluation(evaluation_id):
    user_id = get_jwt_identity()
    logger.info(f"Received update request for evaluation {evaluation_id} from user ID: {user_id}")

    # Find the existing answer record, ensuring it belongs to the authenticated user
    existing_answer = Answer.query.filter_by(id=evaluation_id, user_id=user_id).first()

    if not existing_answer:
        logger.warning(f"Evaluation {evaluation_id} not found or does not belong to user {user_id} for update.")
        return jsonify({"error": "Evaluation not found or unauthorized to update."}), 404

    try:
        data = request.get_json()
        if not data:
            logger.error(f"No JSON data provided for update of evaluation {evaluation_id} by user {user_id}.")
            return jsonify({'error': 'No data provided for update'}), 400

        # Your frontend sends the ratings object directly under 'ratings' key
        ratings_data = data.get('ratings')
        if not ratings_data:
            logger.error(f"Missing 'ratings' object in update data for evaluation {evaluation_id} by user {user_id}.")
            return jsonify({'error': 'Ratings data is required.'}), 400

        # Extract and validate individual questions
        q1_answer = ratings_data.get('q1')
        q2_answer = ratings_data.get('q2')
        q3_answer = ratings_data.get('q3')
        q4_answer = ratings_data.get('q4')
        q5_answer = ratings_data.get('q5') # This will be boolean from frontend

        if any(val is None for val in [q1_answer, q2_answer, q3_answer, q4_answer, q5_answer]):
            logger.error(f"Missing one or more question answers (q1-q5) in update for evaluation {evaluation_id} by user {user_id}.")
            return jsonify({'error': 'All answers (q1-q5) are required.'}), 400

        # Validate rating questions (1-5)
        for i, rating in enumerate([q1_answer, q2_answer, q3_answer, q4_answer]):
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                logger.error(f"Invalid rating for q{i+1}: {rating} in update for evaluation {evaluation_id} by user {user_id}.")
                return jsonify({'error': f'Answer for q{i+1} must be an integer between 1 and 5.'}), 400

        # Validate boolean question (q5)
        if not isinstance(q5_answer, bool): # Frontend sends true/false
             logger.error(f"Invalid value for q5: {q5_answer} in update for evaluation {evaluation_id} by user {user_id}. Must be boolean.")
             return jsonify({'error': 'Answer for q5 must be a boolean (true/false).'}), 400

        # Update the existing record
        existing_answer.q1 = q1_answer
        existing_answer.q2 = q2_answer
        existing_answer.q3 = q3_answer
        existing_answer.q4 = q4_answer
        # Convert boolean q5 from frontend to integer 0/1 for database
        existing_answer.q5 = 1 if q5_answer else 0

        db.session.commit()
        logger.info(f"Evaluation {evaluation_id} updated successfully by user {user_id}.")

        return jsonify({'message': 'Evaluation updated successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during update of evaluation {evaluation_id} by user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while updating the evaluation.',
            'message': str(e) # Provide more detail in development, remove in production
        }), 500





@app.route('/api/user/<int:user_id>', methods=['PUT'])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json() if request.is_json else request.form

    username = data.get('username')
    email = data.get('email')
    position = data.get('position')
    direction = data.get('direction')
    role = data.get('role')
    password = data.get('password')

    if email and email != user.email:
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email is already in use."}), 400

    if username: user.username = username
    if email: user.email = email
    if position: user.position = position
    if direction: user.direction = direction
    if role: user.role = role
    if password and password.strip() != "":
        # user.password_hash = generate_password_hash(password)
        user.password_hash = password  # replace with hash in production

    db.session.commit()
    return jsonify({"message": "User updated successfully."}), 200









@app.route('/api/register', methods=['POST'])


def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    position = data.get('position')
    direction = data.get('direction')

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already in use."}), 400

    user = User(
        username=username,
        email=email,
        password_hash=password,  # Hash this in production!
        position=position,
        direction=direction
    )
    db.session.add(user)
    db.session.commit()

    # Send welcome email
    try:
        send_welcome_email(user.email, password)
    except Exception as e:
        # Log the error but don't crash the request
        app.logger.error(f"Failed to send welcome email: {e}")

    return jsonify({'message': 'User registered successfully!'}), 201






