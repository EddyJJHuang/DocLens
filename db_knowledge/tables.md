# Database schema reference

The demand-planning database has six tables. Months are stored as text in
`YYYY-MM-01` format (the first day of the month). Compare months as strings.

## regions
Sales/operating regions.
- `region_id` (INTEGER, PK)
- `name` (TEXT) — e.g. "North America", "Europe", "Greater China"
- `country` (TEXT) — representative country for the region

## suppliers
Component suppliers, each based in a region.
- `supplier_id` (INTEGER, PK)
- `name` (TEXT)
- `region_id` (INTEGER, FK -> regions.region_id)
- `lead_time_days` (INTEGER) — average days from purchase order to delivery
- `reliability_score` (REAL, 0..1) — historical on-time delivery rate

## products
Product catalog (EV-component themed).
- `product_id` (INTEGER, PK)
- `sku` (TEXT, unique)
- `name` (TEXT) — e.g. "Battery Module", "Onboard Charger"
- `category` (TEXT) — e.g. Battery, Powertrain, Charging, Interior, Chassis, Electronics
- `unit_cost` (REAL) — landed cost to the company
- `unit_price` (REAL) — sale price
- `supplier_id` (INTEGER, FK -> suppliers.supplier_id)

## sales_history
Monthly units sold and revenue, per product per region.
- `sale_id` (INTEGER, PK)
- `product_id` (INTEGER, FK -> products.product_id)
- `region_id` (INTEGER, FK -> regions.region_id)
- `sale_month` (TEXT, 'YYYY-MM-01')
- `units_sold` (INTEGER)
- `revenue` (REAL) — equals units_sold * unit_price

## inventory
Monthly inventory snapshots, per product per region.
- `inventory_id` (INTEGER, PK)
- `product_id` (INTEGER, FK -> products.product_id)
- `region_id` (INTEGER, FK -> regions.region_id)
- `snapshot_month` (TEXT, 'YYYY-MM-01')
- `units_on_hand` (INTEGER) — stock currently available
- `safety_stock` (INTEGER) — buffer stock kept to absorb variability
- `reorder_point` (INTEGER) — on-hand level that triggers replenishment

## demand_forecasts
Forward-looking demand forecasts, per product per region.
- `forecast_id` (INTEGER, PK)
- `product_id` (INTEGER, FK -> products.product_id)
- `region_id` (INTEGER, FK -> regions.region_id)
- `forecast_month` (TEXT, 'YYYY-MM-01')
- `horizon_days` (INTEGER) — how far ahead the forecast looks
- `forecast_units` (INTEGER)
- `forecast_method` (TEXT) — moving_average | exp_smoothing | linear_trend
