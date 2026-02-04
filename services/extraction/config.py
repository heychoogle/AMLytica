import os
from dotenv import load_dotenv

load_dotenv()

MIN_TRANSACTIONS = int(os.getenv("MIN_TRANSACTIONS", "30"))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "60.0"))

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"