# drive_automation.py — Line-by-line explanation

This document explains each line and logical block in `drive_automation.py`. Use this when describing how Drive-side automation is implemented, the OAuth flow, and how files are moved using the Drive API.

---

## Purpose (one-line)
`drive_automation.py` authenticates to Google Drive using OAuth, finds or creates the 3 target folders at Drive root, lists root files, classifies them (by filename currently), and moves them into the corresponding Drive folders.

---

## Header, imports and constants

```python
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
```

- Imports include the Google API client and OAuth helpers.
- `SCOPES` uses the full Drive scope so the script can list and move files. In production you may request narrower scopes if desired.
- `CREDENTIALS` refers to the OAuth client secrets JSON downloaded from Google Cloud Console.
- `TOKEN` is the local file where the authorized user's token is cached after first auth.

---

## get_service — authenticate and build client

```python
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
```

- If `token.json` exists, the token is loaded for reuse.
- If the token is missing or expired, the script either refreshes it (if `refresh_token` exists) or runs a local server auth flow (`InstalledAppFlow`) to open a browser to request consent.
- On successful auth, credentials are pickled to `token.json` for future runs.
- Finally `build('drive', 'v3')` constructs a Drive API client.

---

## find_or_create_folder

```python
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
```

- Uses a query to search for an existing folder with the matching name at Drive root, ensuring the automation doesn't create duplicates.
- If not found, it creates the folder as a Drive folder resource by specifying `mimeType` for folders and `parents=['root']`.

---

## list_root_files

```python
def list_root_files(service):
    # files not in any folder (parent = root)
    q = "'root' in parents and trashed=false"
    fields = 'files(id, name, mimeType)'
    resp = service.files().list(q=q, fields=fields).execute()
    return resp.get('files', [])
```

- Returns metadata for files whose parent is the Drive `root` (i.e., not already inside a folder). This is useful because the dataset requires files to be uploaded to root and then moved by automation.

---

## move_file_to_folder

```python
def move_file_to_folder(service, file_id, folder_id):
    # Retrieve the existing parents to remove
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    service.files().update(fileId=file_id, addParents=folder_id, removeParents=previous_parents, fields='id, parents').execute()
```

- The Drive API uses parent references to determine folder membership. To move a file, we add the new parent (destination folder) and remove the previous parents using `files().update`.
- This method preserves the file resource and metadata while changing its location.

---

## classify_and_move_drive_files

```python
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
```

- Authenticates, ensures folders exist (and gets their IDs), lists root files, classifies by filename using `classify_file`, and moves each file accordingly.
- Currently classification is done by **filename** (not content) for Drive. This is intentional to keep the first iteration simpler and avoid downloading files unnecessarily. See improvement suggestions below for content-based Drive classification.

---

## CLI

```python
if __name__ == '__main__':
    classify_and_move_drive_files()
```

- Simple entrypoint so `python drive_automation.py` runs the whole flow.

---

## Improvements you may describe to the panel
- **Drive-side content extraction**: download files or export Google Docs/Sheets/Slides and feed them through the same `read_text_from_file()` path to classify by content where filenames are ambiguous.
- **Rate limiting & retries**: add exponential-backoff and handle transient API errors gracefully.
- **Scope minimization**: restrict OAuth scope for least privilege if appropriate.
- **Dry-run mode**: add a `--dry` flag to preview moves before making them.

---

## Presentation tips
- Emphasize the auth flow (first-run opens a browser, token saved) and that subsequent runs reuse the token.
- Demonstrate `find_or_create_folder` to show idempotent folder creation and `move_file_to_folder` to show a safe, API-native move operation.

---

If you'd like, I can implement Drive content-based classification and a `--dry` flag now, and add a short demo script that shows how classification decisions were reached for each file.