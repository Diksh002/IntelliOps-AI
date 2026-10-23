"""
IntelliOps AI - Secure Read-Only SQL Executor
Manages read-only SQLite connections, strict query execution timeouts,
and structured analytical result formatting.
"""

import os
import time
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from agents.sql_validator import SQLValidator, ValidationResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0


def resolve_database_path(db_path: Optional[str] = None) -> str:
    """
    Resolve and validate the SQLite database path.
    Guarantees the file exists before connecting to prevent accidental
    creation of empty databases from relative path errors.
    """
    if db_path:
        candidate = os.path.abspath(db_path)
    else:
        env_path = os.getenv("DATASCOUT_DB_PATH")
        if env_path:
            candidate = os.path.abspath(env_path)
        else:
            # Check relative to backend directory or project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate = os.path.join(base_dir, "datascout.db")
            if not os.path.isfile(candidate):
                # Fallback to CWD
                candidate = os.path.abspath("datascout.db")

    if not os.path.isfile(candidate):
        raise FileNotFoundError(
            f"Database file not found at '{candidate}'. "
            f"Connection aborted to prevent creating an empty database."
        )

    return candidate


def get_readonly_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establish a strictly read-only SQLite connection using URI mode=ro
    and SQLite query-only pragma.
    """
    resolved_path = resolve_database_path(db_path)
    uri = f"file:{resolved_path}?mode=ro"
    
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    return conn


def get_database_schema(db_path: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Retrieve live schema metadata (table name -> column list) using a read-only connection.
    """
    conn = get_readonly_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema: Dict[str, List[str]] = {}
        for tbl in tables:
            cursor.execute(f"PRAGMA table_info({tbl});")
            cols = [row[1] for row in cursor.fetchall()]
            schema[tbl] = cols
        return schema
    finally:
        conn.close()


def execute_analytical_query(
    sql_query: str,
    db_path: Optional[str] = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    validator: Optional[SQLValidator] = None,
) -> Dict[str, Any]:
    """
    Execute an analytical query through validation and read-only connection.
    Returns a structured dictionary with success status, rows, columns, and metrics.
    """
    start_time = time.perf_counter()

    # 1. Initialize or use validator
    try:
        if validator is None:
            schema = get_database_schema(db_path)
            validator = SQLValidator(schema_metadata=schema)
    except Exception as ex:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Failed to load schema for validator: {str(ex)}")
        return {
            "success": False,
            "sql_query": sql_query,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_duration_ms": duration_ms,
            "error": f"Schema initialization error: {str(ex)}",
            "data": [],
        }

    # 2. Validate SQL
    val_res: ValidationResult = validator.validate(sql_query)
    if not val_res.is_valid:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning(f"SQL validation rejected query: {val_res.error}")
        return {
            "success": False,
            "sql_query": sql_query,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_duration_ms": duration_ms,
            "error": val_res.error,
            "data": [],
        }

    sanitized_sql = val_res.sanitized_sql or sql_query

    # 3. Execute in read-only connection with timeout
    conn = None
    try:
        conn = get_readonly_connection(db_path)

        # Set progress handler for timeout
        exec_start = time.perf_counter()
        def timeout_handler():
            if time.perf_counter() - exec_start > timeout_seconds:
                return 1  # Interrupt SQLite execution
            return 0

        # Check timeout every 50 virtual machine instructions
        conn.set_progress_handler(timeout_handler, 50)

        cursor = conn.cursor()
        cursor.execute(sanitized_sql)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        fetched_rows = cursor.fetchall()
        rows = [dict(zip(columns, row)) for row in fetched_rows]
        row_count = len(rows)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "success": True,
            "sql_query": sanitized_sql,
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
            "execution_duration_ms": duration_ms,
            "error": None,
            "data": rows,
        }

    except sqlite3.OperationalError as oe:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = str(oe)
        if "interrupted" in err_msg.lower():
            err_msg = f"Query timed out after {timeout_seconds} seconds."
        elif "readonly" in err_msg.lower():
            err_msg = "Database access violation: Attempted modification on a read-only database."
        logger.error(f"SQL operational error: {err_msg}")
        return {
            "success": False,
            "sql_query": sanitized_sql,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_duration_ms": duration_ms,
            "error": err_msg,
            "data": [],
        }

    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Query execution error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "sql_query": sanitized_sql,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_duration_ms": duration_ms,
            "error": f"Database execution error: {str(e)}",
            "data": [],
        }

    finally:
        if conn:
            conn.close()
