from flask_cors import CORS
from app import app  # Import the Flask app

# Enable CORS globally on all routes
CORS(app)