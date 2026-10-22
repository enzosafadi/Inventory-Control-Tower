"""Inventory optimization engine used by the Streamlit application."""

from .analysis import (
    InventoryDataError,
    analyze_inventory,
    calculate_kpis,
    validate_inventory_data,
)

__all__ = [
    "InventoryDataError",
    "analyze_inventory",
    "calculate_kpis",
    "validate_inventory_data",
]

__version__ = "1.0.0"
