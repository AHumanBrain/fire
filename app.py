# app.py
# FIRE Strategy Analyzer – Streamlit version

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
    spend = inputs["desired_retirement_expenses"] * ((1+inputs["inflation_rate"])**yrs)
    need = spend * inputs["taxable_bridge_years_required"]
    avail = inputs["balances"]["taxable_investments"] + inputs["balances"]["cash_emergency"]
    return {
        "spend_at_ret": spend,
        "need": need,
        "avail": avail,
        "status": "OK" if avail >= need else "SHORT"
    }

def monte_carlo(inputs, trials=500, horizon=40):
    start = project(inputs)["nest_egg"]
    spend = required(inputs)["spend_at_ret"]
    swr = inputs["safe_withdrawal_rate"]
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

# ======================
# Streamlit UI
# ======================
st.title("🔥 FIRE Strategy Analyzer")
st.write("Estimate whether your savings, investments, and withdrawal strategy can support early retirement.")

st.sidebar.header("Inputs")

# Basic demographics
current_age = st.sidebar.number_input("Current age", 20, 70, 35)
target_age = st.sidebar.number_input("Target retirement age", 30, 70, 50)
expenses = st.sidebar.number_input("Current annual expenses ($)", 10000, 200000, 40000, step=1000)
desired_expenses = st.sidebar.number_input("Target retirement annual expenses ($)", 10000, 200000, 40000, step=1000)
income = st.sidebar.number_input("Gross annual income ($)", 20000, 500000, 120000, step=1000)

# Contributions
st.sidebar.subheader("Annual Contributions")
pre_tax_401k = st.sidebar.number_input("Pre-tax 401(k)", 0, 22500, 15000, step=500)
roth_ira = st.sidebar.number_input("Roth IRA", 0, 6500, 6000, step=500)
hsa = st.sidebar.number_input("HSA", 0, 4000, 3650, step=100)
taxable = st.sidebar.number_input("Taxable investments", 0, 100000, 12000, step=500)
cash = st.sidebar.number_input("Cash savings", 0, 20000, 2000, step=500)
employer_match = st.sidebar.number_input("Employer 401(k) match", 0, 10000, 3000, step=500)

# Current balances
st.sidebar.subheader("Current Balances")
bal_trad_401k = st.sidebar.number_input("Traditional 401(k)", 0, 1000000, 80000, step=1000)
bal_trad_ira = st.sidebar.number_input("Traditional IRA", 0, 1000000, 20000, step=1000)
bal_roth = st.sidebar.number_input("Roth IRA", 0, 1000000, 15000, step=1000)
bal_hsa = st.sidebar.number_input("HSA", 0, 100000, 5000, step=500)
bal_taxable = st.sidebar.number_input("Taxable investments", 0, 1000000, 30000, step=1000)
bal_cash = st.sidebar.number_input("Cash/emergency fund", 0, 100000, 15000, step=500)

# Assumptions
st.sidebar.subheader("Assumptions")
real_return = st.sidebar.slider("Expected real return (%)", 0.0, 10.0, 5.0) / 100
swr = st.sidebar.slider("Safe withdrawal rate (%)", 2.0, 6.0, 3.5) / 100
infl = st.sidebar.slider("Inflation rate (%)", 0.0, 5.0, 2.0) / 100
bridge_years = st.sidebar.slider("Taxable bridge years for Roth ladder", 0, 10, 3)

# Bundle inputs
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
roth = roth_ladder(inputs)
mc_prob = monte_carlo(inputs, trials=500)

status = "ON TRACK" if proj["nest_egg"] >= reqs["required"]*inputs["safety_margin"] else "UNDER-SAVING"

st.header("Results")
st.metric("Years until retirement", proj["years"])
st.metric("Projected nest egg", f"${proj['nest_egg']:,.0f}")
st.metric("Required nest egg", f"${reqs['required']:,.0f}")
st.metric("Status", status)
st.metric("Monte Carlo success rate", f"{mc_prob:.0%}")

st.subheader("Roth Ladder Bridge")
st.write(f"Need ${roth['need']:,.0f}, Available ${roth['avail']:,.0f} → {roth['status']}")

# Plots
balances = pd.Series(inputs["balances"])
st.bar_chart(balances)

contribs = pd.Series(inputs["contributions"])
st.bar_chart(contribs)
