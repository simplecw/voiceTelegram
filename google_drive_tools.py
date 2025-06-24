from googleapiclient.discovery import build
from google.auth import default
from googleapiclient.http import MediaFileUpload
import mimetypes
import os

# 要上传到的文件夹 ID
FOLDER_ID = 'https://drive.google.com/drive/folders/1XG3tm9UoYhXOTxkDSQ8GUMDN0JxC_hcn'

def upload_file(file_path, folder_id=FOLDER_ID):
    try:
        print("upload_file Start2")
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
        
        # 创建 Drive 客户端
        service = build("drive", "v3", credentials=credentials)
        
        file_name = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_path)[0]
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, mimetype=mime_type)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        print(f"Uploaded: {uploaded_file['name']} (ID: {uploaded_file['id']})")
        return "Upload success"
    except Exception as e:
        print("Upload failed:", e)
        return f"Upload failed: {e}"

def main():
    return upload_file("saved_voice/Simple_20250524_193820.ogg")
    # return "upload_file start"
