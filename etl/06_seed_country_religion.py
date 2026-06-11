"""
ETL: Country-Level Religion Seed Data (Pew 2015 + OWID Aggregate)
=================================================================
Loads two datasets:

  A) Per-religion country shares for 2010 and 2050 (Christianity, Islam,
     Hinduism, Buddhism, Unaffiliated, Judaism, Folk) — sourced from
     Pew Research Center Global Religious Futures 2015.
     Covers ~65 countries across Africa, Americas, Asia, Europe.
     This is the data needed for Tableau world-map charts.

  B) Aggregate "any religion" share 2010 + 2020 from OWID cache
     (already downloaded by 05_load_owid_religion.py) — used for H1 maps.

USAGE:
------
  python3 etl/06_seed_country_religion.py

Run AFTER:
  - setup/01_create_schema.sql
  - etl/02_load_pew.py  (seeds dim_religion)
  - etl/03_load_worldbank.py  (seeds dim_country with ISO codes)
  - etl/05_load_owid_religion.py  (downloads OWID aggregate cache)
"""

import os
import sys
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

DB_CONFIG = {
    "dbname":   os.getenv("PGDATABASE", "god_metric"),
    "user":     os.getenv("PGUSER",     "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
    "host":     os.getenv("PGHOST",     "localhost"),
    "port":     int(os.getenv("PGPORT", 5432)),
}

OWID_CACHE = Path(__file__).parent.parent / "data" / "raw" / "owid" / "owid_religion_shares.csv"

# ── Pew 2015 country-level seed data ──────────────────────────────────────────
# Format: (iso3, country_name, religion, year, affiliated_pct, affiliated_count_millions)
# Sources: Pew Research Center, "The Future of World Religions", April 2015
#          Appendix C: Detailed religious-affiliation data by country
# affiliated_count is in millions (converted to full integers in load step)

PEW_COUNTRY_DATA = [
    # ── CHRISTIANITY ──────────────────────────────────────────────────────────
    # Sub-Saharan Africa — the H2 story
    ("NGA", "Nigeria",               "Christianity",  2010, 49.3,  80.0),
    ("NGA", "Nigeria",               "Christianity",  2050, 59.6, 300.0),
    ("COD", "DR Congo",              "Christianity",  2010, 95.7,  63.2),
    ("COD", "DR Congo",              "Christianity",  2050, 97.0, 197.0),
    ("ETH", "Ethiopia",              "Christianity",  2010, 62.8,  53.3),
    ("ETH", "Ethiopia",              "Christianity",  2050, 58.2, 103.0),
    ("TZA", "Tanzania",              "Christianity",  2010, 61.4,  25.9),
    ("TZA", "Tanzania",              "Christianity",  2050, 60.0,  67.0),
    ("KEN", "Kenya",                 "Christianity",  2010, 82.5,  33.0),
    ("KEN", "Kenya",                 "Christianity",  2050, 82.0,  74.0),
    ("UGA", "Uganda",                "Christianity",  2010, 84.0,  27.9),
    ("UGA", "Uganda",                "Christianity",  2050, 83.0,  84.0),
    ("ZAF", "South Africa",          "Christianity",  2010, 79.3,  39.3),
    ("ZAF", "South Africa",          "Christianity",  2050, 79.0,  60.0),
    ("GHA", "Ghana",                 "Christianity",  2010, 71.2,  17.4),
    ("GHA", "Ghana",                 "Christianity",  2050, 69.0,  36.0),
    ("ZWE", "Zimbabwe",              "Christianity",  2010, 84.3,  11.1),
    ("ZWE", "Zimbabwe",              "Christianity",  2050, 83.0,  21.0),
    ("MOZ", "Mozambique",            "Christianity",  2010, 56.1,  13.4),
    ("MOZ", "Mozambique",            "Christianity",  2050, 55.0,  43.0),
    ("AGO", "Angola",                "Christianity",  2010, 90.5,  16.3),
    ("AGO", "Angola",                "Christianity",  2050, 90.0,  56.0),
    ("CMR", "Cameroon",              "Christianity",  2010, 53.9,  10.2),
    ("CMR", "Cameroon",              "Christianity",  2050, 52.0,  24.0),
    ("RWA", "Rwanda",                "Christianity",  2010, 94.1,  10.1),
    ("RWA", "Rwanda",                "Christianity",  2050, 94.0,  22.0),
    ("ZMB", "Zambia",                "Christianity",  2010, 95.1,  12.9),
    ("ZMB", "Zambia",                "Christianity",  2050, 95.0,  34.0),
    ("SEN", "Senegal",               "Christianity",  2010,  4.1,   0.6),
    ("MWI", "Malawi",                "Christianity",  2010, 76.4,  12.1),
    ("MWI", "Malawi",                "Christianity",  2050, 75.0,  33.0),
    ("CIV", "Cote d'Ivoire",         "Christianity",  2010, 39.4,   7.7),
    # Latin America
    ("BRA", "Brazil",                "Christianity",  2010, 88.5, 175.0),
    ("BRA", "Brazil",                "Christianity",  2050, 84.0, 200.0),
    ("MEX", "Mexico",                "Christianity",  2010, 92.9, 108.0),
    ("MEX", "Mexico",                "Christianity",  2050, 91.0, 138.0),
    ("COL", "Colombia",              "Christianity",  2010, 94.4,  44.0),
    ("ARG", "Argentina",             "Christianity",  2010, 91.9,  37.0),
    ("PER", "Peru",                  "Christianity",  2010, 96.5,  28.0),
    # North America / Europe
    ("USA", "United States",         "Christianity",  2010, 78.3, 243.0),
    ("USA", "United States",         "Christianity",  2050, 66.4, 263.0),
    ("CAN", "Canada",                "Christianity",  2010, 69.9,  22.8),
    ("GBR", "United Kingdom",        "Christianity",  2010, 64.0,  40.2),
    ("GBR", "United Kingdom",        "Christianity",  2050, 45.0,  30.0),
    ("DEU", "Germany",               "Christianity",  2010, 63.4,  52.0),
    ("DEU", "Germany",               "Christianity",  2050, 54.0,  41.0),
    ("FRA", "France",                "Christianity",  2010, 64.6,  40.4),
    ("FRA", "France",                "Christianity",  2050, 54.0,  37.0),
    ("ITA", "Italy",                 "Christianity",  2010, 83.5,  50.0),
    ("POL", "Poland",                "Christianity",  2010, 94.6,  36.0),
    ("ESP", "Spain",                 "Christianity",  2010, 78.0,  35.5),
    ("RUS", "Russia",                "Christianity",  2010, 71.2, 101.0),
    ("RUS", "Russia",                "Christianity",  2050, 67.0,  93.0),
    ("UKR", "Ukraine",               "Christianity",  2010, 83.8,  37.0),
    # Asia-Pacific
    ("PHL", "Philippines",           "Christianity",  2010, 92.6,  87.0),
    ("PHL", "Philippines",           "Christianity",  2050, 92.0, 128.0),
    ("AUS", "Australia",             "Christianity",  2010, 61.1,  13.3),
    ("CHN", "China",                 "Christianity",  2010,  5.1,  68.0),
    ("KOR", "South Korea",           "Christianity",  2010, 29.3,  14.0),
    ("IND", "India",                 "Christianity",  2010,  2.5,  29.0),
    ("IDN", "Indonesia",             "Christianity",  2010,  9.9,  23.0),

    # ── ISLAM ─────────────────────────────────────────────────────────────────
    ("IDN", "Indonesia",             "Islam",         2010, 87.2, 205.0),
    ("IDN", "Indonesia",             "Islam",         2050, 88.0, 257.0),
    ("PAK", "Pakistan",              "Islam",         2010, 96.4, 178.0),
    ("PAK", "Pakistan",              "Islam",         2050, 97.0, 310.0),
    ("BGD", "Bangladesh",            "Islam",         2010, 90.4, 149.0),
    ("BGD", "Bangladesh",            "Islam",         2050, 91.0, 195.0),
    ("NGA", "Nigeria",               "Islam",         2010, 48.8,  75.0),
    ("NGA", "Nigeria",               "Islam",         2050, 39.0, 196.0),
    ("EGY", "Egypt",                 "Islam",         2010, 94.1,  80.0),
    ("EGY", "Egypt",                 "Islam",         2050, 95.0, 118.0),
    ("IRN", "Iran",                  "Islam",         2010, 99.5,  75.0),
    ("TUR", "Turkey",                "Islam",         2010, 98.6,  74.0),
    ("DZA", "Algeria",               "Islam",         2010, 97.9,  35.0),
    ("MAR", "Morocco",               "Islam",         2010, 99.9,  32.0),
    ("SAU", "Saudi Arabia",          "Islam",         2010, 97.1,  24.9),
    ("SDN", "Sudan",                 "Islam",         2010, 97.0,  38.8),
    ("ETH", "Ethiopia",              "Islam",         2010, 33.9,  28.7),
    ("ETH", "Ethiopia",              "Islam",         2050, 40.0,  71.0),
    ("SEN", "Senegal",               "Islam",         2010, 95.9,  13.1),
    ("SEN", "Senegal",               "Islam",         2050, 95.0,  30.0),
    ("MYS", "Malaysia",              "Islam",         2010, 61.3,  17.1),
    ("UZB", "Uzbekistan",            "Islam",         2010, 96.5,  26.8),
    ("AFG", "Afghanistan",           "Islam",         2010, 99.7,  29.1),
    ("IRQ", "Iraq",                  "Islam",         2010, 98.9,  31.3),
    ("YEM", "Yemen",                 "Islam",         2010, 99.1,  24.7),
    ("SYR", "Syrian Arab Republic",  "Islam",         2010, 92.8,  20.2),
    ("TZA", "Tanzania",              "Islam",         2010, 35.2,  14.8),
    ("NER", "Niger",                 "Islam",         2010, 98.3,  15.3),
    ("MLI", "Mali",                  "Islam",         2010, 92.4,  13.0),
    ("BFA", "Burkina Faso",          "Islam",         2010, 58.9,   9.4),
    ("GHA", "Ghana",                 "Islam",         2010, 17.9,   4.4),
    ("CMR", "Cameroon",              "Islam",         2010, 35.7,   6.8),
    ("CIV", "Cote d'Ivoire",         "Islam",         2010, 42.9,   8.4),
    ("FRA", "France",                "Islam",         2010,  7.5,   4.7),
    ("RUS", "Russia",                "Islam",         2010, 10.0,  14.2),
    ("CHN", "China",                 "Islam",         2010,  1.8,  24.7),
    ("IND", "India",                 "Islam",         2010, 14.4, 176.0),
    ("IND", "India",                 "Islam",         2050, 18.4, 311.0),
    ("DEU", "Germany",               "Islam",         2010,  5.8,   4.7),
    ("GBR", "United Kingdom",        "Islam",         2010,  4.8,   2.9),
    ("KAZ", "Kazakhstan",            "Islam",         2010, 70.4,  11.8),
    ("LBY", "Libya",                 "Islam",         2010, 96.6,   6.1),
    ("TUN", "Tunisia",               "Islam",         2010, 99.8,  10.4),
    ("SOM", "Somalia",               "Islam",         2010, 99.8,   9.2),

    # ── HINDUISM ──────────────────────────────────────────────────────────────
    ("IND", "India",                 "Hinduism",      2010, 79.5, 972.0),
    ("IND", "India",                 "Hinduism",      2050, 76.7,1297.0),
    ("NPL", "Nepal",                 "Hinduism",      2010, 81.3,  23.8),
    ("BGD", "Bangladesh",            "Hinduism",      2010,  8.5,  14.0),
    ("IDN", "Indonesia",             "Hinduism",      2010,  1.8,   4.2),
    ("LKA", "Sri Lanka",             "Hinduism",      2010, 13.7,   2.8),
    ("PAK", "Pakistan",              "Hinduism",      2010,  1.6,   2.9),
    ("MYS", "Malaysia",              "Hinduism",      2010,  6.3,   1.8),
    ("ZAF", "South Africa",          "Hinduism",      2010,  2.0,   1.0),
    ("GBR", "United Kingdom",        "Hinduism",      2010,  1.3,   0.8),
    ("USA", "United States",         "Hinduism",      2010,  0.4,   1.2),
    ("MUS", "Mauritius",             "Hinduism",      2010, 48.4,   0.6),
    ("TTO", "Trinidad and Tobago",   "Hinduism",      2010, 22.4,   0.3),
    ("FJI", "Fiji",                  "Hinduism",      2010, 27.9,   0.2),

    # ── BUDDHISM ──────────────────────────────────────────────────────────────
    ("CHN", "China",                 "Buddhism",      2010, 18.2, 244.0),
    ("THA", "Thailand",              "Buddhism",      2010, 92.7,  61.0),
    ("JPN", "Japan",                 "Buddhism",      2010, 36.2,  45.8),
    ("MMR", "Myanmar",               "Buddhism",      2010, 79.7,  38.4),
    ("LKA", "Sri Lanka",             "Buddhism",      2010, 68.5,  14.2),
    ("VNM", "Viet Nam",              "Buddhism",      2010, 16.4,  14.4),
    ("KHM", "Cambodia",              "Buddhism",      2010, 96.9,  13.7),
    ("KOR", "South Korea",           "Buddhism",      2010, 22.9,  11.1),
    ("IND", "India",                 "Buddhism",      2010,  0.8,  10.0),
    ("TWN", "Taiwan",                "Buddhism",      2010, 21.3,   5.0),
    ("MNG", "Mongolia",              "Buddhism",      2010, 53.0,   1.3),
    ("LAO", "Lao PDR",               "Buddhism",      2010, 64.7,   4.2),
    ("BTN", "Bhutan",                "Buddhism",      2010, 73.2,   0.5),
    ("AUS", "Australia",             "Buddhism",      2010,  2.5,   0.5),
    ("USA", "United States",         "Buddhism",      2010,  1.2,   3.9),

    # ── UNAFFILIATED ──────────────────────────────────────────────────────────
    ("CHN", "China",                 "Unaffiliated",  2010, 52.2, 700.0),
    ("CHN", "China",                 "Unaffiliated",  2050, 52.0, 765.0),
    ("USA", "United States",         "Unaffiliated",  2010, 16.4,  51.0),
    ("USA", "United States",         "Unaffiliated",  2050, 26.0, 103.0),
    ("JPN", "Japan",                 "Unaffiliated",  2010, 57.0,  72.2),
    ("DEU", "Germany",               "Unaffiliated",  2010, 24.7,  20.3),
    ("DEU", "Germany",               "Unaffiliated",  2050, 33.0,  25.0),
    ("FRA", "France",                "Unaffiliated",  2010, 28.0,  17.5),
    ("FRA", "France",                "Unaffiliated",  2050, 32.0,  22.0),
    ("GBR", "United Kingdom",        "Unaffiliated",  2010, 25.1,  15.8),
    ("GBR", "United Kingdom",        "Unaffiliated",  2050, 39.0,  26.0),
    ("KOR", "South Korea",           "Unaffiliated",  2010, 46.4,  22.5),
    ("RUS", "Russia",                "Unaffiliated",  2010, 18.5,  26.2),
    ("CZE", "Czech Republic",        "Unaffiliated",  2010, 76.4,   8.1),
    ("NLD", "Netherlands",           "Unaffiliated",  2010, 42.1,   7.0),
    ("AUS", "Australia",             "Unaffiliated",  2010, 24.4,   5.3),
    ("CAN", "Canada",                "Unaffiliated",  2010, 24.0,   7.8),
    ("VNM", "Viet Nam",              "Unaffiliated",  2010, 29.6,  26.0),
    ("SWE", "Sweden",                "Unaffiliated",  2010, 27.0,   2.5),
    ("NOR", "Norway",                "Unaffiliated",  2010, 17.1,   0.8),
    ("DNK", "Denmark",               "Unaffiliated",  2010, 19.0,   1.1),
    ("FIN", "Finland",               "Unaffiliated",  2010, 25.3,   1.4),
    ("EST", "Estonia",               "Unaffiliated",  2010, 59.6,   0.8),
    ("HUN", "Hungary",               "Unaffiliated",  2010, 25.5,   2.5),
    ("SVK", "Slovak Republic",       "Unaffiliated",  2010, 10.4,   0.6),
    ("CHE", "Switzerland",           "Unaffiliated",  2010, 17.9,   1.4),
    ("IND", "India",                 "Unaffiliated",  2010,  0.2,   2.9),
    ("BRA", "Brazil",                "Unaffiliated",  2010,  8.0,  15.8),

    # ── JUDAISM ──────────────────────────────────────────────────────────────
    ("ISR", "Israel",                "Judaism",       2010, 75.6,   5.8),
    ("ISR", "Israel",                "Judaism",       2050, 79.0,   9.9),
    ("USA", "United States",         "Judaism",       2010,  1.8,   5.7),
    ("FRA", "France",                "Judaism",       2010,  0.8,   0.5),
    ("CAN", "Canada",                "Judaism",       2010,  1.0,   0.3),
    ("GBR", "United Kingdom",        "Judaism",       2010,  0.5,   0.3),
    ("ARG", "Argentina",             "Judaism",       2010,  0.6,   0.2),
    ("RUS", "Russia",                "Judaism",       2010,  0.2,   0.2),
    ("AUS", "Australia",             "Judaism",       2010,  0.5,   0.1),

    # ── FOLK / INDIGENOUS ────────────────────────────────────────────────────
    ("CHN", "China",                 "Folk/Indigenous", 2010, 21.9, 294.0),
    ("VNM", "Viet Nam",              "Folk/Indigenous", 2010, 45.3,  39.8),
    ("KOR", "South Korea",           "Folk/Indigenous", 2010, 25.3,  12.3),
    ("JPN", "Japan",                 "Folk/Indigenous", 2010,  3.9,   4.9),
    ("TWN", "Taiwan",                "Folk/Indigenous", 2010, 44.0,  10.2),
    ("ETH", "Ethiopia",              "Folk/Indigenous", 2010,  2.9,   2.4),
    ("TZA", "Tanzania",              "Folk/Indigenous", 2010,  2.4,   1.0),
    ("MOZ", "Mozambique",            "Folk/Indigenous", 2010,  3.7,   0.9),
    ("IND", "India",                 "Folk/Indigenous", 2010,  0.7,   8.7),
    ("USA", "United States",         "Folk/Indigenous", 2010,  0.4,   1.2),
    ("BRA", "Brazil",                "Folk/Indigenous", 2010,  0.4,   0.8),
    ("MNG", "Mongolia",              "Folk/Indigenous", 2010, 38.6,   1.0),
]

PROJECTION_YEARS = {2030, 2050}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connected to PostgreSQL")
        return conn
    except psycopg2.OperationalError as e:
        log.error("Cannot connect: %s", e)
        sys.exit(1)


def build_lookups(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT religion_name, religion_id FROM dim_religion")
        religion_map = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT year, year_id FROM dim_year")
        year_map = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT iso3, country_id FROM dim_country")
        iso3_map = {r[0]: r[1] for r in cur.fetchall()}

    return religion_map, year_map, iso3_map


def ensure_country(conn, iso3: str, name: str, iso3_map: dict) -> int:
    if iso3 in iso3_map:
        return iso3_map[iso3]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_country (iso3, country_name)
            VALUES (%s, %s)
            ON CONFLICT (iso3) DO NOTHING
            RETURNING country_id
            """,
            (iso3, name)
        )
        row = cur.fetchone()
        if row:
            conn.commit()
            iso3_map[iso3] = row[0]
            return row[0]
        cur.execute("SELECT country_id FROM dim_country WHERE iso3 = %s", (iso3,))
        cid = cur.fetchone()[0]
        iso3_map[iso3] = cid
        return cid


def ensure_year(conn, year: int, year_map: dict) -> int:
    if year in year_map:
        return year_map[year]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_year (year, is_projection) VALUES (%s, %s) ON CONFLICT (year) DO NOTHING",
            (year, year in PROJECTION_YEARS)
        )
        conn.commit()
        cur.execute("SELECT year_id FROM dim_year WHERE year = %s", (year,))
        yid = cur.fetchone()[0]
    year_map[year] = yid
    return yid


# ── Load A: Per-religion Pew seed data ───────────────────────────────────────

def load_pew_seed(conn, religion_map, year_map, iso3_map):
    log.info("Loading per-religion country seed data (Pew 2015) …")
    rows = []
    skipped = []

    for iso3, name, religion, year, pct, count_m in PEW_COUNTRY_DATA:
        religion_id = religion_map.get(religion)
        if not religion_id:
            skipped.append(f"Missing religion: {religion}")
            continue

        country_id = ensure_country(conn, iso3, name, iso3_map)
        year_id = ensure_year(conn, year, year_map)
        count_int = int(count_m * 1_000_000) if count_m else None

        rows.append((
            country_id,
            religion_id,
            year_id,
            count_int,
            round(pct, 2),
            None,          # country_total_pop (not provided at country level)
            "pew_2015_seed",
            year in PROJECTION_YEARS,
        ))

    if skipped:
        log.warning("Skipped %d rows: %s", len(skipped), set(skipped))

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
                    affiliated_count       = COALESCE(EXCLUDED.affiliated_count, fact_religious_population.affiliated_count),
                    affiliated_pct_country = EXCLUDED.affiliated_pct_country,
                    loaded_at              = NOW()
                """,
                rows,
            )
        conn.commit()
        log.info("Loaded %d per-religion country rows (Pew 2015)", len(rows))


# ── Load B: OWID aggregate religiosity (% religious, any) ────────────────────

def ensure_any_religion(conn, religion_map):
    """Add 'Any Religion' to dim_religion if not present (for aggregate maps)."""
    if "Any Religion" in religion_map:
        return religion_map["Any Religion"]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_religion (religion_name, propagation_model)
            VALUES ('Any Religion', 'Aggregate')
            ON CONFLICT DO NOTHING
            RETURNING religion_id
            """,
        )
        row = cur.fetchone()
        if row:
            conn.commit()
            religion_map["Any Religion"] = row[0]
            return row[0]
        cur.execute("SELECT religion_id FROM dim_religion WHERE religion_name = 'Any Religion'")
        rid = cur.fetchone()[0]
        religion_map["Any Religion"] = rid
        return rid


def load_owid_aggregate(conn, religion_map, year_map, iso3_map):
    if not OWID_CACHE.exists():
        log.warning("OWID cache not found at %s — skipping aggregate load.", OWID_CACHE)
        log.warning("Run etl/05_load_owid_religion.py first to download the cache.")
        return

    log.info("Loading OWID aggregate religiosity from %s …", OWID_CACHE)
    df = pd.read_csv(OWID_CACHE)
    log.info("Columns: %s | shape: %s", df.columns.tolist(), df.shape)

    # Identify columns
    entity_col = next((c for c in df.columns if c.lower() in ("entity", "country", "location")), None)
    year_col   = next((c for c in df.columns if c.lower() in ("year", "time")), None)
    code_col   = next((c for c in df.columns if c.lower() in ("code", "iso_code", "countrycode")), None)
    # Share column — OWID uses 'share__religion_any_religion' or similar
    skip = {entity_col, year_col, code_col}
    share_cols = [c for c in df.columns if c not in skip and c and "share" in c.lower()]
    if not share_cols:
        share_cols = [c for c in df.columns if c not in skip and c]
    if not share_cols:
        log.error("Cannot identify share column in OWID data. Columns: %s", df.columns.tolist())
        return

    share_col = share_cols[0]
    log.info("Using share column: %s", share_col)

    any_religion_id = ensure_any_religion(conn, religion_map)

    rows = []
    skipped = 0

    for _, row in df.iterrows():
        code = str(row.get(code_col, "")).strip().upper() if code_col else ""
        entity = str(row.get(entity_col, "")).strip() if entity_col else ""

        # Skip aggregates (no valid 3-letter ISO code)
        if not code or len(code) != 3 or not code.isalpha():
            skipped += 1
            continue

        try:
            year = int(float(row[year_col]))
        except (ValueError, TypeError):
            skipped += 1
            continue

        pct = row.get(share_col)
        if pd.isna(pct):
            skipped += 1
            continue

        try:
            pct_val = float(pct)
        except (ValueError, TypeError):
            skipped += 1
            continue

        country_id = iso3_map.get(code)
        if not country_id:
            country_id = ensure_country(conn, code, entity, iso3_map)

        year_id = ensure_year(conn, year, year_map)

        rows.append((
            country_id,
            any_religion_id,
            year_id,
            None,          # no count — only %
            round(pct_val, 2),
            None,
            "owid_pew_aggregate",
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
                    affiliated_pct_country = EXCLUDED.affiliated_pct_country,
                    loaded_at              = NOW()
                """,
                rows,
            )
        conn.commit()
        log.info("Loaded %d OWID aggregate rows (skipped %d)", len(rows), skipped)


