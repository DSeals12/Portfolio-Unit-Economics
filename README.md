# Portfolio Unit Economics Model — BNPL vs. Credit Card

**Author:** Denzel C. Seals | Senior Data Analyst  
**Domain:** Consumer Credit — Portfolio P&L, FP&A, Program Economics  
**Stack:** Python · Pandas · Plotly · Streamlit  

---

## Overview

This project models the **lifetime unit economics** of a consumer credit account from
origination through charge-off or payoff, across two product types:

- **BNPL (Buy Now Pay Later)** — short-duration, fixed installment, merchant-funded yield
- **Credit Card** — revolving, interest-bearing, longer duration, higher yield/loss

For each product, we build a **cohort-level P&L waterfall** that decomposes account
economics into yield, cost of funds, credit loss, servicing cost, and net margin —
then project NPV across the account lifetime under base, stress, and optimistic scenarios.

---

## Business Context

Unit economics answer the foundational question every credit P&L owner must be able to answer:

> *"For every $1,000 we originate today, what do we expect to earn, lose, and net — and under what conditions does this product stop making money?"*

This framework is used by:
- **FP&A teams** to build portfolio-level margin forecasts
- **Credit risk teams** to set loss thresholds and pricing floors
- **Product teams** to compare economics across programs or structures
- **Executives** to evaluate new product launches or acquisition pricing

---

## Project Structure

```
portfolio-unit-economics/
│
├── data/
│   └── processed/              # Generated scenario outputs (parquet)
│
├── src/
│   ├── assumptions.py          # All economic assumptions in one place
│   ├── bnpl_model.py           # BNPL account P&L engine
│   ├── credit_card_model.py    # Credit card revolving P&L engine
│   ├── scenario_engine.py      # Base / stress / optimistic scenario runner
│   ├── npv.py                  # NPV and IRR calculations
│   └── visualization.py        # Reusable Plotly chart functions
│
├── notebooks/
│   └── unit_economics.ipynb    # Full analysis narrative
│
├── app/
│   └── streamlit_app.py        # Interactive P&L & scenario simulator
│
├── outputs/
│   └── charts/                 # Exported chart PNGs
│
├── requirements.txt
└── README.md
```

---

## Quickstart

```bash
git clone https://github.com/DSeals12/portfolio-unit-economics.git
cd portfolio-unit-economics
pip install -r requirements.txt

# Run notebook
jupyter notebook notebooks/unit_economics.ipynb

# Launch Streamlit app
streamlit run app/streamlit_app.py
```

---

## Key Outputs

| Output | Description |
|---|---|
| P&L Waterfall | Yield → Net Revenue → Credit Loss → Servicing → Net Margin per account |
| Cohort NPV Curve | Discounted cumulative cash flows over account lifetime |
| Scenario Analysis | Base / Stress / Optimistic with sensitivity table |
| BNPL vs. Credit Card | Side-by-side economics comparison across all metrics |
| Break-even Analysis | Loss rate at which each product stops being profitable |

---

## Methodology

### BNPL Model
- Fixed installment structure (e.g. 4 payments over 6 weeks or 12 monthly payments)
- Yield = Merchant Discount Rate (MDR) — typically 2–6% of GMV
- No interest charged to consumer; revenue is entirely merchant-funded
- Short duration (3–12 months) means faster loss recognition but lower yield per account

### Credit Card Model
- Revolving structure with monthly minimum payment
- Yield = APR × average daily balance (ADB method)
- Interest accrual, fee income (late fees, annual fees)
- Longer duration (18–36 months average) drives higher lifetime yield and loss

### Scenario Framework
| Scenario | Loss Rate | Yield | Cost of Funds |
|---|---|---|---|
| Optimistic | −25% vs base | +5% | −10bps |
| Base | As modeled | As modeled | As modeled |
| Stress | +40% vs base | −5% | +50bps |

### NPV Methodology
- Discount rate: WACC assumption (configurable, default 8%)
- Cash flows: monthly net revenue minus credit losses minus servicing costs
- Recovery cash flows included at 6 months post charge-off
