"""Synthetic rentals dataset: determinism, counts, integrity, and consistency rules."""
from __future__ import annotations

import hashlib
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
for path in (HERE, HERE / "data"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import generate_data  # noqa: E402
from seed import DATA_PATH, build_seed, dataset_as_of, load_dataset  # noqa: E402
from service import DemoPortfolio  # noqa: E402

AS_OF = generate_data.AS_OF


@pytest.fixture(scope="module")
def raw() -> dict:
    return load_dataset()


@pytest.fixture(scope="module")
def portfolio() -> DemoPortfolio:
    return DemoPortfolio(build_seed(AS_OF))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- Generator determinism -------------------------------------------------

def test_same_seed_gives_identical_hash() -> None:
    first = generate_data.render(generate_data.build_dataset(generate_data.SEED))
    second = generate_data.render(generate_data.build_dataset(generate_data.SEED))
    assert _sha(first) == _sha(second)


def test_committed_dataset_matches_generator() -> None:
    expected = generate_data.render(generate_data.build_dataset())
    assert _sha(DATA_PATH.read_text(encoding="utf-8")) == _sha(expected)


def test_different_seed_changes_dataset() -> None:
    assert generate_data.build_dataset(1) != generate_data.build_dataset(generate_data.SEED)


# --- Provenance and counts -------------------------------------------------

def test_dataset_is_fictional_and_seeded(raw: dict) -> None:
    assert raw["generated"] == "fictional-only"
    assert raw["seed"] == generate_data.SEED
    assert raw["currency"] == "USD"
    assert all(t["email"].endswith("@example.demo") for t in raw["tenants"])
    assert "http" not in DATA_PATH.read_text(encoding="utf-8")


def test_counts_in_band(raw: dict) -> None:
    properties, leases = raw["properties"], raw["leases"]
    assert len(properties) == 30
    per_property = Counter(x["property_id"] for x in leases)
    assert set(per_property) == {p["id"] for p in properties}  # every property has a lease
    assert all(1 <= n <= 2 for n in per_property.values())
    assert sum(1 for n in per_property.values() if n == 2) > len(properties) / 2  # most have a prior lease
    per_lease = Counter(x["lease_id"] for x in raw["payments"])
    assert set(per_lease) == {x["id"] for x in leases}
    assert all(12 <= n <= 24 for n in per_lease.values())
    assert len(raw["expenses"]) >= 30 * 5


def test_global_spread(raw: dict) -> None:
    cities = {p["city"] for p in raw["properties"]}
    countries = {p["country"] for p in raw["properties"]}
    assert 8 <= len(cities) <= 10
    assert len(countries) >= 6
    assert len({p["address"] for p in raw["properties"]}) == 30


def test_money_is_calibrated_per_locale(raw: dict) -> None:
    by_city = defaultdict(list)
    active = {x["property_id"]: x for x in raw["leases"] if x["status"] == "active"}
    for p in raw["properties"]:
        by_city[p["city"]].append(p)
    median = lambda xs: sorted(xs)[len(xs) // 2]  # noqa: E731
    assert median([p["estimated_value"] for p in by_city["Bangalore"]]) < median([p["estimated_value"] for p in by_city["Memphis"]])
    assert median([p["estimated_value"] for p in by_city["London"]]) > 2 * median([p["estimated_value"] for p in by_city["Memphis"]])
    assert median([p["estimated_value"] for p in by_city["Singapore"]]) > median([p["estimated_value"] for p in by_city["Berlin"]])
    for p in by_city["Bangalore"]:
        if p["id"] in active:
            assert active[p["id"]]["monthly_rent"] < 1_000
    for p in raw["properties"]:
        assert p["estimated_value"] > p["purchase_price"] > 0  # appreciating path
        assert p["purchase_date"] < raw["as_of"]


# --- Referential integrity -------------------------------------------------

def test_referential_integrity(raw: dict) -> None:
    property_ids = {p["id"] for p in raw["properties"]}
    tenant_ids = {t["id"] for t in raw["tenants"]}
    lease_ids = {x["id"] for x in raw["leases"]}
    for collection in ("properties", "tenants", "leases", "payments", "expenses", "mortgages"):
        ids = [x["id"] for x in raw[collection]]
        assert len(ids) == len(set(ids)), collection
    assert all(x["property_id"] in property_ids and x["tenant_id"] in tenant_ids for x in raw["leases"])
    assert all(x["lease_id"] in lease_ids for x in raw["payments"])
    assert all(x["property_id"] in property_ids for x in raw["expenses"] + raw["mortgages"] + raw["tenants"])
    tenant_property = {t["id"]: t["property_id"] for t in raw["tenants"]}
    assert all(tenant_property[x["tenant_id"]] == x["property_id"] for x in raw["leases"])


# --- Consistency rules -----------------------------------------------------

def test_no_payment_outside_lease_window(portfolio: DemoPortfolio) -> None:
    leases = {x.id: x for x in portfolio.leases}
    for payment in portfolio.payments:
        lease = leases[payment.lease_id]
        assert lease.covers(payment.due_date), payment.id
        assert payment.due_date <= AS_OF
        if payment.collected_date:
            assert lease.covers(payment.collected_date) and payment.collected_date <= AS_OF, payment.id
        assert payment.amount == lease.monthly_rent
        assert 0 <= payment.paid() <= payment.amount


def test_payment_mix_is_realistic(portfolio: DemoPortfolio) -> None:
    payments = portfolio.payments
    late = sum(1 for p in payments if p.days_late() > 5)
    partial = sum(1 for p in payments if p.status == "partial")
    on_time = sum(1 for p in payments if p.status == "collected" and p.days_late() <= 5)
    assert on_time / len(payments) > 0.75
    assert 0.03 < late / len(payments) < 0.2
    assert 0 < partial / len(payments) < 0.05


def test_no_overlapping_leases(portfolio: DemoPortfolio) -> None:
    by_property = defaultdict(list)
    for lease in portfolio.leases:
        assert lease.start_date < lease.end_date
        by_property[lease.property_id].append(lease)
    for leases in by_property.values():
        leases.sort(key=lambda x: x.start_date)
        for earlier, later in zip(leases, leases[1:]):
            assert earlier.end_date < later.start_date
            assert earlier.status == "ended"
            assert earlier.monthly_rent <= later.monthly_rent  # plausible rent path


def test_lease_status_matches_timeline(portfolio: DemoPortfolio) -> None:
    for lease in portfolio.leases:
        assert lease.status == ("active" if lease.covers(AS_OF) else "ended")


def test_occupancy_derivable_from_leases(portfolio: DemoPortfolio) -> None:
    kpis = portfolio.kpis(AS_OF)
    assert 0 <= kpis["occupancy_rate"] <= 100
    assert kpis["occupancy_rate"] == pytest.approx(portfolio.occupancy_from_leases(AS_OF))
    for prop in portfolio.properties:
        occupied = any(x.covers(AS_OF) for x in portfolio.leases if x.property_id == prop.id)
        assert prop.vacant_units == (0 if occupied else 1)
        assert 0 <= portfolio.occupancy_history(prop.id, today=AS_OF) <= 100


def test_ledger_reconciles(portfolio: DemoPortfolio) -> None:
    kpis = portfolio.kpis(AS_OF)
    ledger = kpis["payments"]
    assert ledger["collected"] == pytest.approx(sum(p.paid() for p in portfolio.payments))
    assert sum(ledger.values()) == pytest.approx(sum(p.amount for p in portfolio.payments))
    assert ledger["overdue"] > 0  # some arrears to demo


def test_dashboard_numbers_come_from_data(raw: dict, portfolio: DemoPortfolio) -> None:
    kpis = portfolio.kpis(AS_OF)
    assert kpis["portfolio_value"] == pytest.approx(sum(p["estimated_value"] for p in raw["properties"]))
    assert kpis["rent_roll"] == pytest.approx(sum(x["monthly_rent"] for x in raw["leases"] if x["status"] == "active"))
    assert kpis["property_count"] == 30
    rows = portfolio.country_summary(AS_OF)
    assert sum(r["Properties"] for r in rows) == 30
    assert sum(r["Rent roll (USD)"] for r in rows) == pytest.approx(kpis["rent_roll"])


def test_expenses_and_mortgages_are_plausible(portfolio: DemoPortfolio) -> None:
    properties = {p.id: p for p in portfolio.properties}
    assert {e.property_id for e in portfolio.expenses} == set(properties)
    assert all(e.amount > 0 and e.date <= AS_OF for e in portfolio.expenses)
    assert {"Management fee", "Inspection"} <= {e.category for e in portfolio.expenses}
    for m in portfolio.mortgages:
        assert 0 < m.ltv(properties[m.property_id].estimated_value) < 0.8
        assert m.maturity_date > AS_OF


def test_dates_shift_with_today() -> None:
    later = AS_OF + timedelta(days=100)
    base, shifted = build_seed(AS_OF), build_seed(later)
    assert dataset_as_of() == AS_OF
    assert shifted["payments"][0].due_date - base["payments"][0].due_date == timedelta(days=100)
    assert DemoPortfolio(shifted).kpis(later) == DemoPortfolio(base).kpis(AS_OF)


def test_filter_by_country_city_and_search(portfolio: DemoPortfolio) -> None:
    india = portfolio.filtered(countries=["India"])
    assert {p.city for p in india.properties} == {"Bangalore"} and len(india.properties) == 3
    assert {x.property_id for x in india.leases} <= {p.id for p in india.properties}
    us_city = portfolio.filtered(countries=["United States"], cities=["Memphis"])
    assert len(us_city.properties) == 3
    assert len(portfolio.filtered(query="hackney").properties) == 1
    assert len(portfolio.filtered(query="no-such-place").properties) == 0
    total = sum(portfolio.filtered(countries=[c]).kpis(AS_OF)["rent_roll"] for c in {p.country for p in portfolio.properties})
    assert total == pytest.approx(portfolio.kpis(AS_OF)["rent_roll"])


def test_existing_operations_still_work(portfolio: DemoPortfolio) -> None:
    working = DemoPortfolio(build_seed(AS_OF))
    before = working.kpis(AS_OF)
    working.add_property("Demo Annex", "1 Example Way, Demo City", "House", 2)
    after = working.kpis(AS_OF)
    assert after["vacant_units"] == before["vacant_units"] + 2
    overdue = next(p for p in working.payments if p.effective_status(AS_OF) == "overdue")
    working.collect_payment(overdue.id, AS_OF)
    assert working.kpis(AS_OF)["payments"]["overdue"] == pytest.approx(before["payments"]["overdue"] - overdue.amount)
    assert any(x.renewal_pending(AS_OF) for x in working.leases)
