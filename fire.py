# FIRE Strategy Analyzer – Streamlit version with radar chart + your defaults

import streamlit as st
import numpy as np
import pandas as pd

# ======================
# Helper functions
# ======================
def years_until(target, current):
    return max(0, target - current)

def grow_balance(balance, years, r):
    return balance * ((1+r)**years)

def fv_annuity(contrib, years, r):
    if years <= 0: return 0
    return contrib * (((1+r)**years - 1) / r)

def project(inputs):
    yrs = years_until(inputs["target_retire_age"], inputs["current_age"])
    total_now = sum(inputs["balances"].values())
    grown_now = grow_balance(total_now, yrs, inputs["real_return"])
    annual_contrib = sum(inputs["contributions"].values())
    fv_contribs = fv_annuity(annual_contrib, yrs, inputs["real_return"])
    return {
        "years": yrs,
        "total_now": total_now,
        "nest_egg": grown_now + fv_contribs,
        "annual_contrib": annual_contrib
    }

def required(inputs):
    yrs = years_until(inputs["target_retire_age"], inputs["current_age"])
    spend = inputs["desired_retirement_expenses"] * ((1+inputs["inflation_rate"])**yrs)
    req = spend / inputs["safe_withdrawal_rate"]
    return {"spend_at_ret": spend, "required": req}

def roth_ladder(inputs):
    yrs = years_until(inputs["target_retire_age"], inputs["current_age"])
    spend = required(inputs)["spend_at_ret"]
    need = spend * inputs["taxable_bridge_years_required"]
    avail = inputs["balances"]["taxable_investments"] + inputs["balances"]["cash_emergency"]
    pct_covered = min(1, avail / need) if need > 0 else 1
    return {
        "Strategy": "Roth Conversion Ladder",
        "Coverage %": pct_covered,
        "Years Covered": avail / spend if spend > 0 else 0,
        "Monte Carlo Success %": None,
        "Status": "OK" if avail >= need else "SHORT"
    }

def sepp_72t(inputs):
    pre_tax_total = inputs["balances"]["traditional_401k"] + inputs["balances"]["traditional_ira"]
    annual_withdraw = 0.04 * pre_tax_total
    spend = required(inputs)["spend_at_ret"]
    pct_covered = min(1, annual_withdraw / spend) if spend > 0 else 0
    return {
        "Strategy": "72(t) SEPP",
        "Coverage %": pct_covered,
        "Years Covered": (annual_withdraw / spend) * 30 if spend > 0 else 0,
        "Monte Carlo Success %": None,
        "Status": "OK" if annual_withdraw >= spend else "SHORT"
    }

def taxable_first(inputs):
    taxable_total = inputs["balances"]["taxable_investments"] + inputs["balances"]["cash_emergency"]
    spend = required(inputs)["spend_at_ret"]
    years_covered = taxable_total / spend if spend > 0 else 0
    pct_covered = min(1, years_covered / 5)  # assume 5 years needed pre-59.5
    return {
        "Strategy": "Taxable Drawdown First",
        "Coverage %": pct_covered,
        "Years Covered": years_covered,
        "Monte Carlo Success %": None,
        "Status": "OK" if years_covered >= 5 else "SHORT"
    }

def monte_carlo(inputs, trials=500, horizon=40):
    start = project(inputs)["nest_egg"]
    spend = required(inputs)["spend_at_ret"]
    annual_spend = spend
    success = 0
    for _ in range(trials):
        bal = start
        for yr in range(horizon):
            r = np.random.normal(loc=inputs["real_return"], scale=0.12)
            bal *= (1 + r)
            bal -= annual_spend
            if bal <= 0:
                break
        else:
            success += 1
    return success / trials

def strategy_roth_ladder(inputs):
    """Check if taxable/cash can cover the 5-year Roth ladder bridge."""
    spend = required(inputs)["spend_at_ret"]
    need = spend * inputs["taxable_bridge_years_required"]
    avail = inputs["balances"]["taxable_investments"] + inputs["balances"]["cash_emergency"]
    coverage = avail / need if need > 0 else 0
    years = avail / spend if spend > 0 else 0
    return coverage, years, "OK" if avail >= need else "SHORT"

def strategy_sepp(inputs):
    """72(t) Substantially Equal Periodic Payments from Traditional IRA/401k."""
    spend = required(inputs)["spend_at_ret"]
    balance = inputs["balances"]["traditional_401k"] + inputs["balances"]["traditional_ira"]
    # crude 72(t) calc: divide by life expectancy (IRS ~30 yrs for early retirees)
    sepp_income = balance / 30  
    coverage = sepp_income / spend
    years = (balance / spend) if spend > 0 else 0
    return coverage, years, "OK" if sepp_income >= spend else "SHORT"

def strategy_taxable_drawdown(inputs):
    """Draw taxable investments/cash until empty."""
    spend = required(inputs)["spend_at_ret"]
    avail = inputs["balances"]["taxable_investments"] + inputs["balances"]["cash_emergency"]
    coverage = avail / spend if spend > 0 else 0
    years = avail / spend if spend > 0 else 0
    return coverage, years, "OK" if years >= 5 else "SHORT"  # needs ~5yr bridge

# ======================
# Streamlit UI
# ======================
st.title("🔥 FIRE Strategy Analyzer")
st.write("Estimate whether your savings, investments, and withdrawal strategy can support early retirement.")

st.sidebar.header("Inputs (pre-filled with your data)")

# ========== Defaults from your inputs ==========
current_age = st.sidebar.number_input("Current age", 20, 70, 30)
target_age = st.sidebar.number_input("Target retirement age", 30, 70, 50)
expenses = st.sidebar.number_input("Current annual expenses ($)", 10000, 200000, 30000, step=1000)
desired_expenses = st.sidebar.number_input("Target retirement annual expenses ($)", 10000, 200000, 60000, step=1000)
income = st.sidebar.number_input("Gross annual income ($)", 20000, 500000, 100000, step=1000)

