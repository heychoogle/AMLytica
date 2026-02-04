import os
from dotenv import load_dotenv

load_dotenv()

SOFT_FLAG_EPSILON = os.getenv("SOFT_FLAG_EPSILON", 2)

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"