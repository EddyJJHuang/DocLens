# Demand-planning business glossary

## Lead time
The number of days between placing a purchase order and receiving the goods.
Stored in `suppliers.lead_time_days`. Longer lead times require larger safety stock.

## Safety stock
Buffer inventory held to absorb variability in demand and supply, so a stockout
is unlikely during the lead time. Stored in `inventory.safety_stock`.

## Reorder point
The inventory level that triggers a replenishment order. It equals the safety
stock plus the expected demand during the lead time. Stored in
`inventory.reorder_point`. If `units_on_hand` falls below `reorder_point`, the
item should be reordered.

## Stockout risk
A product/region is at stockout risk when `units_on_hand` is at or below
`reorder_point` (or below `safety_stock` for high risk).

## Forecast horizon
How far into the future a forecast looks, in days (`demand_forecasts.horizon_days`).

## On-hand inventory
Units currently available in stock (`inventory.units_on_hand`).

## Reliability score
A supplier's historical on-time delivery rate, from 0 to 1
(`suppliers.reliability_score`). Higher is better.

## Revenue
Sales value for a product/region/month: `sales_history.revenue`
(= `units_sold` * `unit_price`).

## Gross margin
`unit_price - unit_cost` per unit; margin rate is `(unit_price - unit_cost) / unit_price`.
