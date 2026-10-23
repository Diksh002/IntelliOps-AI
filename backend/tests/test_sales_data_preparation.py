"""
IntelliOps AI — Automated Test Suite for Sales Data Preparation & Audit Pipeline
Verifies:
- Daily aggregation accuracy
- Strict exclusion of cancelled, refunded, and pending orders
- Exact revenue total reconciliation
- Prevention of revenue double-counting from one-to-many joins
- Continuous calendar date generation and zero-sales day handling
- Chronological sorting
- Handling of empty databases, missing tables, and malformed/invalid dates
- Read-only database access enforcement
- Determinism and reproducibility
- Units sold target calculation
"""

import os
import sys
import sqlite3
import tempfile
import unittest
import csv
import json
from datetime import datetime, timedelta

# Ensure backend directory is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.prepare_sales_data import (
    extract_daily_sales_revenue,
    extract_daily_units_sold,
    run_sales_audit,
    export_prepared_datasets,
    get_readonly_db_connection,
    generate_continuous_date_range,
)


class TestSalesDataPreparation(unittest.TestCase):
    """Unit tests for ML sales data preparation pipeline using isolated temp databases."""

    def setUp(self):
        """Create a fresh isolated temporary SQLite database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_sales.db")
        self._init_test_db()

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def _init_test_db(self):
        """Initialize schema and seed controlled test records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
        """)
        cursor.execute("INSERT INTO categories VALUES (1, 'Software'), (2, 'Hardware');")

        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                sku TEXT UNIQUE,
                name TEXT,
                category_id INTEGER REFERENCES categories(id),
                unit_price REAL,
                unit_cost REAL,
                status TEXT
            );
        """)
        cursor.execute("INSERT INTO products VALUES (1, 'SKU-1', 'Product 1', 1, 100.0, 50.0, 'active');")
        cursor.execute("INSERT INTO products VALUES (2, 'SKU-2', 'Product 2', 2, 250.0, 150.0, 'active');")

        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                customer_code TEXT UNIQUE,
                company_name TEXT,
                contact_name TEXT,
                email TEXT,
                region TEXT,
                tier TEXT,
                industry TEXT,
                signup_date TEXT,
                is_active INTEGER
            );
        """)
        cursor.execute("INSERT INTO customers VALUES (1, 'C-01', 'Acme', 'John', 'j@acme.com', 'NA', 'Enterprise', 'Tech', '2024-01-01', 1);")

        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                order_number TEXT UNIQUE,
                customer_id INTEGER,
                campaign_id INTEGER,
                order_date TEXT,
                subtotal REAL,
                discount REAL,
                tax REAL,
                total_amount REAL,
                status TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                unit_price REAL,
                discount REAL,
                total_price REAL
            );
        """)

        # Seed Controlled Orders:
        # Date 2024-01-10: 2 completed orders ($1,000 + $2,500 = $3,500)
        # Order 1 has 2 order items (testing 1-to-many join prevention)
        cursor.execute("""
            INSERT INTO orders VALUES (1, 'ORD-001', 1, NULL, '2024-01-10', 1000.0, 0.0, 0.0, 1000.0, 'completed');
        """)
        cursor.execute("INSERT INTO order_items VALUES (1, 1, 1, 5, 100.0, 0.0, 500.0);")
        cursor.execute("INSERT INTO order_items VALUES (2, 1, 2, 2, 250.0, 0.0, 500.0);")

        cursor.execute("""
            INSERT INTO orders VALUES (2, 'ORD-002', 1, NULL, '2024-01-10', 2500.0, 0.0, 0.0, 2500.0, 'completed');
        """)
        cursor.execute("INSERT INTO order_items VALUES (3, 2, 2, 10, 250.0, 0.0, 2500.0);")

        # Date 2024-01-11: 1 cancelled order ($500), 1 refunded order ($750), 1 pending order ($300)
        # All three must be excluded!
        cursor.execute("""
            INSERT INTO orders VALUES (3, 'ORD-003', 1, NULL, '2024-01-11', 500.0, 0.0, 0.0, 500.0, 'cancelled');
        """)
        cursor.execute("""
            INSERT INTO orders VALUES (4, 'ORD-004', 1, NULL, '2024-01-11', 750.0, 0.0, 0.0, 750.0, 'refunded');
        """)
        cursor.execute("""
            INSERT INTO orders VALUES (5, 'ORD-005', 1, NULL, '2024-01-11', 300.0, 0.0, 0.0, 300.0, 'pending');
        """)

        # Date 2024-01-12: Zero orders (gap date)

        # Date 2024-01-13: 1 completed order ($1,200.50)
        cursor.execute("""
            INSERT INTO orders VALUES (6, 'ORD-006', 1, NULL, '2024-01-13', 1200.50, 0.0, 0.0, 1200.50, 'completed');
        """)
        cursor.execute("INSERT INTO order_items VALUES (4, 6, 1, 12, 100.0, 0.0, 1200.0);")

        conn.commit()
        conn.close()

    def test_01_daily_aggregation_and_correct_totals(self):
        """Verify that multiple orders on the same calendar day are aggregated correctly."""
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )
        self.assertEqual(len(series), 4)

        # On 2024-01-10: 2 completed orders, total = $3,500.00, AOV = $1,750.00
        d0 = series[0]
        self.assertEqual(d0["date"], "2024-01-10")
        self.assertEqual(d0["order_count"], 2)
        self.assertAlmostEqual(d0["revenue"], 3500.00, places=2)
        self.assertAlmostEqual(d0["avg_order_value"], 1750.00, places=2)
        self.assertAlmostEqual(d0["min_order_value"], 1000.00, places=2)
        self.assertAlmostEqual(d0["max_order_value"], 2500.00, places=2)

    def test_02_excluding_cancelled_refunded_pending_orders(self):
        """Verify that cancelled, refunded, and pending orders are strictly excluded from revenue."""
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )

        # 2024-01-11 only had cancelled, refunded, and pending orders.
        # It must report revenue = 0.0 and order_count = 0.
        d1 = series[1]
        self.assertEqual(d1["date"], "2024-01-11")
        self.assertEqual(d1["revenue"], 0.0)
        self.assertEqual(d1["order_count"], 0)

    def test_03_no_revenue_double_counting(self):
        """
        Verify that orders with multiple order_items do NOT multiply the revenue.
        Order 1 has 2 items ($500 + $500 = $1,000 total).
        If naive join is used, order 1's $1,000 would be summed twice ($2,000).
        """
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-10",
            fill_zeros=False,
        )
        self.assertEqual(len(series), 1)
        # Should be exactly 1000 + 2500 = 3500, NOT 4500
        self.assertAlmostEqual(series[0]["revenue"], 3500.00, places=2)

    def test_04_continuous_calendar_and_zero_sales_dates(self):
        """Verify that date index is strictly continuous and includes zero-sales dates."""
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )
        expected_dates = ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-13"]
        actual_dates = [r["date"] for r in series]
        self.assertEqual(actual_dates, expected_dates)

        # 2024-01-12 had no orders at all
        d2 = series[2]
        self.assertEqual(d2["date"], "2024-01-12")
        self.assertEqual(d2["revenue"], 0.0)
        self.assertEqual(d2["order_count"], 0)

    def test_05_chronological_ordering(self):
        """Verify that records are returned in ascending chronological order."""
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )
        dates = [r["date"] for r in series]
        self.assertEqual(dates, sorted(dates))

    def test_06_empty_database_handling(self):
        """Verify graceful handling when database has no orders."""
        empty_db = os.path.join(self.temp_dir.name, "empty.db")
        conn = sqlite3.connect(empty_db)
        conn.execute("CREATE TABLE orders (id INT, order_date TEXT, total_amount REAL, status TEXT);")
        conn.commit()
        conn.close()

        # With fill_zeros=True and explicit dates
        series = extract_daily_sales_revenue(
            db_path=empty_db,
            start_date="2024-01-01",
            end_date="2024-01-05",
            fill_zeros=True,
        )
        self.assertEqual(len(series), 5)
        self.assertTrue(all(r["revenue"] == 0.0 for r in series))

        # With fill_zeros=False
        series_no_fill = extract_daily_sales_revenue(
            db_path=empty_db,
            fill_zeros=False,
        )
        self.assertEqual(series_no_fill, [])

    def test_07_missing_table_handling(self):
        """Verify handling when orders table does not exist."""
        no_table_db = os.path.join(self.temp_dir.name, "no_orders.db")
        conn = sqlite3.connect(no_table_db)
        conn.execute("CREATE TABLE other (id INT);")
        conn.commit()
        conn.close()

        series = extract_daily_sales_revenue(db_path=no_table_db)
        self.assertEqual(series, [])

    def test_08_invalid_or_missing_order_dates(self):
        """Verify that rows with null or malformed order_date are skipped gracefully."""
        conn = sqlite3.connect(self.db_path)
        # Insert corrupted date orders
        conn.execute("""
            INSERT INTO orders VALUES (90, 'ORD-CORRUPT-1', 1, NULL, 'invalid-date-string', 100.0, 0.0, 0.0, 100.0, 'completed');
        """)
        conn.execute("""
            INSERT INTO orders VALUES (91, 'ORD-CORRUPT-2', 1, NULL, NULL, 100.0, 0.0, 0.0, 100.0, 'completed');
        """)
        conn.commit()
        conn.close()

        # Should not crash, and corrupt dates should be excluded
        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )
        self.assertEqual(len(series), 4)

    def test_09_negative_or_corrupt_amounts_rejected(self):
        """Verify that negative or non-numeric total_amount rows are rejected."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO orders VALUES (92, 'ORD-NEG', 1, NULL, '2024-01-10', -500.0, 0.0, 0.0, -500.0, 'completed');
        """)
        conn.execute("""
            INSERT INTO orders VALUES (93, 'ORD-NAN', 1, NULL, '2024-01-10', 0.0, 0.0, 0.0, 'NOT_A_NUMBER', 'completed');
        """)
        conn.commit()
        conn.close()

        series = extract_daily_sales_revenue(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-10",
            fill_zeros=False,
        )
        # Should remain 3500.00, ignoring negative and non-numeric
        self.assertAlmostEqual(series[0]["revenue"], 3500.00, places=2)

    def test_10_readonly_database_access(self):
        """Verify that get_readonly_db_connection rejects write queries."""
        conn = get_readonly_db_connection(self.db_path)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("INSERT INTO orders (id, total_amount) VALUES (999, 10.0);")
        conn.close()

    def test_11_deterministic_output(self):
        """Verify that consecutive extractions return bit-for-bit identical results."""
        run1 = extract_daily_sales_revenue(self.db_path, "2024-01-10", "2024-01-13", True)
        run2 = extract_daily_sales_revenue(self.db_path, "2024-01-10", "2024-01-13", True)
        self.assertEqual(run1, run2)

    def test_12_daily_units_sold_independent(self):
        """Verify that units sold calculates correctly from order_items."""
        units_series = extract_daily_units_sold(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
            fill_zeros=True,
        )
        self.assertEqual(len(units_series), 4)

        # 2024-01-10: Order 1 has 5 + 2 = 7 units, Order 2 has 10 units -> Total 17 units
        u0 = units_series[0]
        self.assertEqual(u0["date"], "2024-01-10")
        self.assertEqual(u0["units_sold"], 17)
        self.assertEqual(u0["order_count"], 2)
        self.assertEqual(u0["line_item_count"], 3)
        self.assertEqual(u0["distinct_products_sold"], 2)

        # 2024-01-11: No completed orders -> 0 units
        u1 = units_series[1]
        self.assertEqual(u1["units_sold"], 0)

        # 2024-01-13: Order 6 has 12 units
        u3 = units_series[3]
        self.assertEqual(u3["units_sold"], 12)

    def test_13_export_artifacts(self):
        """Verify export_prepared_datasets creates valid CSV and JSON artifacts."""
        out_dir = os.path.join(self.temp_dir.name, "artifacts")
        paths = export_prepared_datasets(
            db_path=self.db_path,
            output_dir=out_dir,
            start_date="2024-01-10",
            end_date="2024-01-13",
        )
        for key, filepath in paths.items():
            self.assertTrue(os.path.isfile(filepath), f"File {filepath} was not created")

        # Verify CSV content
        with open(paths["revenue_csv"], mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["date"], "2024-01-10")
            self.assertEqual(float(rows[0]["revenue"]), 3500.0)

    def test_14_audit_report_generation(self):
        """Verify run_sales_audit generates a complete report with required keys."""
        report = run_sales_audit(
            db_path=self.db_path,
            start_date="2024-01-10",
            end_date="2024-01-13",
        )
        self.assertIn("date_range", report)
        self.assertIn("order_status_breakdown", report)
        self.assertIn("daily_revenue_statistics_all_days", report)
        self.assertIn("autocorrelations", report)
        self.assertIn("baseline_evaluation_benchmarks", report)
        self.assertIn("forecastability_assessment", report)
        self.assertEqual(report["date_range"]["total_calendar_days"], 4)
        self.assertEqual(report["date_range"]["active_sales_days"], 2)
        self.assertEqual(report["date_range"]["zero_sales_days"], 2)


if __name__ == "__main__":
    unittest.main()
