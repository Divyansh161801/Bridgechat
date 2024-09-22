from dotenv import load_dotenv
import logging
from flask import Flask, request, jsonify, render_template, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_migrate import Migrate
from flask_talisman import Talisman
from flask_cors import CORS
import os
import time
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from dm import dm_bp
import traceback
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Set the database URI directly
app.config['postgresql://chatbridge_users_user:g560HHNYPOEoDIYzMWKcWD5RfXpGwcDu@dpg-crgppcbv2p9s73aeji7g-a/chatbridge_users '] = 'postgresql://chatbridge_users_user:g560HHNYPOEoDIYzMWKcWD5RfXpGwcDu@dpg-crgppcbv2p9s73aeji7g-a/chatbridge_users '
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initialize Talisman with your app
csp = {
    'default-src': [
        "'self'",
        'https://cdn.socket.io',  # Allow socket.io scripts
    ],
    'script-src': [
        "'self'",
        'https://cdn.socket.io',
        "'unsafe-inline'",  # Allow inline scripts (if necessary)
    ],
    'connect-src': [
        "'self'",
        'https://bridgechat-hdbq.onrender.com',  # Allow connections to your Socket.IO server
    ],
}

CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for testing
Talisman(app, content_security_policy=csp)

# Initialize SocketIO (only once)
socketio = SocketIO(app, cors_allowed_origins="https://bridgechat-hdbq.onrender.com")

# Set up logging with a rotating file handler
log_handler = RotatingFileHandler('server.log', maxBytes=1000000, backupCount=5)
log_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
log_handler.setFormatter(log_formatter)
app.logger.addHandler(log_handler)

# Set the logger for the app
app.logger.setLevel(logging.INFO)

@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f"404 error: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # In case of a database error
    app.logger.error(f"500 error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    app.logger.error(f"Unhandled Exception: {str(e)}\n{tb}")
    return render_template('500.html'), 500

@socketio.on_error_default  # Handles the default namespace
def default_error_handler(e):
    app.logger.error(f"Socket.IO error: {e}")

# Register the DM blueprint
app.register_blueprint(dm_bp)

# Function to read the PEM files and extract the hash
def read_pem_file(filename):
    with open(filename, 'rb') as pem_file:
        content = pem_file.read()
    return content

# Socket.IO events
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    send(f"{current_user.username} has entered the room.", to=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    send(f"{current_user.username} has left the room.", to=room)

# Load environment variables
load_dotenv()

# Google Drive API setup
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    )
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, folder_id):
    service = get_drive_service()
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

# Additional Flask setup
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)
