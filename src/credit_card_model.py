"""
credit_card_model.py
--------------------
Month-by-month P&L model for a revolving credit card account cohort.

Credit card structure:
  - Revolving balance with monthly purchases, payments, and interest accrual
  - Revenue = interest income (APR × ADB) + interchange + fees
  - Balance evolves each month based on purchases, payments, and defaults
  - Longer duration than BNPL: modeled over 36 months

Returns a DataFrame with one row per month tracking full P&L waterfall.
"""

import numpy as np
import pandas as pd
from src.assumptions import CREDIT_CARD, SHARED


def run_credit_card_model(
    scenario: str = "base",
    n_accounts: int = 1_000,
    assumptions: dict = None,
) -> pd.DataFrame:
    """
    Simulate monthly P&L for a credit card account cohort.

    Parameters
    ----------
    scenario     : 'base', 'stress', or 'optimistic'
    n_accounts   : cohort size
    assumptions  : override CREDIT_CARD assumptions dict (optional)

    Returns
    -------
    DataFrame with monthly P&L, one row per month
    """
    a = {**CREDIT_CARD, **(assumptions or {})}
    s = SHARED

    # Scenario adjustments
    monthly_default = a["monthly_default_rate"] * a["scenario_loss_mult"][scenario]
    apr_annual      = a["apr_annual"] + a["scenario_apr_adj"][scenario]
    monthly_rate    = apr_annual / 12
    cof_monthly     = (a["cost_of_funds_annual"] + a["scenario_cof_adj"][scenario]) / 12

    credit_line      = a["avg_credit_line"]
    balance          = credit_line * a["initial_utilization"]
    active_accounts  = float(n_accounts)
    cumulative_co    = 0.0

    records = []

    for month in range(1, a["max_months"] + 1):

        # ── Defaults ──────────────────────────────────────────────────────────
        new_defaults    = active_accounts * monthly_default
        defaulted_bal   = balance * (new_defaults / max(active_accounts, 1))
        active_accounts = max(active_accounts - new_defaults, 0)
        cumulative_co  += new_defaults

        # ── Balance Evolution (performing accounts) ───────────────────────────
        # Interest accrual
        interest_accrued = balance * monthly_rate * active_accounts

        # New purchases
        new_purchases = balance * a["avg_purchase_rate_mo"] * active_accounts

        # Payments (min payment + voluntary paydown)
        min_payment   = balance * a["min_payment_rate"] * active_accounts
        extra_paydown = balance * a["paydown_rate_mo"] * active_accounts
        total_payment = min_payment + extra_paydown

        # Update balance
        total_balance = balance * active_accounts
        total_balance = total_balance + interest_accrued + new_purchases - total_payment - defaulted_bal
        total_balance = max(total_balance, 0)
        balance       = total_balance / max(active_accounts, 1)
        balance       = min(balance, credit_line)  # cap at credit line

        # ── Revenue ───────────────────────────────────────────────────────────
        interest_income  = interest_accrued
        interchange_rev  = new_purchases * a["interchange_rate"]
        late_fee_rev     = a["late_fee"] * a["late_fee_pct_accounts"] * active_accounts
        annual_fee_rev   = (a["annual_fee"] / 12) * active_accounts
        total_revenue    = interest_income + interchange_rev + late_fee_rev + annual_fee_rev

        # ── Cost of Funds ──────────────────────────────────────────────────────
        cof = total_balance * cof_monthly

        # ── Credit Losses ──────────────────────────────────────────────────────
        gross_loss = 0.0
        recovery   = 0.0

        co_month = a["charge_off_lag_months"]
        if month > co_month:
            # Charge off accounts that defaulted [co_lag] months ago
            # Approximation: spread charge-offs over the loss recognition window
            gross_loss = defaulted_bal * s["loss_given_default"]

        rec_month = co_month + s["recovery_lag_months"]
        if month > rec_month:
            recovery = defaulted_bal * s["loss_given_default"] * s["recovery_rate"]

        net_loss = gross_loss - recovery

        # ── Servicing & Origination ────────────────────────────────────────────
        servicing  = s["cost_per_account_mo"] * active_accounts
        orig_cost  = s["origination_cost"] * n_accounts if month == 1 else 0

        # ── Net Cash Flow ──────────────────────────────────────────────────────
        net_cf = total_revenue - cof - net_loss - servicing - orig_cost

        records.append({
            "month":               month,
            "scenario":            scenario,
            "product":             "Credit Card",
            "active_accounts":     round(active_accounts, 1),
            "outstanding_balance": round(total_balance, 2),
            "avg_balance":         round(balance, 2),
            "interest_income":     round(interest_income, 2),
            "interchange_revenue": round(interchange_rev, 2),
            "late_fee_revenue":    round(late_fee_rev, 2),
            "annual_fee_revenue":  round(annual_fee_rev, 2),
            "total_revenue":       round(total_revenue, 2),
            "cost_of_funds":       round(cof, 2),
            "gross_loss":          round(gross_loss, 2),
            "recovery":            round(recovery, 2),
            "net_loss":            round(net_loss, 2),
            "servicing_cost":      round(servicing, 2),
            "origination_cost":    round(orig_cost, 2),
            "net_cash_flow":       round(net_cf, 2),
        })

        if active_accounts < 1:
            break

    df = pd.DataFrame(records)

    # Per-account & cumulative metrics
    orig_balance_total = CREDIT_CARD["avg_credit_line"] * CREDIT_CARD["initial_utilization"] * n_accounts
    df["revenue_per_acct"]    = df["total_revenue"]  / n_accounts
    df["loss_per_acct"]       = df["net_loss"]        / n_accounts
    df["net_cf_per_acct"]     = df["net_cash_flow"]   / n_accounts
    df["cum_net_cf"]          = df["net_cash_flow"].cumsum()
    df["cum_net_cf_per_acct"] = df["net_cf_per_acct"].cumsum()
    df["cum_loss_rate"]       = df["gross_loss"].cumsum() / orig_balance_total

    return df


def credit_card_summary(df: pd.DataFrame) -> dict:
    """Summarize lifetime P&L from a credit card model run."""
    n = df["active_accounts"].iloc[0] + (df["active_accounts"].iloc[0] - df["active_accounts"].iloc[-1])
    orig_bal = CREDIT_CARD["avg_credit_line"] * CREDIT_CARD["initial_utilization"]
    return {
        "product":            "Credit Card",
        "scenario":           df["scenario"].iloc[0],
        "total_revenue":      round(df["total_revenue"].sum(), 2),
        "total_cof":          round(df["cost_of_funds"].sum(), 2),
        "total_gross_loss":   round(df["gross_loss"].sum(), 2),
        "total_recovery":     round(df["recovery"].sum(), 2),
        "total_net_loss":     round(df["net_loss"].sum(), 2),
        "total_servicing":    round(df["servicing_cost"].sum(), 2),
        "total_orig_cost":    round(df["origination_cost"].sum(), 2),
        "total_net_cf":       round(df["net_cash_flow"].sum(), 2),
        "net_margin_pct":     round(df["net_cash_flow"].sum() / max(df["total_revenue"].sum(), 1) * 100, 2),
        "net_loss_rate":      round(df["gross_loss"].sum() / (orig_bal * df["active_accounts"].iloc[0]) * 100, 2),
        "revenue_yield":      round(df["total_revenue"].sum() / (orig_bal * df["active_accounts"].iloc[0]) * 100, 2),
    }
