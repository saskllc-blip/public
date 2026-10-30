"""Session-scoped business operations and KPI calculations."""
from __future__ import annotations
from dataclasses import replace
from datetime import date, timedelta
from uuid import uuid4
from models import Lease, Payment, Property
from seed import build_seed

class PortfolioError(ValueError):
    """A safe validation message suitable for display in the demo UI."""

class DemoPortfolio:
    def __init__(self, data: dict[str, list[object]] | None = None) -> None:
        seeded = data or build_seed()
        for name in ("properties", "tenants", "leases", "payments", "expenses", "mortgages"):
            setattr(self, name, list(seeded.get(name, [])))

    def add_property(self, name: str, address: str, property_type: str, total_units: int, estimated_value: float = 0) -> Property:
        if not name.strip() or not address.strip(): raise PortfolioError("Name and address are required.")
        if total_units < 1: raise PortfolioError("Total units must be at least one.")
        prop = Property(f"prop-{uuid4().hex[:8]}", name.strip()[:100], address.strip()[:200], property_type, total_units, total_units, estimated_value)
        self.properties.append(prop)
        return prop

    def update_property(self, property_id: str, **changes: object) -> Property:
        index = self._property_index(property_id)
        allowed = {"name", "address", "property_type", "total_units", "vacant_units", "estimated_value"}
        if set(changes) - allowed: raise PortfolioError("Unsupported property field.")
        updated = replace(self.properties[index], **changes)
        if updated.total_units < 1 or not 0 <= updated.vacant_units <= updated.total_units: raise PortfolioError("Unit counts are invalid.")
        self.properties[index] = updated
        return updated

    def delete_property(self, property_id: str) -> None:
        if any(x.property_id == property_id and x.status == "active" for x in self.leases): raise PortfolioError("Cannot delete a property with an active lease.")
        self.properties.pop(self._property_index(property_id))

    def collect_payment(self, payment_id: str, collected_on: date | None = None) -> Payment:
        for index, payment in enumerate(self.payments):
            if payment.id == payment_id:
                updated = replace(payment, status="collected", collected_date=collected_on or date.today(), amount_paid=payment.amount)
                self.payments[index] = updated
                return updated
        raise PortfolioError("Payment was not found.")

    def kpis(self, today: date | None = None) -> dict[str, object]:
        today = today or date.today(); total = sum(x.total_units for x in self.properties); vacant = sum(x.vacant_units for x in self.properties)
        # Ledger: paid amounts are "collected"; any unpaid remainder is pending until its due date passes, then overdue.
        statuses = {"collected": 0.0, "pending": 0.0, "overdue": 0.0}
        for payment in self.payments:
            statuses["collected"] += payment.paid()
            if payment.outstanding(): statuses["overdue" if payment.due_date < today else "pending"] += payment.outstanding()
        return {"occupancy_rate": ((total - vacant) / total * 100) if total else 0.0, "rent_roll": sum(x.monthly_rent for x in self.leases if x.status == "active"), "vacant_units": vacant, "payments": statuses,
                "portfolio_value": sum(x.estimated_value for x in self.properties), "property_count": len(self.properties)}

    def occupancy_from_leases(self, today: date | None = None) -> float:
        """Share of properties with a lease covering `today`, derived only from lease records."""
        today = today or date.today()
        occupied = {x.property_id for x in self.leases if x.covers(today)}
        return len(occupied & {x.id for x in self.properties}) / len(self.properties) * 100 if self.properties else 0.0

    def occupancy_history(self, property_id: str, days: int = 365, today: date | None = None) -> float:
        """Percent of the trailing `days` window covered by this property's leases."""
        end = today or date.today(); start = end - timedelta(days=days - 1)
        covered = set()
        for lease in self._leases_for(property_id):
            first, last = max(lease.start_date, start), min(lease.end_date, end)
            covered.update(first + timedelta(days=n) for n in range((last - first).days + 1))
        return len(covered) / days * 100

    def country_summary(self, today: date | None = None) -> list[dict[str, object]]:
        today = today or date.today(); rows: dict[str, dict[str, object]] = {}
        active = {x.property_id: x for x in self.leases if x.status == "active"}
        for prop in self.properties:
            row = rows.setdefault(prop.country or "—", {"Country": prop.country or "—", "Cities": set(), "Properties": 0, "Occupied": 0, "Value (USD)": 0.0, "Rent roll (USD)": 0.0})
            row["Cities"].add(prop.city or "—"); row["Properties"] += 1; row["Value (USD)"] += prop.estimated_value
            row["Occupied"] += prop.total_units - prop.vacant_units
            if prop.id in active: row["Rent roll (USD)"] += active[prop.id].monthly_rent
        return [{**row, "Cities": ", ".join(sorted(row["Cities"]))} for row in sorted(rows.values(), key=lambda r: str(r["Country"]))]

    def filtered(self, countries: list[str] | None = None, cities: list[str] | None = None, query: str = "") -> "DemoPortfolio":
        """A read-only view scoped to matching properties and their records (actions still go to the full portfolio)."""
        needle = query.strip().lower(); tenants_by_property: dict[str, list[str]] = {}
        for tenant in self.tenants: tenants_by_property.setdefault(tenant.property_id, []).append(tenant.name)
        def keep(prop: Property) -> bool:
            if countries and prop.country not in countries: return False
            if cities and prop.city not in cities: return False
            haystack = " ".join([prop.name, prop.address, prop.city, prop.country, prop.neighbourhood, prop.property_type, *tenants_by_property.get(prop.id, [])]).lower()
            return not needle or needle in haystack
        ids = {x.id for x in self.properties if keep(x)}
        leases = [x for x in self.leases if x.property_id in ids]; lease_ids = {x.id for x in leases}
        return DemoPortfolio({"properties": [x for x in self.properties if x.id in ids], "tenants": [x for x in self.tenants if x.property_id in ids], "leases": leases,
                              "payments": [x for x in self.payments if x.lease_id in lease_ids], "expenses": [x for x in self.expenses if x.property_id in ids],
                              "mortgages": [x for x in self.mortgages if x.property_id in ids]})

    def mortgage_summary(self) -> dict[str, float]:
        balance = sum(x.balance for x in self.mortgages)
        rate = sum(x.balance * x.interest_rate for x in self.mortgages) / balance if balance else 0.0
        return {"total_balance": balance, "monthly_payment": sum(x.monthly_payment for x in self.mortgages), "weighted_rate": rate}

    def _leases_for(self, property_id: str) -> list[Lease]:
        return [x for x in self.leases if x.property_id == property_id]

    def _property_index(self, property_id: str) -> int:
        for index, prop in enumerate(self.properties):
            if prop.id == property_id: return index
        raise PortfolioError("Property was not found.")
