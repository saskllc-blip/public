"""Deterministic, conspicuously fictional demo records.

Loads the committed synthetic dataset (data/rentals.json, produced by
data/generate_data.py) and shifts every date by (today - as_of) so overdue
rows and renewal flags stay true on any calendar day.
"""
from __future__ import annotations
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from models import Expense, Lease, Mortgage, Payment, Property, Tenant

DATA_PATH = Path(__file__).resolve().parent / "data" / "rentals.json"

@lru_cache(maxsize=1)
def load_dataset() -> dict:
    """The committed raw dataset (ISO date strings, USD amounts)."""
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

def dataset_as_of() -> date:
    return date.fromisoformat(load_dataset()["as_of"])

def build_seed(today: date | None = None) -> dict[str, list[object]]:
    raw = load_dataset(); shift = (today or date.today()) - dataset_as_of()
    def day(value: str | None) -> date | None:
        return date.fromisoformat(value) + shift if value else None
    properties = [Property(**{**x, "purchase_date": day(x["purchase_date"])}) for x in raw["properties"]]
    tenants = [Tenant(**x) for x in raw["tenants"]]
    leases = [Lease(**{**x, "start_date": day(x["start_date"]), "end_date": day(x["end_date"])}) for x in raw["leases"]]
    payments = [Payment(**{**x, "due_date": day(x["due_date"]), "collected_date": day(x["collected_date"])}) for x in raw["payments"]]
    expenses = [Expense(**{**x, "date": day(x["date"])}) for x in raw["expenses"]]
    mortgages = [Mortgage(**{**x, "maturity_date": day(x["maturity_date"])}) for x in raw["mortgages"]]
    return {"properties": properties, "tenants": tenants, "leases": leases, "payments": payments, "expenses": expenses, "mortgages": mortgages}
