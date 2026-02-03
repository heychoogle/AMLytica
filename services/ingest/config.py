import os
from dotenv import load_dotenv

load_dotenv()
UPLOAD_DIR = os.getenv("UPLOAD_DIR")
if not UPLOAD_DIR:
    raise RuntimeError("UPLOAD_DIR not set in .env")
