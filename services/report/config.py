import os
from dotenv import load_dotenv

load_dotenv()

#

# Debug mode
DEBUG = os.getenv("DEBUG") == "True"