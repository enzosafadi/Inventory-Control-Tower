"""Regression tests for inventory decision logic."""

from __future__ import annotations

import unittest

import pandas as pd

from inventory_optimizer.analysis import (
    InventoryDataError,
    analyze_inventory,
    calculate_kpis,
    validate_inventory_data,
)


def make_row(**overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "sku": "TEST-001",
        "product_name": "Test Component",
        "category": "Components",
        "supplier": "Test Supplier",
        "unit_cost": 25.0,
        "unit_price": 40.0,
        "current_stock": 50,
        "units_on_order": 0,
        "committed_stock": 0,
        "avg_daily_demand": 10.0,
        "demand_std_dev": 4.0,
        "lead_time_days": 9,
        "order_cost": 50.0,
        "annual_holding_rate": 0.20,
    }
    row.update(overrides)
    return row


class ValidationTests(unittest.TestCase):
    def test_column_names_are_normalized_and_optional_fields_are_added(self) -> None:
        row = make_row()
        row.pop("units_on_order")
        row.pop("committed_stock")
        frame = pd.DataFrame([row]).rename(columns={"unit_cost": "Unit Cost"})

        validated = validate_inventory_data(frame)

        self.assertIn("unit_cost", validated.columns)
        self.assertEqual(validated.loc[0, "units_on_order"], 0)
        self.assertEqual(validated.loc[0, "committed_stock"], 0)

    def test_duplicate_sku_is_rejected(self) -> None:
        frame = pd.DataFrame([make_row(), make_row(product_name="Second")])

        with self.assertRaisesRegex(InventoryDataError, "duplicate"):
            validate_inventory_data(frame)

    def test_missing_required_column_is_rejected(self) -> None:
        frame = pd.DataFrame([make_row()]).drop(columns=["lead_time_days"])

        with self.assertRaisesRegex(InventoryDataError, "lead_time_days"):
            validate_inventory_data(frame)

    def test_invalid_holding_rate_is_rejected(self) -> None:
        frame = pd.DataFrame([make_row(annual_holding_rate=1.2)])

        with self.assertRaisesRegex(InventoryDataError, "annual_holding_rate"):
            validate_inventory_data(frame)


class CalculationTests(unittest.TestCase):
    def test_safety_stock_reorder_point_and_eoq(self) -> None:
        result = analyze_inventory(pd.DataFrame([make_row()]), service_level=0.95)
        item = result.iloc[0]

        self.assertAlmostEqual(item["safety_stock"], 19.7, places=1)
        self.assertAlmostEqual(item["reorder_point"], 109.7, places=1)
        self.assertAlmostEqual(item["eoq"], 270.2, places=1)
        self.assertEqual(item["recommended_order_qty"], 330)

    def test_no_order_is_recommended_above_reorder_point(self) -> None:
        result = analyze_inventory(
            pd.DataFrame([make_row(current_stock=800)]),
            service_level=0.95,
            excess_days_threshold=90,
        )

        self.assertEqual(result.loc[0, "recommended_order_qty"], 0)

    def test_committed_and_inbound_stock_change_inventory_position(self) -> None:
        result = analyze_inventory(
            pd.DataFrame(
                [make_row(current_stock=100, committed_stock=30, units_on_order=45)]
            )
        )

        self.assertEqual(result.loc[0, "available_stock"], 70)
        self.assertEqual(result.loc[0, "inventory_position"], 115)

    def test_abc_classification_preserves_high_value_priority(self) -> None:
        frame = pd.DataFrame(
            [
                make_row(sku="A", avg_daily_demand=1000),
                make_row(sku="B", avg_daily_demand=100),
                make_row(sku="C", avg_daily_demand=9),
                make_row(sku="D", avg_daily_demand=1),
            ]
        )
        result = analyze_inventory(frame).set_index("sku")

        self.assertEqual(result.loc["A", "abc_class"], "A")
        self.assertEqual(result.loc["B", "abc_class"], "B")
        self.assertEqual(result.loc["D", "abc_class"], "C")

    def test_source_frame_is_not_mutated(self) -> None:
        source = pd.DataFrame([make_row()])
        source_copy = source.copy(deep=True)

        analyze_inventory(source)

        pd.testing.assert_frame_equal(source, source_copy)

    def test_kpis_reconcile_to_analyzed_rows(self) -> None:
        frame = pd.DataFrame(
            [
                make_row(sku="LOW", current_stock=0),
                make_row(sku="OK", current_stock=300),
            ]
        )
        result = analyze_inventory(frame)
        kpis = calculate_kpis(result)

        self.assertEqual(kpis["sku_count"], 2)
        self.assertGreaterEqual(kpis["at_risk_skus"], 1)
        self.assertAlmostEqual(
            kpis["recommended_order_value"],
            float(result["suggested_purchase_cost"].sum()),
            places=2,
        )


if __name__ == "__main__":
    unittest.main()
