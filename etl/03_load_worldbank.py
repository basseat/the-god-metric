"""
ETL: World Bank API — Media & Technology Penetration
=====================================================
Pulls radio, TV, mobile, and internet penetration data by country/year
and loads into fact_media_penetration.

No manual download needed — uses the World Bank public API.

USAGE:
------
  python3 etl/03_load_worldbank.py

REQUIREMENTS:
-------------
  pip install psycopg2-binary pandas requests
"""

import os
import sys
import time
import logging
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "dbname":   os.getenv("PGDATABASE", "god_metric"),
    "user":     os.getenv("PGUSER",     "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
    "host":     os.getenv("PGHOST",     "localhost"),
    "port":     int(os.getenv("PGPORT", 5432)),
}

WB_BASE = "https://api.worldbank.org/v2"

# World Bank indicator codes
INDICATORS = {
    "IT.RAD.SETS.PC":  "radio_per_100",     # Radio sets per 100 people (discontinued ~2000)
    "IT.TVS.SETS.PC":  "tv_per_100",        # TV sets per 100 people
    "IT.CEL.SETS.P2":  "mobile_per_100",    # Mobile subscriptions per 100
    "IT.NET.USER.ZS":  "internet_pct",      # Internet users % of population
}

# Focus on countries most relevant to H3 (sub-Saharan Africa) + global coverage
SSA_FOCUS = [
    "NGA", "GHA", "KEN", "ZAF", "ETH", "TZA", "UGA", "CIV",
    "CMR", "SEN", "ZWE", "ZMB", "MOZ", "ANG", "COD",
    "BRA", "COL", "MEX", "PER",   # Latin America for comparison
    "GBR", "DEU", "FRA", "USA",   # Western comparison
    "IND", "IDN", "PHL",          # Asia
]

YEAR_RANGE = "1960:2023"
CACHE_DIR  = Path(__file__).parent.parent / "data" / "raw" / "worldbank"


# ── World Bank API ─────────────────────────────────────────────────────────────

