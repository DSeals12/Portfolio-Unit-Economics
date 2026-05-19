"""
streamlit_app.py
----------------
Interactive Portfolio Unit Economics Simulator

Launch: streamlit run app/streamlit_app.py
"""

import sys
sys.path.insert(0, ".")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.bnpl_model import run_bnpl_model, bnpl_summary
from src.credit_card_model import run_credit_card_model, credit_card_summary
from src.scenario_engine import run_all_scenarios, build_summary_table, npv_summary, compute_npv
from src.assumptions import BNPL, CREDIT_CARD, SHARED

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Unit Economics",
    page_icon="💳",
    layout="wide",
)

BLUE   = "#2E86AB"
RED    = "#C73E1D"
GREEN  = "#44BBA4"
AMBER  = "#F18F01"
GRAY   = "#AAAAAA"

SCENARIO_COLORS = {"optimistic": GREEN, "base": BLUE, "stress": RED}
PRODUCT_COLORS  = {"BNPL": AMBER, "Credit Card": BLUE}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("💳 Portfolio Unit Economics Simulator")
st.markdown(
    "**Products:** BNPL vs. Credit Card · "
    "**Framework:** Account P&L Waterfall + NPV + Scenario Analysis · "
    "**Author:** Denzel C. Seals"
)
st.markdown("---")

# ── Sidebar: Assumption Controls ─────────────────────────────────────────────
st.sidebar.header("⚙️ Model Assumptions")
st.sidebar.markdown("Adjust parameters to see real-time impact on P&L.")

st.sidebar.subheader("BNPL")
bnpl_transaction = st.sidebar.slider("Avg Transaction Size ($)", 200, 2000, int(BNPL["avg_transaction_size"]), 50)
bnpl_mdr         = st.sidebar.slider("MDR Rate (%)", 1.0, 8.0, float(BNPL["mdr_rate"]*100), 0.25) / 100
bnpl_loss        = st.sidebar.slider("Monthly Default Rate (%)", 0.2, 3.0, float(BNPL["monthly_default_rate"]*100), 0.1) / 100
bnpl_term        = st.sidebar.slider("Term (Months)", 3, 12, int(BNPL["term_months"]))
bnpl_cof         = st.sidebar.slider("Cost of Funds — Annual (%)", 2.0, 10.0, float(BNPL["cost_of_funds_annual"]*100), 0.25) / 100

st.sidebar.subheader("Credit Card")
cc_line          = st.sidebar.slider("Avg Credit Line ($)", 1000, 10000, int(CREDIT_CARD["avg_credit_line"]), 500)
cc_util          = st.sidebar.slider("Initial Utilization (%)", 10, 80, int(CREDIT_CARD["initial_utilization"]*100)) / 100
cc_apr           = st.sidebar.slider("APR — Annual (%)", 10.0, 35.0, float(CREDIT_CARD["apr_annual"]*100), 0.5) / 100
cc_loss          = st.sidebar.slider("Monthly Default Rate (%)", 0.1, 2.5, float(CREDIT_CARD["monthly_default_rate"]*100), 0.1) / 100
cc_cof           = st.sidebar.slider("Cost of Funds — Annual (%)", 2.0, 10.0, float(CREDIT_CARD["cost_of_funds_annual"]*100), 0.25) / 100

st.sidebar.subheader("Shared")
wacc             = st.sidebar.slider("WACC / Discount Rate (%)", 4.0, 15.0, float(SHARED["wacc"]*100), 0.5) / 100
n_accounts       = st.sidebar.slider("Cohort Size", 100, 5000, 1000, 100)

# ── Run Models with Sidebar Assumptions ──────────────────────────────────────
bnpl_overrides = {
    "avg_transaction_size":  bnpl_transaction,
    "mdr_rate":              bnpl_mdr,
    "monthly_default_rate":  bnpl_loss,
    "term_months":           bnpl_term,
    "cost_of_funds_annual":  bnpl_cof,
}
cc_overrides = {
    "avg_credit_line":       cc_line,
    "initial_utilization":   cc_util,
    "apr_annual":            cc_apr,
    "monthly_default_rate":  cc_loss,
    "cost_of_funds_annual":  cc_cof,
}

@st.cache_data
def get_results(bnpl_ov, cc_ov, n):
    bnpl_ov = dict(bnpl_ov)
    cc_ov   = dict(cc_ov)
    results = {}
    for scenario in ["optimistic", "base", "stress"]:
        results[("BNPL", scenario)]        = run_bnpl_model(scenario=scenario, n_accounts=n, assumptions={**BNPL, **bnpl_ov})
        results[("Credit Card", scenario)] = run_credit_card_model(scenario=scenario, n_accounts=n, assumptions={**CREDIT_CARD, **cc_ov})
    return results

