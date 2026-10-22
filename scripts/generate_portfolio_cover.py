"""Generate the portfolio preview from the deterministic demo dataset.

This keeps the public-facing image synchronized with the calculation engine
without requiring a browser screenshot or exposing client data.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from inventory_optimizer import analyze_inventory, calculate_kpis  # noqa: E402
from inventory_optimizer.analysis import STATUS_ORDER  # noqa: E402


OUTPUT = ROOT / "assets" / "dashboard_preview.png"
DATA_FILE = ROOT / "data" / "sample_inventory.csv"

WIDTH, HEIGHT = 1600, 900
NAVY = "#102238"
NAVY_2 = "#193B5A"
TEAL = "#17A89A"
TEAL_LIGHT = "#71E0D3"
BLUE = "#2A6FDB"
AMBER = "#F3A712"
RED = "#E05263"
PURPLE = "#725AC1"
SLATE = "#60758A"
LIGHT = "#F4F7FA"
WHITE = "#FFFFFF"
BORDER = "#DFE6ED"

STATUS_COLORS = {
    "STOCKOUT": "#9F1239",
    "CRITICAL": RED,
    "REORDER": AMBER,
    "WATCH": PURPLE,
    "HEALTHY": TEAL,
    "EXCESS": BLUE,
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


F10 = font(10)
F11 = font(11)
F12 = font(12)
F12B = font(12, bold=True)
F13 = font(13)
F13B = font(13, bold=True)
F15B = font(15, bold=True)
F18B = font(18, bold=True)
F21B = font(21, bold=True)
F24B = font(24, bold=True)
F35B = font(35, bold=True)


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"CAD {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"CAD {value / 1_000:.1f}K"
    return f"CAD {value:,.0f}"


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int = 14) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 3, y1 + 5, x2 + 3, y2 + 5), radius=radius, fill="#DCE3E9")
    draw.rounded_rectangle(box, radius=radius, fill=WHITE, outline=BORDER, width=1)


def fit_text(draw: ImageDraw.ImageDraw, value: str, max_width: int, preferred: int, minimum: int = 11) -> ImageFont.ImageFont:
    size = preferred
    while size > minimum:
        candidate = font(size, bold=True)
        if draw.textbbox((0, 0), value, font=candidate)[2] <= max_width:
            return candidate
        size -= 1
    return font(minimum, bold=True)


def draw_kpis(draw: ImageDraw.ImageDraw, kpis: dict[str, float | int]) -> None:
    items = [
        ("INVENTORY VALUE", money(float(kpis["inventory_value"]))),
        ("SKUS AT RISK", f"{int(kpis['at_risk_skus']):,}"),
        ("SKUS TO REORDER", f"{int(kpis['reorder_skus']):,}"),
        ("RECOMMENDED PURCHASE", money(float(kpis["recommended_order_value"]))),
        ("MARGIN AT RISK", money(float(kpis["margin_at_risk"]))),
    ]
    start_x, gap, y1, y2 = 305, 14, 203, 296
    available = WIDTH - start_x - 30 - gap * 4
    width = available // 5
    for index, (label, value) in enumerate(items):
        x1 = start_x + index * (width + gap)
        x2 = x1 + width
        card(draw, (x1, y1, x2, y2))
        draw.text((x1 + 17, y1 + 17), label, font=F11, fill=SLATE)
        value_font = fit_text(draw, value, width - 34, 24)
        draw.text((x1 + 17, y1 + 43), value, font=value_font, fill=NAVY)


def draw_status_chart(draw: ImageDraw.ImageDraw, analyzed: pd.DataFrame) -> None:
    box = (305, 316, 818, 563)
    card(draw, box)
    x1, y1, x2, y2 = box
    draw.text((x1 + 18, y1 + 16), "SKUs by inventory status", font=F15B, fill=NAVY)
    counts = analyzed["inventory_status"].value_counts().reindex(STATUS_ORDER, fill_value=0)
    statuses = [status for status in STATUS_ORDER if int(counts[status]) > 0]
    max_count = max(int(counts[status]) for status in statuses)
    chart_top, chart_bottom = y1 + 57, y2 - 39
    chart_height = chart_bottom - chart_top
    plot_left, plot_right = x1 + 35, x2 - 18
    baseline = chart_bottom
    draw.line((plot_left, baseline, plot_right, baseline), fill=BORDER, width=2)
    slot = (plot_right - plot_left) / len(statuses)
    bar_width = min(52, int(slot * 0.56))
    for i, status in enumerate(statuses):
        count = int(counts[status])
        height = max(5, int(chart_height * count / max_count))
        center = int(plot_left + slot * (i + 0.5))
        bx1, bx2 = center - bar_width // 2, center + bar_width // 2
        by1 = baseline - height
        draw.rounded_rectangle((bx1, by1, bx2, baseline), radius=5, fill=STATUS_COLORS[status])
        label_box = draw.textbbox((0, 0), str(count), font=F12B)
        draw.text((center - (label_box[2] - label_box[0]) / 2, by1 - 19), str(count), font=F12B, fill=NAVY)
        short = status.title()
        label_box = draw.textbbox((0, 0), short, font=F10)
        draw.text((center - (label_box[2] - label_box[0]) / 2, baseline + 9), short, font=F10, fill=SLATE)


def draw_action_chart(draw: ImageDraw.ImageDraw, analyzed: pd.DataFrame) -> None:
    box = (835, 316, 1570, 563)
    card(draw, box)
    x1, y1, x2, y2 = box
    draw.text((x1 + 18, y1 + 16), "Working-capital actions by category", font=F15B, fill=NAVY)
    draw.rectangle((x2 - 232, y1 + 20, x2 - 222, y1 + 30), fill=TEAL)
    draw.text((x2 - 216, y1 + 17), "Purchase", font=F10, fill=SLATE)
    draw.rectangle((x2 - 142, y1 + 20, x2 - 132, y1 + 30), fill=BLUE)
    draw.text((x2 - 126, y1 + 17), "Above target", font=F10, fill=SLATE)

    summary = (
        analyzed.groupby("category", as_index=False)
        .agg(purchase=("suggested_purchase_cost", "sum"), excess=("excess_capital", "sum"))
        .sort_values("purchase", ascending=False)
    )
    maximum = max(float(summary[["purchase", "excess"]].max().max()), 1.0)
    label_x = x1 + 18
    bar_x = x1 + 155
    max_width = x2 - bar_x - 64
    row_height = 28
    top = y1 + 57
    for i, row in summary.iterrows():
        y = top + i * row_height
        draw.text((label_x, y + 3), str(row["category"]), font=F11, fill=NAVY)
        purchase_width = int(float(row["purchase"]) / maximum * max_width)
        excess_width = int(float(row["excess"]) / maximum * max_width)
        draw.rounded_rectangle((bar_x, y, bar_x + max(purchase_width, 2), y + 9), radius=4, fill=TEAL)
        draw.rounded_rectangle((bar_x, y + 13, bar_x + max(excess_width, 2), y + 22), radius=4, fill=BLUE)
        if purchase_width > 54:
            draw.text((bar_x + purchase_width + 6, y - 1), money(float(row["purchase"])).replace("CAD ", ""), font=F10, fill=SLATE)


def draw_decision_brief(draw: ImageDraw.ImageDraw, analyzed: pd.DataFrame) -> None:
    priority_item = analyzed.iloc[0]
    risk_by_category = (
        analyzed.assign(at_risk=analyzed["inventory_status"].isin(["STOCKOUT", "CRITICAL", "REORDER"]))
        .groupby("category")["at_risk"]
        .sum()
        .sort_values(ascending=False)
    )
    excess_item = analyzed.sort_values("excess_capital", ascending=False).iloc[0]
    cards = [
        ("HIGHEST PRIORITY", str(priority_item["sku"]), f"{str(priority_item['inventory_status']).title()} · score {int(priority_item['priority_score'])}/100"),
        ("MOST EXPOSED CATEGORY", str(risk_by_category.index[0]), f"{int(risk_by_category.iloc[0])} SKU(s) at immediate risk"),
        ("LARGEST EXCESS POSITION", str(excess_item["sku"]), f"{money(float(excess_item['excess_capital']))} above modeled target"),
    ]
    draw.text((305, 586), "Decision brief", font=F18B, fill=NAVY)
    x_start, gap, y1, y2 = 305, 16, 617, 712
    width = (1570 - x_start - gap * 2) // 3
    for i, (label, value, copy) in enumerate(cards):
        x1 = x_start + i * (width + gap)
        x2 = x1 + width
        card(draw, (x1, y1, x2, y2), radius=11)
        draw.rounded_rectangle((x1, y1, x1 + 5, y2), radius=3, fill=TEAL)
        draw.text((x1 + 18, y1 + 14), label, font=F10, fill=SLATE)
        draw.text((x1 + 18, y1 + 36), value, font=F18B, fill=NAVY)
        draw.text((x1 + 18, y1 + 65), copy, font=F11, fill=SLATE)


def draw_watchlist(draw: ImageDraw.ImageDraw, analyzed: pd.DataFrame) -> None:
    box = (305, 735, 1570, 868)
    card(draw, box, radius=11)
    x1, y1, x2, _ = box
    draw.text((x1 + 18, y1 + 13), "Priority watchlist", font=F15B, fill=NAVY)
    columns = [
        ("SKU", 18),
        ("PRODUCT", 132),
        ("CATEGORY", 410),
        ("ABC", 580),
        ("STATUS", 648),
        ("DAYS SUPPLY", 785),
        ("ORDER QTY", 918),
        ("PURCHASE VALUE", 1040),
    ]
    header_y = y1 + 43
    draw.rectangle((x1 + 1, header_y - 3, x2 - 1, header_y + 22), fill="#EDF2F6")
    for label, offset in columns:
        draw.text((x1 + offset, header_y + 2), label, font=F10, fill=SLATE)
    for row_index, (_, row) in enumerate(analyzed.head(3).iterrows()):
        y = header_y + 28 + row_index * 24
        if row_index % 2:
            draw.rectangle((x1 + 1, y - 2, x2 - 1, y + 20), fill="#F8FAFC")
        values = [
            str(row["sku"]),
            str(row["product_name"])[:31],
            str(row["category"]),
            str(row["abc_class"]),
            str(row["inventory_status"]),
            f"{float(row['days_of_supply']):.1f}" if not math.isnan(float(row["days_of_supply"])) else "—",
            f"{int(row['recommended_order_qty']):,}",
            money(float(row["suggested_purchase_cost"])),
        ]
        for value, (_, offset) in zip(values, columns):
            color = STATUS_COLORS.get(value, NAVY)
            draw.text((x1 + offset, y), value, font=F11, fill=color)


def main() -> None:
    source = pd.read_csv(DATA_FILE)
    analyzed = analyze_inventory(source, service_level=0.95, excess_days_threshold=90)
    kpis = calculate_kpis(analyzed)

    image = Image.new("RGB", (WIDTH, HEIGHT), LIGHT)
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 270, HEIGHT), fill=NAVY)
    draw.text((30, 34), "INVENTORY", font=F24B, fill=WHITE)
    draw.text((30, 64), "CONTROL TOWER", font=F24B, fill=TEAL_LIGHT)
    draw.text((30, 105), "REPLENISHMENT & RISK", font=F10, fill="#B8C8D6")
    draw.text((30, 122), "INTELLIGENCE", font=F10, fill="#B8C8D6")
    draw.line((30, 155, 240, 155), fill="#36536B", width=1)
    draw.text((30, 178), "CONTROL PANEL", font=F12B, fill=WHITE)
    controls = [
        ("DATA SOURCE", "Professional demo dataset"),
        ("TARGET SERVICE LEVEL", "95%"),
        ("EXCESS THRESHOLD", "90 days"),
        ("REPORTING CURRENCY", "CAD"),
    ]
    for i, (label, value) in enumerate(controls):
        y = 214 + i * 74
        draw.text((30, y), label, font=F10, fill="#95AABC")
        draw.rounded_rectangle((30, y + 20, 240, y + 54), radius=7, fill="#193B5A")
        draw.text((43, y + 29), value, font=F11, fill=WHITE)
    draw.line((30, 522, 240, 522), fill="#36536B", width=1)
    draw.text((30, 546), "FILTERS", font=F12B, fill=WHITE)
    for i, value in enumerate(["All categories", "All statuses", "ABC: A · B · C"]):
        y = 582 + i * 52
        draw.rounded_rectangle((30, y, 240, y + 34), radius=7, fill="#193B5A")
        draw.text((43, y + 9), value, font=F11, fill=WHITE)
    draw.text((30, 826), "Model v1.0", font=F10, fill="#95AABC")
    draw.text((30, 844), "Synthetic data · 2020", font=F10, fill="#95AABC")

    hero = Image.new("RGB", (1265, 151), NAVY)
    hero_pixels = hero.load()
    for x in range(hero.width):
        ratio = x / max(hero.width - 1, 1)
        start = (16, 34, 56)
        end = (23, 107, 117)
        color = tuple(int(start[i] * (1 - ratio) + end[i] * ratio) for i in range(3))
        for y in range(hero.height):
            hero_pixels[x, y] = color
    image.paste(hero, (305, 28))
    draw.rounded_rectangle((305, 28, 1570, 179), radius=17, outline=NAVY, width=1)
    draw.text((335, 50), "OPERATIONS ANALYTICS · REPLENISHMENT CONTROL", font=F11, fill=TEAL_LIGHT)
    draw.text((335, 76), "Inventory Control Tower", font=F35B, fill=WHITE)
    draw.text((335, 124), "Replenishment & Risk Intelligence", font=F15B, fill=TEAL_LIGHT)
    draw.text((335, 148), "From raw inventory data to a prioritized purchase plan.", font=F13, fill="#D5E2EC")
    draw.text((1452, 49), "BRAULIO", font=F12B, fill=WHITE)
    draw.text((1487, 68), "2020", font=F11, fill="#D5E2EC")

    draw_kpis(draw, kpis)
    draw_status_chart(draw, analyzed)
    draw_action_chart(draw, analyzed)
    draw_decision_brief(draw, analyzed)
    draw_watchlist(draw, analyzed)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=True)
    print(f"Created {OUTPUT} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
