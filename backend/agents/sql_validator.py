"""
IntelliOps AI - Secure SQL Validator
Validates SQL queries using AST parsing (sqlglot) to guarantee:
- Read-only analytical queries only (SELECT, CTEs, Aggregations, Joins)
- Rejection of DDL, DML, ATTACH, DETACH, PRAGMA, and Transaction control
- Single-statement enforcement
- Whitelist enforcement of approved business tables
- Protection against unauthorized access to sensitive payroll data
- Column existence validation against the live database schema
- Row limit injection and enforcement
"""

import logging
from typing import Set, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

logger = logging.getLogger(__name__)

# Approved analytical tables
APPROVED_TABLES: Set[str] = {
    "categories",
    "products",
    "customers",
    "marketing_campaigns",
    "orders",
    "order_items",
    "payments",
    "inventory",
    "customer_interactions",
    "support_tickets",
    "transactions",  # legacy read-only analytics
}

# Sensitive or internal tables strictly forbidden from analytical access
FORBIDDEN_TABLES: Set[str] = {
    "payroll",  # sensitive employee compensation
    "sqlite_master",
    "sqlite_temp_master",
    "sqlite_sequence",
    "query_audit",
    "agent_logs",
    "custom_agents",
    "user_settings",
}

# Prohibited statement types
PROHIBITED_EXP_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Pragma,
)

MAX_ROW_LIMIT = 1000


@dataclass
class ValidationResult:
    is_valid: bool
    sanitized_sql: Optional[str] = None
    error: Optional[str] = None
    tables: List[str] = field(default_factory=list)
    statement_type: str = "UNKNOWN"


