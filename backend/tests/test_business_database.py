"""
IntelliOps AI — Automated Test Suite for Relational Business Database
Tests:
- Schema initialization in isolated temporary databases
- Foreign key referential integrity and constraint enforcement
- Transaction rollback safety
- Deterministic data generation & idempotency
- Business rule validation (mathematical reconciliation, chronology, non-negativity)
- Analytical query execution
- Backward compatibility with existing development database
"""

import unittest
import os
import sys
import sqlite3
import tempfile
import shutil

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_schema import init_relational_schema, get_connection
from data.generate_business_data import generate_business_data
from data.validate_business_data import validate_database


class TestRelationalBusinessDatabase(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test_business.db")

    def tearDown(self):
        # Clean up temporary directory and database files
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_schema_initialization_fresh_db(self):
        """Verify that a fresh database initializes all 10 business tables and indexes."""
        init_relational_schema(self.test_db_path)
        self.assertTrue(os.path.exists(self.test_db_path))

        conn = get_connection(self.test_db_path, read_only=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "categories", "products", "customers", "marketing_campaigns",
            "orders", "order_items", "payments", "inventory",
            "customer_interactions", "support_tickets"
        }
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' not found in fresh database.")

    def test_02_foreign_key_enforcement(self):
        """Verify SQLite PRAGMA foreign_keys = ON rejects orphan records."""
        init_relational_schema(self.test_db_path)
        conn = get_connection(self.test_db_path)
        cursor = conn.cursor()

        # Attempt to insert an order referencing non-existent customer_id = 99999
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO orders (order_number, customer_id, order_date, subtotal, discount, tax, total_amount, status)
                VALUES ('ORD-TEST-001', 99999, '2024-05-01', 100.0, 0.0, 0.0, 100.0, 'completed');
            """)
        conn.close()

    def test_03_check_constraint_enforcement(self):
        """Verify CHECK constraints reject invalid domain values (e.g., negative prices, invalid regions)."""
        init_relational_schema(self.test_db_path)
        conn = get_connection(self.test_db_path)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Software');")

        # Negative unit price should fail CHECK(unit_price > 0)
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO products (sku, name, category_id, unit_price, unit_cost, status)
                VALUES ('TEST-SKU', 'Negative Product', 1, -50.0, 10.0, 'active');
            """)

        # Invalid region should fail CHECK(region IN ('NA', 'EMEA', 'APAC', 'LATAM'))
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO customers (customer_code, company_name, contact_name, email, region, tier, industry, signup_date)
                VALUES ('C-BAD', 'Bad Region Co', 'Contact', 'bad@test.com', 'ANTARCTICA', 'SMB', 'Tech', '2024-01-01');
            """)
        conn.close()

    def test_04_transaction_rollback_safety(self):
        """Verify that an error inside a transaction rolls back uncommitted records."""
        init_relational_schema(self.test_db_path)
        conn = get_connection(self.test_db_path)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Hardware');")
        conn.commit()

        # Start manual transaction
        try:
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("INSERT INTO categories (id, name) VALUES (2, 'Cloud');")
            # Force integrity error (duplicate ID 1)
            cursor.execute("INSERT INTO categories (id, name) VALUES (1, 'Duplicate ID');")
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()

        # Category 2 should have been rolled back
        cursor.execute("SELECT COUNT(*) FROM categories WHERE id = 2;")
        self.assertEqual(cursor.fetchone()[0], 0, "Rolled-back record was unexpectedly committed.")
        conn.close()

    def test_05_reproducible_data_generation(self):
        """Verify deterministic generation: same seed generates identical row counts."""
        counts_1 = generate_business_data(db_path=self.test_db_path, scale="small", seed=42)
        
        # Second run on a separate test database with the same seed
        db_path_2 = os.path.join(self.test_dir, "test_business_2.db")
        counts_2 = generate_business_data(db_path=db_path_2, scale="small", seed=42)

        self.assertEqual(counts_1, counts_2, "Data generation with identical seed produced divergent counts.")
        self.assertGreaterEqual(counts_1["orders"], 500)
        self.assertGreaterEqual(counts_1["order_items"], 1000)

    def test_06_idempotent_generator_rerun(self):
        """Verify running generator without force skips insertion if data already exists."""
        generate_business_data(db_path=self.test_db_path, scale="small", seed=42)
        
        conn = get_connection(self.test_db_path, read_only=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders;")
        initial_order_count = cursor.fetchone()[0]
        conn.close()

        # Re-run generator without force
        generate_business_data(db_path=self.test_db_path, scale="small", seed=42, force=False)

        conn = get_connection(self.test_db_path, read_only=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders;")
        subsequent_order_count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(initial_order_count, subsequent_order_count, "Re-running without force modified row counts.")

    def test_07_automated_data_validation(self):
        """Verify that generated data passes all automated integrity and mathematical checks."""
        # Initialize legacy tables to verify backward compat check
        conn = get_connection(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INT);")
        cursor.execute("INSERT INTO transactions VALUES (1);")
        cursor.execute("CREATE TABLE IF NOT EXISTS payroll (id INT);")
        cursor.execute("INSERT INTO payroll VALUES (1);")
        conn.commit()
        conn.close()

        generate_business_data(db_path=self.test_db_path, scale="small", seed=42)
        
        val_res = validate_database(self.test_db_path)
        # Check non-compat validations
        self.assertGreaterEqual(val_res["passed_checks"], 8)
        # Check that no foreign key violations or order math mismatches exist
        for detail in val_res["details"]:
            if detail["check"] in ("Foreign Key Referential Integrity", "Order Total Reconciliation", "Non-Negative Quantities & Prices"):
                self.assertEqual(detail["status"], "PASS", f"Critical check failed: {detail['message']}")

    def test_08_analytical_queries_correctness(self):
        """Verify that basic analytical queries run and return valid non-empty numeric results."""
        generate_business_data(db_path=self.test_db_path, scale="small", seed=42)
        conn = get_connection(self.test_db_path, read_only=True)
        cursor = conn.cursor()

        # Monthly Revenue Query
        cursor.execute("""
            SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount)
            FROM orders WHERE status = 'completed'
            GROUP BY month ORDER BY month DESC;
        """)
        monthly_rev = cursor.fetchall()
        self.assertGreater(len(monthly_rev), 6, "Expected at least 6 months of historical data.")
        self.assertGreater(monthly_rev[0][1], 0, "Monthly revenue should be positive.")

        # Revenue by Category Query
        cursor.execute("""
            SELECT c.name, SUM(oi.total_price)
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            GROUP BY c.name;
        """)
        cat_rev = cursor.fetchall()
        self.assertEqual(len(cat_rev), 5, "All 5 product categories should have recorded sales.")

        conn.close()

    def test_09_backward_compatibility_live_db(self):
        """Verify that the primary development database preserves legacy tables and rows."""
        live_db = "datascout.db"
        if os.path.exists(live_db):
            conn = sqlite3.connect(f"file:{os.path.abspath(live_db)}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions;")
            tx_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM payroll;")
            payroll_count = cursor.fetchone()[0]
            conn.close()

            self.assertGreaterEqual(tx_count, 1000, "Live transactions table was corrupted or reduced.")
            self.assertGreaterEqual(payroll_count, 3, "Live payroll table was corrupted or reduced.")


if __name__ == "__main__":
    unittest.main()
