from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from services.ingest.utils import save_uploaded_file
from services.ingest.config import UPLOAD_DIR

app = FastAPI()

@app.post("/upload")
async def upload_single_file(file: UploadFile = File(...)):
    saved_path = save_uploaded_file(UPLOAD_DIR, file)
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "saved_at": saved_path
    }

@app.get("/")
def read_root():
    return {"status": "ok"}
