-- DocLens sample demand-planning database.
-- ALL DATA IS SYNTHETIC — a generated sample dataset, not real company data.
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS demand_forecasts;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS sales_history;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS regions;

-- Sales/operating regions.
CREATE TABLE regions (
    region_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    country   TEXT NOT NULL
);

-- Component suppliers, each based in a region.
CREATE TABLE suppliers (
    supplier_id       INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,
    region_id         INTEGER NOT NULL REFERENCES regions(region_id),
    lead_time_days    INTEGER NOT NULL,  -- avg days from purchase order to delivery
    reliability_score REAL    NOT NULL   -- historical on-time delivery rate, 0..1
);

-- Product catalog (EV-component flavored, synthetic).
CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    unit_cost   REAL NOT NULL,  -- landed cost to the company
    unit_price  REAL NOT NULL,  -- sale price
    supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id)
);

-- Monthly units sold and revenue, per product per region.
CREATE TABLE sales_history (
    sale_id    INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    region_id  INTEGER NOT NULL REFERENCES regions(region_id),
    sale_month TEXT    NOT NULL,  -- first day of month, 'YYYY-MM-01'
    units_sold INTEGER NOT NULL,
    revenue    REAL    NOT NULL   -- units_sold * unit_price
);

-- Monthly inventory snapshots, per product per region.
CREATE TABLE inventory (
    inventory_id   INTEGER PRIMARY KEY,
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    region_id      INTEGER NOT NULL REFERENCES regions(region_id),
    snapshot_month TEXT    NOT NULL,  -- 'YYYY-MM-01'
    units_on_hand  INTEGER NOT NULL,
    safety_stock   INTEGER NOT NULL,  -- buffer stock to absorb demand variability
    reorder_point  INTEGER NOT NULL   -- on-hand level that triggers replenishment
);

-- Forward-looking demand forecasts, per product per region.
CREATE TABLE demand_forecasts (
    forecast_id     INTEGER PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    region_id       INTEGER NOT NULL REFERENCES regions(region_id),
    forecast_month  TEXT    NOT NULL,  -- 'YYYY-MM-01'
    horizon_days    INTEGER NOT NULL,  -- how far ahead the forecast looks
    forecast_units  INTEGER NOT NULL,
    forecast_method TEXT    NOT NULL   -- moving_average | exp_smoothing | linear_trend
);

CREATE INDEX idx_sales_product   ON sales_history(product_id);
CREATE INDEX idx_sales_region    ON sales_history(region_id);
CREATE INDEX idx_sales_month     ON sales_history(sale_month);
CREATE INDEX idx_inv_product     ON inventory(product_id);
CREATE INDEX idx_forecast_product ON demand_forecasts(product_id);
