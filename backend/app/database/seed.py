"""Seed a synthetic demand-planning SQLite database for DocLens.

ALL DATA IS SYNTHETIC sample data for a demo. It is themed around
EV-component demand planning but does not represent any real company.

Run:  python -m app.database.seed
Output: <DATA_DIR>/doclens.db
"""
from __future__ import annotations

import logging
import random
import sqlite3
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(settings.data_dir) / "doclens.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

RANDOM_SEED = 42
N_HISTORY_MONTHS = 24          # months of sales/inventory history
N_FORECAST_MONTHS = 6          # months of forward forecasts
ANCHOR_YEAR, ANCHOR_MONTH = 2026, 6  # history ends at this month (fixed for reproducibility)

REGIONS = [
    ("North America", "USA"),
    ("Europe", "Germany"),
    ("Greater China", "China"),
    ("Asia Pacific", "Japan"),
    ("Middle East", "UAE"),
    ("Latin America", "Brazil"),
]
# Relative market size per region (drives baseline demand).
REGION_WEIGHTS = [1.0, 0.8, 0.9, 0.5, 0.25, 0.2]

SUPPLIER_NAMES = [
    "Volt Dynamics", "CoreCell Industries", "Apex Powertrain", "Nimbus Electronics",
    "Meridian Components", "Ironforge Manufacturing", "BlueArc Systems", "Helio Materials",
    "Quantum Drive Co", "Summit Fabrication", "Orion Modules", "Vertex Assemblies",
]

# category -> list of product base names
CATALOG = {
    "Battery": ["Battery Module", "Battery Pack", "Cell Cooling Plate", "BMS Controller"],
    "Powertrain": ["Drive Unit", "Inverter", "Stator Assembly"],
    "Charging": ["Onboard Charger", "Charge Port", "Charging Cable"],
    "Interior": ["Seat Frame", "Touchscreen Display", "Cabin Air Filter"],
    "Chassis": ["Brake Pad Set", "Suspension Arm", "Wheel Bearing"],
    "Electronics": ["Autopilot Camera", "Radar Sensor", "Ultrasonic Sensor"],
    "Thermal": ["Heat Pump", "Coolant Compressor"],
    "Body": ["Door Handle", "Mirror Assembly", "Frunk Latch"],
}
# Rough cost band per category: (unit_cost_low, unit_cost_high, margin).
CATEGORY_COST = {
    "Battery": (400, 9000, 0.28), "Powertrain": (600, 4000, 0.30),
    "Charging": (40, 500, 0.35), "Interior": (30, 900, 0.45),
    "Chassis": (25, 300, 0.40), "Electronics": (50, 700, 0.50),
    "Thermal": (120, 600, 0.33), "Body": (15, 200, 0.55),
}


def _month_iter(count: int, end_year: int, end_month: int, offset: int = 0):
    """Yield 'YYYY-MM-01' strings, oldest first, ending `offset` months after (end_year, end_month)."""
    # Absolute month index of the end anchor, then walk backwards/forwards.
    end_idx = end_year * 12 + (end_month - 1) + offset
    start_idx = end_idx - (count - 1)
    for idx in range(start_idx, end_idx + 1):
        year, month = divmod(idx, 12)
        yield f"{year:04d}-{month + 1:02d}-01"


def _seasonal_factor(month_str: str) -> float:
    """Mild seasonality: stronger in Q2/Q4."""
    month = int(month_str[5:7])
    return 1.0 + 0.15 * (1 if month in (3, 4, 5, 10, 11, 12) else -1)


