"""Deterministic, 100% synthetic rental-portfolio generator for Rentals OS.

Hard rule: every record is fictional. Cities and neighbourhoods are real places
so the global spread reads true, but every street name, building, tenant, lease,
payment, expense, and mortgage is invented. No real listings, no scraped data,
no real people.

Money is stored in USD, calibrated to each locale's market level (a Bangalore
flat does not carry US-suburb numbers). Dates are absolute and anchored to
AS_OF; the app's loader shifts them so AS_OF lands on "today".

Run from the app folder:  python3 data/generate_data.py
Re-running with the same SEED rewrites data/rentals.json byte-for-byte.
"""
from __future__ import annotations

import json
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "rentals.json"

SEED = 20261025
AS_OF = date(2026, 10, 20)
N_PROPERTIES = 30
SCHEMA_VERSION = 1

# Per-city market calibration (USD, approximate 2026 levels).
#   value: typical current value range for the property type below
#   rent: typical monthly rent range
#   growth: long-run annual appreciation
#   deposit: security deposit in months of rent (local custom)
#   cost: maintenance/labour cost factor relative to the US
#   rate: typical mortgage rate range (%)
# Street names are invented; they are not meant to match real streets.
CITIES = [
    {"city": "Memphis", "country": "United States", "locale": "us", "value": (175_000, 265_000), "rent": (1_250, 1_700), "growth": 0.045, "deposit": 1.0, "cost": 1.0, "rate": (4.5, 7.0),
     "types": ["House", "House", "Townhouse"], "hoods": ["Cooper-Young", "Midtown", "East Memphis"],
     "streets": ["Tallowmere Ave", "Quillby Cove", "Brackenfold St"], "fmt": "{n} {street}, {hood}, Memphis, TN"},
    {"city": "Greensboro", "country": "United States", "locale": "us", "value": (225_000, 320_000), "rent": (1_350, 1_800), "growth": 0.05, "deposit": 1.0, "cost": 1.0, "rate": (4.5, 7.0),
     "types": ["House", "Townhouse", "House"], "hoods": ["Fisher Park", "Lindley Park", "Westerwood"],
     "streets": ["Larkspire Dr", "Oxenbridge Ct", "Wrenhallow Rd"], "fmt": "{n} {street}, {hood}, Greensboro, NC"},
    {"city": "Toronto", "country": "Canada", "locale": "ca", "value": (470_000, 760_000), "rent": (1_850, 2_700), "growth": 0.055, "deposit": 1.0, "cost": 1.1, "rate": (3.5, 5.8),
     "types": ["Condo", "Townhouse", "Condo"], "hoods": ["Leslieville", "The Annex", "Liberty Village"],
     "streets": ["Marrowfield Cres", "Thistlebury Ave", "Cindergate Lane"], "fmt": "{n} {street}, {hood}, Toronto, ON"},
    {"city": "London", "country": "United Kingdom", "locale": "uk", "value": (560_000, 820_000), "rent": (2_500, 3_400), "growth": 0.035, "deposit": 1.15, "cost": 1.15, "rate": (3.0, 5.5),
     "types": ["Apartment", "Apartment", "Apartment"], "hoods": ["Hackney", "Clapham", "Islington"],
     "streets": ["Fennimore Mews", "Quaverly Road", "Ashcombe Yard"], "fmt": "Flat {unit}, {n} {street}, {hood}, London"},
    {"city": "Berlin", "country": "Germany", "locale": "de", "value": (360_000, 520_000), "rent": (1_250, 1_750), "growth": 0.04, "deposit": 3.0, "cost": 1.05, "rate": (2.0, 4.2),
     "types": ["Apartment", "Apartment", "Apartment"], "hoods": ["Prenzlauer Berg", "Kreuzberg", "Neukölln"],
     "streets": ["Kranichwiesenweg", "Holunderhofstraße", "Mövenschlagallee"], "fmt": "{street} {n}, {hood}, Berlin"},
    {"city": "Sydney", "country": "Australia", "locale": "au", "value": (480_000, 760_000), "rent": (1_750, 2_500), "growth": 0.05, "deposit": 0.92, "cost": 1.15, "rate": (4.5, 6.8),
     "types": ["Apartment", "Townhouse", "Apartment"], "hoods": ["Surry Hills", "Newtown", "Bondi"],
     "streets": ["Wattlebrook Lane", "Corellan Street", "Banksiamere Parade"], "fmt": "{n} {street}, {hood} NSW, Sydney"},
    {"city": "Bangalore", "country": "India", "locale": "in", "value": (95_000, 170_000), "rent": (380, 650), "growth": 0.06, "deposit": 8.0, "cost": 0.25, "rate": (8.0, 9.8),
     "types": ["Apartment", "Apartment", "House"], "hoods": ["Indiranagar", "Koramangala", "Whitefield"],
     "streets": ["Champakavana Cross Road", "Neelagiri Layout Main", "Suvarnapatha Road"], "fmt": "No. {n}, {street}, {hood}, Bengaluru"},
    {"city": "São Paulo", "country": "Brazil", "locale": "br", "value": (140_000, 230_000), "rent": (650, 1_050), "growth": 0.05, "deposit": 3.0, "cost": 0.35, "rate": (9.5, 12.0),
     "types": ["Apartment", "Apartment", "Apartment"], "hoods": ["Pinheiros", "Vila Madalena", "Moema"],
     "streets": ["Rua dos Jacarandás Altos", "Rua Ventania Clara", "Alameda Sabiá-Laranjeira"], "fmt": "{street}, {n}, {hood}, São Paulo - SP"},
    {"city": "Cape Town", "country": "South Africa", "locale": "za", "value": (120_000, 210_000), "rent": (720, 1_150), "growth": 0.05, "deposit": 1.5, "cost": 0.4, "rate": (10.0, 12.0),
     "types": ["Apartment", "House", "Apartment"], "hoods": ["Sea Point", "Observatory", "Gardens"],
     "streets": ["Fynbosrand Road", "Protea Kloof Street", "Klipspringer Terrace"], "fmt": "{n} {street}, {hood}, Cape Town"},
    {"city": "Singapore", "country": "Singapore", "locale": "sg", "value": (1_000_000, 1_450_000), "rent": (3_100, 4_300), "growth": 0.035, "deposit": 2.0, "cost": 1.1, "rate": (2.8, 4.2),
     "types": ["Condo", "Condo", "Condo"], "hoods": ["Tiong Bahru", "Novena", "Tampines"],
     "streets": ["Merbau Vale", "Tembusu Rise", "Angsana Grove"], "fmt": "#{floor}-{unit:02d}, {n} {street}, {hood}, Singapore"},
]