results    = get_results(tuple(bnpl_overrides.items()), tuple(cc_overrides.items()), n_accounts)
summary_df = build_summary_table(results)
npv_df     = npv_summary(results, n_accounts=n_accounts)

# ── Section 1: KPI Cards ──────────────────────────────────────────────────────
st.subheader("Base Scenario — Lifetime Economics Summary")

bnpl_base = summary_df[(summary_df["product"] == "BNPL") & (summary_df["scenario"] == "base")].iloc[0]
cc_base   = summary_df[(summary_df["product"] == "Credit Card") & (summary_df["scenario"] == "base")].iloc[0]
bnpl_npv  = npv_df[(npv_df["product"] == "BNPL") & (npv_df["scenario"] == "base")].iloc[0]
cc_npv    = npv_df[(npv_df["product"] == "Credit Card") & (npv_df["scenario"] == "base")].iloc[0]

col1, col2, col3, col4, col5 = st.columns(5)
col1.markdown("**Metric**")
col2.markdown("**BNPL**")
col3.markdown("**Credit Card**")
col4.markdown("**BNPL**")
col5.markdown("**Credit Card**")

metrics = [
    ("Revenue Yield",   f"{bnpl_base['revenue_yield']:.1f}%",    f"{cc_base['revenue_yield']:.1f}%"),
    ("Net Loss Rate",   f"{bnpl_base['net_loss_rate']:.1f}%",    f"{cc_base['net_loss_rate']:.1f}%"),
    ("Net Margin %",    f"{bnpl_base['net_margin_pct']:.1f}%",   f"{cc_base['net_margin_pct']:.1f}%"),
    ("NPV / Account",   f"${bnpl_npv['npv_per_acct']:,.0f}",     f"${cc_npv['npv_per_acct']:,.0f}"),
    ("IRR (Annual)",    f"{bnpl_npv['irr_annual_pct']:.1f}%",    f"{cc_npv['irr_annual_pct']:.1f}%"),
]

for label, bval, cval in metrics:
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.metric(label, "")
    c2.metric("", bval)
    c3.metric("", cval)

# Cleaner KPI display
st.markdown("---")
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
r1c1.metric("BNPL Revenue Yield",    f"{bnpl_base['revenue_yield']:.1f}%")
r1c2.metric("BNPL Net Margin",       f"{bnpl_base['net_margin_pct']:.1f}%")
r1c3.metric("CC Revenue Yield",      f"{cc_base['revenue_yield']:.1f}%")
r1c4.metric("CC Net Margin",         f"{cc_base['net_margin_pct']:.1f}%")

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
r2c1.metric("BNPL NPV / Account",    f"${bnpl_npv['npv_per_acct']:,.0f}")
r2c2.metric("BNPL Net Loss Rate",    f"{bnpl_base['net_loss_rate']:.1f}%")
r2c3.metric("CC NPV / Account",      f"${cc_npv['npv_per_acct']:,.0f}")
r2c4.metric("CC Net Loss Rate",      f"{cc_base['net_loss_rate']:.1f}%")

st.markdown("---")

# ── Section 2: P&L Waterfalls ─────────────────────────────────────────────────
st.subheader("P&L Waterfall — Base Scenario")
wl, wr = st.columns(2)

def waterfall(row, title):
    items = [
        ("Revenue",      row["total_revenue"],   "increasing"),
        ("CoF",         -row["total_cof"],        "decreasing"),
        ("Gross Loss",  -row["total_gross_loss"], "decreasing"),
        ("Recovery",     row["total_recovery"],   "increasing"),
        ("Servicing",   -row["total_servicing"],  "decreasing"),
        ("Orig. Cost",  -row["total_orig_cost"],  "decreasing"),
        ("Net CF",       row["total_net_cf"],     "total"),
    ]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=[i[2] for i in items],
        x=[i[0] for i in items],
        y=[i[1] for i in items],
        text=[f"${i[1]:,.0f}" for i in items],
        textposition="outside",
        connector=dict(line=dict(color="#CCC", width=1)),
        increasing=dict(marker_color=GREEN),
        decreasing=dict(marker_color=RED),
        totals=dict(marker_color=BLUE),
    ))
    fig.update_layout(
        title=title, height=380,
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=11),
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEE")
    return fig

with wl:
    st.plotly_chart(waterfall(bnpl_base, "BNPL — Lifetime P&L (1,000 accounts)"), use_container_width=True)