class SQLValidator:
    """
    AST-based SQL Validator for safe analytical query execution.
    """

    def __init__(
        self,
        schema_metadata: Optional[Dict[str, List[str]]] = None,
        max_rows: int = MAX_ROW_LIMIT,
        allow_legacy_transactions: bool = True,
    ):
        self.schema_metadata: Dict[str, Set[str]] = (
            {tbl.lower(): {col.lower() for col in cols} for tbl, cols in schema_metadata.items()}
            if schema_metadata
            else {}
        )
        self.max_rows = max_rows
        self.approved_tables = set(APPROVED_TABLES)
        if not allow_legacy_transactions:
            self.approved_tables.discard("transactions")

    def validate(self, sql_query: str) -> ValidationResult:
        """
        Validate an SQL string against security and schema rules.
        """
        if not sql_query or not sql_query.strip():
            return ValidationResult(is_valid=False, error="Empty SQL query provided.")

        raw_sql = sql_query.strip().rstrip(";")

        # 1. Parse statement(s) using sqlglot SQLite dialect
        try:
            statements = sqlglot.parse(raw_sql, read="sqlite")
        except ParseError as pe:
            logger.warning(f"SQL parsing failed: {str(pe)}")
            return ValidationResult(is_valid=False, error=f"SQL syntax error: {str(pe)}")
        except Exception as ex:
            logger.warning(f"SQL parser error: {str(ex)}")
            return ValidationResult(is_valid=False, error=f"Malformed SQL query: {str(ex)}")

        if not statements:
            return ValidationResult(is_valid=False, error="No executable SQL statements found.")

        # 2. Reject multiple statements
        if len(statements) > 1:
            return ValidationResult(
                is_valid=False,
                error="Multiple statements are not permitted. Only single analytical queries are allowed.",
            )

        stmt = statements[0]
        if stmt is None:
            return ValidationResult(is_valid=False, error="Invalid or empty SQL statement.")

        stmt_type = type(stmt).__name__

        # 3. Permitted root statement check (must be Select or Union)
        if not isinstance(stmt, (exp.Select, exp.Union)):
            prohibited_match = self._identify_prohibited_action(stmt)
            return ValidationResult(
                is_valid=False,
                statement_type=stmt_type,
                error=f"Forbidden statement type: {prohibited_match} statements are not permitted.",
            )

        # 4. Check for nested prohibited operations (e.g. subqueries containing DDL/DML)
        for prohibited_type in PROHIBITED_EXP_TYPES:
            found = stmt.find(prohibited_type)
            if found:
                action_name = type(found).__name__.upper()
                return ValidationResult(
                    is_valid=False,
                    statement_type=stmt_type,
                    error=f"Query contains forbidden operation: {action_name}.",
                )

        # 5. Extract CTE aliases so they aren't treated as physical tables
        cte_aliases: Set[str] = set()
        for cte in stmt.find_all(exp.CTE):
            alias = cte.alias_or_name
            if alias:
                cte_aliases.add(alias.lower())

        # 6. Extract physical tables
        referenced_tables: Set[str] = set()
        table_aliases: Dict[str, str] = {}  # alias -> table_name

        for tbl_node in stmt.find_all(exp.Table):
            tbl_name = tbl_node.name.lower() if tbl_node.name else ""
            if not tbl_name:
                continue
            if tbl_name in cte_aliases:
                continue

            referenced_tables.add(tbl_name)
            if tbl_node.alias:
                table_aliases[tbl_node.alias.lower()] = tbl_name
            table_aliases[tbl_name] = tbl_name

        # Reject if no tables or only dummy tables (allow SELECT 1 for smoke tests, but table queries must be checked)
        for tbl in referenced_tables:
            # Check payroll specifically
            if tbl == "payroll":
                return ValidationResult(
                    is_valid=False,
                    statement_type=stmt_type,
                    error="Access to sensitive payroll data is strictly restricted.",
                )
            if tbl in FORBIDDEN_TABLES or tbl not in self.approved_tables:
                return ValidationResult(
                    is_valid=False,
                    statement_type=stmt_type,
                    error=f"Access to table '{tbl}' is not permitted or table does not exist in the analytical schema.",
                )

        # 7. Validate columns if schema metadata is provided
        if self.schema_metadata and referenced_tables:
            col_err = self._validate_columns(stmt, referenced_tables, table_aliases, cte_aliases)
            if col_err:
                return ValidationResult(
                    is_valid=False,
                    statement_type=stmt_type,
                    tables=sorted(referenced_tables),
                    error=col_err,
                )

        # 8. Apply row limits safely
        sanitized_sql = self._enforce_limit(stmt)

        return ValidationResult(
            is_valid=True,
            sanitized_sql=sanitized_sql,
            tables=sorted(referenced_tables),
            statement_type=stmt_type,
        )

    def _identify_prohibited_action(self, stmt: exp.Expression) -> str:
        if isinstance(stmt, exp.Insert):
            return "INSERT"
        if isinstance(stmt, exp.Update):
            return "UPDATE"
        if isinstance(stmt, exp.Delete):
            return "DELETE"
        if isinstance(stmt, exp.Drop):
            return "DROP"
        if isinstance(stmt, exp.Alter):
            return "ALTER"
        if isinstance(stmt, exp.Create):
            return "CREATE"
        if isinstance(stmt, (exp.Command, exp.Pragma)):
            return "COMMAND / PRAGMA"
        if isinstance(stmt, (exp.Transaction, exp.Commit, exp.Rollback)):
            return "TRANSACTION"
        return type(stmt).__name__.upper()

    def _validate_columns(
        self,
        stmt: exp.Expression,
        referenced_tables: Set[str],
        table_aliases: Dict[str, str],
        cte_aliases: Set[str],
    ) -> Optional[str]:
        """
        Validate referenced column names against physical schema.
        """
        # Collect aliases defined within the query (e.g. SELECT total_amount AS rev)
        defined_aliases: Set[str] = set()
        for alias_node in stmt.find_all(exp.Alias):
            if alias_node.alias:
                defined_aliases.add(alias_node.alias.lower())

        # Collect all valid physical columns across all referenced tables
        all_allowed_cols: Set[str] = set()
        for tbl in referenced_tables:
            if tbl in self.schema_metadata:
                all_allowed_cols.update(self.schema_metadata[tbl])

        for col_node in stmt.find_all(exp.Column):
            col_name = col_node.name.lower() if col_node.name else ""
            if not col_name or col_name == "*":
                continue

            # If column is an alias defined in the query or CTE, it's valid
            if col_name in defined_aliases:
                continue

            tbl_qualifier = col_node.table.lower() if col_node.table else ""

            if tbl_qualifier:
                # If qualified with a CTE alias, let SQLite handle CTE column resolution
                if tbl_qualifier in cte_aliases:
                    continue

                # Map alias to physical table
                target_table = table_aliases.get(tbl_qualifier, tbl_qualifier)
                if target_table in self.schema_metadata:
                    if col_name not in self.schema_metadata[target_table]:
                        return f"Invalid column name: '{col_name}' does not exist on table '{target_table}'."
                elif target_table not in cte_aliases:
                    return f"Unknown table or alias '{tbl_qualifier}' in column reference '{col_node.sql()}'."
            else:
                # Unqualified column: must exist in at least one referenced physical table or defined aliases
                if col_name not in all_allowed_cols and col_name not in defined_aliases:
                    return f"Invalid column name: '{col_name}' does not exist in referenced tables {sorted(referenced_tables)}."

        return None

    def _enforce_limit(self, stmt: exp.Expression) -> str:
        """
        Ensures a maximum row limit is enforced on the query.
        """
        limit_node = stmt.args.get("limit")
        if limit_node is None:
            stmt = stmt.limit(self.max_rows)
        else:
            try:
                current_limit = int(limit_node.expression.this)
                if current_limit > self.max_rows:
                    stmt = stmt.limit(self.max_rows)
            except Exception:
                stmt = stmt.limit(self.max_rows)

        return stmt.sql(dialect="sqlite")
