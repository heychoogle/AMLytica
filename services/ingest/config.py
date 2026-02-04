import os
from dotenv import load_dotenv

load_dotenv()
DEBUG = os.getenv("DEBUG") == "True"
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE") or 10) * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}

if not UPLOAD_DIR:
    raise RuntimeError("UPLOAD_DIR not set in .env")
    