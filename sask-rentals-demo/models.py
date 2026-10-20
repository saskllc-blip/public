"""Small domain model for the public demo; no persistence or integrations."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Property:
    id: str; name: str; address: str; property_type: str
    total_units: int; vacant_units: int; estimated_value: float

@dataclass(frozen=True)
class Tenant:
    id: str; name: str; email: str; property_id: str

@dataclass(frozen=True)
class Lease:
    id: str; tenant_id: str; property_id: str; monthly_rent: float
    start_date: date; end_date: date; status: str = "active"
    def days_to_expiry(self, today: date | None = None) -> int:
        return (self.end_date - (today or date.today())).days
    def renewal_pending(self, today: date | None = None) -> bool:
        return self.status == "active" and 0 <= self.days_to_expiry(today) <= 30

@dataclass(frozen=True)
class Payment:
    id: str; lease_id: str; due_date: date; amount: float
    status: str = "pending"; collected_date: date | None = None
    def effective_status(self, today: date | None = None) -> str:
        if self.status == "pending" and self.due_date < (today or date.today()):
            return "overdue"
        return self.status

@dataclass(frozen=True)
class Mortgage:
    id: str; property_id: str; balance: float; interest_rate: float
    monthly_payment: float; maturity_date: date
    def ltv(self, property_value: float) -> float:
        return self.balance / property_value if property_value > 0 else 0.0
