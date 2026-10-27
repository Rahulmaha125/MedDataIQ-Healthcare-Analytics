"""
MedDataIQ Configuration Module
Handles environment variables, paths, and database connection strings.
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", DATA_DIR / "raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", DATA_DIR / "processed"))
POWER_BI_EXPORT_DIR = Path(os.getenv("POWER_BI_EXPORT_DIR", DATA_DIR / "power_bi_exports"))

# Ensure directories exist
for p in [RAW_DATA_DIR, PROCESSED_DATA_DIR, POWER_BI_EXPORT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Try loading .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # Lightweight fallback parser for .env
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

# Database Settings
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "meddataiq")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", PROCESSED_DATA_DIR / "meddataiq.db"))

def get_db_url() -> str:
    """Returns the SQLAlchemy connection URL based on configuration."""
    if DB_TYPE == "postgresql":
        return f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    return f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

# Logging configuration helper
import logging

def setup_logging(name: str = "MedDataIQ") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
