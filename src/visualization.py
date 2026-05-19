"""
visualization.py
----------------
Reusable Plotly chart functions for the portfolio unit economics project.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("outputs/charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
BLUE   = "#2E86AB"
RED    = "#C73E1D"
GREEN  = "#44BBA4"
AMBER  = "#F18F01"
PURPLE = "#7B2D8B"
GRAY   = "#AAAAAA"

SCENARIO_COLORS = {
    "optimistic": GREEN,
    "base":       BLUE,
    "stress":     RED,
}

PRODUCT_COLORS = {
    "BNPL":        AMBER,
    "Credit Card": BLUE,
}


# ── P&L Waterfall ─────────────────────────────────────────────────────────────

def plot_pl_waterfall(summary_row: dict, title: str = None, save: bool = False) -> go.Figure:
    """
    Waterfall chart decomposing revenue → net margin for one product/scenario.
    """
    r = summary_row
    items = [
        ("Total Revenue",    r["total_revenue"],              "increasing"),
        ("Cost of Funds",   -r["total_cof"],                  "decreasing"),
        ("Gross Loss",      -r["total_gross_loss"],            "decreasing"),
        ("Recovery",         r["total_recovery"],              "increasing"),
        ("Servicing",       -r["total_servicing"],             "decreasing"),
        ("Orig. Cost",      -r["total_orig_cost"],             "decreasing"),
        ("Net Cash Flow",    r["total_net_cf"],                "total"),
    ]
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    measures = [i[2] for i in items]

    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        textposition="outside",
        text=[f"${v:,.0f}" for v in values],
        connector=dict(line=dict(color="#CCCCCC", width=1)),
        increasing=dict(marker_color=GREEN),
        decreasing=dict(marker_color=RED),
        totals=dict(marker_color=BLUE),
    ))

    t = title or f"{r.get('product','?')} — {r.get('scenario','?').title()} Scenario"
    fig.update_layout(
        title=dict(text=t, font=dict(size=15)),
        yaxis_title="$ (1,000-account cohort)",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=420, margin=dict(l=60, r=40, t=60, b=60),
        showlegend=False,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    if save:
        fname = OUTPUT_DIR / f"waterfall_{r.get('product','x').replace(' ','_')}_{r.get('scenario','x')}.png"
        fig.write_image(str(fname), scale=2)
    return fig


# ── Cumulative Net Cash Flow ──────────────────────────────────────────────────

def plot_cumulative_cf(results: dict, product: str = "BNPL", save: bool = False) -> go.Figure:
    """
    Cumulative net cash flow over time for all 3 scenarios of one product.
    """
    fig = go.Figure()

    for scenario in ["optimistic", "base", "stress"]:
        df = results.get((product, scenario))
        if df is None:
            continue
        fig.add_trace(go.Scatter(
            x=df["month"],
            y=df["cum_net_cf_per_acct"],
            mode="lines",
            name=scenario.title(),
            line=dict(color=SCENARIO_COLORS[scenario], width=2),
            hovertemplate=f"<b>{scenario.title()}</b><br>Month: %{{x}}<br>Cum. CF/Acct: $%{{y:,.2f}}<extra></extra>",
        ))

    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)

    fig.update_layout(
        title=dict(text=f"{product} — Cumulative Net Cash Flow per Account", font=dict(size=15)),
        xaxis_title="Month",
        yaxis_title="Cumulative Net CF per Account ($)",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=400, legend_title="Scenario",
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    if save:
        fig.write_image(str(OUTPUT_DIR / f"cum_cf_{product.replace(' ','_')}.png"), scale=2)
    return fig


# ── Monthly P&L Components ────────────────────────────────────────────────────

def plot_monthly_pl(df: pd.DataFrame, save: bool = False) -> go.Figure:
    """
    Stacked area chart of monthly revenue, cost of funds, and net cash flow.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=df["month"], y=df["total_revenue"],
        name="Revenue", marker_color=GREEN, opacity=0.7,
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=df["month"], y=-df["cost_of_funds"],
        name="Cost of Funds", marker_color=AMBER, opacity=0.7,
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=df["month"], y=-df["net_loss"],
        name="Net Loss", marker_color=RED, opacity=0.7,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["month"], y=df["net_cash_flow"],
        name="Net CF", mode="lines+markers",
        line=dict(color=BLUE, width=2), marker=dict(size=5),
    ), secondary_y=False)

    product  = df["product"].iloc[0]
    scenario = df["scenario"].iloc[0]

    fig.update_layout(
        title=dict(text=f"{product} — Monthly P&L Components ({scenario.title()})", font=dict(size=15)),
        barmode="relative",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=400, legend=dict(x=0.01, y=0.99),
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_xaxes(title_text="Month", showgrid=True, gridcolor="#EEEEEE")
    fig.update_yaxes(title_text="$ (cohort)", secondary_y=False, showgrid=True, gridcolor="#EEEEEE")

    if save:
        fig.write_image(str(OUTPUT_DIR / f"monthly_pl_{product.replace(' ','_')}_{scenario}.png"), scale=2)
    return fig


# ── Product Comparison ────────────────────────────────────────────────────────

def plot_product_comparison(summary_df: pd.DataFrame, metric: str = "net_margin_pct", save: bool = False) -> go.Figure:
    """
    Grouped bar chart comparing BNPL vs Credit Card across scenarios.
    """
    scenarios = ["optimistic", "base", "stress"]
    products  = ["BNPL", "Credit Card"]

    fig = go.Figure()
    for product in products:
        vals = []
        for s in scenarios:
            row = summary_df[(summary_df["product"] == product) & (summary_df["scenario"] == s)]
            vals.append(row[metric].values[0] if len(row) else 0)

        fig.add_trace(go.Bar(
            name=product,
            x=scenarios,
            y=vals,
            marker_color=PRODUCT_COLORS[product],
            text=[f"{v:.1f}%" if "pct" in metric or "rate" in metric else f"${v:,.0f}" for v in vals],
            textposition="outside",
        ))

    label = metric.replace("_", " ").title()
    fig.update_layout(
        title=dict(text=f"BNPL vs. Credit Card — {label} by Scenario", font=dict(size=15)),
        barmode="group",
        xaxis_title="Scenario",
        yaxis_title=label,
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=400, legend_title="Product",
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    if save:
        fig.write_image(str(OUTPUT_DIR / f"product_comparison_{metric}.png"), scale=2)
    return fig


# ── NPV Curves ────────────────────────────────────────────────────────────────

def plot_npv_curves(results: dict, wacc: float = 0.08, save: bool = False) -> go.Figure:
    """
    Discounted cumulative cash flow curves — both products, base scenario.
    """
    from src.scenario_engine import compute_npv
    import numpy as np

    fig = go.Figure()
    monthly_rate = (1 + wacc) ** (1/12) - 1

    for product in ["BNPL", "Credit Card"]:
        df = results.get((product, "base"))
        if df is None:
            continue
        months = df["month"].values
        discount_factors = 1 / (1 + monthly_rate) ** months
        discounted_cf = df["net_cf_per_acct"].values * discount_factors
        cum_npv = np.cumsum(discounted_cf)

        fig.add_trace(go.Scatter(
            x=months, y=cum_npv,
            mode="lines", name=product,
            line=dict(color=PRODUCT_COLORS[product], width=2.5),
            hovertemplate=f"<b>{product}</b><br>Month: %{{x}}<br>Cum. NPV/Acct: $%{{y:,.2f}}<extra></extra>",
        ))

    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)

    fig.update_layout(
        title=dict(text=f"Cumulative Discounted NPV per Account — Base Scenario (WACC={wacc:.0%})", font=dict(size=15)),
        xaxis_title="Month",
        yaxis_title="Cumulative NPV per Account ($)",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=400, legend_title="Product",
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    if save:
        fig.write_image(str(OUTPUT_DIR / "npv_curves.png"), scale=2)
    return fig


# ── Break-even Loss Rate ──────────────────────────────────────────────────────

def plot_breakeven(results: dict, save: bool = False) -> go.Figure:
    """
    Show at what cumulative loss rate each product's net CF turns negative.
    """
    fig = go.Figure()

    for product in ["BNPL", "Credit Card"]:
        df = results.get((product, "base"))
        if df is None:
            continue
        fig.add_trace(go.Scatter(
            x=df["month"],
            y=df["cum_loss_rate"] * 100,
            mode="lines", name=product,
            line=dict(color=PRODUCT_COLORS[product], width=2),
            hovertemplate=f"<b>{product}</b><br>Month: %{{x}}<br>Cum. Loss Rate: %{{y:.2f}}%<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="Cumulative Net Loss Rate Over Time — Base Scenario", font=dict(size=15)),
        xaxis_title="Month",
        yaxis_title="Cumulative Net Loss Rate (%)",
        yaxis_ticksuffix="%",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        height=380, legend_title="Product",
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    if save:
        fig.write_image(str(OUTPUT_DIR / "breakeven_loss_rate.png"), scale=2)
    return fig
