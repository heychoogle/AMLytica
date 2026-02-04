import os
from dotenv import load_dotenv

load_dotenv()
DEBUG = os.getenv("DEBUG") == "True"

# Address Config
ORCH_IP = os.getenv("ORCH_IP") or "127.0.0.1"
ORCH_PORT = os.getenv("ORCH_PORT") or "8001"
ORCH_URL = "http://" + ORCH_IP + ":" + ORCH_PORT

INGEST_IP = os.getenv("INGEST_IP") or "127.0.0.1"
INGEST_PORT = os.getenv("INGEST_PORT") or "8002"
INGEST_URL = "http://" + INGEST_IP + ":" + INGEST_PORT

CL_IP = os.getenv("CL_IP") or "127.0.0.1"
CL_PORT = os.getenv("CL_PORT") or "8003"
CL_URL = "http://" + CL_IP + ":" + CL_PORT

EXTRACTION_IP = os.getenv("EXTRACTION_IP") or "127.0.0.1"
EXTRACTION_PORT = os.getenv("EXTRACTION_PORT") or "8004"
EXTRACTION_URL = "http://" + EXTRACTION_IP + ":" + EXTRACTION_PORT

ANALYSIS_IP = os.getenv("ANALYSIS_IP") or "127.0.0.1"
ANALYSIS_PORT = os.getenv("ANALYSIS_PORT") or "8005"
ANALYSIS_URL = "http://" + ANALYSIS_IP + ":" + ANALYSIS_PORT

REPORT_IP = os.getenv("REPORT_IP") or "127.0.0.1"
REPORT_PORT = os.getenv("REPORT_PORT") or "8006"
REPORT_URL = "http://" + REPORT_IP + ":" + REPORT_PORT