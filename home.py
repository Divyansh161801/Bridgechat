from dotenv import load_dotenv
import logging
from flask import Flask, request, jsonify, render_template, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_migrate import Migrate
import os
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from dm import dm_bp

app = Flask(__name__)

# Register the DM blueprint
app.register_blueprint(dm_bp)

# Function to read the PEM files and extract the hash
def read_pem_file(filename):
    with open(filename, 'r') as pem_file:
        pem_content = pem_file.read()
        hash_start = pem_content.find("-----BEGIN HASH-----") + len("-----BEGIN HASH-----\n")
        hash_end = pem_content.find("-----END HASH-----")
        hashed_key = pem_content[hash_start:hash_end].strip()
    return hashed_key

# Load hashed keys from PEM files
hashed_private_key = read_pem_file('config/hashed_private_key.pem')
hashed_public_key = read_pem_file('config/hashed_public_key.pem')

# Set keys in Flask config
load_dotenv('keys.env')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['HASHED_PRIVATE_KEY'] = hashed_private_key
app.config['HASHED_PUBLIC_KEY'] = hashed_public_key
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable the warning

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'instance/public key.json'

KEEP_ALIVE_DURATION = 10 * 60  # 10 minutes
last_interaction_time = time.time()
shutdown_timer = None

def reset_shutdown_timer(shutdown_callback):
    global last_interaction_time, shutdown_timer
    last_interaction_time = time.time()
    
    if shutdown_timer is not None:
        shutdown_timer.cancel()
    
    shutdown_timer = threading.Timer(KEEP_ALIVE_DURATION, shutdown_callback)
    shutdown_timer.start()

def init_keep_alive(shutdown_callback):
    reset_shutdown_timer(shutdown_callback)

# Check if the service account file path is provided
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError("Service account file not found. Please check the path and try again.")

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    room = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
            return redirect('/profile')
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('login.html', error='User already exists. Please log in.')
        else:
            new_user = User(username=username, password=password, email=email)
            db.session.add(new_user)
            db.session.commit()
            return render_template('login.html', success='Registration successful. Please log in.')
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/enter_chatroom', methods=['POST'])
@login_required
def enter_chatroom():
    chatroom_number = request.form['chatroom_number']
    return redirect(f'/chatroom/{chatroom_number}')

@app.route('/chatroom/<room>', methods=['GET', 'POST'])
@login_required
def chatroom(room):
    return render_template('chatroom.html', room=room, username=current_user.username)

@app.route('/dm', methods=['POST'])
@login_required
def dm():
    recipient_username = request.form['recipient']
    return redirect(f'/dm/{recipient_username}')

@app.route('/dm/<username>', methods=['GET'])
@login_required
def dm_chat(username):
    return render_template('dm.html', username=username)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send({'username': username, 'message': f'{username} has joined the room.'}, to=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send({'username': username, 'message': f'{username} has left the room.'}, to=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    username = data['username']
    app.logger.info(f"Received message from {username} in room {room}: {message}")
    
    # Save the message to the database
    new_message = Message(username=username, room=room, message=message)
    db.session.add(new_message)
    db.session.commit()

    # Save the message to Google Drive
    save_message_to_drive(room, username, message)

    send({'username': username, 'message': message}, to=room)

def save_message_to_drive(room, username, message):
    try:
        timestamp = int(time.time())
        filename = f"{username}_{timestamp}.txt"
        file_path = f"cache/temp_dir/chatroom/{room}/{filename}"

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as file:
            file.write(message)

        credentials = service_account.Credentials.from_service_account_file('instance/public key.json')
        drive_service = build('drive', 'v3', credentials=credentials)
        folder_id = "13VyJ03E2hW35njJt4Kl2epjc0x_R9Cfu"  # Change to your Google Drive folder ID

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='text/plain')

        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        app.logger.info(f"File {filename} written and uploaded successfully.")
    except Exception as e:
        app.logger.error(f"Error in getting or creating folder: {e}")
# Other routes and views go here
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=True)