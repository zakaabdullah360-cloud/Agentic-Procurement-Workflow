"""
Seeds the `suppliers` table from the 4 uploaded laptop-catalog CSVs (treated
as 4 distinct supplier data sources - see README for why) plus 3 hardcoded
software-vendor-renewal options for the second (generalizability) use case.

Run with:  python -m app.scripts.load_data
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import Base, engine, SessionLocal
from app.models import Supplier
from app.config import EUR_TO_PKR

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _extract_years(text, default=1.0):
    """Pull a warranty/term length in years out of a messy text field."""
    if text is None:
        return default
    text = str(text)
    m = re.search(r"(\d+(?:\.\d+)?)\s*Year", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return default


def _clean_price_series(series):
    """Strip currency symbols/commas and coerce to float, dropping junk rows."""
    cleaned = (
        series.astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
        .replace("", None)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def load_alpha_pk():
    """Original PKR-labelled catalog: Brand:, Product name, Warranty, Price."""
    path = os.path.join(DATA_DIR, "supplier_alpha_pk.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    prices = _clean_price_series(df["Price"])
    # representative business-laptop band: exclude ultra-budget/ultra-premium
    band = prices[(prices >= 50000) & (prices <= 250000)]
    unit_price = float(band.median()) if len(band) else float(prices.median())
    warranty_years = df["Warranty"].apply(_extract_years).mean()
    return Supplier(
        name="AlphaTech Distributors",
        category="laptop_supplier",
        source_file="supplier_alpha_pk.csv",
        currency="PKR",
        unit_price=round(unit_price, 2),
        lead_time_days=9,
        warranty_years=round(float(warranty_years), 2),
        rating=None,
        catalog_size=len(df),
    )


def load_bravo_eu():
    """EUR-denominated catalog: Company, Product, Price_euros. Converted to PKR."""
    path = os.path.join(DATA_DIR, "supplier_bravo_eu.csv")
    df = pd.read_csv(path, encoding="latin1")
    df.columns = [c.strip() for c in df.columns]
    prices_eur = pd.to_numeric(df["Price_euros"], errors="coerce")
    band = prices_eur[(prices_eur >= 600) & (prices_eur <= 2800)]
    unit_price_eur = float(band.median()) if len(band) else float(prices_eur.median())
    unit_price_pkr = unit_price_eur * EUR_TO_PKR
    return Supplier(
        name="BravoLaptops Wholesale",
        category="laptop_supplier",
        source_file="supplier_bravo_eu.csv",
        currency="PKR",  # normalized from EUR using EUR_TO_PKR for comparison
        unit_price=round(unit_price_pkr, 2),
        lead_time_days=14,
        warranty_years=2.0,  # dataset doesn't carry a warranty column; disclosed default
        rating=None,
        catalog_size=len(df),
    )


def load_charlie_in():
    """INR-labelled catalog: title, price (with rupee sign), warranty text."""
    path = os.path.join(DATA_DIR, "supplier_charlie_in.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    prices = _clean_price_series(df["price"])
    band = prices[(prices >= 30000) & (prices <= 150000)]
    unit_price = float(band.median()) if len(band) else float(prices.median())
    warranty_years = df["warranty"].apply(_extract_years).mean()
    return Supplier(
        name="CharlieLaptop Traders",
        category="laptop_supplier",
        source_file="supplier_charlie_in.csv",
        currency="PKR",  # treated as PKR-equivalent for the demo; see README
        unit_price=round(unit_price, 2),
        lead_time_days=6,
        warranty_years=round(float(warranty_years), 2),
        rating=None,
        catalog_size=len(df),
    )


def load_delta_clean():
    """Cleaned catalog with an actual numeric rating column."""
    path = os.path.join(DATA_DIR, "supplier_delta_clean.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    prices = pd.to_numeric(df["price"], errors="coerce")
    band = prices[(prices >= 40000) & (prices <= 200000)]
    unit_price = float(band.median()) if len(band) else float(prices.median())
    warranty_years = pd.to_numeric(df["warrenty"], errors="coerce").mean()
    rating = pd.to_numeric(df["rating"], errors="coerce").mean()
    return Supplier(
        name="DeltaTech Systems",
        category="laptop_supplier",
        source_file="supplier_delta_clean.csv",
        currency="PKR",
        unit_price=round(unit_price, 2),
        lead_time_days=11,
        warranty_years=round(float(warranty_years), 2) if pd.notna(warranty_years) else 1.0,
        rating=round(float(rating), 2) if pd.notna(rating) else None,
        catalog_size=len(df),
    )


def load_vendor_renewal_options():
    """
    No dataset exists for software-vendor renewal (out of scope of the
    uploaded CSVs), so these 3 options are explicitly mocked, matching the
    hackathon's own suggestion to use a realistic mock where no real/public
    API is available. category='software_vendor' routes them through the
    exact same scoring/validation/approval pipeline as the laptop suppliers.
    """
    return [
        Supplier(
            name="CloudSuite Renewal (incumbent)",
            category="software_vendor",
            source_file="mocked",
            currency="USD",
            unit_price=18000,      # annual contract cost
            lead_time_days=2,       # activation/switchover time
            warranty_years=1,       # contract term, reused as "warranty_years"
            rating=4.2,
            catalog_size=None,
        ),
        Supplier(
            name="NextGen Alternative",
            category="software_vendor",
            source_file="mocked",
            currency="USD",
            unit_price=15500,
            lead_time_days=7,
            warranty_years=2,
            rating=4.0,
            catalog_size=None,
        ),
        Supplier(
            name="PremiumSuite Enterprise",
            category="software_vendor",
            source_file="mocked",
            currency="USD",
            unit_price=23000,       # deliberately over the $20,000 budget
            lead_time_days=1,
            warranty_years=3,
            rating=4.7,
            catalog_size=None,
        ),
    ]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Supplier).count()
        if existing > 0:
            print(f"suppliers table already has {existing} rows - skipping seed. "
                  f"Delete workflow.db to reseed from scratch.")
            return

        suppliers = [
            load_alpha_pk(),
            load_bravo_eu(),
            load_charlie_in(),
            load_delta_clean(),
            *load_vendor_renewal_options(),
        ]
        db.add_all(suppliers)
        db.commit()
        for s in suppliers:
            print(f"seeded: {s.name:32s} category={s.category:16s} "
                  f"unit_price={s.unit_price:>10.2f} {s.currency} "
                  f"lead_time={s.lead_time_days}d warranty={s.warranty_years}y")
    finally:
        db.close()


if __name__ == "__main__":
    run()
