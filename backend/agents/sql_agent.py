"""
IntelliOps AI - Secure Natural-Language SQL Agent
Phase 5 Architecture:
- Schema context across 10 normalized business tables + legacy transactions
- Strict SQL validation layer (sqlglot AST) rejecting DDL, DML, ATTACH, DETACH, and multi-statements
- Separate read-only database connections (mode=ro + PRAGMA query_only)
- Execution timeouts and row-count limits
- Accurate business metrics calculation (avoiding double-counting, status filtering)
- Resilient operation when OpenAI credentials are not configured
- Deterministic analytical benchmark queries
- Structured result formatting for API, chat, and visualizer
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from agents.sql_validator import SQLValidator, ValidationResult
from agents.sql_executor import (
    resolve_database_path,
    get_readonly_connection,
    get_database_schema,
    execute_analytical_query,
)

logger = logging.getLogger(__name__)

# Complete schema description provided to LLMs
DATABASE_SCHEMA_DESCRIPTION = """
IntelliOps AI Business Database Schema (SQLite 3):

1. categories (id INTEGER PK, name TEXT UNIQUE, description TEXT, created_at TEXT)
2. products (id INTEGER PK, sku TEXT UNIQUE, name TEXT, category_id INTEGER FK -> categories(id), unit_price REAL, unit_cost REAL, status TEXT CHECK ('active', 'discontinued', 'upcoming'), created_at TEXT)
3. customers (id INTEGER PK, customer_code TEXT UNIQUE, company_name TEXT, contact_name TEXT, email TEXT UNIQUE, region TEXT CHECK ('NA', 'EMEA', 'APAC', 'LATAM'), tier TEXT CHECK ('Enterprise', 'Mid-Market', 'SMB'), industry TEXT, signup_date TEXT, is_active INTEGER CHECK (0, 1))
4. marketing_campaigns (id INTEGER PK, name TEXT, channel TEXT CHECK ('Email', 'Search / PPC', 'Social Media', 'Webinar / Event', 'Direct Outreach', 'Partner Referral'), budget REAL, spend REAL, start_date TEXT, end_date TEXT, target_region TEXT, status TEXT)
5. orders (id INTEGER PK, order_number TEXT UNIQUE, customer_id INTEGER FK -> customers(id), campaign_id INTEGER FK -> marketing_campaigns(id), order_date TEXT, subtotal REAL, discount REAL, tax REAL, total_amount REAL, status TEXT CHECK ('completed', 'pending', 'cancelled', 'refunded'), created_at TEXT)
6. order_items (id INTEGER PK, order_id INTEGER FK -> orders(id), product_id INTEGER FK -> products(id), quantity INTEGER, unit_price REAL, discount REAL, total_price REAL)
7. payments (id INTEGER PK, payment_number TEXT UNIQUE, order_id INTEGER FK -> orders(id), payment_date TEXT, amount REAL, payment_method TEXT, status TEXT CHECK ('completed', 'pending', 'failed', 'refunded'))
8. inventory (id INTEGER PK, product_id INTEGER FK -> products(id), warehouse_region TEXT CHECK ('NA', 'EMEA', 'APAC', 'LATAM'), stock_on_hand INTEGER, reorder_point INTEGER, safety_stock INTEGER, last_restocked_date TEXT)
9. customer_interactions (id INTEGER PK, customer_id INTEGER FK -> customers(id), interaction_date TEXT, channel TEXT, interaction_type TEXT, notes TEXT)
10. support_tickets (id INTEGER PK, ticket_number TEXT UNIQUE, customer_id INTEGER FK -> customers(id), product_id INTEGER FK -> products(id), created_date TEXT, resolved_date TEXT, category TEXT, priority TEXT, status TEXT CHECK ('open', 'in_progress', 'resolved', 'closed'), resolution_time_hours REAL, customer_satisfaction INTEGER)
11. transactions (id INTEGER PK, transaction_id TEXT, date TEXT, amount REAL, category TEXT, status TEXT, account_id TEXT, description TEXT) [Legacy analytical table]