# Common given and family names per locale, combined at random. The resulting
# people are fictional; no name is drawn from a real tenant or record.
NAMES = {
    "us": (["Jordan", "Taylor", "Marcus", "Keisha", "Brandon", "Emily", "Darnell", "Hannah", "Tyler", "Brianna"],
           ["Whitfield", "Coleman", "Barnes", "Hollis", "Pruitt", "Mayfield", "Dunbar", "Sutton", "Rhodes", "Gaines"]),
    "ca": (["Liam", "Chloe", "Ethan", "Priya", "Noah", "Mei", "Owen", "Sophie", "Arjun", "Avery"],
           ["Tremblay", "MacLeod", "Gagnon", "Chen", "Bouchard", "Fraser", "Singh", "Lavoie", "Morin", "Wong"]),
    "uk": (["Oliver", "Amelia", "Harry", "Isla", "George", "Poppy", "Alfie", "Freya", "Rhys", "Imogen"],
           ["Ashworth", "Pemberton", "Holloway", "Fenwick", "Gallagher", "Thornton", "Barlow", "Okafor", "Whitlock", "Hughes"]),
    "de": (["Lukas", "Lena", "Jonas", "Hannah", "Felix", "Marie", "Paul", "Clara", "Moritz", "Ida"],
           ["Schröder", "Becker", "Hoffmann", "Wagner", "Krüger", "Lehmann", "Neumann", "Zimmermann", "Hartmann", "Brandt"]),
    "au": (["Jack", "Matilda", "Cooper", "Ruby", "Lachlan", "Zoe", "Mitchell", "Grace", "Hamish", "Ella"],
           ["Kowalski", "Brennan", "McIntyre", "Nguyen", "Fitzgerald", "Doyle", "Papadopoulos", "Riley", "Hartley", "Lynch"]),
    "in": (["Aarav", "Ananya", "Rohan", "Kavya", "Vikram", "Meera", "Siddharth", "Diya", "Karthik", "Sneha"],
           ["Rao", "Iyer", "Hegde", "Nair", "Shetty", "Kulkarni", "Reddy", "Menon", "Gowda", "Bhat"]),
    "br": (["Lucas", "Beatriz", "Gabriel", "Larissa", "Rafael", "Camila", "Thiago", "Juliana", "Mateus", "Fernanda"],
           ["Oliveira", "Santos", "Carvalho", "Pereira", "Almeida", "Ribeiro", "Barbosa", "Rocha", "Moreira", "Teixeira"]),
    "za": (["Thabo", "Naledi", "Pieter", "Zanele", "Sipho", "Anika", "Lwazi", "Lerato", "Ruan", "Ayanda"],
           ["Naidoo", "van der Merwe", "Dlamini", "Botha", "Mokoena", "Petersen", "Khumalo", "Jacobs", "Ndlovu", "Fourie"]),
    "sg": (["Wei Ling", "Darren", "Hui Min", "Ravi", "Jia Hui", "Marcus", "Nurul", "Kelvin", "Shu Fen", "Faizal"],
           ["Tan", "Lim", "Ng", "Goh", "Pillai", "Teo", "Chua", "Rahman", "Ong", "Koh"]),
}

