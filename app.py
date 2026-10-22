"""Streamlit front end for Inventory Control Tower."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from inventory_optimizer import (
    InventoryDataError,
    analyze_inventory,
    calculate_kpis,
)
from inventory_optimizer.analysis import STATUS_ORDER


ROOT = Path(__file__).resolve().parent
DEMO_FILE = ROOT / "data" / "sample_inventory.csv"
TEMPLATE_FILE = ROOT / "data" / "inventory_upload_template.csv"

COLORS = {
    "navy": "#102238",
    "blue": "#2A6FDB",
    "teal": "#17A89A",
    "amber": "#F3A712",
    "red": "#E05263",
    "purple": "#725AC1",
    "slate": "#60758A",
    "light": "#F4F7FA",
}

STATUS_COLORS = {
    "STOCKOUT": "#9F1239",
    "CRITICAL": "#E05263",
    "REORDER": "#F3A712",
    "WATCH": "#725AC1",
    "HEALTHY": "#17A89A",
    "EXCESS": "#2A6FDB",
}


st.set_page_config(
    page_title="Inventory Control Tower | Braulio",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #F4F7FA; }
      [data-testid="stSidebar"] { background: #102238; }
      [data-testid="stSidebar"] * { color: #F8FAFC; }
      [data-testid="stSidebar"] input,
      [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] [data-baseweb="select"] * { color: #102238; }
      [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E5EAF0;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 3px 12px rgba(16, 34, 56, 0.05);
      }
      [data-testid="stMetricLabel"] { color: #60758A; }
      [data-testid="stMetricValue"] { color: #102238; font-weight: 700; }
      .hero {
        background: linear-gradient(115deg, #102238 0%, #193B5A 58%, #176B75 100%);
        padding: 28px 32px;
        border-radius: 18px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 30px rgba(16, 34, 56, 0.15);
      }
      .hero-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #71E0D3;
        margin-bottom: 7px;
      }
      .hero h1 { margin: 0 0 6px 0; font-size: 34px; line-height: 1.15; }
      .hero p { margin: 0; color: #D5E2EC; font-size: 15px; }
      .section-note { color: #60758A; font-size: 13px; margin-top: -10px; }
      .insight-card {
        background: white;
        border-left: 4px solid #17A89A;
        border-radius: 10px;
        padding: 14px 16px;
        min-height: 94px;
        box-shadow: 0 3px 12px rgba(16, 34, 56, 0.04);
      }
      .insight-title { color: #60758A; font-size: 12px; font-weight: 700; text-transform: uppercase; }
      .insight-value { color: #102238; font-size: 17px; font-weight: 700; margin-top: 5px; }
      .insight-copy { color: #60758A; font-size: 12px; margin-top: 3px; }
      .footer { color: #7A8A9A; font-size: 12px; text-align: center; margin: 28px 0 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_money(value: float, currency: str, decimals: int = 0) -> str:
    return f"{currency} {value:,.{decimals}f}"


def load_source(uploaded_file) -> tuple[pd.DataFrame, str]:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file), uploaded_file.name
    return pd.read_csv(DEMO_FILE), "Professional demo dataset"


def chart_layout(figure, *, height: int = 355) -> None:
    figure.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["navy"], family="Arial"),
        title_font=dict(size=16),
        legend_title_text="",
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#E8EDF2", zeroline=False)


def render_insight(title: str, value: str, copy: str) -> None:
    safe_title = escape(str(title))
    safe_value = escape(str(value))
    safe_copy = escape(str(copy))
    st.markdown(
        f"""
        <div class="insight-card">
          <div class="insight-title">{safe_title}</div>
          <div class="insight-value">{safe_value}</div>
          <div class="insight-copy">{safe_copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">OPERATIONS ANALYTICS · REPLENISHMENT CONTROL</div>
      <h1>Inventory Control Tower</h1>
      <p style="font-weight: 700; color: #71E0D3; margin-bottom: 7px;">Replenishment &amp; Risk Intelligence</p>
      <p>Turn a raw inventory extract into a prioritized purchase plan, risk view, and working-capital decision set.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Control panel")
    st.caption("Upload client data or use the validated demo dataset.")
    uploaded_file = st.file_uploader("Inventory CSV", type=["csv"])
    service_level_pct = st.slider(
        "Target service level",
        min_value=85,
        max_value=99,
        value=95,
        step=1,
        help="Probability of meeting demand during replenishment lead time.",
    )
    excess_days = st.slider(
        "Excess-stock threshold (days)",
        min_value=30,
        max_value=180,
        value=90,
        step=5,
    )
    currency = st.selectbox("Reporting currency", ["CAD", "USD", "EUR"], index=0)

try:
    source, source_name = load_source(uploaded_file)
    analyzed = analyze_inventory(
        source,
        service_level=service_level_pct / 100,
        excess_days_threshold=excess_days,
    )
except (InventoryDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"The file could not be analyzed: {error}")
    st.info("Use the downloadable template in the Data & Method tab and retain the required column names.")
    st.stop()
except Exception as error:
    st.error(f"Unexpected processing error: {error}")
    st.stop()

with st.sidebar:
    st.divider()
    st.markdown("### Filters")
    all_categories = sorted(analyzed["category"].dropna().astype(str).unique())
    all_statuses = [
        status for status in STATUS_ORDER if status in analyzed["inventory_status"].unique()
    ]
    selected_categories = st.multiselect(
        "Category", all_categories, default=all_categories
    )
    selected_statuses = st.multiselect(
        "Inventory status", all_statuses, default=all_statuses
    )
    selected_abc = st.multiselect("ABC class", ["A", "B", "C"], default=["A", "B", "C"])
    st.divider()
    st.caption(f"Source: {source_name}")
    st.caption(f"Model: v1.0 · {service_level_pct}% service level")

filtered = analyzed.loc[
    analyzed["category"].isin(selected_categories)
    & analyzed["inventory_status"].isin(selected_statuses)
    & analyzed["abc_class"].isin(selected_abc)
].copy()

if filtered.empty:
    st.warning("No SKUs match the selected filters. Adjust the control panel to restore results.")
    st.stop()

kpis = calculate_kpis(filtered)
scope_text = f"Showing {len(filtered):,} of {len(analyzed):,} SKUs"
st.caption(scope_text)

metric_columns = st.columns(5)
metric_columns[0].metric("Inventory value", format_money(kpis["inventory_value"], currency))
metric_columns[1].metric("SKUs at risk", f"{kpis['at_risk_skus']:,}")
metric_columns[2].metric("SKUs to reorder", f"{kpis['reorder_skus']:,}")
metric_columns[3].metric(
    "Recommended purchase", format_money(kpis["recommended_order_value"], currency)
)
metric_columns[4].metric("Margin at risk", format_money(kpis["margin_at_risk"], currency))

tabs = st.tabs(
    [
        "Executive View",
        "Reorder Action List",
        "ABC & Working Capital",
        "Data & Method",
    ]
)

with tabs[0]:
    st.subheader("Portfolio health")
    st.markdown(
        '<p class="section-note">A management view of service risk, purchasing demand, and the most urgent interventions.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.9, 1.1])
    with left:
        status_counts = (
            filtered.groupby("inventory_status", observed=True)["sku"]
            .nunique()
            .reindex(STATUS_ORDER, fill_value=0)
            .reset_index(name="sku_count")
        )
        status_counts = status_counts[status_counts["sku_count"] > 0]
        status_figure = px.bar(
            status_counts,
            x="inventory_status",
            y="sku_count",
            color="inventory_status",
            color_discrete_map=STATUS_COLORS,
            text="sku_count",
            title="SKUs by inventory status",
            labels={"inventory_status": "Status", "sku_count": "SKUs"},
        )
        status_figure.update_traces(textposition="outside", cliponaxis=False)
        status_figure.update_layout(showlegend=False)
        chart_layout(status_figure)
        st.plotly_chart(status_figure, width="stretch", config={"displayModeBar": False})

    with right:
        category_actions = (
            filtered.groupby("category", as_index=False)
            .agg(
                recommended_purchase=("suggested_purchase_cost", "sum"),
                excess_capital=("excess_capital", "sum"),
            )
            .sort_values("recommended_purchase", ascending=True)
        )
        action_figure = go.Figure()
        action_figure.add_bar(
            y=category_actions["category"],
            x=category_actions["recommended_purchase"],
            name="Recommended purchase",
            orientation="h",
            marker_color=COLORS["teal"],
        )
        action_figure.add_bar(
            y=category_actions["category"],
            x=category_actions["excess_capital"],
            name="Capital above target",
            orientation="h",
            marker_color=COLORS["blue"],
        )
        action_figure.update_layout(
            barmode="group",
            title="Working-capital actions by category",
            xaxis_title=f"Value ({currency})",
            yaxis_title="",
        )
        chart_layout(action_figure)
        st.plotly_chart(action_figure, width="stretch", config={"displayModeBar": False})

    st.subheader("Decision brief")
    insight_columns = st.columns(3)
    priority_item = filtered.sort_values(
        ["priority_score", "annual_usage_value"], ascending=[False, False]
    ).iloc[0]
    risk_by_category = (
        filtered.assign(
            at_risk=filtered["inventory_status"].isin(["STOCKOUT", "CRITICAL", "REORDER"])
        )
        .groupby("category")["at_risk"]
        .sum()
        .sort_values(ascending=False)
    )
    excess_item = filtered.sort_values("excess_capital", ascending=False).iloc[0]
    with insight_columns[0]:
        render_insight(
            "Highest priority",
            str(priority_item["sku"]),
            f"{priority_item['inventory_status'].title()} · score {int(priority_item['priority_score'])}/100",
        )
    with insight_columns[1]:
        render_insight(
            "Most exposed category",
            str(risk_by_category.index[0]),
            f"{int(risk_by_category.iloc[0])} SKU(s) at immediate replenishment risk",
        )
    with insight_columns[2]:
        if float(excess_item["excess_capital"]) > 0:
            render_insight(
                "Largest excess position",
                str(excess_item["sku"]),
                f"{format_money(float(excess_item['excess_capital']), currency)} above modeled target",
            )
        else:
            render_insight(
                "Excess position",
                "No material excess",
                "No filtered SKU exceeds the modeled target and days threshold",
            )

    st.markdown("### Priority watchlist")
    watch_columns = [
        "sku",
        "product_name",
        "category",
        "abc_class",
        "inventory_status",
        "days_of_supply",
        "reorder_point",
        "inventory_position",
        "recommended_order_qty",
        "suggested_purchase_cost",
        "priority_score",
    ]
    st.dataframe(
        filtered[watch_columns].head(12),
        width="stretch",
        hide_index=True,
        column_config={
            "sku": "SKU",
            "product_name": "Product",
            "category": "Category",
            "abc_class": "ABC",
            "inventory_status": "Status",
            "days_of_supply": st.column_config.NumberColumn("Days supply", format="%.1f"),
            "reorder_point": st.column_config.NumberColumn("Reorder point", format="%.1f"),
            "inventory_position": st.column_config.NumberColumn("Inventory position", format="%.1f"),
            "recommended_order_qty": st.column_config.NumberColumn("Order qty", format="%d"),
            "suggested_purchase_cost": st.column_config.NumberColumn(
                "Purchase value", format=f"{currency} %.2f"
            ),
            "priority_score": st.column_config.ProgressColumn("Priority", min_value=0, max_value=100),
        },
    )

with tabs[1]:
    st.subheader("Reorder action list")
    reorder_data = filtered.loc[filtered["recommended_order_qty"] > 0].copy()
    if reorder_data.empty:
        st.success("No filtered SKU has reached its reorder point.")
    else:
        order_value = float(reorder_data["suggested_purchase_cost"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Purchase lines", f"{len(reorder_data):,}")
        c2.metric("Proposed order value", format_money(order_value, currency))
        c3.metric(
            "Critical / stockout lines",
            f"{int(reorder_data['inventory_status'].isin(['STOCKOUT', 'CRITICAL']).sum()):,}",
        )

        reorder_columns = [
            "priority_score",
            "sku",
            "product_name",
            "category",
            "supplier",
            "abc_class",
            "inventory_status",
            "current_stock",
            "committed_stock",
            "units_on_order",
            "reorder_point",
            "eoq",
            "recommended_order_qty",
            "unit_cost",
            "suggested_purchase_cost",
            "margin_at_risk",
        ]
        reorder_columns = [column for column in reorder_columns if column in reorder_data.columns]
        st.dataframe(
            reorder_data[reorder_columns],
            width="stretch",
            hide_index=True,
            height=490,
            column_config={
                "priority_score": st.column_config.ProgressColumn("Priority", min_value=0, max_value=100),
                "sku": "SKU",
                "product_name": "Product",
                "category": "Category",
                "supplier": "Supplier",
                "abc_class": "ABC",
                "inventory_status": "Status",
                "current_stock": st.column_config.NumberColumn("On hand", format="%.0f"),
                "committed_stock": st.column_config.NumberColumn("Committed", format="%.0f"),
                "units_on_order": st.column_config.NumberColumn("Inbound", format="%.0f"),
                "reorder_point": st.column_config.NumberColumn("Reorder point", format="%.1f"),
                "eoq": st.column_config.NumberColumn("EOQ", format="%.1f"),
                "recommended_order_qty": st.column_config.NumberColumn("Recommended qty", format="%d"),
                "unit_cost": st.column_config.NumberColumn(
                    "Unit cost", format=f"{currency} %.2f"
                ),
                "suggested_purchase_cost": st.column_config.NumberColumn(
                    "Line value", format=f"{currency} %.2f"
                ),
                "margin_at_risk": st.column_config.NumberColumn(
                    "Margin at risk", format=f"{currency} %.2f"
                ),
            },
        )
        action_export = reorder_data[reorder_columns].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download purchase action list",
            data=action_export,
            file_name="inventory_reorder_action_list.csv",
            mime="text/csv",
            type="primary",
        )

with tabs[2]:
    st.subheader("ABC segmentation and working capital")
    left, right = st.columns([0.85, 1.15])
    with left:
        abc_summary = (
            filtered.groupby("abc_class", as_index=False)
            .agg(
                sku_count=("sku", "nunique"),
                annual_usage_value=("annual_usage_value", "sum"),
                inventory_value=("inventory_value", "sum"),
            )
            .sort_values("abc_class")
        )
        abc_figure = px.pie(
            abc_summary,
            names="abc_class",
            values="annual_usage_value",
            hole=0.58,
            color="abc_class",
            color_discrete_map={"A": COLORS["navy"], "B": COLORS["blue"], "C": COLORS["teal"]},
            title="Annual usage value by ABC class",
        )
        abc_figure.update_traces(textposition="inside", textinfo="label+percent")
        chart_layout(abc_figure)
        st.plotly_chart(abc_figure, width="stretch", config={"displayModeBar": False})

    with right:
        scatter_data = filtered.dropna(subset=["days_of_supply"]).copy()
        scatter_figure = px.scatter(
            scatter_data,
            x="days_of_supply",
            y="annual_usage_value",
            size="inventory_value",
            color="inventory_status",
            color_discrete_map=STATUS_COLORS,
            hover_name="sku",
            hover_data={
                "product_name": True,
                "category": True,
                "abc_class": True,
                "inventory_value": ":,.2f",
                "days_of_supply": ":.1f",
            },
            title="Value concentration vs. days of supply",
            labels={
                "days_of_supply": "Days of supply",
                "annual_usage_value": f"Annual usage value ({currency})",
                "inventory_status": "Status",
            },
        )
        scatter_figure.add_vline(
            x=excess_days,
            line_dash="dash",
            line_color=COLORS["slate"],
            annotation_text="Excess threshold",
        )
        chart_layout(scatter_figure)
        st.plotly_chart(scatter_figure, width="stretch", config={"displayModeBar": False})

    st.markdown("### ABC summary")
    abc_summary["usage_share_pct"] = (
        abc_summary["annual_usage_value"] / abc_summary["annual_usage_value"].sum() * 100
    ).round(1)
    st.dataframe(
        abc_summary,
        width="stretch",
        hide_index=True,
        column_config={
            "abc_class": "ABC class",
            "sku_count": "SKUs",
            "annual_usage_value": st.column_config.NumberColumn(
                "Annual usage value", format=f"{currency} %.2f"
            ),
            "inventory_value": st.column_config.NumberColumn(
                "Inventory value", format=f"{currency} %.2f"
            ),
            "usage_share_pct": st.column_config.NumberColumn("Value share", format="%.1f%%"),
        },
    )

    excess_data = filtered.loc[filtered["excess_capital"] > 0].sort_values(
        "excess_capital", ascending=False
    )
    st.markdown("### Excess-capital opportunities")
    if excess_data.empty:
        st.info("No filtered SKU is above both the target stock and the selected days-of-supply threshold.")
    else:
        st.dataframe(
            excess_data[
                [
                    "sku",
                    "product_name",
                    "category",
                    "abc_class",
                    "days_of_supply",
                    "excess_units",
                    "excess_capital",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "sku": "SKU",
                "product_name": "Product",
                "category": "Category",
                "abc_class": "ABC",
                "days_of_supply": st.column_config.NumberColumn("Days supply", format="%.1f"),
                "excess_units": st.column_config.NumberColumn("Units above target", format="%.1f"),
                "excess_capital": st.column_config.NumberColumn(
                    "Capital above target", format=f"{currency} %.2f"
                ),
            },
        )

with tabs[3]:
    st.subheader("Data quality and model transparency")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Rows processed", f"{len(source):,}")
    q2.metric("Unique SKUs", f"{analyzed['sku'].nunique():,}")
    q3.metric("Missing source cells", f"{int(source.isna().sum().sum()):,}")
    q4.metric("Validation result", "Passed")

    with st.expander("Required input schema", expanded=True):
        schema_rows = [
            ("sku", "Text", "Unique item identifier", "ELC-001"),
            ("product_name", "Text", "Readable item description", "Servo Drive Pro"),
            ("category", "Text", "Reporting category", "Electrical"),
            ("unit_cost", "Number", "Landed or standard unit cost", "84.50"),
            ("unit_price", "Number", "Selling price used for margin exposure", "129.00"),
            ("current_stock", "Number", "Physical on-hand quantity", "120"),
            ("avg_daily_demand", "Number", "Mean units consumed per day", "8.4"),
            ("demand_std_dev", "Number", "Standard deviation of daily demand", "2.1"),
            ("lead_time_days", "Number", "Supplier replenishment lead time", "21"),
            ("order_cost", "Number", "Administrative cost per purchase order", "75.00"),
            ("annual_holding_rate", "Decimal", "Annual carrying rate as a decimal", "0.24"),
            ("units_on_order", "Number", "Optional open inbound quantity", "50"),
            ("committed_stock", "Number", "Optional allocated quantity", "20"),
            ("supplier", "Text", "Optional supplier name", "Atlas Industrial"),
        ]
        schema = pd.DataFrame(schema_rows, columns=["Field", "Type", "Business definition", "Example"])
        st.dataframe(schema, width="stretch", hide_index=True)
        st.download_button(
            "Download blank CSV template",
            data=TEMPLATE_FILE.read_bytes(),
            file_name="inventory_upload_template.csv",
            mime="text/csv",
        )

    with st.expander("Calculation methodology"):
        st.markdown(
            """
            - **Safety stock:** service-factor × daily-demand standard deviation × √lead time
            - **Reorder point:** expected lead-time demand + safety stock
            - **EOQ:** √(2 × annual demand × order cost ÷ annual holding cost per unit)
            - **Recommended quantity:** replenish to reorder point + EOQ once inventory position reaches the reorder point
            - **Inventory position:** on hand − committed stock + open inbound stock
            - **ABC class:** cumulative share of annual demand value using 80% / 15% / 5% bands

            Assumptions should be reviewed with procurement and operations before production use. Supplier minimums,
            case packs, capacity constraints, seasonality, and negotiated order calendars are outside this version.
            """
        )

    with st.expander("Analyzed dataset"):
        st.dataframe(filtered, width="stretch", hide_index=True, height=450)
        full_export = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download full analysis",
            data=full_export,
            file_name="inventory_optimization_analysis.csv",
            mime="text/csv",
        )

st.markdown(
    '<div class="footer">Decision-support portfolio project · 2020 · Demo data only · Built by Braulio</div>',
    unsafe_allow_html=True,
)
