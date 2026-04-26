import os
import subprocess
import sys

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    viewer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_viewer.py")
    viewer = subprocess.Popen([sys.executable, viewer_path])
    try:
        socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("Server stopped cleanly")
    finally:
        viewer.terminate()