# ── Spot checks ───────────────────────────────────────────────────────────────

def spot_check(conn):
    with conn.cursor() as cur:
        # Per-religion check: top Christian countries 2010
        cur.execute("""
            SELECT dc.country_name, dy.year, dr.religion_name,
                   frp.affiliated_count, frp.affiliated_pct_country
            FROM fact_religious_population frp
            JOIN dim_country  dc ON frp.country_id  = dc.country_id
            JOIN dim_religion dr ON frp.religion_id = dr.religion_id
            JOIN dim_year     dy ON frp.year_id     = dy.year_id
            WHERE dr.religion_name = 'Christianity'
              AND dy.year = 2010
              AND frp.source = 'pew_2015_seed'
            ORDER BY frp.affiliated_count DESC NULLS LAST
            LIMIT 10
        """)
        rows = cur.fetchall()
        log.info("── Top 10 Christian populations 2010 (country-level seed) ──")
        for r in rows:
            count = f"{float(r[3])/1e6:.1f}M" if r[3] else "pct only"
            log.info("  %-25s %d | %s (%.1f%%)", r[0], r[1], count, r[4] or 0)

        # H2 summary: Africa vs Europe Christianity 2010 vs 2050
        cur.execute("""
            SELECT dy.year,
                   CASE WHEN dc.region ILIKE '%africa%' THEN 'Africa'
                        WHEN dc.region ILIKE '%europe%' THEN 'Europe'
                        ELSE 'Other'
                   END AS region_grp,
                   SUM(frp.affiliated_count) AS total
            FROM fact_religious_population frp
            JOIN dim_country  dc ON frp.country_id  = dc.country_id
            JOIN dim_religion dr ON frp.religion_id = dr.religion_id
            JOIN dim_year     dy ON frp.year_id     = dy.year_id
            WHERE dr.religion_name = 'Christianity'
              AND frp.source = 'pew_2015_seed'
              AND dy.year IN (2010, 2050)
            GROUP BY dy.year, region_grp
            ORDER BY dy.year, total DESC NULLS LAST
        """)
        log.info("── H2 check: Africa vs Europe Christianity (seed data) ──")
        for r in cur.fetchall():
            v = float(r[2]) if r[2] else None
            total = f"{v/1e9:.2f}B" if v and v > 1e9 else (f"{v/1e6:.0f}M" if v else "—")
            log.info("  %d | %-8s | %s", r[0], r[1], total)

        # Aggregate religiosity sample
        cur.execute("""
            SELECT dc.country_name, dy.year, frp.affiliated_pct_country
            FROM fact_religious_population frp
            JOIN dim_country  dc ON frp.country_id  = dc.country_id
            JOIN dim_religion dr ON frp.religion_id = dr.religion_id
            JOIN dim_year     dy ON frp.year_id     = dy.year_id
            WHERE dr.religion_name = 'Any Religion'
              AND frp.source = 'owid_pew_aggregate'
            ORDER BY frp.affiliated_pct_country ASC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            log.info("── 10 least religious countries (OWID aggregate) ──")
            for r in rows:
                log.info("  %-25s %d | %.1f%%", r[0], r[1], r[2] or 0)

        # Total row count
        cur.execute("""
            SELECT source, COUNT(DISTINCT country_id) AS countries, COUNT(*) AS rows
            FROM fact_religious_population
            WHERE source IN ('pew_2015_seed', 'owid_pew_aggregate')
            GROUP BY source ORDER BY source
        """)
        log.info("── Row counts ──")
        for r in cur.fetchall():
            log.info("  %-25s | %d countries | %d rows", r[0], r[1], r[2])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_connection()
    religion_map, year_map, iso3_map = build_lookups(conn)

    load_pew_seed(conn, religion_map, year_map, iso3_map)
    load_owid_aggregate(conn, religion_map, year_map, iso3_map)
    spot_check(conn)

    conn.close()
    log.info("Done. ✓")


if __name__ == "__main__":
    main()
