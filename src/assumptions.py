"""
assumptions.py
--------------
Single source of truth for all economic assumptions across both models.
Editing values here propagates through the entire analysis.

All rates are monthly unless noted as annual.
"""

# ── Shared ────────────────────────────────────────────────────────────────────

SHARED = {
    "wacc":                  0.08,    # Annual discount rate (WACC)
    "loss_given_default":    0.75,    # LGD — fraction of balance lost at charge-off
    "recovery_rate":         0.15,    # Recovery on charged-off balances
    "recovery_lag_months":   6,       # Months after charge-off to apply recovery
    "cost_per_account_mo":   2.50,    # Monthly servicing cost per active account ($)
    "origination_cost":      25.0,    # One-time origination cost per account ($)
}

# ── BNPL Assumptions ─────────────────────────────────────────────────────────

BNPL = {
    # Product structure
    "avg_transaction_size":  650,     # Average purchase amount ($)
    "term_months":           6,       # Installment term (months)
    "payment_frequency":     "monthly",

    # Revenue
    "mdr_rate":              0.04,    # Merchant Discount Rate (4% of GMV)
    "late_fee":              8.0,     # Late fee per missed payment ($)
    "late_fee_pct_accounts": 0.08,    # % of accounts that pay a late fee per month

    # Credit
    "monthly_default_rate":  0.012,   # Monthly probability of default (base)
    "charge_off_lag_months": 3,       # Months delinquent before charge-off

    # Funding
    "cost_of_funds_annual":  0.055,   # Annual cost of funds (warehouse line)

    # Scenarios (multipliers on base monthly_default_rate)
    "scenario_loss_mult": {
        "optimistic": 0.75,
        "base":       1.00,
        "stress":     1.40,
    },
    "scenario_mdr_adj": {            # Additive adjustment to MDR
        "optimistic":  0.002,
        "base":        0.000,
        "stress":     -0.005,
    },
    "scenario_cof_adj": {            # Additive adjustment to annual CoF
        "optimistic": -0.001,
        "base":        0.000,
        "stress":      0.005,
    },
}

# ── Credit Card Assumptions ───────────────────────────────────────────────────

CREDIT_CARD = {
    # Product structure
    "avg_credit_line":       4_500,   # Average credit line ($)
    "initial_utilization":   0.35,    # Starting utilization rate
    "min_payment_rate":      0.02,    # Minimum payment as % of balance
    "avg_purchase_rate_mo":  0.015,   # Monthly new purchases as % of line
    "paydown_rate_mo":       0.025,   # Extra paydown beyond minimum (% of balance)

    # Revenue
    "apr_annual":            0.2199,  # Annual Percentage Rate (21.99%)
    "annual_fee":            0.0,     # Annual fee per account ($)
    "late_fee":              30.0,    # Late fee per occurrence ($)
    "late_fee_pct_accounts": 0.06,    # % of accounts triggering late fee per month
    "interchange_rate":      0.015,   # Monthly interchange on purchases

    # Credit
    "monthly_default_rate":  0.008,   # Monthly probability of default (base)
    "charge_off_lag_months": 6,       # Months before charge-off

    # Funding
    "cost_of_funds_annual":  0.060,   # Annual cost of funds

    # Max months to model
    "max_months":            36,

    # Scenarios
    "scenario_loss_mult": {
        "optimistic": 0.75,
        "base":       1.00,
        "stress":     1.40,
    },
    "scenario_apr_adj": {            # Additive adjustment to annual APR
        "optimistic":  0.010,
        "base":        0.000,
        "stress":     -0.010,
    },
    "scenario_cof_adj": {
        "optimistic": -0.001,
        "base":        0.000,
        "stress":      0.005,
    },
}
