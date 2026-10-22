"""Generate a deterministic, realistic inventory demo dataset."""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "sample_inventory.csv"
SEED = 2020

CATEGORY_CONFIG = {
    "Electrical": {
        "prefix": "ELC",
        "cost": (18, 180),
        "demand": (1.5, 15),
        "lead": (12, 42),
        "products": [
            "Servo Drive",
            "Proximity Sensor",
            "Control Relay",
            "Power Supply",
            "Encoder Module",
            "Industrial Switch",
            "Terminal Block",
            "Circuit Breaker",
            "Signal Converter",
            "Motor Starter",
        ],
    },
    "Mechanical": {
        "prefix": "MEC",
        "cost": (8, 125),
        "demand": (2, 20),
        "lead": (7, 35),
        "products": [
            "Precision Bearing",
            "Shaft Coupling",
            "Drive Belt",
            "Linear Guide",
            "Gear Assembly",
            "Pneumatic Cylinder",
            "Valve Actuator",
            "Timing Pulley",
            "Rotary Seal",
            "Vibration Mount",
        ],
    },
    "Fasteners": {
        "prefix": "FST",
        "cost": (0.12, 4.5),
        "demand": (18, 95),
        "lead": (3, 18),
        "products": [
            "Hex Bolt",
            "Lock Nut",
            "Flat Washer",
            "Socket Screw",
            "Spring Pin",
            "Threaded Insert",
            "Retaining Ring",
            "Machine Screw",
            "Anchor Bolt",
            "Rivet Nut",
        ],
    },
    "Packaging": {
        "prefix": "PKG",
        "cost": (0.2, 12),
        "demand": (8, 65),
        "lead": (4, 21),
        "products": [
            "Shipping Carton",
            "Protective Insert",
            "Stretch Film",
            "Barcode Label",
            "Poly Mailer",
            "Foam Sheet",
            "Packing Tape",
            "Corner Protector",
            "Pallet Cover",
            "Document Pouch",
        ],
    },
    "Safety": {
        "prefix": "SAF",
        "cost": (3, 75),
        "demand": (1, 12),
        "lead": (5, 28),
        "products": [
            "Safety Glasses",
            "Cut-Resistant Gloves",
            "Hearing Protection",
            "Face Shield",
            "Respirator Cartridge",
            "High-Visibility Vest",
            "Protective Helmet",
            "Spill Kit",
            "First Aid Refill",
            "Safety Harness",
        ],
    },
    "MRO Supplies": {
        "prefix": "MRO",
        "cost": (4, 95),
        "demand": (1, 18),
        "lead": (4, 30),
        "products": [
            "Industrial Lubricant",
            "Cleaning Solvent",
            "Shop Towel Roll",
            "Cutting Fluid",
            "Adhesive Sealant",
            "Abrasive Disc",
            "Filter Element",
            "Maintenance Spray",
            "Grease Cartridge",
            "Welding Wire",
        ],
    },
}

SUPPLIERS = [
    "Atlas Industrial",
    "Boreal Components",
    "Crown Supply Group",
    "Delta Motion",
    "Evergreen Safety",
    "Northline Packaging",
    "Precision Source",
    "Summit MRO",
]


def build_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED)
    rows: list[dict[str, object]] = []
    stock_factors = [0.0, 0.22, 0.48, 0.75, 0.95, 1.15, 1.55, 2.4, 3.8]
    stock_weights = [2, 4, 7, 10, 12, 17, 18, 15, 8]

    for category, config in CATEGORY_CONFIG.items():
        for index, product in enumerate(config["products"], start=1):
            cost = round(rng.uniform(*config["cost"]), 2)
            margin_rate = rng.uniform(0.22, 0.46)
            price = round(cost / (1 - margin_rate), 2)
            avg_demand = round(rng.uniform(*config["demand"]), 2)
            demand_std = round(avg_demand * rng.uniform(0.14, 0.48), 2)
            lead_time = rng.randint(*config["lead"])
            lead_demand = avg_demand * lead_time
            estimated_safety_stock = 1.645 * demand_std * math.sqrt(lead_time)
            estimated_reorder_point = lead_demand + estimated_safety_stock
            stock_factor = rng.choices(stock_factors, weights=stock_weights, k=1)[0]
            current_stock = max(0, round(estimated_reorder_point * stock_factor))

            if stock_factor <= 0.75 and rng.random() < 0.44:
                units_on_order = round(estimated_reorder_point * rng.uniform(0.35, 1.05))
            else:
                units_on_order = 0

            committed_stock = (
                round(current_stock * rng.uniform(0.02, 0.18)) if current_stock else 0
            )
            descriptor = rng.choice(
                ["Standard", "Premium", "Compact", "Heavy-Duty", "Series X", "Pro"]
            )

            rows.append(
                {
                    "sku": f"{config['prefix']}-{index:03d}",
                    "product_name": f"{product} {descriptor}",
                    "category": category,
                    "supplier": rng.choice(SUPPLIERS),
                    "unit_cost": cost,
                    "unit_price": price,
                    "current_stock": current_stock,
                    "units_on_order": units_on_order,
                    "committed_stock": committed_stock,
                    "avg_daily_demand": avg_demand,
                    "demand_std_dev": demand_std,
                    "lead_time_days": lead_time,
                    "order_cost": round(rng.uniform(28, 165), 2),
                    "annual_holding_rate": round(rng.uniform(0.18, 0.32), 2),
                }
            )

    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {OUTPUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
