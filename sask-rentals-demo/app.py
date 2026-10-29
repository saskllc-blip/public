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
st.warning("Demo data — all properties, tenants, and records are fictional. Amounts in USD.")
page = st.sidebar.radio("Navigation", ["Dashboard", "Properties", "Tenants & Leases", "Payments", "Mortgages"])
if st.sidebar.button("Reset to demo data"):
    st.session_state.portfolio = DemoPortfolio(); st.rerun()
st.sidebar.subheader("Filter portfolio")
countries = st.sidebar.multiselect("Country", sorted({x.country for x in portfolio.properties if x.country}))
cities = st.sidebar.multiselect("City", sorted({x.city for x in portfolio.properties if x.city and (not countries or x.country in countries)}))
query = st.sidebar.text_input("Search", placeholder="Name, address, neighbourhood, tenant…")
view = portfolio.filtered(countries, cities, query) if countries or cities or query.strip() else portfolio
if view is not portfolio: st.info(f"Showing {len(view.properties)} of {len(portfolio.properties)} properties.")
properties = {x.id: x for x in view.properties}; tenants = {x.id: x for x in view.tenants}; leases = {x.id: x for x in view.leases}

if page == "Dashboard":
    kpis = view.kpis(); columns = st.columns(4)
    columns[0].metric("Occupancy rate", f"{kpis['occupancy_rate']:.1f}%")
    columns[1].metric("Monthly rent roll", f"${kpis['rent_roll']:,.0f}")
    columns[2].metric("Overdue", f"${kpis['payments']['overdue']:,.0f}")
    columns[3].metric("Vacant units", kpis["vacant_units"])
    columns = st.columns(4)
    columns[0].metric("Portfolio value", f"${kpis['portfolio_value']:,.0f}")
    columns[1].metric("Properties", kpis["property_count"])
    columns[2].metric("Rent collected to date", f"${kpis['payments']['collected']:,.0f}")
    columns[3].metric("Pending", f"${kpis['payments']['pending']:,.0f}")
    st.subheader("By country"); st.dataframe(view.country_summary(), use_container_width=True, hide_index=True)
elif page == "Properties":
    st.header("Properties")
    st.dataframe([{"Name": x.name, "Address": x.address, "City": x.city, "Country": x.country, "Type": x.property_type, "Beds": x.bedrooms, "Baths": x.bathrooms, "Sq ft": x.sqft,
                   "Built": x.year_built, "Purchased": x.purchase_date, "Purchase price": x.purchase_price, "Est. value": x.estimated_value, "Units": x.total_units, "Vacant": x.vacant_units,
                   "Occupancy (12m)": f"{view.occupancy_history(x.id):.0f}%"} for x in view.properties], use_container_width=True, hide_index=True)
    st.subheader("Maintenance & expenses"); st.metric("Total expenses", f"${sum(x.amount for x in view.expenses):,.0f}")
    st.dataframe([{"Date": x.date, "Property": properties[x.property_id].name, "Category": x.category, "Description": x.description, "Amount": x.amount}
                  for x in sorted(view.expenses, key=lambda e: e.date, reverse=True)], use_container_width=True, hide_index=True)
    with st.form("add-property"):
        name = st.text_input("Property name"); address = st.text_input("Fictional address")
        kind = st.selectbox("Property type", ["Apartments", "Townhomes", "House", "Commercial"])
        units = st.number_input("Units", min_value=1, value=1)
        if st.form_submit_button("Add property"):
            try:
                portfolio.add_property(name, address, kind, int(units)); st.success("Property added. Portfolio metrics are updated.")
            except PortfolioError as exc: st.error(str(exc))
elif page == "Tenants & Leases":
    st.header("Tenants and leases")
    st.dataframe([{"Tenant": tenants[x.tenant_id].name, "Property": properties[x.property_id].name, "City": properties[x.property_id].city, "Country": properties[x.property_id].country,
                   "Rent": x.monthly_rent, "Deposit": x.deposit, "Start": x.start_date, "End": x.end_date, "Status": x.status, "Renewal": "Renewal pending" if x.renewal_pending() else "—"}
                  for x in sorted(view.leases, key=lambda l: (properties[l.property_id].name, l.start_date))], use_container_width=True, hide_index=True)
elif page == "Payments":
    st.header("Rent payments"); totals = view.kpis()["payments"]; columns = st.columns(3)
    columns[0].metric("Collected", f"${totals['collected']:,.0f}"); columns[1].metric("Pending", f"${totals['pending']:,.0f}"); columns[2].metric("Total overdue", f"${totals['overdue']:,.0f}")
    outstanding = [x for x in view.payments if x.outstanding()]
    st.subheader(f"Outstanding ({len(outstanding)})")
    for payment in outstanding:
        lease = leases[payment.lease_id]; left, right = st.columns([4, 1])
        left.write(f"{payment.id} · {tenants[lease.tenant_id].name} · {properties[lease.property_id].name} · {payment.due_date} · ${payment.outstanding():,.0f} of ${payment.amount:,.0f} · {payment.effective_status().title()}")
        if right.button("Mark collected", key=payment.id): portfolio.collect_payment(payment.id, date.today()); st.rerun()
    st.subheader(f"Payment history ({len(view.payments)})")
    st.dataframe([{"Payment": x.id, "Due": x.due_date, "Tenant": tenants[leases[x.lease_id].tenant_id].name, "Property": properties[leases[x.lease_id].property_id].name, "Amount": x.amount,
                   "Paid": x.paid(), "Collected on": x.collected_date, "Days late": x.days_late(), "Status": x.effective_status().title()}
                  for x in sorted(view.payments, key=lambda p: p.due_date, reverse=True)], use_container_width=True, hide_index=True)
else:
    st.header("Mortgage summary"); summary = view.mortgage_summary()
    st.metric("Total debt", f"${summary['total_balance']:,.0f}"); st.metric("Monthly payments", f"${summary['monthly_payment']:,.0f}"); st.metric("Weighted average rate", f"{summary['weighted_rate']:.2f}%")
    st.dataframe([{"Property": properties[x.property_id].name, "Country": properties[x.property_id].country, "Balance": x.balance, "Rate": x.interest_rate, "Monthly payment": x.monthly_payment, "LTV": f"{x.ltv(properties[x.property_id].estimated_value):.1%}", "Maturity": x.maturity_date} for x in view.mortgages], use_container_width=True, hide_index=True)
st.caption("© 2026 SASK LLC — SW Services · Public portfolio demonstration")
