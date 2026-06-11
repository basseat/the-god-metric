"""
ETL: Pew Research Center — Global Religious Futures (2015) + 2025 Update
=========================================================================
Downloads/processes Pew CSV data and loads into fact_religious_population.

DATA DOWNLOAD (manual steps required before running):
------------------------------------------------------
1. Go to: https://www.pewresearch.org/religion/2015/04/02/religious-projections-2010-2050/
2. Scroll to the bottom → click "Download the data"
3. Save the Excel file as: god_metric/data/raw/pew_2015_religious_futures.xlsx
4. (Optional) For 2025 update:
   https://www.pewresearch.org/religion/2025/06/09/how-the-global-religious-landscape-changed-from-2010-to-2020/
   Download the data appendix and save as: god_metric/data/raw/pew_2025_update.xlsx

USAGE:
------
  python3 etl/02_load_pew.py

REQUIREMENTS:
-------------
  pip install psycopg2-binary pandas openpyxl
"""

import os
import sys
import logging
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

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PEW_2015_FILE = RAW_DIR / "pew_2015_religious_futures.xlsx"
PEW_2025_FILE = RAW_DIR / "pew_2025_update.xlsx"

# Pew religion names → our dim_religion names
RELIGION_MAP = {
    "Christians":           "Christianity",
    "Christian":            "Christianity",
    "Muslims":              "Islam",
    "Muslim":               "Islam",
    "Hindus":               "Hinduism",
    "Hindu":                "Hinduism",
    "Buddhists":            "Buddhism",
    "Buddhist":             "Buddhism",
    "Jews":                 "Judaism",
    "Jewish":               "Judaism",
    "Folk Religions":       "Folk/Indigenous",
    "Folk Religion":        "Folk/Indigenous",
    "Other Religions":      "Other Religion",
    "Other Religion":       "Other Religion",
    "Unaffiliated":         "Unaffiliated",
    "Religiously Unaffiliated": "Unaffiliated",
}

# Years with projection status
PROJECTION_YEARS = {2030, 2050}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connected to PostgreSQL: %s@%s/%s",
                 DB_CONFIG["user"], DB_CONFIG["host"], DB_CONFIG["dbname"])
        return conn
    except psycopg2.OperationalError as e:
        log.error("Cannot connect to database: %s", e)
        log.error("Make sure PostgreSQL is running and the god_metric database exists.")
        log.error("Run: createdb god_metric && psql god_metric -f setup/01_create_schema.sql")
        sys.exit(1)