with wr:
    st.plotly_chart(waterfall(cc_base, "Credit Card — Lifetime P&L (1,000 accounts)"), use_container_width=True)

st.markdown("---")

# ── Section 3: Scenario Comparison ───────────────────────────────────────────
st.subheader("Scenario Analysis — Net Margin % by Product")

scenario_tab = summary_df.pivot_table(index="scenario", columns="product", values="net_margin_pct").reset_index()

fig_scenario = go.Figure()
for product in ["BNPL", "Credit Card"]:
    if product in scenario_tab.columns:
        fig_scenario.add_trace(go.Bar(
            name=product,
            x=scenario_tab["scenario"],
            y=scenario_tab[product],
            marker_color=PRODUCT_COLORS[product],
            text=scenario_tab[product].round(1).astype(str) + "%",
            textposition="outside",
        ))

fig_scenario.update_layout(
    barmode="group", height=360,
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Arial", size=12),
    xaxis_title="Scenario", yaxis_title="Net Margin (%)",
    legend_title="Product", margin=dict(l=60, r=40, t=20, b=60),
)
fig_scenario.update_yaxes(showgrid=True, gridcolor="#EEE", ticksuffix="%")
st.plotly_chart(fig_scenario, use_container_width=True)
st.markdown("---")

# ── Section 4: Cumulative CF Curves ──────────────────────────────────────────
st.subheader("Cumulative Net Cash Flow per Account")
cf_left, cf_right = st.columns(2)

for col, product in zip([cf_left, cf_right], ["BNPL", "Credit Card"]):
    with col:
        fig = go.Figure()
        for scenario in ["optimistic", "base", "stress"]:
            df = results[(product, scenario)]
            fig.add_trace(go.Scatter(
                x=df["month"], y=df["cum_net_cf_per_acct"],
                mode="lines", name=scenario.title(),
                line=dict(color=SCENARIO_COLORS[scenario], width=2),
            ))
        fig.add_hline(y=0, line_dash="dash", line_color=GRAY)
        fig.update_layout(
            title=f"{product} — Cumulative CF/Account", height=360,
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Arial", size=11),
            legend_title="Scenario", margin=dict(l=50, r=20, t=50, b=50),
        )
        fig.update_xaxes(title_text="Month", showgrid=True, gridcolor="#EEE")
        fig.update_yaxes(title_text="$ / Account", showgrid=True, gridcolor="#EEE")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Section 5: NPV Comparison ─────────────────────────────────────────────────
st.subheader(f"Discounted NPV per Account — Base Scenario (WACC={wacc:.0%})")

monthly_rate = (1 + wacc) ** (1/12) - 1
fig_npv = go.Figure()
for product in ["BNPL", "Credit Card"]:
    df = results[(product, "base")]
    months = df["month"].values
    disc   = 1 / (1 + monthly_rate) ** months
    cum_npv = np.cumsum(df["net_cf_per_acct"].values * disc)
    fig_npv.add_trace(go.Scatter(
        x=months, y=cum_npv,
        mode="lines", name=product,
        line=dict(color=PRODUCT_COLORS[product], width=2.5),
    ))

fig_npv.add_hline(y=0, line_dash="dash", line_color=GRAY)
fig_npv.update_layout(
    height=380, plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Arial", size=12), legend_title="Product",
    margin=dict(l=60, r=40, t=20, b=60),
)
fig_npv.update_xaxes(title_text="Month", showgrid=True, gridcolor="#EEE")
fig_npv.update_yaxes(title_text="Cumulative NPV / Account ($)", showgrid=True, gridcolor="#EEE")
st.plotly_chart(fig_npv, use_container_width=True)

st.markdown("---")

# ── Section 6: Full Scenario Summary Table ────────────────────────────────────
st.subheader("Full Scenario Summary Table")
display_cols = ["product", "scenario", "revenue_yield", "net_loss_rate", "net_margin_pct",
                "total_revenue", "total_net_loss", "total_net_cf"]
st.dataframe(
    summary_df[display_cols].style.format({
        "revenue_yield":    "{:.2f}%",
        "net_loss_rate":    "{:.2f}%",
        "net_margin_pct":   "{:.2f}%",
        "total_revenue":    "${:,.0f}",
        "total_net_loss":   "${:,.0f}",
        "total_net_cf":     "${:,.0f}",
    }).background_gradient(subset=["net_margin_pct"], cmap="RdYlGn"),
    use_container_width=True,
)

st.markdown("---")
st.caption(
    "Built by Denzel C. Seals · "
    "Framework: BNPL vs. Credit Card Unit Economics · "
    "github.com/DSeals12"
)
