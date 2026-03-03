import os
import gzip
import shutil
import time
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleBackupEngine:

    def __init__(self, backup_folder="InstitutionalBackups"):

        self.backup_folder_name = backup_folder
        self.service = None
        self.folder_id = None

        # Safety controls
        self.max_retries = 3
        self.delete_retries = 3
        self.max_file_size_mb = 500  # safety cap

    # --------------------------------
    # AUTHENTICATION
    # --------------------------------
    def _authenticate(self):

        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file(
                'token.json', SCOPES
            )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return build('drive', 'v3', credentials=creds)

    # --------------------------------
    # ENSURE FOLDER EXISTS
    # --------------------------------
    def _ensure_folder(self):

        query = (
            f"name='{self.backup_folder_name}' "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])

        if files:
            return files[0]['id']

        file_metadata = {
            'name': self.backup_folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return folder.get('id')

    # --------------------------------
    # SAFE DATABASE COPY
    # --------------------------------
    def _create_safe_copy(self, original_path):

        temp_copy = original_path + ".copy"

        with open(original_path, 'rb') as src:
            with open(temp_copy, 'wb') as dst:
                shutil.copyfileobj(src, dst)

        return temp_copy

    # --------------------------------
    # COMPRESS FILE
    # --------------------------------
    def _compress_file(self, file_path):

        compressed_path = file_path + ".gz"

        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        return compressed_path

    # --------------------------------
    # SAFE DELETE
    # --------------------------------
    def _safe_delete(self, file_path):

        for _ in range(self.delete_retries):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return
            except:
                time.sleep(1)

    # --------------------------------
    # BACKUP DATABASE
    # --------------------------------
    def backup_database(self):

        file_path = "data/execution_log.db"

        if not os.path.exists(file_path):
            print("Backup skipped (no database found).")
            return

        try:

            # File size guard
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                print("Backup skipped (file too large).")
                return

            # Lazy authentication
            if not self.service:
                self.service = self._authenticate()

            if not self.folder_id:
                self.folder_id = self._ensure_folder()

            # Create safe copy (prevents SQLite lock issue)
            safe_copy = self._create_safe_copy(file_path)

            # Compress copy
            compressed_path = self._compress_file(safe_copy)

            timestamp = datetime.now(
                timezone.utc
            ).strftime("%Y%m%d_%H%M%S")

            file_name = f"backup_{timestamp}.db.gz"

            file_metadata = {
                'name': file_name,
                'parents': [self.folder_id]
            }

            media = MediaFileUpload(
                compressed_path,
                resumable=True
            )

            # Retry upload
            for attempt in range(self.max_retries):
                try:
                    file = self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()

                    print("Backup uploaded. File ID:", file.get('id'))
                    break
                except Exception as upload_error:
                    if attempt == self.max_retries - 1:
                        raise upload_error
                    time.sleep(2)

            # Cleanup temp files
            self._safe_delete(safe_copy)
            self._safe_delete(compressed_path)

        except Exception as e:
            print("Backup failed (non-critical):", str(e))
