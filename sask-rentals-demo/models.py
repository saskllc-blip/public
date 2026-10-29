"""Small domain model for the public demo; no persistence or integrations."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Property:
    id: str; name: str; address: str; property_type: str
    total_units: int; vacant_units: int; estimated_value: float
    # Global-portfolio detail; defaults keep the Add-property form working.
    city: str = ""; country: str = ""; neighbourhood: str = ""
    bedrooms: int = 0; bathrooms: float = 0.0; sqft: int = 0; year_built: int = 0
    purchase_date: date | None = None; purchase_price: float = 0.0

@dataclass(frozen=True)
class Tenant:
    id: str; name: str; email: str; property_id: str

@dataclass(frozen=True)
class Lease:
    id: str; tenant_id: str; property_id: str; monthly_rent: float
    start_date: date; end_date: date; status: str = "active"; deposit: float = 0.0
    def days_to_expiry(self, today: date | None = None) -> int:
        return (self.end_date - (today or date.today())).days
    def renewal_pending(self, today: date | None = None) -> bool:
        return self.status == "active" and 0 <= self.days_to_expiry(today) <= 30
    def covers(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date

@dataclass(frozen=True)
class Payment:
    id: str; lease_id: str; due_date: date; amount: float
    status: str = "pending"; collected_date: date | None = None
    amount_paid: float | None = None  # None means "all of it" once collected
    def effective_status(self, today: date | None = None) -> str:
        if self.status == "pending" and self.due_date < (today or date.today()):
            return "overdue"
        return self.status
    def paid(self) -> float:
        if self.amount_paid is not None: return self.amount_paid
        return self.amount if self.status == "collected" else 0.0
    def outstanding(self) -> float:
        return max(self.amount - self.paid(), 0.0)
    def days_late(self) -> int:
        return (self.collected_date - self.due_date).days if self.collected_date else 0

@dataclass(frozen=True)
class Expense:
    id: str; property_id: str; date: date; category: str; description: str; amount: float

@dataclass(frozen=True)
class Mortgage:
    id: str; property_id: str; balance: float; interest_rate: float
    monthly_payment: float; maturity_date: date
    def ltv(self, property_value: float) -> float:
        return self.balance / property_value if property_value > 0 else 0.0