st.sidebar.subheader("Annual Contributions")
pre_tax_401k = st.sidebar.number_input("Pre-tax 401(k)", 0, 30000, 23500, step=500)
roth_ira = st.sidebar.number_input("Roth IRA", 0, 6500, 0, step=500)
hsa = st.sidebar.number_input("HSA", 0, 4000, 0, step=100)
taxable = st.sidebar.number_input("Taxable investments", 0, 100000, 10000, step=500)
cash = st.sidebar.number_input("Cash savings", 0, 50000, 20000, step=500)
employer_match = st.sidebar.number_input("Employer 401(k) match", 0, 10000, 4000, step=500)

st.sidebar.subheader("Current Balances")
bal_trad_401k = st.sidebar.number_input("Traditional 401(k)", 0, 1000000, 100000, step=1000)
bal_trad_ira = st.sidebar.number_input("Traditional IRA", 0, 1000000, 69000, step=1000)
bal_roth = st.sidebar.number_input("Roth IRA", 0, 1000000, 69000, step=1000)
bal_hsa = st.sidebar.number_input("HSA", 0, 100000, 20000, step=500)
bal_taxable = st.sidebar.number_input("Taxable investments", 0, 1000000, 50000, step=1000)
bal_cash = st.sidebar.number_input("Cash/emergency fund", 0, 100000, 20000, step=500)

st.sidebar.subheader("Assumptions")
real_return = st.sidebar.slider("Expected real return (%)", 0.0, 10.0, 5.0) / 100
swr = st.sidebar.slider("Safe withdrawal rate (%)", 2.0, 6.0, 3.5) / 100
infl = st.sidebar.slider("Inflation rate (%)", 0.0, 5.0, 3.0) / 100
bridge_years = st.sidebar.slider("Taxable bridge years for Roth ladder", 0, 10, 3)

inputs = {
    "current_age": current_age,
    "target_retire_age": target_age,
    "current_yearly_expenses": expenses,
    "desired_retirement_expenses": desired_expenses,
    "inflation_rate": infl,
    "gross_income": income,
    "balances": {
        "traditional_401k": bal_trad_401k,
        "traditional_ira": bal_trad_ira,
        "roth_ira": bal_roth,
        "hsa": bal_hsa,
        "taxable_investments": bal_taxable,
        "cash_emergency": bal_cash,
    },
    "contributions": {
        "pre_tax_401k": pre_tax_401k,
        "roth_401k": 0,
        "roth_ira": roth_ira,
        "hsa": hsa,
        "taxable_investments": taxable,
        "cash_savings": cash,
        "employer_match": employer_match,
    },
    "real_return": real_return,
    "safe_withdrawal_rate": swr,
    "plan_for_roth_ladder": True,
    "taxable_bridge_years_required": bridge_years,
    "safety_margin": 0.9,
}

# ======================
# Run calculations
# ======================
proj = project(inputs)
reqs = required(inputs)
mc_prob = monte_carlo(inputs, trials=500)

# Build withdrawal strategies dynamically
coverage_rl, years_rl, status_rl = strategy_roth_ladder(inputs)
coverage_sepp, years_sepp, status_sepp = strategy_sepp(inputs)
coverage_tax, years_tax, status_tax = strategy_taxable_drawdown(inputs)

strategies = [
    {
        "Strategy": "Roth Conversion Ladder",
        "Coverage %": coverage_rl,
        "Years Covered": years_rl,
        "Monte Carlo Success %": mc_prob,
        "Status": status_rl
    },
    {
        "Strategy": "72(t) SEPP",
        "Coverage %": coverage_sepp,
        "Years Covered": years_sepp,
        "Monte Carlo Success %": mc_prob,
        "Status": status_sepp
    },
    {
        "Strategy": "Taxable Drawdown First",
        "Coverage %": coverage_tax,
        "Years Covered": years_tax,
        "Monte Carlo Success %": mc_prob,
        "Status": status_tax
    },
]

df_strategies = pd.DataFrame(strategies)

status = "ON TRACK" if proj["nest_egg"] >= reqs["required"]*inputs["safety_margin"] else "UNDER-SAVING"

# ======================
# Output
# ======================
st.header("Results")
st.metric("Years until retirement", proj["years"])
st.metric("Projected nest egg", f"${proj['nest_egg']:,.0f}")
st.metric("Required nest egg", f"${reqs['required']:,.0f}")
st.metric("Overall Status", status)
st.metric("Monte Carlo success rate", f"{mc_prob:.0%}")

st.subheader("Withdrawal Strategies – Comparison")
st.dataframe(df_strategies.set_index("Strategy"), use_container_width=True)

# ======================
# Strategy Comparison Bar Chart
# ======================
st.subheader("Strategy Metrics Comparison")

# Convert Coverage % and Monte Carlo Success % into % scale
df_plot = df_strategies.copy()
df_plot["Coverage %"] = df_plot["Coverage %"] * 100
df_plot["Monte Carlo Success %"] = df_plot["Monte Carlo Success %"] * 100

# Melt to long format for easier plotting
df_melted = df_plot.melt(id_vars="Strategy", 
                         value_vars=["Coverage %", "Years Covered", "Monte Carlo Success %"],
                         var_name="Metric", value_name="Value")

st.bar_chart(df_melted, x="Strategy", y="Value", color="Metric")



# ======================
# Bar Charts
# ======================
balances = pd.Series(inputs["balances"])
st.bar_chart(balances)

contribs = pd.Series(inputs["contributions"])
st.bar_chart(contribs)