BUSINESS METRIC RULES:
- Revenue: Calculated exclusively on completed orders: `status = 'completed'` in `orders`.
- Do not double-count revenue: If joining orders with order_items or payments, do NOT sum orders.total_amount directly across joined rows. For product-level revenue, sum `order_items.total_price`. For order-level revenue, sum `orders.total_amount`.
- Cancelled or refunded orders (`status IN ('cancelled', 'refunded')`) must NOT be counted as revenue or completed sales.
- Average Order Value (AOV): `AVG(total_amount)` for `orders WHERE status = 'completed'`.
- Dataset Date Range: 2024-01-01 to 2025-12-31. When asked about "last month", the latest completed month in the operational dataset is December 2025 ('2025-12').
- Sensitive Payroll table is strictly restricted and cannot be queried.
"""

# SQL statement keywords that indicate direct SQL
DIRECT_SQL_KEYWORDS = (
    "SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "ATTACH", "DETACH", "PRAGMA", "BEGIN", "COMMIT", "ROLLBACK", "EXPLAIN"
)

# Deterministic Benchmark Analytical Queries
BENCHMARK_QUERIES: List[Tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"revenue.*last month|last month.*revenue", re.IGNORECASE),
        "What was our revenue last month?",
        """
        SELECT strftime('%Y-%m', order_date) AS month,
               ROUND(SUM(total_amount), 2) AS monthly_revenue,
               COUNT(id) AS completed_orders
        FROM orders
        WHERE status = 'completed' AND order_date >= '2025-12-01' AND order_date <= '2025-12-31'
        GROUP BY month;
        """,
    ),
    (
        re.compile(r"products.*(most|top).*revenue|(most|top).*revenue.*products", re.IGNORECASE),
        "Which products generated the most revenue?",
        """
        SELECT p.id, p.name, p.sku,
               ROUND(SUM(oi.total_price), 2) AS total_revenue,
               SUM(oi.quantity) AS total_units_sold
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'completed'
        GROUP BY p.id, p.name, p.sku
        ORDER BY total_revenue DESC
        LIMIT 10;
        """,
    ),
    (
        re.compile(r"compare revenue.*regions?|revenue.*(across|by).*regions?", re.IGNORECASE),
        "Compare revenue across regions.",
        """
        SELECT c.region,
               ROUND(SUM(o.total_amount), 2) AS regional_revenue,
               COUNT(DISTINCT c.id) AS customer_count,
               COUNT(o.id) AS completed_orders
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.status = 'completed'
        GROUP BY c.region
        ORDER BY regional_revenue DESC;
        """,
    ),
    (
        re.compile(r"customers.*not ordered recently|inactive customers|customer recency", re.IGNORECASE),
        "Which customers have not ordered recently?",
        """
        SELECT c.customer_code, c.company_name, c.region, c.tier,
               MAX(o.order_date) AS last_order_date,
               CAST(ROUND(JULIANDAY('2025-12-31') - JULIANDAY(MAX(o.order_date))) AS INT) AS days_inactive
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY c.id, c.customer_code, c.company_name, c.region, c.tier
        ORDER BY days_inactive DESC
        LIMIT 10;
        """,
    ),
    (
        re.compile(r"average order value|aov", re.IGNORECASE),
        "What is our average order value?",
        """
        SELECT ROUND(AVG(total_amount), 2) AS avg_order_value,
               ROUND(SUM(total_amount), 2) AS total_revenue,
               COUNT(id) AS total_completed_orders
        FROM orders
        WHERE status = 'completed';
        """,
    ),
    (
        re.compile(r"reorder points?|inventory.*shortages?|approaching.*reorder", re.IGNORECASE),
        "Which products are approaching their reorder points?",
        """
        SELECT p.sku, p.name, i.warehouse_region,
               i.stock_on_hand, i.reorder_point, i.safety_stock,
               (i.stock_on_hand - i.reorder_point) AS buffer_to_reorder
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        ORDER BY buffer_to_reorder ASC
        LIMIT 10;
        """,
    ),
    (
        re.compile(r"monthly.*demand|product demand.*chang(ed?|ing)|demand.*chang(ed?|ing)", re.IGNORECASE),
        "How has monthly product demand changed?",
        """
        SELECT strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity) AS total_units_demanded,
               COUNT(DISTINCT o.id) AS total_orders
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'completed'
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12;
        """,
    ),
    (
        re.compile(r"campaign.*(most|top).*revenue|attributed revenue|campaign.*roas", re.IGNORECASE),
        "Which marketing campaigns generated the most attributed revenue?",
        """
        SELECT mc.id, mc.name, mc.channel, mc.spend,
               COUNT(o.id) AS attributed_orders,
               ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS attributed_revenue,
               ROUND(COALESCE(SUM(o.total_amount), 0) / mc.spend, 2) AS roas
        FROM marketing_campaigns mc
        LEFT JOIN orders o ON mc.id = o.campaign_id AND o.status = 'completed'
        GROUP BY mc.id, mc.name, mc.channel, mc.spend
        ORDER BY attributed_revenue DESC
        LIMIT 10;
        """,
    ),
    (
        re.compile(r"compare enterprise and smb|enterprise.*smb|smb.*enterprise", re.IGNORECASE),
        "Compare enterprise and SMB customers.",
        """
        SELECT c.tier,
               COUNT(DISTINCT c.id) AS customer_count,
               COUNT(o.id) AS completed_orders,
               ROUND(AVG(o.total_amount), 2) AS avg_order_value,
               ROUND(SUM(o.total_amount), 2) AS total_revenue
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id AND o.status = 'completed'
        WHERE c.tier IN ('Enterprise', 'SMB')
        GROUP BY c.tier
        ORDER BY total_revenue DESC;
        """,
    ),
    (
        re.compile(r"monthly revenue.*12 months|revenue.*last 12 months", re.IGNORECASE),
        "Show monthly revenue for the last 12 months.",
        """
        SELECT strftime('%Y-%m', order_date) AS month,
               ROUND(SUM(total_amount), 2) AS monthly_revenue,
               COUNT(id) AS order_count
        FROM orders
        WHERE status = 'completed'
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12;
        """,
    ),
]


class SQLAgent:
    """
    Secure SQL Agent for analytical business intelligence.
    Supports natural language querying, direct SQL execution, AST-based validation,
    read-only database isolation, and structured result returns.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = resolve_database_path(db_path)
        self.schema = get_database_schema(self.db_path)
        self.validator = SQLValidator(schema_metadata=self.schema)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.is_openai_configured = self._check_api_key_validity(self.api_key)

    @staticmethod
    def _check_api_key_validity(key: Optional[str]) -> bool:
        if not key:
            return False
        clean = key.strip()
        if clean.startswith("your-") or clean.startswith("sk-placeholder") or "your-key" in clean:
            return False
        return clean.startswith("sk-") or clean.startswith("sk-proj-")

    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Directly execute a validated analytical SQL query against the read-only database.
        """
        return execute_analytical_query(
            sql_query=sql_query,
            db_path=self.db_path,
            validator=self.validator,
        )

    def query(self, user_question: str, return_data: bool = True) -> Dict[str, Any]:
        """
        Process a user question or direct SQL query.
        
        Workflow:
        1. Direct SQL detection -> validate -> execute -> format
        2. Benchmark query matching -> validate -> execute -> format
        3. LLM-based generation (if OpenAI configured) -> validate -> execute -> format
        4. Graceful configuration requirement message (if LLM not configured)
        """
        cleaned_question = user_question.strip()
        upper_q = cleaned_question.upper()
        logger.info(f"SQLAgent processing query: {cleaned_question}")

        # Check if input is a direct SQL query or command
        first_token = upper_q.split()[0].rstrip(";") if upper_q.split() else ""
        if first_token in DIRECT_SQL_KEYWORDS:
            exec_result = self.execute_sql(cleaned_question)
            if not exec_result["success"]:
                return {
                    "success": False,
                    "answer": f"Query Validation / Execution Error: {exec_result['error']}",
                    "sql_query": exec_result.get("sql_query"),
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "execution_duration_ms": exec_result.get("execution_duration_ms", 0),
                    "error": exec_result["error"],
                    "data": [],
                }
            answer = self._synthesize_answer_from_rows(
                user_question="Direct SQL Query",
                sql_query=exec_result["sql_query"],
                columns=exec_result["columns"],
                rows=exec_result["rows"],
            )
            self._audit_log(cleaned_question, answer)
            return {
                "success": True,
                "answer": answer,
                "sql_query": exec_result["sql_query"],
                "columns": exec_result["columns"],
                "rows": exec_result["rows"],
                "row_count": exec_result["row_count"],
                "execution_duration_ms": exec_result["execution_duration_ms"],
                "error": None,
                "data": exec_result["rows"] if return_data else [],
            }

        # Check benchmark queries
        for pattern, label, sql in BENCHMARK_QUERIES:
            if pattern.search(cleaned_question):
                logger.info(f"Matched benchmark analytical template: '{label}'")
                exec_result = self.execute_sql(sql)
                if not exec_result["success"]:
                    return {
                        "success": False,
                        "answer": f"Error executing benchmark query: {exec_result['error']}",
                        "sql_query": sql,
                        "columns": [],
                        "rows": [],
                        "row_count": 0,
                        "execution_duration_ms": exec_result.get("execution_duration_ms", 0),
                        "error": exec_result["error"],
                        "data": [],
                    }
                answer = self._synthesize_answer_from_rows(
                    user_question=cleaned_question,
                    sql_query=exec_result["sql_query"],
                    columns=exec_result["columns"],
                    rows=exec_result["rows"],
                )
                self._audit_log(cleaned_question, answer, exec_result["sql_query"])
                return {
                    "success": True,
                    "answer": answer,
                    "sql_query": exec_result["sql_query"],
                    "columns": exec_result["columns"],
                    "rows": exec_result["rows"],
                    "row_count": exec_result["row_count"],
                    "execution_duration_ms": exec_result["execution_duration_ms"],
                    "error": None,
                    "data": exec_result["rows"] if return_data else [],
                }

        # Check if LLM is configured for general natural-language SQL generation
        if not self.is_openai_configured:
            msg = (
                "OpenAI API key is not configured. Natural language SQL generation for arbitrary queries "
                "requires a valid OPENAI_API_KEY in backend/.env. Direct SQL execution and predefined "
                "analytical benchmarks remain fully operational."
            )
            logger.warning(msg)
            return {
                "success": False,
                "answer": msg,
                "sql_query": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_duration_ms": 0,
                "error": "Missing or placeholder OPENAI_API_KEY",
                "data": [],
            }

        # LLM-based SQL generation workflow
        try:
            generated_sql = self._generate_sql_via_llm(cleaned_question)
            exec_result = self.execute_sql(generated_sql)
            if not exec_result["success"]:
                return {
                    "success": False,
                    "answer": f"Generated SQL was rejected by validation or database: {exec_result['error']}",
                    "sql_query": generated_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "execution_duration_ms": exec_result.get("execution_duration_ms", 0),
                    "error": exec_result["error"],
                    "data": [],
                }

            answer = self._synthesize_answer_from_rows(
                user_question=cleaned_question,
                sql_query=exec_result["sql_query"],
                columns=exec_result["columns"],
                rows=exec_result["rows"],
            )
            self._audit_log(cleaned_question, answer, exec_result["sql_query"])

            return {
                "success": True,
                "answer": answer,
                "sql_query": exec_result["sql_query"],
                "columns": exec_result["columns"],
                "rows": exec_result["rows"],
                "row_count": exec_result["row_count"],
                "execution_duration_ms": exec_result["execution_duration_ms"],
                "error": None,
                "data": exec_result["rows"] if return_data else [],
            }

        except Exception as e:
            logger.error(f"Natural language SQL workflow error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "answer": f"Failed to process natural language query: {str(e)}",
                "sql_query": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_duration_ms": 0,
                "error": str(e),
                "data": [],
            }

    def _generate_sql_via_llm(self, question: str) -> str:
        """
        Generate SQL from natural language using OpenAI.
        """
        import httpx

        system_prompt = (
            "You are a principal SQL engineer for SQLite 3. "
            "Write ONLY a single valid, read-only SELECT or WITH statement answering the user's question. "
            "Output RAW SQL ONLY, without markdown code fences, comments, or explanations.\n\n"
            f"{DATABASE_SCHEMA_DESCRIPTION}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.0,
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_sql = data["choices"][0]["message"]["content"].strip()

        # Clean markdown wrappers if returned
        clean_sql = re.sub(r"^```(?:sql)?\n", "", raw_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r"\n```$", "", clean_sql).strip()
        return clean_sql

    def _synthesize_answer_from_rows(
        self,
        user_question: str,
        sql_query: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
    ) -> str:
        """
        Synthesize a factual, concise natural-language answer based strictly on returned rows.
        Does not fabricate or extrapolate information.
        """
        if not rows:
            return "The database query completed successfully, but returned 0 rows matching the specified criteria."

        # Handle specific common metrics
        row_0 = rows[0]
        # Monthly revenue
        if "monthly_revenue" in row_0 and "month" in row_0 and len(rows) == 1:
            m = row_0["month"]
            rev = f"${row_0['monthly_revenue']:,.2f}"
            orders = row_0.get("completed_orders", "N/A")
            return f"In {m}, total revenue from completed orders was {rev} across {orders} orders."

        # Top products
        if "total_revenue" in row_0 and "name" in row_0:
            lines = []
            for i, r in enumerate(rows[:5], 1):
                name = r.get("name", "Unknown")
                sku = r.get("sku", "")
                rev = f"${r.get('total_revenue', 0):,.2f}"
                units = r.get("total_units_sold") or r.get("units_sold", 0)
                sku_str = f" ({sku})" if sku else ""
                lines.append(f"{i}. {name}{sku_str}: {rev} ({units} units sold)")
            return "Top products by generated revenue:\n" + "\n".join(lines)

        # Regional revenue
        if "regional_revenue" in row_0 and "region" in row_0:
            parts = []
            for r in rows:
                reg = r.get("region", "N/A")
                rev = f"${r.get('regional_revenue', 0):,.2f}"
                custs = r.get("customer_count") or r.get("active_customers", "")
                cust_str = f" ({custs} customers)" if custs else ""
                parts.append(f"{reg}: {rev}{cust_str}")
            return "Revenue breakdown across regions: " + ", ".join(parts) + "."

        # Inactive customers
        if "days_inactive" in row_0 and "company_name" in row_0:
            lines = []
            for i, r in enumerate(rows[:5], 1):
                company = r.get("company_name", "N/A")
                code = r.get("customer_code", "")
                days = r.get("days_inactive", 0)
                last_dt = r.get("last_order_date", "")
                lines.append(f"{i}. {company} ({code}): {days} days inactive (Last order: {last_dt})")
            return "Customers with longest inactivity since last order:\n" + "\n".join(lines)

        # Average order value
        if "avg_order_value" in row_0 and len(rows) == 1:
            aov = f"${row_0.get('avg_order_value', 0):,.2f}"
            tot_rev = f"${row_0.get('total_revenue', 0):,.2f}" if "total_revenue" in row_0 else None
            orders = row_0.get("total_completed_orders") or row_0.get("completed_orders")
            ans = f"The average order value (AOV) across completed orders is {aov}"
            if orders:
                ans += f" across {orders} completed orders"
            if tot_rev:
                ans += f" (Total Revenue: {tot_rev})"
            return ans + "."

        # Customer tier comparison
        if "tier" in row_0 and ("avg_order_value" in row_0 or "total_revenue" in row_0):
            lines = []
            for r in rows:
                tier = r.get("tier", "N/A")
                rev = f"${r.get('total_revenue', 0):,.2f}" if "total_revenue" in r else "N/A"
                aov = f"${r.get('avg_order_value', 0):,.2f}" if "avg_order_value" in r else "N/A"
                custs = r.get("customer_count", "N/A")
                lines.append(f"- {tier}: Total Revenue {rev}, AOV {aov}, Customers: {custs}")
            return "Customer tier comparison:\n" + "\n".join(lines)

        # Marketing campaigns
        if "attributed_revenue" in row_0 and "name" in row_0:
            lines = []
            for i, r in enumerate(rows[:5], 1):
                name = r.get("name", "N/A")
                ch = r.get("channel", "N/A")
                rev = f"${r.get('attributed_revenue', 0):,.2f}"
                roas = f"{r.get('roas', 0)}x" if "roas" in r else "N/A"
                orders = r.get("attributed_orders", 0)
                lines.append(f"{i}. {name} ({ch}): {rev} attributed revenue, ROAS: {roas} ({orders} orders)")
            return "Top marketing campaigns by attributed revenue:\n" + "\n".join(lines)

        # Reorder buffer
        if "buffer_to_reorder" in row_0 and "sku" in row_0:
            lines = []
            for i, r in enumerate(rows[:5], 1):
                name = r.get("name", "N/A")
                sku = r.get("sku", "")
                reg = r.get("warehouse_region", "")
                stock = r.get("stock_on_hand", 0)
                reorder = r.get("reorder_point", 0)
                buf = r.get("buffer_to_reorder", 0)
                lines.append(f"{i}. {name} ({sku}) in {reg}: {stock} units on hand (Reorder point: {reorder}, buffer: {buf})")
            return "Products closest to their reorder points:\n" + "\n".join(lines)

        # Generic summary for other queries
        summary_lines = [f"Retrieved {len(rows)} record(s):"]
        for r in rows[:5]:
            summary_lines.append(str(r))
        if len(rows) > 5:
            summary_lines.append(f"... and {len(rows) - 5} more rows.")
        return "\n".join(summary_lines)

    def _audit_log(self, query: str, result: str, sql_query: Optional[str] = None):
        """
        Log queries and results to query_audit table in a separate write connection.
        Ensures audit logging failures never break query response delivery.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    query TEXT,
                    result TEXT
                )
            """)
            cursor.execute(
                "INSERT INTO query_audit (timestamp, query, result) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), query, result[:1000])
            )
            conn.commit()
            conn.close()
            logger.info("Query successfully recorded to query_audit")
        except Exception as e:
            logger.warning(f"Audit logging failed: {str(e)}")


# Backward compatibility wrapper functions
def run_sql_query(query: str, db_path: Optional[str] = None) -> str:
    """
    Execute an SQL query or natural-language business question.
    Maintains backward compatibility with main.py endpoints.
    """
    try:
        agent = SQLAgent(db_path=db_path)
        result = agent.query(query)
        return result["answer"]
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}", exc_info=True)
        return f"Error executing database query: {str(e)}"
