"""
Baseline Smoke Tests for DataScout / IntelliOps AI
Created in Phase 1 to verify core API endpoints, database connectivity, and error handling.
"""

import unittest
import os
import sqlite3
import json
from fastapi.testclient import TestClient

# Import FastAPI app from main
from main import app


class TestBaselineSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db_path = "datascout.db"

    def test_01_database_file_exists(self):
        """Verify that datascout.db exists in the working directory."""
        self.assertTrue(os.path.exists(self.db_path), f"Database file not found at {self.db_path}")

    def test_02_database_schema_integrity(self):
        """Verify that all expected enterprise and seed tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "documents",
            "agent_logs",
            "query_audit",
            "custom_agents",
            "user_settings",
            "transactions",
            "payroll",
        }
        for table in expected_tables:
            self.assertIn(table, tables, f"Expected table '{table}' is missing from database")

    def test_03_database_records_present(self):
        """Verify that seed data exists in transactions and payroll tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions;")
        tx_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM payroll;")
        payroll_count = cursor.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(tx_count, 1000, "Transactions table should have at least 1000 records")
        self.assertGreaterEqual(payroll_count, 3, "Payroll table should have at least 3 records")

    def test_04_health_endpoint(self):
        """Verify GET /health reports healthy status and database connection."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("ai_providers", data)

    def test_05_stats_endpoint(self):
        """Verify GET /api/stats returns valid metrics structure."""
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("revenue", data)
        self.assertIn("documents", data)
        self.assertIn("queries", data)
        self.assertIn("agents_active", data)

    def test_06_analytics_summary_endpoint(self):
        """Verify GET /api/analytics/summary returns metrics structure."""
        response = self.client.get("/api/analytics/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_queries", data)
        self.assertIn("avg_latency_ms", data)
        self.assertIn("success_rate", data)

    def test_07_settings_endpoint(self):
        """Verify GET /api/settings retrieves stored user configuration."""
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("theme", data)
        self.assertIn("openai_model", data)

    def test_08_chat_resilience_without_api_key(self):
        """Verify POST /chat returns informative configuration message instead of crashing when OPENAI_API_KEY is missing."""
        response = self.client.post("/chat", json={"message": "What were our laptop sales in August?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("response", data)
        self.assertIn("thoughts", data)
        # Should not crash or produce fake chart data
        self.assertEqual(data.get("visual_artifact"), "")


if __name__ == "__main__":
    unittest.main()
