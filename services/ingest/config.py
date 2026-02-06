import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG") == "True"

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
if not RABBITMQ_URL:
        raise ValueError("ERROR: RABBITMQ_URL environment variable not set")

UPLOAD_DIR = os.getenv("UPLOAD_DIR")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE") or 10) * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}

if not DEBUG and (UPLOAD_DIR == "/tmp/uploads" or not UPLOAD_DIR):
        raise RuntimeError("""
        UPLOAD_DIR must be set to a non-ephemeral directory
        Enable debug in .env if you are sure you want to do this
        """)
    