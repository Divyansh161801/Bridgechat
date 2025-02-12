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
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv('keys.env')

app = Flask(__name__)

CACHE_DIR = "cache"
CHAT_PARENT_FOLDER_ID ="13VyJ03E2hW35njJt4Kl2epjc0x_R9Cfu"


# Set the database URI and other configurations from environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://avnadmin:AVNS_4OjKcOSQHS3y2h-Ppgz@chatbridge-user-divyanshkushwaha161801-chatbridge.l.aivencloud.com:15967/defaultdb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize Talisman with content security policy
csp = {
    'default-src': ["'self'", "https://cdn.socket.io"],
    'style-src': ["'self'", "https://cdn.socket.io", "'unsafe-inline'"],
    'script-src': ["'self'", "https://cdn.socket.io", "'unsafe-inline'"],  # Add 'unsafe-inline' cautiously
}
permissions_policy = {
    "geolocation": "self",
    "camera": "none",
    "microphone": "none",
}

Talisman(app, content_security_policy=csp,)

# Initialize SocketIO

socketio = SocketIO(app, cors_allowed_origins=os.getenv('CORS_ALLOWED_ORIGINS', "*"),async_mode="threading",manage_session=False)

# Initialize database and migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up logging with a rotating file handler
log_handler = RotatingFileHandler('server.log', maxBytes=1000000, backupCount=5)
log_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
log_handler.setFormatter(log_formatter)
app.logger.addHandler(log_handler)

app.logger.setLevel(logging.INFO)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitly set the table name to 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)


@app.route('/register', methods=['get','POST'])
def register():
    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        
        # Check if the user already exists (add your own logic here)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another one.', 'error')
            return render_template('register.html')

        # Add user to the database (this is an example, modify as needed)
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user)
        db.session.commit()

        # Success message
        flash('Registration successful! You can now log in.', 'success')
        return render_template('login.html')
    
    return render_template('register.html')



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
# Error handlers
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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
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


@app.route('/chatroom', methods=['GET', 'POST'])
def chatroom():
    room = session.get('room', '0000')  # Default room if not defined
    username = session.get('username', 'Guest')

    if request.method == 'POST':
        message = request.form.get('message')  # Get the message from form input

        if message:
            folder_id = get_or_create_chatroom_folder(room)  # Step 1: Ensure chatroom folder exists
            file_path = save_message_to_cache(username, room, message)  # Step 2: Save message to local cache
            upload_to_drive(file_path, folder_id)  # Step 3: Upload the file to Google Drive

    return render_template('chatroom.html', room=room, username=username)
    
# Google Drive API setup
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    )
    return build('drive', 'v3', credentials=creds)


def save_message_to_cache(username, room, message):
    """Creates a file in /cache/ with the message content."""
    timestamp = int(time.time())
    file_name = f"{username}.{room}.{timestamp}.txt"
    file_path = os.path.join(CACHE_DIR, file_name)

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)  # Create cache directory if missing

    with open(file_path, "w") as f:
        f.write(message)
    
    return file_path  # Return file path for uploading
    

def upload_to_drive(username, room, message):
    """Saves message locally and uploads it to the correct Google Drive folder."""
    service = get_drive_service()
    chatroom_folder_id = get_or_create_chatroom_folder(service, room or "0000")

    file_path = save_message_to_cache(username, room, message)
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [chatroom_folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()



# Main entry point
if __name__ == '__main__':
    socketio.run(app, debug=os.getenv('FLASK_DEBUG', False))
