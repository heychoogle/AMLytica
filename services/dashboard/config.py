import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG") == "True"

REFRESH_INTERVAL = os.getenv("DASHBOARD_REFRESH_INTERVAL", 5)
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")