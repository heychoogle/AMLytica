import os
from dotenv import load_dotenv

load_dotenv()

MIN_TRANSACTIONS = int(os.getenv("MIN_TRANSACTIONS", "30"))

OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "60.0"))

# Service addresses
EXTRACTION_IP = os.getenv("EXTRACTION_IP") or "127.0.0.1"
EXTRACTION_PORT = os.getenv("EXTRACTION_PORT") or "8003"
EXTRACTION_URL = f"http://{EXTRACTION_IP}:{EXTRACTION_PORT}"

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"