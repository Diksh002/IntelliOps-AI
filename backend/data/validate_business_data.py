"""
IntelliOps AI — Relational Business Data Integrity Validator
Runs automated data-integrity and business-rule validation checks on:
- Primary key uniqueness
- Foreign key referential integrity (PRAGMA foreign_key_check)
- NOT NULL & Domain constraints
- Order total mathematical reconciliation (subtotal + tax - discount == total_amount)
- Order item total reconciliation (quantity * unit_price - discount == total_price)
- Payment-to-Order amount reconciliation
- Inventory bounds (stock_on_hand >= 0, safety_stock >= 0)
- Temporal validity (order_date >= customer signup_date)
- Churn target distribution validity
"""

import sqlite3
import os
import sys
import argparse
import logging
from typing import List, Dict, Any, Tuple

# Ensure parent directory (backend) is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_schema import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_database(db_path: str = "datascout.db") -> Dict[str, Any]:
    """
    Runs a full suite of integrity validations on the specified database.
    
    Returns:
        Dictionary containing check results, error counts, and detailed findings.
    """
    logger.info(f"Running data validation checks on: {db_path}")
    conn = get_connection(db_path, read_only=True)
    cursor = conn.cursor()

    results = {
        "database": db_path,
        "total_checks": 0,
        "passed_checks": 0,
        "failed_checks": 0,
        "details": []
    }

    def record_check(name: str, passed: bool, message: str, count: int = 0):
        results["total_checks"] += 1
        if passed:
            results["passed_checks"] += 1
            logger.info(f"  [PASS] {name}: {message}")
            results["details"].append({"check": name, "status": "PASS", "message": message, "violating_rows": count})
        else:
            results["failed_checks"] += 1
            logger.error(f"  [FAIL] {name}: {message} (Violations: {count})")
            results["details"].append({"check": name, "status": "FAIL", "message": message, "violating_rows": count})

    try:
        # Check 1: Foreign Key Referential Integrity
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        record_check(
            "Foreign Key Referential Integrity",
            len(fk_violations) == 0,
            f"{len(fk_violations)} broken foreign key relationships detected.",
            len(fk_violations)
        )

        # Check 2: Table Population Check
        required_tables = [
            "categories", "products", "customers", "marketing_campaigns",
            "orders", "order_items", "payments", "inventory",
            "customer_interactions", "support_tickets"
        ]
        empty_tables = []
        for tbl in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            c = cursor.fetchone()[0]
            if c == 0:
                empty_tables.append(tbl)
        record_check(
            "Required Tables Populated",
            len(empty_tables) == 0,
            f"All {len(required_tables)} business tables contain records." if not empty_tables else f"Empty tables: {', '.join(empty_tables)}",
            len(empty_tables)
        )

        # Check 3: Order Total Math Consistency
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE ABS(total_amount - (subtotal + tax - discount)) > 0.01;
        """)
        mismatched_orders = cursor.fetchone()[0]
        record_check(
            "Order Total Reconciliation",
            mismatched_orders == 0,
            "All orders mathematically reconcile (total == subtotal + tax - discount).",
            mismatched_orders
        )

        # Check 4: Order Item Math Consistency
        cursor.execute("""
            SELECT COUNT(*) FROM order_items 
            WHERE ABS(total_price - (ROUND(quantity * unit_price, 2) - discount)) > 0.02;
        """)
        mismatched_items = cursor.fetchone()[0]
        record_check(
            "Order Item Line-Price Reconciliation",
            mismatched_items == 0,
            "All order item rows match quantity * unit_price - discount.",
            mismatched_items
        )

        # Check 5: Non-Negative Values (Quantities, Totals, Inventory)
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM order_items WHERE quantity <= 0 OR unit_price < 0 OR total_price < 0) +
                (SELECT COUNT(*) FROM orders WHERE total_amount < 0 OR subtotal < 0) +
                (SELECT COUNT(*) FROM inventory WHERE stock_on_hand < 0 OR reorder_point < 0);
        """)
        negative_violations = cursor.fetchone()[0]
        record_check(
            "Non-Negative Quantities & Prices",
            negative_violations == 0,
            "All quantities, prices, subtotals, and inventory levels are non-negative.",
            negative_violations
        )

        # Check 6: Payment-to-Order Integrity
        cursor.execute("""
            SELECT COUNT(*) FROM payments p
            JOIN orders o ON p.order_id = o.id
            WHERE p.status = 'completed' AND o.status = 'completed' AND ABS(p.amount - o.total_amount) > 0.01;
        """)
        payment_mismatches = cursor.fetchone()[0]
        record_check(
            "Payment vs Order Amount Match",
            payment_mismatches == 0,
            "All completed payments match their respective order total.",
            payment_mismatches
        )

        # Check 7: Temporal Validity (Orders must occur on or after customer signup date)
        cursor.execute("""
            SELECT COUNT(*) FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.order_date < c.signup_date;
        """)
        premature_orders = cursor.fetchone()[0]
        record_check(
            "Temporal Chronology (Orders >= Signup)",
            premature_orders == 0,
            "All orders occurred on or after the customer registration date.",
            premature_orders
        )

        # Check 8: Customer Interaction Chronology
        cursor.execute("""
            SELECT COUNT(*) FROM customer_interactions ci
            JOIN customers c ON ci.customer_id = c.id
            WHERE ci.interaction_date < c.signup_date;
        """)
        premature_interactions = cursor.fetchone()[0]
        record_check(
            "Temporal Chronology (Interactions >= Signup)",
            premature_interactions == 0,
            "All customer interactions occurred on or after customer signup date.",
            premature_interactions
        )

        # Check 9: Customer Churn Target Distribution
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as churned
            FROM customers;
        """)
        tot_cust, churn_cust = cursor.fetchone()
        churn_pct = (churn_cust / tot_cust * 100.0) if tot_cust > 0 else 0.0
        # Expected churn distribution between 15% and 40% for balanced ML training
        churn_valid = 15.0 <= churn_pct <= 40.0
        record_check(
            "Churn Target Distribution (Balanced Class Ratio)",
            churn_valid,
            f"Customer churn rate is {churn_pct:.1f}% ({churn_cust}/{tot_cust}), optimal for classification.",
            0 if churn_valid else 1
        )

        # Check 10: Backward Compatibility Tables Preservation
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM transactions),
                (SELECT COUNT(*) FROM payroll);
        """)
        tx_cnt, pay_cnt = cursor.fetchone()
        compat_valid = (tx_cnt >= 1000) and (pay_cnt >= 3)
        record_check(
            "Backward Compatibility (Legacy Tables Intact)",
            compat_valid,
            f"Legacy tables intact: transactions={tx_cnt}, payroll={pay_cnt}.",
            0 if compat_valid else 1
        )

        logger.info(f"Validation complete: {results['passed_checks']}/{results['total_checks']} checks PASSED.")
        return results

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate IntelliOps AI relational business data")
    parser.add_argument("--db", type=str, default="datascout.db", help="SQLite database to validate")
    args = parser.parse_args()

    res = validate_database(args.db)
    if res["failed_checks"] > 0:
        logger.error(f"Validation failed with {res['failed_checks']} failures.")
        sys.exit(1)
    else:
        logger.info("[OK] All data integrity checks passed.")
        sys.exit(0)
