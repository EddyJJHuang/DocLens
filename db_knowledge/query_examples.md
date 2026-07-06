# Example questions and SQL

Reference patterns for common demand-planning questions. Each example is a
question paired with a correct, read-only SQLite SELECT.

## Top products by total revenue
Q: Which products have the highest total revenue?
```sql
SELECT p.name, SUM(sh.revenue) AS total_revenue
FROM sales_history sh
JOIN products p ON p.product_id = sh.product_id
GROUP BY p.product_id, p.name
ORDER BY total_revenue DESC
LIMIT 10;
```

## Revenue by region
Q: What is the total revenue per region?
```sql
SELECT r.name AS region, SUM(sh.revenue) AS total_revenue
FROM sales_history sh
JOIN regions r ON r.region_id = sh.region_id
GROUP BY r.region_id, r.name
ORDER BY total_revenue DESC;
```

## Product count per category
Q: How many products are in each category?
```sql
SELECT category, COUNT(*) AS product_count
FROM products
GROUP BY category
ORDER BY product_count DESC;
```

## Monthly sales trend for a product
Q: Show the monthly units sold for the Battery Module over time.
```sql
SELECT sh.sale_month, SUM(sh.units_sold) AS units
FROM sales_history sh
JOIN products p ON p.product_id = sh.product_id
WHERE p.name = 'Battery Module'
GROUP BY sh.sale_month
ORDER BY sh.sale_month;
```

## Products at stockout risk (latest snapshot)
Q: Which products are at risk of stockout right now?
```sql
SELECT p.name, r.name AS region, i.units_on_hand, i.reorder_point
FROM inventory i
JOIN products p ON p.product_id = i.product_id
JOIN regions r ON r.region_id = i.region_id
WHERE i.snapshot_month = (SELECT MAX(snapshot_month) FROM inventory)
  AND i.units_on_hand <= i.reorder_point
ORDER BY (i.reorder_point - i.units_on_hand) DESC
LIMIT 20;
```

## Suppliers ranked by lead time
Q: Which suppliers have the longest lead times?
```sql
SELECT name, lead_time_days, reliability_score
FROM suppliers
ORDER BY lead_time_days DESC
LIMIT 10;
```

## Forecast vs recent sales for a product
Q: Compare the upcoming forecast to recent sales for the Onboard Charger.
```sql
SELECT df.forecast_month, SUM(df.forecast_units) AS forecast_units
FROM demand_forecasts df
JOIN products p ON p.product_id = df.product_id
WHERE p.name = 'Onboard Charger'
GROUP BY df.forecast_month
ORDER BY df.forecast_month;
```

## Highest-margin products
Q: Which products have the highest gross margin per unit?
```sql
SELECT name, unit_price - unit_cost AS unit_margin,
       ROUND((unit_price - unit_cost) / unit_price, 3) AS margin_rate
FROM products
ORDER BY unit_margin DESC
LIMIT 10;
```

## Total units sold by region in a date range
Q: How many units were sold per region in the first half of 2026?
```sql
SELECT r.name AS region, SUM(sh.units_sold) AS units
FROM sales_history sh
JOIN regions r ON r.region_id = sh.region_id
WHERE sh.sale_month BETWEEN '2026-01-01' AND '2026-06-01'
GROUP BY r.region_id, r.name
ORDER BY units DESC;
```
