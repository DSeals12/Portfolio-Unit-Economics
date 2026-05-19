"""
bnpl_model.py
-------------
Month-by-month P&L model for a single BNPL account cohort.

BNPL structure:
  - Fixed installment loan (e.g. 4x or 6 monthly payments)
  - Revenue = Merchant Discount Rate (MDR) × original transaction size
    recognized upfront or ratably over the term
  - No interest charged to consumer
  - Loss = account defaults and stops paying remaining balance

Returns a DataFrame with one row per month, tracking:
  - Outstanding balance
  - Revenue components (MDR, late fees)
  - Cost of funds
  - Credit losses
  - Servicing costs
  - Net cash flow
"""

import numpy as np
import pandas as pd
from src.assumptions import BNPL, SHARED


def run_bnpl_model(
    scenario: str = "base",
    n_accounts: int = 1_000,
    assumptions: dict = None,
) -> pd.DataFrame:
    """
    Simulate monthly P&L for a BNPL account cohort.

    Parameters
    ----------
    scenario     : 'base', 'stress', or 'optimistic'
    n_accounts   : cohort size (scales all dollar amounts)
    assumptions  : override BNPL assumptions dict (optional)

    Returns
    -------
    DataFrame with monthly P&L per account (then scaled by n_accounts)
    """
    a = {**BNPL, **(assumptions or {})}
    s = SHARED

    # Scenario adjustments
    monthly_default = a["monthly_default_rate"] * a["scenario_loss_mult"][scenario]
    mdr             = a["mdr_rate"] + a["scenario_mdr_adj"][scenario]
    cof_annual      = a["cost_of_funds_annual"] + a["scenario_cof_adj"][scenario]
    cof_monthly     = cof_annual / 12

    term     = a["term_months"]
    balance  = a["avg_transaction_size"]
    monthly_payment = balance / term

    # MDR revenue — recognized ratably over the term
    mdr_revenue_total = balance * mdr
    mdr_per_month     = mdr_revenue_total / term

    records = []
    remaining_balance   = balance
    cumulative_defaults = 0.0
    active_accounts     = n_accounts  # accounts still paying

    for month in range(1, term + a["charge_off_lag_months"] + s["recovery_lag_months"] + 1):

        # Defaults this month
        new_defaults     = active_accounts * monthly_default
        defaulted_bal    = (remaining_balance / max(active_accounts, 1)) * new_defaults if active_accounts > 0 else 0
        active_accounts  = max(active_accounts - new_defaults, 0)
        cumulative_defaults += new_defaults

        # Balance paydown (performing accounts only)
        if month <= term and active_accounts > 0:
            payment_received = monthly_payment * active_accounts
            remaining_balance = max(remaining_balance * active_accounts - payment_received, 0) / max(active_accounts, 1) if active_accounts > 0 else 0
        else:
            remaining_balance = 0.0

        # Revenue
        mdr_rev    = mdr_per_month * active_accounts if month <= term else 0
        late_rev   = a["late_fee"] * a["late_fee_pct_accounts"] * active_accounts

        # Cost of funds (on average outstanding balance)
        avg_bal_total  = remaining_balance * active_accounts
        cof            = avg_bal_total * cof_monthly

        # Credit losses (charge off at lag)
        gross_loss = 0.0
        recovery   = 0.0
        if month == a["charge_off_lag_months"] + 1:
            gross_loss = cumulative_defaults * (balance / n_accounts) * s["loss_given_default"]
        if month == a["charge_off_lag_months"] + 1 + s["recovery_lag_months"]:
            recovery = cumulative_defaults * (balance / n_accounts) * s["loss_given_default"] * s["recovery_rate"]

        net_loss = gross_loss - recovery

        # Servicing
        servicing = s["cost_per_account_mo"] * active_accounts
        orig_cost = s["origination_cost"] * n_accounts if month == 1 else 0

        # Net cash flow
        net_revenue  = mdr_rev + late_rev
        net_cf       = net_revenue - cof - net_loss - servicing - orig_cost

        records.append({
            "month":              month,
            "scenario":           scenario,
            "product":            "BNPL",
            "active_accounts":    round(active_accounts, 1),
            "outstanding_balance":round(remaining_balance * active_accounts, 2),
            "mdr_revenue":        round(mdr_rev, 2),
            "late_fee_revenue":   round(late_rev, 2),
            "total_revenue":      round(net_revenue, 2),
            "cost_of_funds":      round(cof, 2),
            "gross_loss":         round(gross_loss, 2),
            "recovery":           round(recovery, 2),
            "net_loss":           round(net_loss, 2),
            "servicing_cost":     round(servicing, 2),
            "origination_cost":   round(orig_cost, 2),
            "net_cash_flow":      round(net_cf, 2),
        })

        if active_accounts < 1 and gross_loss > 0 and recovery > 0:
            break

    df = pd.DataFrame(records)

    # Per-account metrics
    orig_balance_total = a["avg_transaction_size"] * n_accounts
    df["revenue_per_acct"]  = df["total_revenue"]  / n_accounts
    df["loss_per_acct"]     = df["net_loss"]        / n_accounts
    df["net_cf_per_acct"]   = df["net_cash_flow"]   / n_accounts
    df["cum_net_cf"]        = df["net_cash_flow"].cumsum()
    df["cum_net_cf_per_acct"] = df["net_cf_per_acct"].cumsum()
    df["cum_loss_rate"]     = df["gross_loss"].cumsum() / orig_balance_total

    return df


def bnpl_summary(df: pd.DataFrame) -> dict:
    """Summarize lifetime P&L from a BNPL model run."""
    orig_bal = df["outstanding_balance"].iloc[0] + df["gross_loss"].sum() / SHARED["loss_given_default"]
    return {
        "product":            "BNPL",
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
        "net_loss_rate":      round(df["gross_loss"].sum() / (BNPL["avg_transaction_size"] * df["active_accounts"].iloc[0]) * 100, 2),
        "revenue_yield":      round(df["total_revenue"].sum() / (BNPL["avg_transaction_size"] * df["active_accounts"].iloc[0]) * 100, 2),
    }
