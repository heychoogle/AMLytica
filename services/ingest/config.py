import os
from dotenv import load_dotenv

load_dotenv()
DEBUG = os.getenv("DEBUG") == "True"
UPLOAD_DIR = os.getenv("UPLOAD_DIR")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE") or 10) * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}

# Address Config
INGEST_IP = os.getenv("INGEST_IP") or "127.0.0.1"
INGEST_PORT = os.getenv("INGEST_PORT") or "8001"
INGEST_URL = "http://" + INGEST_IP + ":" + INGEST_PORT

CL_IP = os.getenv("CL_IP") or "127.0.0.1"
CL_PORT = os.getenv("CL_PORT") or "8002"
CL_URL = "http://" + CL_IP + ":" + CL_PORT


if not DEBUG and (UPLOAD_DIR == "/tmp/uploads" or not UPLOAD_DIR):
        raise RuntimeError("""
        UPLOAD_DIR must be set to a non-ephemeral directory
        Enable debug in .env if you are sure you want to do this
        """)
    