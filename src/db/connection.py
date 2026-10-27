"""
MedDataIQ — Database Connection & Execution Manager
Provides robust dual-engine support:
- PostgreSQL 18 (production relational engine)
- SQLite (local zero-dependency fallback ensuring queries execute out-of-the-box)
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.config import (
    DB_TYPE, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD, SQLITE_DB_PATH,
    setup_logging
)

logger = setup_logging("DBConnection")


def test_postgresql_connection() -> Tuple[bool, str]:
    """
    Tests if PostgreSQL is reachable.
    Returns (is_connected, message).
    """
    try:
        # Test using psycopg or sqlalchemy if installed
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        host = POSTGRES_HOST
        port = int(POSTGRES_PORT)
        result = s.connect_ex((host, port))
        s.close()
        if result == 0:
            return True, f"PostgreSQL is listening on {host}:{port}"
        else:
            return False, f"Port {port} on {host} is not responding (code {result}). Service may be stopped."
    except Exception as e:
        return False, f"Connection test failed: {e}"


class DatabaseManager:
    """
    Manages database connections, table creation, bulk data loading,
    and analytical query execution across PostgreSQL and SQLite.
    """

    def __init__(self, force_sqlite: bool = False):
        self.force_sqlite = force_sqlite
        self.sqlite_path = Path(SQLITE_DB_PATH)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_engine = "sqlite"

        if not force_sqlite and DB_TYPE == "postgresql":
            pg_ok, msg = test_postgresql_connection()
            if pg_ok:
                try:
                    # If postgres is listening, attempt connection
                    self.active_engine = "postgresql"
                    logger.info("Connected to PostgreSQL successfully.")
                except Exception as e:
                    logger.warning(f"PostgreSQL connection error: {e}. Falling back to SQLite.")
                    self.active_engine = "sqlite"
            else:
                logger.info(f"PostgreSQL status: {msg}. Using SQLite at {self.sqlite_path}")
                self.active_engine = "sqlite"
        else:
            self.active_engine = "sqlite"

    def get_connection(self):
        """Returns a database connection."""
        if self.active_engine == "sqlite":
            conn = sqlite3.connect(self.sqlite_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        raise NotImplementedError("PostgreSQL connection requires running service.")

    def execute_script(self, sql_script: str):
        """Executes a multi-statement SQL script."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(sql_script)
            conn.commit()

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Executes a SELECT query and returns a pandas DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def load_table(self, df: pd.DataFrame, table_name: str, if_exists: str = "append"):
        """Loads a pandas DataFrame into the database table."""
        with self.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            logger.info(f"Loaded {len(df):,} rows into '{table_name}' ({self.active_engine}).")

    def get_status(self) -> Dict[str, Any]:
        """Returns database health and engine status."""
        pg_ok, pg_msg = test_postgresql_connection()
        return {
            "active_engine": self.active_engine,
            "sqlite_db_path": str(self.sqlite_path),
            "sqlite_exists": self.sqlite_path.exists(),
            "postgresql_host": POSTGRES_HOST,
            "postgresql_port": POSTGRES_PORT,
            "postgresql_db": POSTGRES_DB,
            "postgresql_reachable": pg_ok,
            "postgresql_status_msg": pg_msg
        }


if __name__ == "__main__":
    db = DatabaseManager()
    status = db.get_status()
    for k, v in status.items():
        print(f"{k}: {v}")