def fetch_indicator(indicator_code: str, country_codes: list, year_range: str) -> pd.DataFrame:
    """
    Fetch one WB indicator for all countries (more reliable than semicolon list).
    Returns long-format DataFrame: country_code | year | value
    """
    # Use 'all' to fetch all countries — more reliable than joining codes with semicolons
    url = (
        f"{WB_BASE}/country/all/indicator/{indicator_code}"
        f"?format=json&per_page=1000&date={year_range}"
    )

    all_data = []
    page = 1

    while True:
        resp = requests.get(f"{url}&page={page}", timeout=30)
        if resp.status_code != 200:
            log.error("WB API error %d for %s", resp.status_code, indicator_code)
            break

        payload = resp.json()
        if len(payload) < 2 or not payload[1]:
            break

        meta, data = payload
        all_data.extend(data)

        total_pages = meta.get("pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)  # be polite to the API

    if not all_data:
        return pd.DataFrame()

    rows = []
    for item in all_data:
        if item.get("value") is None:
            continue
        rows.append({
            "iso3":    item["country"]["id"],
            "country": item["country"]["value"],
            "year":    int(item["date"]),
            "value":   float(item["value"]),
        })

    df = pd.DataFrame(rows)
    log.info("  Fetched %d non-null rows for %s", len(df), indicator_code)
    return df


def fetch_country_metadata() -> pd.DataFrame:
    """Fetch country metadata (region, income group) from World Bank."""
    url = f"{WB_BASE}/country?format=json&per_page=300"
    resp = requests.get(url, timeout=30)
    payload = resp.json()

    rows = []
    if len(payload) > 1:
        for c in payload[1]:
            if c.get("region", {}).get("id") == "NA":
                continue  # skip aggregates
            rows.append({
                "iso3":         c["id"],
                "iso2":         c.get("iso2Code", ""),
                "country_name": c["name"],
                "region":       c.get("region", {}).get("value", ""),
                "income_group": c.get("incomeLevel", {}).get("value", ""),
            })

    df = pd.DataFrame(rows)
    log.info("Fetched metadata for %d countries from World Bank", len(df))
    return df


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connected to PostgreSQL")
        return conn
    except psycopg2.OperationalError as e:
        log.error("Cannot connect: %s", e)
        sys.exit(1)


def upsert_countries(conn, df_meta: pd.DataFrame):
    """Insert/update dim_country with World Bank metadata."""
    with conn.cursor() as cur:
        for _, row in df_meta.iterrows():
            cur.execute(
                """
                INSERT INTO dim_country (iso3, iso2, country_name, region, wb_income_group)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (iso3) DO UPDATE SET
                    iso2           = EXCLUDED.iso2,
                    region         = COALESCE(EXCLUDED.region, dim_country.region),
                    wb_income_group = EXCLUDED.wb_income_group
                """,
                (
                    row["iso3"],
                    row["iso2"] or None,
                    row["country_name"],
                    row["region"] or None,
                    row["income_group"] or None,
                )
            )
    conn.commit()
    log.info("dim_country upserted with World Bank metadata")


def ensure_year(conn, year: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_year (year) VALUES (%s) ON CONFLICT (year) DO NOTHING", (year,)
        )
        conn.commit()
        cur.execute("SELECT year_id FROM dim_year WHERE year = %s", (year,))
        return cur.fetchone()[0]


def load_media_data(conn, wide_df: pd.DataFrame):
    """
    wide_df: iso3 | year | radio_per_100 | tv_per_100 | mobile_per_100 | internet_pct
    """
    with conn.cursor() as cur:
        # Map BOTH iso3 and iso2 → country_id
        # World Bank indicator API returns ISO2 codes; metadata returns ISO3.
        cur.execute("SELECT iso3, iso2, country_id FROM dim_country")
        country_map = {}
        for iso3, iso2, cid in cur.fetchall():
            country_map[iso3] = cid
            if iso2:
                country_map[iso2] = cid

        cur.execute("SELECT year, year_id FROM dim_year")
        year_map = {r[0]: r[1] for r in cur.fetchall()}

    rows = []
    skipped = 0

    for _, row in wide_df.iterrows():
        iso3 = row["iso3"]
        year = int(row["year"])

        if iso3 not in country_map:
            skipped += 1
            continue
        if year not in year_map:
            year_map[year] = ensure_year(conn, year)

        rows.append((
            country_map[iso3],
            year_map[year],
            row.get("radio_per_100"),
            row.get("tv_per_100"),
            row.get("mobile_per_100"),
            row.get("internet_pct"),
            "world_bank",
        ))

    if rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO fact_media_penetration
                    (country_id, year_id, radio_per_100, tv_per_100,
                     mobile_per_100, internet_pct, source)
                VALUES %s
                ON CONFLICT (country_id, year_id, source) DO UPDATE SET
                    radio_per_100  = COALESCE(EXCLUDED.radio_per_100,  fact_media_penetration.radio_per_100),
                    tv_per_100     = COALESCE(EXCLUDED.tv_per_100,     fact_media_penetration.tv_per_100),
                    mobile_per_100 = COALESCE(EXCLUDED.mobile_per_100, fact_media_penetration.mobile_per_100),
                    internet_pct   = COALESCE(EXCLUDED.internet_pct,   fact_media_penetration.internet_pct),
                    loaded_at      = NOW()
                """,
                rows,
                template="(%s, %s, %s, %s, %s, %s, %s)"
            )
        conn.commit()
        log.info("Loaded %d rows into fact_media_penetration (skipped %d)", len(rows), skipped)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_connection()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Update country metadata
    log.info("Fetching country metadata from World Bank …")
    df_meta = fetch_country_metadata()
    if not df_meta.empty:
        upsert_countries(conn, df_meta)

    # 2. Fetch each indicator and build a wide table
    cache_file = CACHE_DIR / "media_penetration_wide.parquet"

    if cache_file.exists():
        log.info("Loading from cache: %s", cache_file)
        df_wide = pd.read_parquet(cache_file)
    else:
        dfs = {}
        for indicator_code, col_name in INDICATORS.items():
            log.info("Fetching %s (%s) …", indicator_code, col_name)
            df = fetch_indicator(indicator_code, SSA_FOCUS, YEAR_RANGE)
            if not df.empty:
                dfs[col_name] = df.rename(columns={"value": col_name})

        if not dfs:
            log.error("No data fetched from World Bank API. Check your internet connection.")
            sys.exit(1)

        # Merge all indicators on iso3 + year
        df_wide = None
        for col_name, df in dfs.items():
            if df_wide is None:
                df_wide = df[["iso3", "country", "year", col_name]]
            else:
                df_wide = df_wide.merge(
                    df[["iso3", "year", col_name]],
                    on=["iso3", "year"],
                    how="outer"
                )

        df_wide.to_parquet(cache_file, index=False)
        log.info("Cached wide table to %s (%d rows)", cache_file, len(df_wide))

    log.info("Loading %d rows into fact_media_penetration …", len(df_wide))
    load_media_data(conn, df_wide)

    # 3. Spot check
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dc.country_name, dy.year,
                   fmp.radio_per_100, fmp.tv_per_100,
                   fmp.mobile_per_100, fmp.internet_pct
            FROM fact_media_penetration fmp
            JOIN dim_country dc ON fmp.country_id = dc.country_id
            JOIN dim_year    dy ON fmp.year_id    = dy.year_id
            WHERE dc.iso3 = 'NGA'
            ORDER BY dy.year
            LIMIT 8
        """)
        rows = cur.fetchall()
        log.info("Sample: Nigeria media penetration")
        for r in rows:
            log.info("  %s %d | radio=%-6s tv=%-6s mobile=%-6s internet=%s",
                     r[0], r[1],
                     f"{r[2]:.1f}" if r[2] else "-",
                     f"{r[3]:.1f}" if r[3] else "-",
                     f"{r[4]:.1f}" if r[4] else "-",
                     f"{r[5]:.1f}" if r[5] else "-")

    conn.close()
    log.info("Done. ✓")


if __name__ == "__main__":
    main()
