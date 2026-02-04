from fastapi import FastAPI, File, UploadFile, HTTPException
from services.ingest.utils import save_uploaded_file
from services.ingest.config import UPLOAD_DIR, DEBUG, MAX_FILE_SIZE, ALLOWED_TYPES

app = FastAPI()

@app.post("/upload")
async def upload_single_file(file: UploadFile = File(...)):
    
    # validate file type
    mime_type = file.content_type.split(";")[0].lower()
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {mime_type}. Allowed types: {ALLOWED_TYPES}"
        )
    
    # read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE/1024/1024}MB)")
    
    # Save file
    saved_path = save_uploaded_file(UPLOAD_DIR, file.filename, content)
    
    if DEBUG:
        print(f''' 
        File Uploaded
        File name: {file.filename}
        Content type: {file.content_type}
        Saved at: {saved_path}
        Size: {len(content)} bytes
        ''')
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "saved_at": saved_path,
        "size_bytes": len(content)
    }

@app.get("/")
def read_root():
    return {"status": "ok"}