# Upwork Portfolio Case Study

## Recommended title

**Inventory Control Tower | Python Replenishment & Risk Intelligence**

## Short description

In 2020, I built a professional Python application that converts an inventory CSV into a prioritized replenishment plan. The tool validates client data, calculates safety stock, reorder points and EOQ, classifies SKUs by ABC value, flags stockout and excess risk, and produces downloadable buyer action lists through an interactive Streamlit dashboard.

## Full portfolio description

### The business problem

Inventory decisions are often spread across manual spreadsheets. Planners can see stock quantities, but they may not have one controlled view showing which items require action, how much to order, what margin is exposed, or where excess inventory is tying up cash.

### My solution

I designed and developed a reusable Python decision-support application with a clear separation between the calculation engine and the user interface. A user can upload an inventory CSV, choose a service level and excess-stock threshold, filter the portfolio, review executive KPIs, and export a purchase action list.

The calculation engine includes:

- data-schema validation and readable exception messages;
- safety stock and reorder point calculations;
- Economic Order Quantity (EOQ);
- net inventory position using on-hand, committed, and inbound quantities;
- recommended order quantity and purchase value;
- ABC segmentation by annual usage value;
- margin-at-risk and excess-capital estimates; and
- a transparent operational priority score.

### Business value

The application turns a raw operational extract into a repeatable decision process. It helps a buyer or inventory planner focus first on high-value stockout risks, quantify the proposed purchase requirement, and identify inventory positions that may deserve a working-capital review.

In the included 60-SKU synthetic demonstration, the default model identifies 26 replenishment lines, calculates a CAD 376,128.17 proposed purchase requirement, and highlights CAD 18,142.87 in modeled margin exposure. These are reproducible demonstration outputs, not claimed client performance results.

### Quality and delivery

I included a realistic 60-SKU synthetic dataset, a blank upload template, regression tests, continuous-integration configuration, a data dictionary, calculation assumptions, and a client handoff guide. The project is designed as a portfolio demonstration and can be extended to SAP, another ERP, a database, or an API.

## Suggested Upwork skills

Python · Pandas · Streamlit · Data Analysis · Inventory Management · Supply Chain · Process Optimization · Business Analysis · Data Visualization · ERP

## Suggested role

**Python Developer / Business Process Analyst**

## Suggested cover caption

**From raw inventory data to a prioritized purchase plan.**

## Honest disclosure

This is a portfolio demonstration built with synthetic data. It represents client-ready delivery quality without identifying or claiming a confidential client engagement.
