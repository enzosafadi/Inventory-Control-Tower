"""Core inventory calculations.

The functions in this module are deliberately independent from Streamlit so
they can be tested, reused in an API, or scheduled as a batch process.
"""

from __future__ import annotations

from statistics import NormalDist
from typing import Final

import numpy as np
import pandas as pd


class InventoryDataError(ValueError):
    """Raised when an inventory file cannot be analyzed safely."""


REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "sku",
    "product_name",
    "category",
    "unit_cost",
    "unit_price",
    "current_stock",
    "avg_daily_demand",
    "demand_std_dev",
    "lead_time_days",
    "order_cost",
    "annual_holding_rate",
)

OPTIONAL_DEFAULTS: Final[dict[str, float]] = {
    "units_on_order": 0.0,
    "committed_stock": 0.0,
}

NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "unit_cost",
    "unit_price",
    "current_stock",
    "units_on_order",
    "committed_stock",
    "avg_daily_demand",
    "demand_std_dev",
    "lead_time_days",
    "order_cost",
    "annual_holding_rate",
)

STATUS_ORDER: Final[tuple[str, ...]] = (
    "STOCKOUT",
    "CRITICAL",
    "REORDER",
    "WATCH",
    "HEALTHY",
    "EXCESS",
)


def _normalize_column_name(name: object) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def validate_inventory_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize and validate a client inventory extract.

    Returns a defensive copy with normalized column names and optional numeric
    fields added. All validation errors are collected into one readable
    exception so users can correct their source file in a single pass.
    """

    if frame is None or frame.empty:
        raise InventoryDataError("The uploaded file contains no inventory rows.")

    data = frame.copy(deep=True)
    normalized = [_normalize_column_name(column) for column in data.columns]
    duplicate_columns = sorted(
        {column for column in normalized if normalized.count(column) > 1}
    )
    if duplicate_columns:
        raise InventoryDataError(
            "Duplicate columns after normalization: " + ", ".join(duplicate_columns)
        )
    data.columns = normalized

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]
    if missing_columns:
        raise InventoryDataError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    for column, default in OPTIONAL_DEFAULTS.items():
        if column not in data.columns:
            data[column] = default

    errors: list[str] = []

    for column in ("sku", "product_name", "category"):
        data[column] = data[column].astype("string").str.strip()
        empty_mask = data[column].isna() | data[column].eq("")
        if empty_mask.any():
            errors.append(f"{column}: {int(empty_mask.sum())} blank value(s)")

    duplicated_skus = data.loc[data["sku"].duplicated(keep=False), "sku"].dropna()
    if not duplicated_skus.empty:
        examples = ", ".join(duplicated_skus.astype(str).unique()[:5])
        errors.append(f"sku: duplicate value(s), including {examples}")

    for column in NUMERIC_COLUMNS:
        original = data[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid_mask = converted.isna()
        if invalid_mask.any():
            errors.append(f"{column}: {int(invalid_mask.sum())} missing or non-numeric value(s)")
        data[column] = converted

    if not errors:
        non_negative_columns = [
            column for column in NUMERIC_COLUMNS if column != "annual_holding_rate"
        ]
        for column in non_negative_columns:
            negative_count = int((data[column] < 0).sum())
            if negative_count:
                errors.append(f"{column}: {negative_count} negative value(s)")

        invalid_lead_time = int((data["lead_time_days"] <= 0).sum())
        if invalid_lead_time:
            errors.append(
                f"lead_time_days: {invalid_lead_time} value(s) must be greater than zero"
            )

        invalid_holding_rate = int(
            ((data["annual_holding_rate"] <= 0) | (data["annual_holding_rate"] > 1)).sum()
        )
        if invalid_holding_rate:
            errors.append(
                "annual_holding_rate: "
                f"{invalid_holding_rate} value(s) must be greater than 0 and at most 1"
            )

    if errors:
        raise InventoryDataError("; ".join(errors))

    return data


def _assign_abc_classes(annual_usage_value: pd.Series) -> pd.Series:
    """Assign ABC classes by cumulative annual consumption value.

    A items drive roughly the first 80% of value, B the next 15%, and C the
    remaining 5%. Classification uses the share before each item, ensuring the
    highest-value item is always classified as A.
    """

    values = annual_usage_value.fillna(0).clip(lower=0)
    result = pd.Series("C", index=values.index, dtype="string")
    total = float(values.sum())
    if total <= 0:
        return result

    ordered = values.sort_values(ascending=False, kind="stable")
    share = ordered / total
    share_before_item = share.cumsum() - share
    ordered_classes = np.select(
        [share_before_item < 0.80, share_before_item < 0.95],
        ["A", "B"],
        default="C",
    )
    result.loc[ordered.index] = ordered_classes
    return result


def analyze_inventory(
    frame: pd.DataFrame,
    *,
    service_level: float = 0.95,
    excess_days_threshold: int = 90,
    days_per_year: int = 365,
) -> pd.DataFrame:
    """Calculate replenishment, risk, and working-capital recommendations.

    The model assumes independent daily demand and a continuous-review policy.
    It is a decision-support model: planners remain responsible for supplier
    constraints, minimum order quantities, capacity, and exceptional events.
    """

    if not 0.50 < service_level < 0.999:
        raise ValueError("service_level must be between 0.50 and 0.999")
    if excess_days_threshold <= 0:
        raise ValueError("excess_days_threshold must be greater than zero")
    if days_per_year <= 0:
        raise ValueError("days_per_year must be greater than zero")

    data = validate_inventory_data(frame)
    z_score = NormalDist().inv_cdf(service_level)

    data["annual_demand_units"] = data["avg_daily_demand"] * days_per_year
    data["annual_usage_value"] = data["annual_demand_units"] * data["unit_cost"]
    data["inventory_value"] = data["current_stock"] * data["unit_cost"]
    data["annual_holding_cost"] = (
        data["inventory_value"] * data["annual_holding_rate"]
    )

    data["lead_time_demand"] = data["avg_daily_demand"] * data["lead_time_days"]
    data["safety_stock"] = (
        z_score * data["demand_std_dev"] * np.sqrt(data["lead_time_days"])
    )
    data["reorder_point"] = data["lead_time_demand"] + data["safety_stock"]

    holding_cost_per_unit = data["unit_cost"] * data["annual_holding_rate"]
    eoq_numerator = 2 * data["annual_demand_units"] * data["order_cost"]
    data["eoq"] = np.where(
        (holding_cost_per_unit > 0) & (data["annual_demand_units"] > 0),
        np.sqrt(eoq_numerator / holding_cost_per_unit),
        0.0,
    )

    data["available_stock"] = data["current_stock"] - data["committed_stock"]
    data["inventory_position"] = data["available_stock"] + data["units_on_order"]
    data["target_stock"] = data["reorder_point"] + data["eoq"]

    should_reorder = data["inventory_position"] <= data["reorder_point"]
    order_gap = (data["target_stock"] - data["inventory_position"]).clip(lower=0)
    data["recommended_order_qty"] = np.where(
        should_reorder,
        np.ceil(order_gap),
        0,
    ).astype(int)
    data["suggested_purchase_cost"] = (
        data["recommended_order_qty"] * data["unit_cost"]
    )

    data["days_of_supply"] = np.where(
        data["avg_daily_demand"] > 0,
        data["available_stock"].clip(lower=0) / data["avg_daily_demand"],
        np.inf,
    )
    data["reorder_gap_units"] = (
        data["reorder_point"] - data["inventory_position"]
    ).clip(lower=0)
    data["projected_shortfall_units"] = (
        data["lead_time_demand"] - data["inventory_position"]
    ).clip(lower=0)
    data["gross_margin_per_unit"] = (
        data["unit_price"] - data["unit_cost"]
    ).clip(lower=0)
    data["margin_at_risk"] = (
        data["projected_shortfall_units"] * data["gross_margin_per_unit"]
    )
    data["excess_units"] = (
        data["inventory_position"] - data["target_stock"]
    ).clip(lower=0)
    data["excess_capital"] = data["excess_units"] * data["unit_cost"]

    stockout = data["available_stock"] <= 0
    critical = (~stockout) & (data["inventory_position"] <= data["safety_stock"])
    reorder = (
        (~stockout)
        & (~critical)
        & (data["inventory_position"] <= data["reorder_point"])
    )
    excess = (
        (data["days_of_supply"] >= excess_days_threshold)
        & (data["inventory_position"] > data["target_stock"])
    )
    watch = (
        (~stockout)
        & (~critical)
        & (~reorder)
        & (~excess)
        & (data["inventory_position"] <= data["reorder_point"] + 0.5 * data["eoq"])
    )

    data["inventory_status"] = np.select(
        [stockout, critical, reorder, excess, watch],
        ["STOCKOUT", "CRITICAL", "REORDER", "EXCESS", "WATCH"],
        default="HEALTHY",
    )

    data["abc_class"] = _assign_abc_classes(data["annual_usage_value"])
    status_score = data["inventory_status"].map(
        {
            "STOCKOUT": 100,
            "CRITICAL": 85,
            "REORDER": 65,
            "WATCH": 35,
            "HEALTHY": 10,
            "EXCESS": 5,
        }
    )
    abc_weight = data["abc_class"].map({"A": 15, "B": 8, "C": 3})
    data["priority_score"] = (status_score + abc_weight).clip(upper=100).astype(int)

    data["service_level"] = service_level
    data["service_level_pct"] = service_level * 100

    quantity_columns = [
        "annual_demand_units",
        "lead_time_demand",
        "safety_stock",
        "reorder_point",
        "eoq",
        "available_stock",
        "inventory_position",
        "target_stock",
        "reorder_gap_units",
        "projected_shortfall_units",
        "excess_units",
    ]
    currency_columns = [
        "annual_usage_value",
        "inventory_value",
        "annual_holding_cost",
        "suggested_purchase_cost",
        "gross_margin_per_unit",
        "margin_at_risk",
        "excess_capital",
    ]
    data[quantity_columns] = data[quantity_columns].round(1)
    data[currency_columns] = data[currency_columns].round(2)
    data["days_of_supply"] = data["days_of_supply"].replace(np.inf, np.nan).round(1)

    return data.sort_values(
        ["priority_score", "annual_usage_value"],
        ascending=[False, False],
        kind="stable",
    ).reset_index(drop=True)


def calculate_kpis(analyzed: pd.DataFrame) -> dict[str, float | int]:
    """Return executive KPIs for an analyzed inventory table."""

    if analyzed is None or analyzed.empty:
        return {
            "sku_count": 0,
            "inventory_value": 0.0,
            "at_risk_skus": 0,
            "reorder_skus": 0,
            "recommended_order_value": 0.0,
            "margin_at_risk": 0.0,
            "excess_capital": 0.0,
        }

    at_risk = analyzed["inventory_status"].isin(
        ["STOCKOUT", "CRITICAL", "REORDER"]
    )
    return {
        "sku_count": int(analyzed["sku"].nunique()),
        "inventory_value": float(analyzed["inventory_value"].sum()),
        "at_risk_skus": int(at_risk.sum()),
        "reorder_skus": int((analyzed["recommended_order_qty"] > 0).sum()),
        "recommended_order_value": float(analyzed["suggested_purchase_cost"].sum()),
        "margin_at_risk": float(analyzed["margin_at_risk"].sum()),
        "excess_capital": float(analyzed["excess_capital"].sum()),
    }
