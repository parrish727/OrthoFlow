"""Spend Intelligence — vendor negotiation insights + budget forecasting."""
from datetime import datetime, timedelta


# Industry benchmark prices for common ortho supplies (per unit averages)
BENCHMARKS = {
    "brackets": {"avg": 400, "low": 350, "high": 450, "unit": "kit"},
    "archwires": {"avg": 42, "low": 35, "high": 52, "unit": "pack"},
    "elastics": {"avg": 25, "low": 20, "high": 32, "unit": "1000ct"},
    "bonding": {"avg": 82, "low": 70, "high": 95, "unit": "syringe"},
    "retainers": {"avg": 160, "low": 130, "high": 190, "unit": "each"},
    "expanders": {"avg": 600, "low": 500, "high": 750, "unit": "each"},
    "invisalign_comprehensive": {"avg": 4000, "low": 3800, "high": 4500, "unit": "case"},
    "invisalign_lite": {"avg": 2000, "low": 1800, "high": 2300, "unit": "case"},
    "gloves": {"avg": 26, "low": 22, "high": 32, "unit": "box"},
    "sterilization": {"avg": 36, "low": 30, "high": 45, "unit": "2000ct"},
}


def analyze_vendor_pricing(invoices: list[dict]) -> list[dict]:
    """Compare practice's vendor prices against industry benchmarks."""
    insights = []

    for inv in invoices:
        if not inv.get("coded_json"):
            continue
        import json
        try:
            coded = json.loads(inv["coded_json"])
        except (json.JSONDecodeError, TypeError):
            continue

        for item in coded.get("line_items", []):
            category = item.get("category", "")
            unit_price = item.get("unit_price", 0)
            if not unit_price:
                continue

            # Check against benchmarks
            for bench_key, bench in BENCHMARKS.items():
                if bench_key in item.get("description", "").lower() or bench_key in category.lower():
                    if unit_price > bench["avg"] * 1.1:  # 10% above average
                        pct_over = round(((unit_price - bench["avg"]) / bench["avg"]) * 100)
                        savings = round((unit_price - bench["avg"]) * item.get("quantity", 1))
                        insights.append({
                            "type": "overpriced",
                            "vendor": inv.get("vendor_name", "Unknown"),
                            "item": item["description"],
                            "your_price": unit_price,
                            "market_avg": bench["avg"],
                            "market_low": bench["low"],
                            "pct_over": pct_over,
                            "potential_savings": savings,
                            "recommendation": f"You're paying {pct_over}% above market average. Consider requesting a price match or switching vendors. Potential savings: ${savings}/order.",
                        })
                    break

    return sorted(insights, key=lambda x: x["potential_savings"], reverse=True)


def forecast_spend(invoices: list[dict], months_ahead: int = 3) -> dict:
    """Project future spend based on historical patterns."""
    if not invoices:
        return {"forecast": [], "budget_status": "no_data"}

    # Group by month
    monthly = {}
    for inv in invoices:
        created = inv.get("created_at", "")
        if not created:
            continue
        month_key = created[:7]  # YYYY-MM
        monthly[month_key] = monthly.get(month_key, 0) + inv.get("total_amount", 0)

    if not monthly:
        return {"forecast": [], "budget_status": "no_data"}

    # Calculate average monthly spend
    values = list(monthly.values())
    avg_monthly = sum(values) / len(values)
    trend = (values[-1] - values[0]) / max(len(values), 1) if len(values) > 1 else 0

    # Project forward
    forecast = []
    now = datetime.utcnow()
    for i in range(1, months_ahead + 1):
        future_month = now + timedelta(days=30 * i)
        projected = avg_monthly + (trend * i)
        forecast.append({
            "month": future_month.strftime("%Y-%m"),
            "projected_spend": round(max(projected, 0)),
        })

    quarterly_projected = sum(f["projected_spend"] for f in forecast)

    return {
        "avg_monthly_spend": round(avg_monthly),
        "trend_direction": "up" if trend > 0 else "down" if trend < 0 else "flat",
        "trend_amount": round(abs(trend)),
        "forecast": forecast,
        "quarterly_projected": quarterly_projected,
    }


def generate_budget_report(invoices: list[dict], budget: dict = None) -> dict:
    """Compare actual spend against budget targets."""
    if not budget:
        # Default budget based on industry averages for a single-provider practice
        budget = {
            "supplies": 5000,
            "lab": 4000,
            "equipment": 2000,
            "invisalign": 8000,
            "services": 1500,
            "total": 25000,
        }

    # Calculate actual spend by category
    import json
    actual = {}
    for inv in invoices:
        if not inv.get("coded_json"):
            continue
        try:
            coded = json.loads(inv["coded_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        for item in coded.get("line_items", []):
            cat = item.get("category", "other")
            actual[cat] = actual.get(cat, 0) + item.get("total", 0)

    total_actual = sum(actual.values())

    categories = []
    for cat, budgeted in budget.items():
        if cat == "total":
            continue
        spent = actual.get(cat, 0)
        categories.append({
            "category": cat,
            "budgeted": budgeted,
            "actual": round(spent),
            "remaining": round(budgeted - spent),
            "pct_used": round((spent / budgeted) * 100) if budgeted > 0 else 0,
            "over_budget": spent > budgeted,
        })

    return {
        "total_budget": budget.get("total", 25000),
        "total_spent": round(total_actual),
        "total_remaining": round(budget.get("total", 25000) - total_actual),
        "categories": sorted(categories, key=lambda x: x["pct_used"], reverse=True),
    }
