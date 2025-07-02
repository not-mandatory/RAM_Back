



"""
from app import app


if __name__ == "__main__":

    app.run(debug=True)
"""

  # Important for WebSocket support

from app import app, socketio

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

