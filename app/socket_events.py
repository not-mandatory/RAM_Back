from flask_socketio import emit, join_room
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app import socketio, db
from app.models import User, Role


@socketio.on('connect')
def handle_connect():
    """Handle client connection using JWT from cookies"""
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        # Check role using your model's Enum
        if user and str(user.role.value) == 'admin':

            join_room('admin_room')
            emit('connected', {'message': 'Connected to admin notifications'})
            print(f"Admin user {user.username} connected to notifications")
        else:
            emit('error', {'message': 'Access denied - Admin only'})
            return False

    except Exception as e:
        print(f"Connection error: {e}")
        emit('error', {'message': 'Not authenticated or invalid token'})
        return False

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from notifications')


@socketio.on('join_admin_room')
def handle_join_admin_room():
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user and str(user.role) == 'admin':
            join_room('admin_room')
            emit('joined_admin_room', {'message': 'Successfully joined admin notifications'})
        else:
            emit('error', {'message': 'Access denied'})
    except Exception as e:
        print(f"Error joining admin room: {e}")
        emit('error', {'message': 'Failed to join admin room'})
