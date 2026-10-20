"""Deterministic, conspicuously fictional demo records."""
from __future__ import annotations
from datetime import date, timedelta
from models import Lease, Mortgage, Payment, Property, Tenant

def build_seed(today: date | None = None) -> dict[str, list[object]]:
    today = today or date.today()
    properties = [
        Property("prop-1", "Aurora Demo Flats", "101 Example Way, Demo City", "Apartments", 8, 2, 800_000),
        Property("prop-2", "Cedar Sample Homes", "202 Fiction Avenue, Sample Town", "Townhomes", 4, 0, 560_000),
    ]
    tenants = [Tenant("tenant-1", "Avery Example", "avery@example.demo", "prop-1"), Tenant("tenant-2", "Morgan Sample", "morgan@example.demo", "prop-2")]
    leases = [
        Lease("lease-1", "tenant-1", "prop-1", 1_250, today - timedelta(days=335), today + timedelta(days=30)),
        Lease("lease-2", "tenant-2", "prop-2", 1_600, today - timedelta(days=180), today + timedelta(days=185)),
    ]
    payments = [Payment("payment-1", "lease-1", today - timedelta(days=10), 1_250), Payment("payment-2", "lease-2", today, 1_600)]
    mortgages = [
        Mortgage("mortgage-1", "prop-1", 440_000, 4.25, 2_450, today + timedelta(days=365 * 15)),
        Mortgage("mortgage-2", "prop-2", 280_000, 4.75, 1_780, today + timedelta(days=365 * 18)),
    ]
    return {"properties": properties, "tenants": tenants, "leases": leases, "payments": payments, "mortgages": mortgages}