def _build_reference_data(rng: random.Random):
    regions = [(i + 1, name, country) for i, (name, country) in enumerate(REGIONS)]

    suppliers = []
    for i, name in enumerate(SUPPLIER_NAMES):
        region_id = (i % len(regions)) + 1
        lead_time = rng.choice([21, 30, 45, 60, 75, 90])
        reliability = round(rng.uniform(0.82, 0.99), 3)
        suppliers.append((i + 1, name, region_id, lead_time, reliability))

    products = []
    pid = 1
    flat = [(cat, name) for cat, names in CATALOG.items() for name in names]
    for cat, name in flat:
        low, high, margin = CATEGORY_COST[cat]
        unit_cost = round(rng.uniform(low, high), 2)
        unit_price = round(unit_cost * (1 + margin), 2)
        supplier_id = ((pid - 1) % len(suppliers)) + 1
        sku = f"{cat[:3].upper()}-{pid:04d}"
        products.append((pid, sku, name, cat, unit_cost, unit_price, supplier_id))
        pid += 1

    # Per-product baseline monthly demand (region-1 scale) and growth trend.
    product_baseline = {p[0]: rng.randint(80, 1200) for p in products}
    product_trend = {p[0]: rng.uniform(-0.01, 0.03) for p in products}  # monthly growth
    return regions, suppliers, products, product_baseline, product_trend


def _generate_rows(rng, regions, products, baseline, trend):
    history_months = list(_month_iter(N_HISTORY_MONTHS, ANCHOR_YEAR, ANCHOR_MONTH))
    price_by_product = {p[0]: p[5] for p in products}

    sales, inventory, forecasts = [], [], []
    sale_id = inv_id = fc_id = 1

    for (pid, *_rest) in products:
        base = baseline[pid]
        growth = trend[pid]
        for region in regions:
            region_id, _name, _country = region
            weight = REGION_WEIGHTS[region_id - 1]
            monthly_units = []
            for m_idx, month in enumerate(history_months):
                trend_mult = (1 + growth) ** m_idx
                seasonal = _seasonal_factor(month)
                noise = rng.uniform(0.85, 1.15)
                units = max(0, int(base * weight * trend_mult * seasonal * noise))
                monthly_units.append(units)
                revenue = round(units * price_by_product[pid], 2)
                sales.append((sale_id, pid, region_id, month, units, revenue))
                sale_id += 1

            # Inventory snapshots for the last 12 months, tied to demand + safety stock.
            avg_recent = max(1, sum(monthly_units[-6:]) // 6)
            safety = int(avg_recent * rng.uniform(0.3, 0.6))
            reorder = safety + int(avg_recent * rng.uniform(0.8, 1.2))
            for month in history_months[-12:]:
                on_hand = max(0, int(reorder * rng.uniform(0.4, 1.6)))
                inventory.append((inv_id, pid, region_id, month, on_hand, safety, reorder))
                inv_id += 1

            # Forward forecasts anchored to recent average with the product trend.
            recent_avg = max(1, sum(monthly_units[-3:]) // 3)
            method = rng.choice(["moving_average", "exp_smoothing", "linear_trend"])
            for h_idx, month in enumerate(
                _month_iter(N_FORECAST_MONTHS, ANCHOR_YEAR, ANCHOR_MONTH, offset=N_FORECAST_MONTHS)
            ):
                proj = int(recent_avg * ((1 + growth) ** (h_idx + 1)) * rng.uniform(0.95, 1.05))
                forecasts.append((fc_id, pid, region_id, month, (h_idx + 1) * 30, proj, method))
                fc_id += 1

    return sales, inventory, forecasts


def seed_database(db_path: Path = DB_PATH) -> Path:
    """(Re)build the synthetic demand-planning database. Returns the DB path."""
    rng = random.Random(RANDOM_SEED)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    regions, suppliers, products, baseline, trend = _build_reference_data(rng)
    sales, inventory, forecasts = _generate_rows(rng, regions, products, baseline, trend)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.executemany("INSERT INTO regions VALUES (?, ?, ?)", regions)
        conn.executemany("INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)", suppliers)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", products)
        conn.executemany("INSERT INTO sales_history VALUES (?, ?, ?, ?, ?, ?)", sales)
        conn.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?)", inventory)
        conn.executemany("INSERT INTO demand_forecasts VALUES (?, ?, ?, ?, ?, ?, ?)", forecasts)
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Seeded %s: %d regions, %d suppliers, %d products, %d sales, %d inventory, %d forecasts",
        db_path, len(regions), len(suppliers), len(products), len(sales), len(inventory), len(forecasts),
    )
    return db_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = seed_database()
    print(f"Seeded synthetic demand-planning DB at: {path}")
