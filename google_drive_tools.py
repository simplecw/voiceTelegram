from googleapiclient.discovery import build
from google.auth import default
from googleapiclient.http import MediaFileUpload
import notion
import mimetypes
import os

# 要上传到的文件夹 ID
FOLDER_ID = '1XG3tm9UoYhXOTxkDSQ8GUMDN0JxC_hcn'

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

        file_id = uploaded_file['id']

        # 设置公开权限
        service.permissions().create(
            fileId=file_id,
            body={
                'role': 'reader',
                'type': 'anyone'
            }
        ).execute()
    
        # 构造可公开访问链接
        public_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        
        print(f"Uploaded: {uploaded_file['name']} (ID: {uploaded_file['id']})")
        return public_url
    except Exception as e:
        print("Upload failed:", e)
        return f"Upload failed: {e}"

def main():
    strUrl = upload_file("saved_voice/Simple_20250524_194040.ogg")
    notion.create_task(
        name="Write Notion API Guide",
        status="Not Started",
        strUrl=strUrl
    )
    return strUrl
    # return "upload_file start"
