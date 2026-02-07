import os
import time

def save_uploaded_file(upload_dir: str, filename: str, content: bytes) -> str:

    os.makedirs(upload_dir, exist_ok=True)
    
    # sanitise filename
    safe_filename = os.path.basename(filename)
    
    # filename sanity check, if somehow still empty or just "."
    if not safe_filename or safe_filename == ".":
        safe_filename = "uploaded_file" + time.time()
    
    file_location = os.path.join(upload_dir, safe_filename)
    
    with open(file_location, "wb") as f:
        f.write(content)
    
    return file_location