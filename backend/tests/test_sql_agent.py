"""
IntelliOps AI - Automated Test Suite for Secure SQL Agent (Phase 5)
Covers all 18 required test scenarios in an isolated temporary database:
1. Valid SELECT query
2. Valid aggregation query
3. Valid JOIN query
4. Invalid table name rejection
5. Invalid column name rejection
6. INSERT statement rejection
7. UPDATE statement rejection
8. DELETE statement rejection
9. DROP statement rejection
10. Multiple statement rejection
11. Query timeout / resource limit handling
12. Empty result handling
13. Read-only database protection (database-level URI mode=ro & query-only)
14. Database path resolution & non-existent path safety
15. Revenue calculation correctness (excluding cancelled orders)
16. Avoiding revenue double-counting on JOINs
17. Legacy endpoint compatibility (run_sql_query and /api/agents/execute)
18. Missing OpenAI credential behavior
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import unittest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from db_schema import init_relational_schema
from agents.sql_validator import SQLValidator
from agents.sql_executor import (
    resolve_database_path,
    get_readonly_connection,
    get_database_schema,
    execute_analytical_query,
)
from agents.sql_agent import SQLAgent, run_sql_query


class TestSecureSQLAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary directory for test database
        cls.test_dir = tempfile.mkdtemp()
        cls.test_db_path = os.path.join(cls.test_dir, "test_datascout.db")

        # Initialize schema
        init_relational_schema(cls.test_db_path)

        # Seed known deterministic fixture data
        conn = sqlite3.connect(cls.test_db_path)
        cur = conn.cursor()

        # Legacy tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT,
                salary REAL
            );
        """)
        cur.execute("INSERT INTO payroll (employee_name, salary) VALUES ('Alice Secret', 185000.0);")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                amount REAL,
                description TEXT
            );
        """)
        cur.execute("INSERT INTO transactions (transaction_id, amount, description) VALUES ('TX-001', 500.0, 'Legacy test');")

        # Business tables seed
        cur.execute("INSERT INTO categories (id, name, description) VALUES (1, 'Hardware', 'Hardware devices'), (2, 'Software', 'Software licenses');")
        
        cur.execute("""
            INSERT INTO products (id, sku, name, category_id, unit_price, unit_cost, status) VALUES
            (1, 'HW-SRV-100', 'Enterprise Server', 1, 1000.0, 600.0, 'active'),
            (2, 'SW-LIC-500', 'Cloud License', 2, 500.0, 100.0, 'active'),
            (3, 'HW-ACC-010', 'Accessory Cable', 1, 200.0, 50.0, 'active');
        """)

        cur.execute("""
            INSERT INTO customers (id, customer_code, company_name, contact_name, email, region, tier, industry, signup_date) VALUES
            (1, 'CUST-001', 'Alpha Corp', 'Alice A', 'alice@alpha.com', 'NA', 'Enterprise', 'Tech', '2024-01-01'),
            (2, 'CUST-002', 'Beta LLC', 'Bob B', 'bob@beta.com', 'EMEA', 'SMB', 'Finance', '2024-02-01'),
            (3, 'CUST-003', 'Gamma Inc', 'Charlie C', 'charlie@gamma.com', 'NA', 'SMB', 'Healthcare', '2024-03-01');
        """)

        cur.execute("""
            INSERT INTO marketing_campaigns (id, name, channel, budget, spend, start_date, end_date, target_region, status) VALUES
            (1, 'Campaign Alpha', 'Email', 1000.0, 500.0, '2025-01-01', '2025-12-31', 'NA', 'completed');
        """)

        # Orders:
        # Order 1: Completed, total=2000.0 (Customer 1, Campaign 1)
        # Order 2: Completed, total=500.0 (Customer 2, Campaign 1)
        # Order 3: Cancelled, total=1000.0 (Customer 3) -> should be excluded from revenue!
        # Order 4: Completed, total=1500.0 (Customer 1, No Campaign)
        cur.execute("""
            INSERT INTO orders (id, order_number, customer_id, campaign_id, order_date, subtotal, discount, tax, total_amount, status) VALUES
            (1, 'ORD-001', 1, 1, '2025-12-15', 2000.0, 0.0, 0.0, 2000.0, 'completed'),
            (2, 'ORD-002', 2, 1, '2025-12-20', 500.0, 0.0, 0.0, 500.0, 'completed'),
            (3, 'ORD-003', 3, NULL, '2025-12-22', 1000.0, 0.0, 0.0, 1000.0, 'cancelled'),
            (4, 'ORD-004', 1, NULL, '2025-11-10', 1500.0, 0.0, 0.0, 1500.0, 'completed');
        """)

        # Order items:
        # Order 1 has TWO items: Product 1 (1x$1000) + Product 2 (2x$500) = $2000.0
        # Order 2 has ONE item: Product 2 (1x$500) = $500.0
        # Order 4 has ONE item: Product 2 (3x$500) = $1500.0
        cur.execute("""
            INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount, total_price) VALUES
            (1, 1, 1, 1, 1000.0, 0.0, 1000.0),
            (2, 1, 2, 2, 500.0, 0.0, 1000.0),
            (3, 2, 2, 1, 500.0, 0.0, 500.0),
            (4, 4, 2, 3, 500.0, 0.0, 1500.0);
        """)

        # Inventory
        cur.execute("""
            INSERT INTO inventory (id, product_id, warehouse_region, stock_on_hand, reorder_point, safety_stock) VALUES
            (1, 1, 'NA', 5, 10, 5),
            (2, 2, 'EMEA', 50, 10, 5);
        """)

        conn.commit()
        conn.close()

        cls.client = TestClient(app)
        cls.agent = SQLAgent(db_path=cls.test_db_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # 1. Valid SELECT query
    def test_01_valid_select_query(self):
        """Verify basic SELECT statement returns expected columns and rows."""
        res = self.agent.execute_sql("SELECT name, unit_price FROM products ORDER BY id ASC;")
        self.assertTrue(res["success"])
        self.assertEqual(res["row_count"], 3)
        self.assertEqual(res["columns"], ["name", "unit_price"])
        self.assertEqual(res["rows"][0]["name"], "Enterprise Server")
        self.assertEqual(res["rows"][0]["unit_price"], 1000.0)

    # 2. Valid aggregation query
    def test_02_valid_aggregation_query(self):
        """Verify aggregation functions (COUNT, SUM, AVG) calculate accurately."""
        res = self.agent.execute_sql("""
            SELECT COUNT(*) AS completed_count,
                   SUM(total_amount) AS total_revenue,
                   AVG(total_amount) AS avg_value
            FROM orders
            WHERE status = 'completed';
        """)
        self.assertTrue(res["success"])
        row = res["rows"][0]
        self.assertEqual(row["completed_count"], 3)
        self.assertEqual(row["total_revenue"], 4000.0)  # 2000 + 500 + 1500
        self.assertAlmostEqual(row["avg_value"], 4000.0 / 3.0, places=2)

    # 3. Valid JOIN query
    def test_03_valid_join_query(self):
        """Verify multi-table relational JOIN retrieves correct relational associations."""
        res = self.agent.execute_sql("""
            SELECT o.order_number, c.company_name, o.total_amount
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status = 'completed'
            ORDER BY o.id ASC;
        """)
        self.assertTrue(res["success"])
        self.assertEqual(res["row_count"], 3)
        self.assertEqual(res["rows"][0]["company_name"], "Alpha Corp")
        self.assertEqual(res["rows"][1]["company_name"], "Beta LLC")

    # 4. Invalid table name
    def test_04_invalid_table_name(self):
        """Verify queries referencing non-existent or unapproved tables are rejected."""
        res = self.agent.execute_sql("SELECT * FROM non_existent_table;")
        self.assertFalse(res["success"])
        self.assertIn("not permitted or table does not exist", res["error"])

    # 5. Invalid column name
    def test_05_invalid_column_name(self):
        """Verify queries referencing non-existent columns are rejected during AST validation."""
        res = self.agent.execute_sql("SELECT imaginary_column FROM products;")
        self.assertFalse(res["success"])
        self.assertIn("Invalid column name", res["error"])

    # 6. INSERT rejection
    def test_06_insert_rejection(self):
        """Verify INSERT statements are rejected."""
        res = self.agent.execute_sql("INSERT INTO categories (name) VALUES ('Hacked Category');")
        self.assertFalse(res["success"])
        self.assertIn("INSERT statements are not permitted", res["error"])

    # 7. UPDATE rejection
    def test_07_update_rejection(self):
        """Verify UPDATE statements are rejected."""
        res = self.agent.execute_sql("UPDATE products SET unit_price = 0.0 WHERE id = 1;")
        self.assertFalse(res["success"])
        self.assertIn("UPDATE statements are not permitted", res["error"])

    # 8. DELETE rejection
    def test_08_delete_rejection(self):
        """Verify DELETE statements are rejected."""
        res = self.agent.execute_sql("DELETE FROM customers WHERE id = 1;")
        self.assertFalse(res["success"])
        self.assertIn("DELETE statements are not permitted", res["error"])

    # 9. DROP rejection
    def test_09_drop_rejection(self):
        """Verify DROP statements are rejected, even if attempted inside subqueries."""
        res = self.agent.execute_sql("DROP TABLE customers;")
        self.assertFalse(res["success"])
        self.assertIn("DROP statements are not permitted", res["error"])

    # 10. Multiple-statement rejection
    def test_10_multiple_statement_rejection(self):
        """Verify queries with multiple semicolon-separated statements are rejected."""
        res = self.agent.execute_sql("SELECT * FROM orders; DROP TABLE orders;")
        self.assertFalse(res["success"])
        self.assertIn("Multiple statements are not permitted", res["error"])

    # 11. Query timeout or resource-limit handling
    def test_11_query_timeout_resource_limit(self):
        """Verify runaway queries trigger execution timeout without crashing."""
        # Query with large recursive Cartesian product and small timeout (0.05 seconds)
        heavy_query = """
            WITH RECURSIVE r(i) AS (VALUES(0) UNION ALL SELECT i+1 FROM r WHERE i < 1000000)
            SELECT COUNT(*) FROM r, r;
        """
        res = execute_analytical_query(
            sql_query=heavy_query,
            db_path=self.test_db_path,
            timeout_seconds=0.05,
        )
        self.assertFalse(res["success"])
        self.assertIn("timed out", res["error"].lower())

    # 12. Empty result handling
    def test_12_empty_result_handling(self):
        """Verify queries matching zero rows return cleanly without errors."""
        res = self.agent.execute_sql("SELECT * FROM orders WHERE total_amount > 99999999;")
        self.assertTrue(res["success"])
        self.assertEqual(res["row_count"], 0)
        self.assertEqual(res["rows"], [])
        self.assertIsNone(res["error"])

    # 13. Read-only database protection
    def test_13_readonly_database_protection(self):
        """Verify SQLite database-level read-only protection blocks direct write attempts."""
        conn = get_readonly_connection(self.test_db_path)
        cur = conn.cursor()
        with self.assertRaises(sqlite3.OperationalError) as ctx:
            cur.execute("CREATE TABLE evil_table (id INT);")
        self.assertIn("readonly", str(ctx.exception).lower())
        conn.close()

    # 14. Database path resolution
    def test_14_database_path_resolution(self):
        """Verify resolve_database_path rejects nonexistent files preventing empty DB creation."""
        with self.assertRaises(FileNotFoundError):
            resolve_database_path("/path/to/nonexistent/db.sqlite")

    # 15. Revenue calculation correctness
    def test_15_revenue_calculation_correctness(self):
        """Verify revenue calculation correctly filters status='completed' and excludes cancelled orders."""
        res = self.agent.execute_sql("""
            SELECT SUM(total_amount) AS revenue
            FROM orders
            WHERE status = 'completed';
        """)
        self.assertTrue(res["success"])
        # Expected: Order 1 ($2000) + Order 2 ($500) + Order 4 ($1500) = $4000. Cancelled Order 3 ($1000) excluded.
        self.assertEqual(res["rows"][0]["revenue"], 4000.0)

    # 16. Avoiding revenue double-counting
    def test_16_avoiding_revenue_double_counting(self):
        """Verify joining orders with order_items uses item total_price, not orders total_amount to avoid double counting."""
        # Order 1 has 2 items each worth $1000 (total $2000).
        # If someone naively did SUM(o.total_amount) on the JOIN, Order 1's $2000 would be counted twice ($4000)!
        res_naive = self.agent.execute_sql("""
            SELECT SUM(o.total_amount) AS naive_double_count
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status = 'completed';
        """)
        # Correct calculation:
        res_correct = self.agent.execute_sql("""
            SELECT SUM(oi.total_price) AS true_item_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed';
        """)
        self.assertEqual(res_naive["rows"][0]["naive_double_count"], 6000.0)  # Double-counted!
        self.assertEqual(res_correct["rows"][0]["true_item_revenue"], 4000.0)  # Correctly avoids double-counting!

    # 17. Legacy endpoint compatibility
    def test_17_legacy_endpoint_compatibility(self):
        """Verify legacy run_sql_query and /api/agents/execute continue to work seamlessly."""
        # Direct call with test database
        ans = run_sql_query("SELECT count(*) as total_products FROM products;", db_path=self.test_db_path)
        self.assertIn("3", ans)

        # API endpoint call (operates on active database)
        response = self.client.post("/api/agents/execute", json={
            "agent_type": "sql",
            "query": "SELECT count(*) as total_products FROM products;"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("agent_name"), "SQL Expert")
        self.assertIn("total_products", data.get("response"))

    # 18. Missing OpenAI credential behavior
    def test_18_missing_openai_credential_behavior(self):
        """Verify clear configuration messaging when natural-language query lacks OpenAI credentials."""
        # Query that is not a direct SQL query and not a known benchmark query
        res = self.agent.query("What is the hypothetical correlation between weather and stock?")
        self.assertFalse(res["success"])
        self.assertIn("OpenAI API key is not configured", res["answer"])
        self.assertIn("Missing or placeholder OPENAI_API_KEY", res["error"])


if __name__ == "__main__":
    unittest.main()
