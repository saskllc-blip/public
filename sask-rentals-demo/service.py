"""Session-scoped business operations and KPI calculations."""
from __future__ import annotations
from dataclasses import replace
from datetime import date
from uuid import uuid4
from models import Payment, Property
from seed import build_seed

class PortfolioError(ValueError):
    """A safe validation message suitable for display in the demo UI."""

class DemoPortfolio:
    def __init__(self, data: dict[str, list[object]] | None = None) -> None:
        seeded = data or build_seed()
        for name in ("properties", "tenants", "leases", "payments", "mortgages"):
            setattr(self, name, list(seeded[name]))

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
                updated = replace(payment, status="collected", collected_date=collected_on or date.today())
                self.payments[index] = updated
                return updated
        raise PortfolioError("Payment was not found.")

    def kpis(self, today: date | None = None) -> dict[str, object]:
        today = today or date.today(); total = sum(x.total_units for x in self.properties); vacant = sum(x.vacant_units for x in self.properties)
        statuses = {"collected": 0.0, "pending": 0.0, "overdue": 0.0}
        for payment in self.payments: statuses[payment.effective_status(today)] += payment.amount
        return {"occupancy_rate": ((total - vacant) / total * 100) if total else 0.0, "rent_roll": sum(x.monthly_rent for x in self.leases if x.status == "active"), "vacant_units": vacant, "payments": statuses}

    def mortgage_summary(self) -> dict[str, float]:
        balance = sum(x.balance for x in self.mortgages)
        rate = sum(x.balance * x.interest_rate for x in self.mortgages) / balance if balance else 0.0
        return {"total_balance": balance, "monthly_payment": sum(x.monthly_payment for x in self.mortgages), "weighted_rate": rate}

    def _property_index(self, property_id: str) -> int:
        for index, prop in enumerate(self.properties):
            if prop.id == property_id: return index
        raise PortfolioError("Property was not found.")
