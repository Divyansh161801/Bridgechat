from flask import Blueprint, request, jsonify
import os
import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import time

dm_bp = Blueprint('dm_bp', __name__)

# Initialize Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'instance/public key.json'  # Update with the correct path to your service account JSON file

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

@dm_bp.route('/send_dm', methods=['POST'])
def send_dm():
    data = request.get_json()
    sender = data['sender']
    recipient = data['recipient']
    message = data['message']

    folder_path = f"dms/{sender}=>{recipient}"
    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{sender}.txt"
    
    save_to_drive(folder_path, file_name, message)
    return jsonify({'status': 'success', 'message': 'Message sent successfully'})

@dm_bp.route('/fetch_dms', methods=['GET'])
def fetch_dms():
    sender = request.args.get('sender')
    recipient = request.args.get('recipient')

    folder_path = f"dms/{sender}=>{recipient}"
    messages = fetch_messages_from_drive(folder_path)
    return jsonify({'status': 'success', 'messages': messages})

def save_to_drive(folder_path, file_name, file_content):
    folder_id = get_or_create_folder(folder_path)
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    
    with open('/tmp/temp_file.txt', 'w') as temp_file:
        temp_file.write(file_content)
    
    media = MediaFileUpload('/tmp/temp_file.txt', mimetype='text/plain')
    retry_with_exponential_backoff(service.files().create, body=file_metadata, media_body=media, fields='id').execute()
    os.remove('/tmp/temp_file.txt')

def get_or_create_folder(folder_path):
    query = f"name='{folder_path}' and mimeType='application/vnd.google-apps.folder'"
    results = retry_with_exponential_backoff(service.files().list, q=query, spaces='drive').execute()
    items = results.get('files', [])
    if not items:
        file_metadata = {'name': folder_path, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = retry_with_exponential_backoff(service.files().create, body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
    else:
        folder_id = items[0].get('id')
    return folder_id

def fetch_messages_from_drive(folder_path):
    folder_id = get_or_create_folder(folder_path)
    query = f"'{folder_id}' in parents"
    results = retry_with_exponential_backoff(service.files().list, q=query, spaces='drive', fields="files(id, name)").execute()
    items = results.get('files', [])
    
    messages = []
    for item in items:
        file_id = item['id']
        request = retry_with_exponential_backoff(service.files().get_media, fileId=file_id)
        file_content = request.execute().decode('utf-8')
        messages.append({'file_name': item['name'], 'content': file_content})
    return messages

def retry_with_exponential_backoff(func, *args, **kwargs):
    max_retries = 5
    delay = 1
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise e