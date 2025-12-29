"""
Google Drive automation using Drive API (recommended over brittle Selenium flows).

Setup:
- Create a project in Google Cloud Console and enable Drive API
- Create OAuth 2.0 Client ID credentials (Desktop app) and download `credentials.json` into this repo
- First run will open a browser to authorize; token will be saved to `token.json`

This script will:
- ensure the three folders exist in Drive
- list files in the root (not inside the target folders)
- classify files using the same classifier and move them into corresponding Drive folders
"""
import os
import io
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from classifier import classify_file

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS = Path('credentials.json')
TOKEN = Path('token.json')

TARGET_FOLDERS = ["University Docs", "Technical Work", "Capstone Work"]


def get_service():
    creds = None
    if TOKEN.exists():
        with open(TOKEN, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS.exists():
                raise FileNotFoundError('credentials.json not found. Follow README to create credentials.')
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN, 'wb') as f:
            pickle.dump(creds, f)
    service = build('drive', 'v3', credentials=creds)
    return service


def find_or_create_folder(service, name):
    # Search for a folder in Drive with the given name at root
    q = f"name = '{name.replace("'","\\'")}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
    resp = service.files().list(q=q, fields='files(id, name)').execute()
    files = resp.get('files', [])
    if files:
        return files[0]['id']
    # create folder
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': ['root']
    }
    f = service.files().create(body=file_metadata, fields='id').execute()
    return f['id']


def list_root_files(service):
    # files not in any folder (parent = root)
    q = "'root' in parents and trashed=false"
    fields = 'files(id, name, mimeType)'
    resp = service.files().list(q=q, fields=fields).execute()
    return resp.get('files', [])


def move_file_to_folder(service, file_id, folder_id):
    # Retrieve the existing parents to remove
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    service.files().update(fileId=file_id, addParents=folder_id, removeParents=previous_parents, fields='id, parents').execute()


def classify_and_move_drive_files():
    service = get_service()
    folder_ids = {name: find_or_create_folder(service, name) for name in TARGET_FOLDERS}
    files = list_root_files(service)
    for f in files:
        name = f['name']
        fid = f['id']
        # classify by name
        cat = classify_file(name)
        dest_folder_id = folder_ids.get(cat)
        if dest_folder_id:
            move_file_to_folder(service, fid, dest_folder_id)
            print(f"Moved '{name}' -> {cat}")


if __name__ == '__main__':
    classify_and_move_drive_files()