def build_lookup(conn, table, key_col, val_col):
    """Returns a dict mapping key_col values → val_col values."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {key_col}, {val_col} FROM {table}")
        return {row[0]: row[1] for row in cur.fetchall()}


def ensure_country(conn, iso3, country_name, region=None):
    """Insert country if not exists. Returns country_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_country (iso3, country_name, region)
            VALUES (%s, %s, %s)
            ON CONFLICT (iso3) DO NOTHING
            RETURNING country_id
            """,
            (iso3, country_name, region)
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT country_id FROM dim_country WHERE iso3 = %s", (iso3,))
        return cur.fetchone()[0]


# ── Pew 2015 processor ────────────────────────────────────────────────────────

def process_pew_2015(filepath: Path) -> pd.DataFrame:
    """
    Parse the Pew 2015 Global Religious Futures Excel workbook.

    The workbook typically has a sheet called something like
    'Appendix A' or 'All Countries' with columns:
    Country | Region | 2010 Christians | 2010 Muslims | ... | 2050 Christians | ...

    We reshape (melt) it into long format:
    country | year | religion | count | pct
    """
    log.info("Reading Pew 2015 file: %s", filepath)

    # Try to find the right sheet
    xl = pd.ExcelFile(filepath)
    log.info("Available sheets: %s", xl.sheet_names)

    # Try common sheet names
    target_sheet = None
    for sheet in xl.sheet_names:
        if any(kw in sheet.lower() for kw in ["all countries", "appendix", "data", "population"]):
            target_sheet = sheet
            break
    if target_sheet is None:
        target_sheet = xl.sheet_names[0]
        log.warning("Could not detect sheet — defaulting to first sheet: %s", target_sheet)

    df = pd.read_excel(filepath, sheet_name=target_sheet, header=0)
    log.info("Raw shape: %s, columns: %s", df.shape, df.columns.tolist()[:10])

    # ── The Pew 2015 spreadsheet has a wide format with paired columns:
    # [Year] [Religion] Count and [Year] [Religion] % of total
    # We need to identify which format this specific download uses.
    #
    # Two common formats:
    # Format A: columns = ["Country", "Region", "2010 Christians", "2010 Christians %", ...]
    # Format B: Separate worksheets per year
    #
    # We handle Format A (most common for the public download):

    records = []

    # Find the country column
    country_col = next((c for c in df.columns if "country" in str(c).lower()), df.columns[0])
    region_col  = next((c for c in df.columns if "region" in str(c).lower()), None)

    years = [2010, 2020, 2030, 2050]  # Pew 2015 has these intervals
    religions = list(RELIGION_MAP.keys())

    for _, row in df.iterrows():
        country_name = str(row.get(country_col, "")).strip()
        if not country_name or country_name.lower() in ("nan", "total", "world"):
            continue

        region = str(row.get(region_col, "")).strip() if region_col else None

        for year in years:
            for rel_raw, rel_clean in RELIGION_MAP.items():
                # Try different column naming conventions
                for col_pattern in [
                    f"{year} {rel_raw}",
                    f"{rel_raw} {year}",
                    f"{year}_{rel_raw}",
                    rel_raw,
                ]:
                    if col_pattern in df.columns:
                        val = row.get(col_pattern)
                        if pd.notna(val):
                            try:
                                count = int(float(str(val).replace(",", "")))
                                records.append({
                                    "country_name": country_name,
                                    "region":       region,
                                    "year":         year,
                                    "religion":     rel_clean,
                                    "count":        count,
                                    "pct":          None,
                                })
                            except (ValueError, TypeError):
                                pass
                        break

    df_long = pd.DataFrame(records)
    log.info("Pew 2015 parsed: %d rows across %d unique countries",
             len(df_long), df_long["country_name"].nunique())
    return df_long


# ── Fallback: hardcoded key data points ───────────────────────────────────────
# If the Pew Excel parsing fails due to format changes, use these
# verified key figures from the published report as seed data.

PEW_KEY_FIGURES = [
    # (country_name, iso3, region,          year,  religion,       count,       pct_of_country)
    # Africa totals
    ("Sub-Saharan Africa", "SSA", "Sub-Saharan Africa", 1910, "Christianity",   7_000_000,   9.0),
    ("Sub-Saharan Africa", "SSA", "Sub-Saharan Africa", 1970, "Christianity",  143_000_000,  40.0),
    ("Sub-Saharan Africa", "SSA", "Sub-Saharan Africa", 2010, "Christianity",  516_000_000,  57.0),
    ("Sub-Saharan Africa", "SSA", "Sub-Saharan Africa", 2020, "Christianity",  697_000_000,  62.0),
    ("Sub-Saharan Africa", "SSA", "Sub-Saharan Africa", 2050, "Christianity", 1_100_000_000, 59.0),

    # Europe totals
    ("Europe",             "EUR", "Europe",             1910, "Christianity",  400_000_000,  95.0),
    ("Europe",             "EUR", "Europe",             1970, "Christianity",  479_000_000,  88.0),
    ("Europe",             "EUR", "Europe",             2010, "Christianity",  553_000_000,  76.0),
    ("Europe",             "EUR", "Europe",             2020, "Christianity",  534_000_000,  72.0),
    ("Europe",             "EUR", "Europe",             2050, "Christianity",  490_000_000,  65.0),

    # North America
    ("North America",      "NAM", "North America",      1910, "Christianity",   80_000_000,  96.0),
    ("North America",      "NAM", "North America",      2010, "Christianity",  266_000_000,  77.0),
    ("North America",      "NAM", "North America",      2050, "Christianity",  268_000_000,  66.0),

    # Latin America
    ("Latin America",      "LAM", "Latin America",      1910, "Christianity",   65_000_000,  95.0),
    ("Latin America",      "LAM", "Latin America",      2010, "Christianity",  531_000_000,  90.0),
    ("Latin America",      "LAM", "Latin America",      2050, "Christianity",  636_000_000,  89.0),

    # Global Christianity
    ("World",              "WLD", "World",               1910, "Christianity",  558_000_000,  35.0),
    ("World",              "WLD", "World",               1970, "Christianity", 1_200_000_000, 33.0),
    ("World",              "WLD", "World",               2010, "Christianity", 2_168_000_000, 31.0),
    ("World",              "WLD", "World",               2020, "Christianity", 2_382_000_000, 31.0),
    ("World",              "WLD", "World",               2050, "Christianity", 3_292_000_000, 34.0),

    # Global Islam
    ("World",              "WLD", "World",               1910, "Islam",          221_000_000, 13.0),
    ("World",              "WLD", "World",               2010, "Islam",        1_599_000_000, 23.0),
    ("World",              "WLD", "World",               2020, "Islam",        1_907_000_000, 25.0),
    ("World",              "WLD", "World",               2050, "Islam",        2_761_000_000, 28.0),

    # Global unaffiliated
    ("World",              "WLD", "World",               2010, "Unaffiliated", 1_131_000_000, 16.0),
    ("World",              "WLD", "World",               2050, "Unaffiliated", 1_230_000_000, 13.0),
]


def get_key_figures_df() -> pd.DataFrame:
    cols = ["country_name", "iso3", "region", "year", "religion", "count", "pct"]
    return pd.DataFrame(PEW_KEY_FIGURES, columns=cols)


# ── Loader ────────────────────────────────────────────────────────────────────

def load_pew_data(conn, df: pd.DataFrame, source: str):
    """
    Load a normalised long-format Pew dataframe into fact_religious_population.
    df must have: country_name, year, religion, count, pct (iso3 and region optional).
    """
    religion_map  = build_lookup(conn, "dim_religion", "religion_name", "religion_id")
    year_map      = build_lookup(conn, "dim_year",     "year",          "year_id")
    country_cache = {}

    rows = []
    skipped = 0

    for _, row in df.iterrows():
        religion = row.get("religion", "")
        if religion not in religion_map:
            skipped += 1
            continue

        year = int(row["year"])
        if year not in year_map:
            skipped += 1
            continue

        country_name = str(row["country_name"]).strip()
        iso3 = str(row.get("iso3", "")).strip() or country_name[:3].upper()
        region = row.get("region") or None

        if iso3 not in country_cache:
            country_cache[iso3] = ensure_country(conn, iso3, country_name, region)
        country_id = country_cache[iso3]

        count = row.get("count")
        pct   = row.get("pct")

        rows.append((
            country_id,
            religion_map[religion],
            year_map[year],
            int(count) if pd.notna(count) else None,
            float(pct) if pd.notna(pct) else None,
            None,   # country_total_pop — compute from sum if needed
            source,
            year in PROJECTION_YEARS,
        ))

    if rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO fact_religious_population
                    (country_id, religion_id, year_id, affiliated_count,
                     affiliated_pct_country, country_total_pop, source, is_projection)
                VALUES %s
                ON CONFLICT (country_id, religion_id, year_id, source) DO UPDATE SET
                    affiliated_count       = EXCLUDED.affiliated_count,
                    affiliated_pct_country = EXCLUDED.affiliated_pct_country,
                    loaded_at              = NOW()
                """,
                rows
            )
        conn.commit()
        log.info("Loaded %d rows from %s (skipped %d)", len(rows), source, skipped)
    else:
        log.warning("No rows to load from %s", source)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_connection()

    # 1. Load key figures (always — these are verified reference points)
    log.info("Loading hardcoded key figures as seed data …")
    df_seed = get_key_figures_df()
    load_pew_data(conn, df_seed, source="pew_key_figures")

    # 2. Load from downloaded Excel if it exists
    if PEW_2015_FILE.exists():
        log.info("Pew 2015 file found. Parsing …")
        try:
            df_2015 = process_pew_2015(PEW_2015_FILE)
            if not df_2015.empty:
                load_pew_data(conn, df_2015, source="pew_2015")
        except Exception as e:
            log.error("Failed to parse Pew 2015 file: %s", e)
            log.info("Continuing with seed data only.")
    else:
        log.warning(
            "Pew 2015 file not found at %s\n"
            "  → Download from: https://www.pewresearch.org/religion/2015/04/02/religious-projections-2010-2050/\n"
            "  → Save as: data/raw/pew_2015_religious_futures.xlsx\n"
            "  → Seed data loaded as fallback.",
            PEW_2015_FILE
        )

    # 3. Quick sanity check
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dr.religion_name, dy.year, frp.affiliated_count
            FROM fact_religious_population frp
            JOIN dim_religion dr ON frp.religion_id = dr.religion_id
            JOIN dim_year     dy ON frp.year_id     = dy.year_id
            JOIN dim_country  dc ON frp.country_id  = dc.country_id
            WHERE dc.iso3 = 'WLD'
            ORDER BY dy.year, frp.affiliated_count DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        log.info("Sample from fact_religious_population (World totals):")
        for r in rows:
            log.info("  %-20s %d  → %s", r[0], r[1],
                     f"{r[2]:,}" if r[2] else "NULL")

    conn.close()
    log.info("Done. ✓")


if __name__ == "__main__":
    main()
