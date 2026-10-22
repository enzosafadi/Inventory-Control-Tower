# Data Dictionary and Calculation Specification

## Input fields

| Field | Required | Type | Validation | Business definition |
|---|---:|---|---|---|
| `sku` | Yes | Text | Unique, nonblank | Stock-keeping unit identifier |
| `product_name` | Yes | Text | Nonblank | Human-readable item description |
| `category` | Yes | Text | Nonblank | Product or procurement category |
| `supplier` | No | Text | None | Preferred or current supplier |
| `unit_cost` | Yes | Decimal | ≥ 0 | Landed or standard unit cost |
| `unit_price` | Yes | Decimal | ≥ 0 | Selling price used to estimate gross-margin exposure |
| `current_stock` | Yes | Number | ≥ 0 | Physical on-hand quantity at extraction time |
| `units_on_order` | No | Number | ≥ 0; defaults to 0 | Confirmed open inbound purchase quantity |
| `committed_stock` | No | Number | ≥ 0; defaults to 0 | On-hand stock already allocated to demand |
| `avg_daily_demand` | Yes | Decimal | ≥ 0 | Mean units consumed per calendar day |
| `demand_std_dev` | Yes | Decimal | ≥ 0 | Standard deviation of daily unit demand |
| `lead_time_days` | Yes | Decimal | > 0 | Calendar days from order placement to availability |
| `order_cost` | Yes | Decimal | ≥ 0 | Administrative and transaction cost per order |
| `annual_holding_rate` | Yes | Decimal | > 0 and ≤ 1 | Annual holding-cost percentage expressed as a decimal |

Column names are normalized to lowercase snake case. Spaces, hyphens, and slashes are converted to underscores.

## Derived fields

| Field | Definition |
|---|---|
| `annual_demand_units` | `avg_daily_demand × 365` |
| `annual_usage_value` | `annual_demand_units × unit_cost` |
| `inventory_value` | `current_stock × unit_cost` |
| `annual_holding_cost` | `inventory_value × annual_holding_rate` |
| `lead_time_demand` | `avg_daily_demand × lead_time_days` |
| `safety_stock` | `z(service_level) × demand_std_dev × √lead_time_days` |
| `reorder_point` | `lead_time_demand + safety_stock` |
| `eoq` | `√(2 × annual_demand_units × order_cost ÷ (unit_cost × annual_holding_rate))` |
| `available_stock` | `current_stock − committed_stock` |
| `inventory_position` | `available_stock + units_on_order` |
| `target_stock` | `reorder_point + eoq` |
| `recommended_order_qty` | If inventory position ≤ reorder point, round up `target_stock − inventory_position`; otherwise 0 |
| `suggested_purchase_cost` | `recommended_order_qty × unit_cost` |
| `days_of_supply` | `max(available_stock, 0) ÷ avg_daily_demand` |
| `reorder_gap_units` | `max(reorder_point − inventory_position, 0)` |
| `projected_shortfall_units` | `max(lead_time_demand − inventory_position, 0)` |
| `gross_margin_per_unit` | `max(unit_price − unit_cost, 0)` |
| `margin_at_risk` | `projected_shortfall_units × gross_margin_per_unit` |
| `excess_units` | `max(inventory_position − target_stock, 0)` |
| `excess_capital` | `excess_units × unit_cost` |

## ABC classification

Items are sorted by annual usage value from highest to lowest. Class A covers items contributing to approximately the first 80% of annual usage value, class B the next 15%, and class C the remaining 5%. The boundary item remains in the class it causes to cross, ensuring the highest-value item is always class A.

## Priority score

The priority score is a transparent triage aid, not an optimization objective.

| Component | Points |
|---|---:|
| Stockout | 100 base |
| Critical | 85 base |
| Reorder | 65 base |
| Watch | 35 base |
| Healthy | 10 base |
| Excess | 5 base |
| ABC A / B / C | +15 / +8 / +3 |

The final score is capped at 100. It helps planners order the work queue; the financial and operational fields remain the decision evidence.

## Modeling assumptions

- Daily demand is independent and sufficiently approximated by a normal distribution.
- Lead time is represented by one current expected value.
- Service level is global for the analyzed run.
- Cost and price fields use the selected reporting currency without conversion.
- Inbound quantities are assumed valid and available within the relevant replenishment horizon.
- No supplier MOQ, case-pack, shelf-life, capacity, or budget constraints are modeled.
