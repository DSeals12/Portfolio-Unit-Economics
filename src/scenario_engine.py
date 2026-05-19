"""
scenario_engine.py
------------------
Runs all scenarios (base / stress / optimistic) for both products
and assembles a unified comparison DataFrame.
"""

import pandas as pd
import numpy as np
from src.bnpl_model import run_bnpl_model, bnpl_summary
from src.credit_card_model import run_credit_card_model, credit_card_summary
from src.assumptions import SHARED

SCENARIOS = ["optimistic", "base", "stress"]
PRODUCTS  = ["BNPL", "Credit Card"]


def run_all_scenarios(n_accounts: int = 1_000) -> dict:
    """
    Run all 6 combinations (2 products × 3 scenarios).
    Returns a dict keyed by (product, scenario) → monthly DataFrame.
    """
    results = {}
    for scenario in SCENARIOS:
        results[("BNPL", scenario)]          = run_bnpl_model(scenario=scenario, n_accounts=n_accounts)
        results[("Credit Card", scenario)]   = run_credit_card_model(scenario=scenario, n_accounts=n_accounts)
    return results


def build_summary_table(results: dict) -> pd.DataFrame:
    """
    Build a summary table across all scenarios and products.
    One row per (product, scenario).
    """
    rows = []
    for (product, scenario), df in results.items():
        if product == "BNPL":
            row = bnpl_summary(df)
        else:
            row = credit_card_summary(df)
        rows.append(row)
    return pd.DataFrame(rows)


def build_sensitivity_table(
    product: str = "BNPL",
    n_accounts: int = 1_000,
    loss_shocks: list = None,
    yield_shocks: list = None,
) -> pd.DataFrame:
    """
    Two-dimensional sensitivity: net margin % across loss rate shocks × yield shocks.
    """
    from src.bnpl_model import run_bnpl_model
    from src.credit_card_model import run_credit_card_model
    from src.assumptions import BNPL, CREDIT_CARD

    loss_shocks  = loss_shocks  or [-0.30, -0.15, 0, +0.15, +0.30, +0.50]
    yield_shocks = yield_shocks or [-0.010, -0.005, 0, +0.005, +0.010]

    rows = []
    for ls in loss_shocks:
        row = {"loss_shock": f"{ls:+.0%}"}
        for ys in yield_shocks:
            if product == "BNPL":
                overrides = {
                    "scenario_loss_mult": {"base": 1 + ls, "optimistic": 1 + ls, "stress": 1 + ls},
                    "scenario_mdr_adj":   {"base": ys, "optimistic": ys, "stress": ys},
                }
                df = run_bnpl_model(scenario="base", n_accounts=n_accounts, assumptions={**BNPL, **overrides})
                s  = bnpl_summary(df)
            else:
                overrides = {
                    "scenario_loss_mult": {"base": 1 + ls, "optimistic": 1 + ls, "stress": 1 + ls},
                    "scenario_apr_adj":   {"base": ys, "optimistic": ys, "stress": ys},
                }
                df = run_credit_card_model(scenario="base", n_accounts=n_accounts, assumptions={**CREDIT_CARD, **overrides})
                s  = credit_card_summary(df)

            row[f"yield {ys:+.1%}"] = f"{s['net_margin_pct']:.1f}%"
        rows.append(row)

    return pd.DataFrame(rows).set_index("loss_shock")


# ── NPV ───────────────────────────────────────────────────────────────────────

def compute_npv(cash_flows: pd.Series, annual_wacc: float = None) -> float:
    """
    Compute NPV of a monthly cash flow series.
    Month 0 is the origination cost (negative cash flow).
    """
    wacc = annual_wacc or SHARED["wacc"]
    monthly_rate = (1 + wacc) ** (1/12) - 1
    months = np.arange(1, len(cash_flows) + 1)
    discount_factors = 1 / (1 + monthly_rate) ** months
    return float((cash_flows.values * discount_factors).sum())


def compute_irr(cash_flows: pd.Series, initial_investment: float) -> float:
    """
    Compute monthly IRR annualized.
    initial_investment should be positive (the cost).
    """
    flows = np.concatenate([[-initial_investment], cash_flows.values])
    # Newton-Raphson approximation
    rate = 0.01  # initial guess (monthly)
    for _ in range(1000):
        months = np.arange(len(flows))
        npv  = np.sum(flows / (1 + rate) ** months)
        dnpv = np.sum(-months * flows / (1 + rate) ** (months + 1))
        if abs(dnpv) < 1e-10:
            break
        rate -= npv / dnpv
        if rate <= -1:
            return float("nan")
    annual_irr = (1 + rate) ** 12 - 1
    return round(annual_irr * 100, 2)


def npv_summary(results: dict, n_accounts: int = 1_000) -> pd.DataFrame:
    """
    Compute NPV and IRR per account for all scenario/product combinations.
    """
    from src.assumptions import BNPL, CREDIT_CARD
    rows = []
    for (product, scenario), df in results.items():
        npv_total = compute_npv(df["net_cash_flow"])
        npv_per_acct = npv_total / n_accounts

        if product == "BNPL":
            init_inv = BNPL["avg_transaction_size"] * n_accounts
        else:
            init_inv = CREDIT_CARD["avg_credit_line"] * CREDIT_CARD["initial_utilization"] * n_accounts

        irr = compute_irr(df["net_cash_flow"], initial_investment=init_inv)

        rows.append({
            "product":       product,
            "scenario":      scenario,
            "npv_total":     round(npv_total, 2),
            "npv_per_acct":  round(npv_per_acct, 2),
            "irr_annual_pct": irr,
        })
    return pd.DataFrame(rows)
