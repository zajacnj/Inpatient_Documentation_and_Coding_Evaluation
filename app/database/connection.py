"""
Database Connection Management for Inpatient Documentation Evaluation
Handles VA SQL Server connections with Windows/SSPI authentication.
"""

import pyodbc
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connections with retry logic."""

    def __init__(
        self,
        server: str,
        database: str,
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize connection parameters.

        Args:
            server: SQL Server hostname or IP
            database: Database name
            timeout: Connection timeout in seconds (default 300s for large operations)
            max_retries: Maximum connection retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        self.server = server
        self.database = database
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Connect to database with retry logic and exponential backoff.
        Uses Windows Authentication (SSPI) for VA network security.

        Returns:
            True if successful, False otherwise
        """
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"Trusted_Connection=yes;"
            f"timeout={self.timeout}"
        )

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Connecting to {self.server}.{self.database} (attempt {attempt + 1}/{self.max_retries})")

                self.connection = pyodbc.connect(connection_string)
                self.is_connected = True

                logger.info(f"Connected to {self.server}.{self.database}")
                return True

            except pyodbc.Error as e:
                logger.warning(
                    f"Connection attempt {attempt + 1}/{self.max_retries} failed: {str(e)}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect after {self.max_retries} attempts")
                    self.is_connected = False
                    return False

        return False

    def disconnect(self) -> None:
        """Disconnect from database."""
        if self.connection:
            try:
                self.connection.close()
                self.is_connected = False
                logger.info(f"Disconnected from {self.server}.{self.database}")
            except Exception as e:
                logger.warning(f"Error disconnecting: {str(e)}")

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute query with error handling.

        Args:
            query: SQL query string
            params: Optional query parameters
            timeout: Optional query timeout (overrides connection timeout)

        Returns:
            Dict with keys: success, rows, columns, row_count, error
        """
        if not self.connection or not self.is_connected:
            logger.error("Database not connected")
            return {
                "success": False,
                "error": "Database not connected",
                "rows": [],
                "columns": [],
                "row_count": 0
            }

        try:
            cursor = self.connection.cursor()

            # Set query timeout if specified
            if timeout:
                cursor.timeout = timeout

            # Execute query
            if params:
                logger.debug(f"Executing query: {query[:100]}... with {len(params)} params")
                cursor.execute(query, params)
            else:
                logger.debug(f"Executing query: {query[:100]}...")
                cursor.execute(query)

            # Fetch results
            results = cursor.fetchall()

            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert rows to list of dicts for JSON serialization
            rows = [dict(zip(columns, row)) for row in results]

            cursor.close()

            logger.info(f"Query completed successfully, {len(results)} rows returned")
            return {
                "success": True,
                "rows": rows,
                "columns": columns,
                "row_count": len(rows),
                "error": None
            }

        except pyodbc.Error as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "columns": [],
                "row_count": 0
            }
        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "columns": [],
                "row_count": 0
            }

    def execute_query_large(
        self,
        query: str,
        params: Optional[tuple] = None,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute query with batched fetching for large result sets.
        Useful for extracting large amounts of clinical documentation.

        Args:
            query: SQL query string
            params: Optional query parameters
            batch_size: Number of rows to fetch at a time

        Returns:
            Dict with keys: success, rows, columns, row_count, error
        """
        if not self.connection or not self.is_connected:
            return {
                "success": False,
                "error": "Database not connected",
                "rows": [],
                "columns": [],
                "row_count": 0
            }

        try:
            cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            all_rows = []
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                all_rows.extend([dict(zip(columns, row)) for row in batch])
                logger.debug(f"Fetched {len(all_rows)} rows so far...")

            cursor.close()

            logger.info(f"Large query completed, {len(all_rows)} total rows")
            return {
                "success": True,
                "rows": all_rows,
                "columns": columns,
                "row_count": len(all_rows),
                "error": None
            }

        except Exception as e:
            logger.error(f"Large query failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "columns": [],
                "row_count": 0
            }

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def load_database_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load database configuration from JSON file.

    Args:
        config_file: Path to config file or None for default

    Returns:
        Database configuration dictionary
    """
    if not config_file:
        config_file = str(Path(__file__).parent.parent.parent / "config" / "database_config.json")

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Database config not found at {config_file}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in database config: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error loading database config: {str(e)}")
        return {}


def get_database_connection(config: Dict[str, Any]) -> Optional[DatabaseConnection]:
    """
    Factory function to create database connection from config.

    Args:
        config: Database configuration dictionary with keys: server, database

    Returns:
        DatabaseConnection instance or None if config invalid
    """
    server = config.get("server")
    database = config.get("database")

    if not server or not database:
        logger.error("Database config missing 'server' or 'database' keys")
        return None

    connection = DatabaseConnection(
        server=server,
        database=database,
        timeout=config.get("timeout", 300),
        max_retries=config.get("max_retries", 3)
    )

    if connection.connect():
        return connection
    else:
        return None
