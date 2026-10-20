"""Streamlit entry point for the Rentals OS public demo."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import streamlit as st
from service import DemoPortfolio, PortfolioError

st.set_page_config(page_title="SASK LLC — SW Services", layout="wide")
if "portfolio" not in st.session_state: st.session_state.portfolio = DemoPortfolio()
portfolio: DemoPortfolio = st.session_state.portfolio
st.title("SASK LLC — SW Services")
st.warning("Demo data — all properties are fictional.")
page = st.sidebar.radio("Navigation", ["Dashboard", "Properties", "Tenants & Leases", "Payments", "Mortgages"])
if st.sidebar.button("Reset to demo data"):
    st.session_state.portfolio = DemoPortfolio(); st.rerun()

if page == "Dashboard":
    kpis = portfolio.kpis(); columns = st.columns(4)
    columns[0].metric("Occupancy rate", f"{kpis['occupancy_rate']:.1f}%")
    columns[1].metric("Monthly rent roll", f"${kpis['rent_roll']:,.0f}")
    columns[2].metric("Overdue", f"${kpis['payments']['overdue']:,.0f}")
    columns[3].metric("Vacant units", kpis["vacant_units"])
elif page == "Properties":
    st.header("Properties"); st.dataframe([vars(x) for x in portfolio.properties], use_container_width=True)
    with st.form("add-property"):
        name = st.text_input("Property name"); address = st.text_input("Fictional address")
        kind = st.selectbox("Property type", ["Apartments", "Townhomes", "House", "Commercial"])
        units = st.number_input("Units", min_value=1, value=1)
        if st.form_submit_button("Add property"):
            try:
                portfolio.add_property(name, address, kind, int(units)); st.success("Property added. Portfolio metrics are updated.")
            except PortfolioError as exc: st.error(str(exc))
elif page == "Tenants & Leases":
    st.header("Tenants and leases"); tenants = {x.id: x for x in portfolio.tenants}; properties = {x.id: x for x in portfolio.properties}
    st.dataframe([{"Tenant": tenants[x.tenant_id].name, "Property": properties[x.property_id].name, "Rent": x.monthly_rent, "Start": x.start_date, "End": x.end_date, "Status": x.status, "Renewal": "Renewal pending" if x.renewal_pending() else "—"} for x in portfolio.leases], use_container_width=True)
elif page == "Payments":
    st.header("Rent payments"); st.metric("Total overdue", f"${portfolio.kpis()['payments']['overdue']:,.0f}")
    for payment in portfolio.payments:
        left, right = st.columns([4, 1]); left.write(f"{payment.id} · {payment.due_date} · ${payment.amount:,.0f} · {payment.effective_status().title()}")
        if payment.status != "collected" and right.button("Mark collected", key=payment.id): portfolio.collect_payment(payment.id, date.today()); st.rerun()
else:
    st.header("Mortgage summary"); summary = portfolio.mortgage_summary(); properties = {x.id: x for x in portfolio.properties}
    st.metric("Total debt", f"${summary['total_balance']:,.0f}"); st.metric("Monthly payments", f"${summary['monthly_payment']:,.0f}"); st.metric("Weighted average rate", f"{summary['weighted_rate']:.2f}%")
    st.dataframe([{"Property": properties[x.property_id].name, "Balance": x.balance, "Rate": x.interest_rate, "Monthly payment": x.monthly_payment, "LTV": f"{x.ltv(properties[x.property_id].estimated_value):.1%}", "Maturity": x.maturity_date} for x in portfolio.mortgages], use_container_width=True)
st.caption("© 2026 SASK LLC — SW Services · Public portfolio demonstration")
