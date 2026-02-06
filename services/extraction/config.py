import os
from dotenv import load_dotenv

load_dotenv()


CL_IP = os.getenv("CL_IP") or "customer_lookup"
CL_PORT = os.getenv("CL_PORT") or "8001"
CL_URL = "http://" + CL_IP + ":" + CL_PORT

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
if not RABBITMQ_URL:
	raise ValueError("ERROR: RABBITMQ_URL environment variable not set")
INPUT_QUEUE = os.getenv("RAW_EXTRACTION_QUEUE")
OUTPUT_QUEUE = os.getenv("EXTRACTED_DATA_QUEUE")

MIN_TRANSACTIONS = int(os.getenv("MIN_TRANSACTIONS", "30"))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "60.0"))

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"