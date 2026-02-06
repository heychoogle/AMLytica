import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
if not RABBITMQ_URL:
	raise ValueError("ERROR: RABBITMQ_URL environment variable not set")
INPUT_QUEUE = os.getenv("EXTRACTED_DATA_QUEUE")
OUTPUT_QUEUE = os.getenv("ANALYSIS_RESULTS_QUEUE")

SOFT_FLAG_EPSILON = float(os.getenv("SOFT_FLAG_EPSILON", 2))

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"