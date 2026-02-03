import os
from fastapi import UploadFile

def save_uploaded_file(upload_dir: str, file: UploadFile) -> str:
    """Save an uploaded file to the given directory and return the path."""
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, file.filename)
    with open(file_location, "wb") as f:
        content = file.file.read()
        f.write(content)
    return file_location