BEDS = {"House": (3, 4), "Townhouse": (2, 3), "Apartment": (1, 3), "Condo": (1, 3)}
SQFT_PER_BED = {"House": (550, 700), "Townhouse": (480, 600), "Apartment": (380, 520), "Condo": (400, 540)}
REPAIRS = [
    ("Plumbing", "Leaking tap and trap replaced", (80, 380)),
    ("Electrical", "Faulty outlet and breaker repaired", (90, 420)),
    ("Appliance", "Refrigerator compressor serviced", (150, 650)),
    ("HVAC", "Cooling/heating unit serviced", (120, 700)),
    ("Painting", "Interior touch-up painting", (250, 1_200)),
    ("Pest control", "Scheduled pest treatment", (60, 220)),
    ("Roof", "Roof/gutter repair after storm", (300, 1_800)),
    ("Locks", "Locks rekeyed and door hardware fixed", (70, 260)),
]


def _add_months(day: date, months: int) -> date:
    """Same day-of-month `months` later (only used with day 1)."""
    total = day.month - 1 + months
    return date(day.year + total // 12, total % 12 + 1, day.day)


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def _round_to(value: float, step: int) -> float:
    return float(int(round(value / step)) * step)


def _amortized_balance(principal: float, annual_rate: float, years: int, months_paid: int) -> tuple[float, float]:
    """Return (monthly payment, remaining balance) for a standard amortizing loan."""
    r = annual_rate / 100 / 12
    n = years * 12
    payment = principal * r / (1 - (1 + r) ** -n)
    balance = principal * (1 + r) ** months_paid - payment * ((1 + r) ** months_paid - 1) / r
    return round(payment, 2), round(max(balance, 0.0), 2)


def _payments_for_lease(rng: random.Random, lease: dict, ids: dict) -> list[dict]:
    """Monthly rent rows due on the 1st inside the lease window and on/before AS_OF."""
    start, end = date.fromisoformat(lease["start_date"]), date.fromisoformat(lease["end_date"])
    rows = []
    due = start
    while due <= end and due <= AS_OF:
        ids["payment"] += 1
        rent = lease["monthly_rent"]
        latest_bound = min(end, AS_OF)
        roll = rng.random()
        if (AS_OF - due).days < 30 and roll < 0.22:
            status, paid, collected = "pending", 0.0, None  # current month not yet received
        elif roll < 0.015:
            status, paid = "partial", _round_to(rent * rng.uniform(0.4, 0.8), 5)
            collected = min(due + timedelta(days=rng.randint(3, 12)), latest_bound)
        elif roll < 0.14:
            status, paid = "collected", rent  # late but paid in full
            collected = min(due + timedelta(days=rng.randint(6, 24)), latest_bound)
        else:
            status, paid = "collected", rent
            collected = min(due + timedelta(days=rng.randint(0, 3)), latest_bound)
        rows.append({
            "id": f"payment-{ids['payment']:04d}", "lease_id": lease["id"], "due_date": due.isoformat(),
            "amount": rent, "status": status, "collected_date": collected.isoformat() if collected else None,
            "amount_paid": paid,
        })
        due = _add_months(due, 1)
    return rows


def build_dataset(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    ids = {"tenant": 0, "lease": 0, "payment": 0, "expense": 0, "mortgage": 0}
    properties, tenants, leases, payments, expenses, mortgages = [], [], [], [], [], []
    used_names: set[str] = set()

    # Exactly 4 properties sit vacant between tenants on AS_OF; 24 of 30 have a prior lease.
    vacant_slots = set(rng.sample(range(N_PROPERTIES), 4))
    no_prior_slots = set(rng.sample(range(N_PROPERTIES), 6))
    financed_slots = set(rng.sample(range(N_PROPERTIES), 21))

    def new_tenant(locale: str, property_id: str) -> str:
        first_names, last_names = NAMES[locale]
        while True:
            first, last = rng.choice(first_names), rng.choice(last_names)
            if f"{first} {last}" not in used_names:
                break
        used_names.add(f"{first} {last}")
        ids["tenant"] += 1
        tenant_id = f"tenant-{ids['tenant']:03d}"
        email = unicodedata.normalize("NFKD", f"{first}.{last}".lower().replace(" ", "")).encode("ascii", "ignore").decode()
        tenants.append({"id": tenant_id, "name": f"{first} {last}", "email": f"{email}@example.demo", "property_id": property_id})
        return tenant_id

    def new_lease(prop: dict, locale: str, deposit_months: float, rent: float, start: date, months: int, status: str) -> dict:
        ids["lease"] += 1
        lease = {
            "id": f"lease-{ids['lease']:03d}", "tenant_id": new_tenant(locale, prop["id"]), "property_id": prop["id"],
            "monthly_rent": rent, "start_date": start.isoformat(),
            "end_date": (_add_months(start, months) - timedelta(days=1)).isoformat(), "status": status,
            "deposit": _round_to(rent * deposit_months, 5),
        }
        leases.append(lease)
        payments.extend(_payments_for_lease(rng, lease, ids))
        return lease

    def add_expense(prop_id: str, day: date, category: str, description: str, amount: float) -> None:
        ids["expense"] += 1
        expenses.append({"id": f"expense-{ids['expense']:04d}", "property_id": prop_id, "date": day.isoformat(),
                         "category": category, "description": description, "amount": round(amount, 2)})

    slot = 0
    for city in CITIES:
        for k in range(3):
            prop_id = f"prop-{slot + 1:03d}"
            kind = city["types"][k]
            beds = rng.randint(*BEDS[kind])
            baths = min(beds, max(1.0, beds - rng.choice([0, 0.5, 1])))
            sqft = int(beds * rng.randint(*SQFT_PER_BED[kind]) + rng.randint(0, 150))
            value_now = _round_to(rng.uniform(*city["value"]) * (0.85 + 0.12 * beds / 3), 1_000)
            purchase = date(rng.randint(2012, 2022), rng.randint(1, 12), 1)
            years_held = (AS_OF - purchase).days / 365.25
            growth = city["growth"] * rng.uniform(0.8, 1.2)
            purchase_price = _round_to(value_now / (1 + growth) ** years_held, 1_000)
            address = city["fmt"].format(n=rng.randint(2, 180), street=city["streets"][k], hood=city["hoods"][k], floor=f"{rng.randint(3, 24):02d}", unit=rng.randint(1, 12))
            prop = {
                "id": prop_id, "name": f"{city['hoods'][k]} {kind}", "address": address, "property_type": kind,
                "total_units": 1, "vacant_units": 0, "estimated_value": value_now,
                "city": city["city"], "country": city["country"], "neighbourhood": city["hoods"][k],
                "bedrooms": beds, "bathrooms": float(baths), "sqft": sqft,
                "year_built": rng.randint(1925 if kind == "House" else 1965, min(purchase.year, 2021)),
                "purchase_date": purchase.isoformat(), "purchase_price": purchase_price,
            }
            properties.append(prop)

            # Lease timeline, built backwards from AS_OF so the latest lease always has 12+ payments.
            current_rent = _round_to(rng.uniform(*city["rent"]) * (0.85 + 0.12 * beds / 3), 5)
            if slot in vacant_slots:
                cur_months = rng.choice([12, 18, 24])
                cur_end_month = _add_months(date(AS_OF.year, AS_OF.month, 1), -rng.randint(1, 3))
                cur_start = _add_months(cur_end_month, -cur_months)
                status = "ended"
                prop["vacant_units"] = 1
            else:
                cur_months = rng.choice([24, 24, 24, 36]) if city["locale"] != "de" else 36
                elapsed = rng.randint(12, min(23, cur_months - 1))
                cur_start = _add_months(date(AS_OF.year, AS_OF.month, 1), -elapsed)
                status = "active"
            if slot not in no_prior_slots:
                prior_months = rng.choice([12, 12, 18, 24])
                gap_months = rng.choice([0, 0, 1, 1, 2])
                prior_start = _add_months(cur_start, -(prior_months + gap_months))
                prior_rent = _round_to(current_rent / rng.uniform(1.02, 1.08), 5)
                prior = new_lease(prop, city["locale"], city["deposit"], prior_rent, prior_start, prior_months, "ended")
                add_expense(prop_id, date.fromisoformat(prior["end_date"]) + timedelta(days=rng.randint(1, 10)), "Turnover",
                            "Move-out clean and re-letting prep", rng.uniform(200, 700) * city["cost"])
            current = new_lease(prop, city["locale"], city["deposit"], current_rent, cur_start, cur_months, status)

            # Expense scatter over the ownership window shown in the data (from first lease start).
            window_start = date.fromisoformat(min(x["start_date"] for x in leases if x["property_id"] == prop_id))
            quarter = window_start
            while quarter <= AS_OF:
                active = next((x for x in leases if x["property_id"] == prop_id and x["start_date"] <= quarter.isoformat() <= x["end_date"]), None)
                if active:
                    add_expense(prop_id, quarter + timedelta(days=4), "Management fee", "Quarterly property-management fee (8% of rent)",
                                active["monthly_rent"] * 3 * 0.08)
                quarter = _add_months(quarter, 3)
            months = _months_between(window_start, AS_OF)
            for year_offset in range(0, months // 12 + 1):
                inspect_day = _add_months(window_start, year_offset * 12 + rng.randint(1, 11)) + timedelta(days=rng.randint(0, 20))
                if inspect_day <= AS_OF:
                    add_expense(prop_id, inspect_day, "Inspection", "Annual safety and condition inspection", rng.uniform(90, 260) * city["cost"])
            for _ in range(rng.randint(2, 6)):
                category, description, (low, high) = rng.choice(REPAIRS)
                day = window_start + timedelta(days=rng.randint(10, max(11, (AS_OF - window_start).days - 1)))
                add_expense(prop_id, day, category, description, rng.uniform(low, high) * city["cost"])

            if slot in financed_slots:
                ids["mortgage"] += 1
                term = 30 if city["locale"] in ("us", "uk", "in", "sg") else 25
                rate = round(rng.uniform(*city["rate"]), 2)
                principal = _round_to(purchase_price * rng.uniform(0.6, 0.8), 1_000)
                monthly, balance = _amortized_balance(principal, rate, term, _months_between(purchase, AS_OF))
                mortgages.append({"id": f"mortgage-{ids['mortgage']:03d}", "property_id": prop_id, "balance": balance,
                                  "interest_rate": rate, "monthly_payment": monthly,
                                  "maturity_date": _add_months(purchase, term * 12).isoformat()})
            slot += 1

    expenses.sort(key=lambda x: (x["property_id"], x["date"], x["id"]))
    return {
        "generated": "fictional-only", "seed": seed, "schema_version": SCHEMA_VERSION, "as_of": AS_OF.isoformat(),
        "currency": "USD",
        "note": "100% synthetic demo data. Real cities and neighbourhoods; fictional streets, people, and records.",
        "properties": properties, "tenants": tenants, "leases": leases, "payments": payments,
        "expenses": expenses, "mortgages": mortgages,
    }


def render(dataset: dict) -> str:
    """Canonical serialization: stable key order, trailing newline."""
    return json.dumps(dataset, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    dataset = build_dataset()
    DATA_PATH.write_text(render(dataset), encoding="utf-8")
    counts = {k: len(v) for k, v in dataset.items() if isinstance(v, list)}
    print(f"Wrote {DATA_PATH.name}: {counts}")


if __name__ == "__main__":
    main()
