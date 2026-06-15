"""
ETL: Load multi-religion country-level data from OWID
Source: Our World in Data — Share of population by religion
        (based on Pew Research Center Global Religious Futures 2015)

Expected CSV columns:
    Entity, Code, Year,
    Buddhism, Christianity, Folk Religions,
    Hinduism, Islam, Judaism,
    Other Religions, Unaffiliated

Values are percentages (0–100). Years available: 2010, 2050.

Save the CSV to:
    data/raw/owid/owid_religion_by_country.csv
"""

import os
import sys
import pandas as pd
import psycopg2

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "raw", "owid", "owid_religion_by_country.csv"
)

conn = psycopg2.connect(
    dbname=os.environ.get("PGDATABASE", "god_metric"),
    user=os.environ.get("PGUSER", "postgres"),
    password=os.environ.get("PGPASSWORD", ""),
    host=os.environ.get("PGHOST", "localhost"),
    port=os.environ.get("PGPORT", "5432"),
)
cur = conn.cursor()

SOURCE = "owid_multi_religion"

# ── Religion name mapping ──────────────────────────────────────────────────────
# Maps CSV column names → canonical religion names in dim_religion
RELIGION_MAP = {
    "Christians":  "Christianity",
    "Jews":        "Judaism",
    "Muslims":     "Islam",
    "Hindus":      "Hinduism",
    "Buddhists":   "Buddhism",
    "Other":       "Other Religions",
    "No religion": "Unaffiliated",
}

def get_or_create_religion(name):
    cur.execute("SELECT religion_id FROM dim_religion WHERE religion_name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO dim_religion (religion_name) VALUES (%s) RETURNING religion_id",
        (name,)
    )
    rid = cur.fetchone()[0]
    print(f"  CREATED dim_religion: {name}")
    return rid

def get_or_create_country(name, iso3):
    cur.execute("SELECT country_id FROM dim_country WHERE iso3 = %s", (iso3,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO dim_country (country_name, iso3, region) VALUES (%s, %s, %s) RETURNING country_id",
        (name, iso3, None)
    )
    cid = cur.fetchone()[0]
    print(f"  CREATED dim_country: {name} ({iso3})")
    return cid

def get_or_create_year(year):
    cur.execute("SELECT year_id FROM dim_year WHERE year = %s", (year,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO dim_year (year, is_projection) VALUES (%s, %s) RETURNING year_id",
        (year, year >= 2020)
    )
    return cur.fetchone()[0]

def main():
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: File not found at {DATA_PATH}")
        print("Download from: https://ourworldindata.org/grapher/share-of-population-by-religion")
        print("Save as: data/raw/owid/owid_religion_by_country.csv")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Detect actual religion columns present in the file
    religion_cols = [c for c in df.columns if c in RELIGION_MAP]
    if not religion_cols:
        print(f"ERROR: No recognised religion columns found. Got: {list(df.columns)}")
        sys.exit(1)
    print(f"Religion columns found: {religion_cols}")

    # Standardise column names (OWID sometimes uses different capitalisations)
    country_col = next((c for c in df.columns if c.lower() == 'entity'), None)
    code_col    = next((c for c in df.columns if c.lower() == 'code'), None)
    year_col    = next((c for c in df.columns if c.lower() == 'year'), None)

    if not all([country_col, code_col, year_col]):
        print(f"ERROR: Expected Entity, Code, Year columns. Got: {list(df.columns)}")
        sys.exit(1)

    # Pre-cache religion IDs
    religion_ids = {col: get_or_create_religion(RELIGION_MAP[col]) for col in religion_cols}

    # Filter to valid country rows (iso3 = 3 letters, not aggregates)
    df = df[df[code_col].notna() & (df[code_col].str.len() == 3)].copy()
    df = df[df[year_col].isin([2010, 2050])]
    print(f"Rows after filtering to countries + years 2010/2050: {len(df)}")

    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        country_name = str(row[country_col]).strip()
        iso3         = str(row[code_col]).strip().upper()
        year         = int(row[year_col])

        country_id = get_or_create_country(country_name, iso3)
        year_id    = get_or_create_year(year)
        is_proj    = year >= 2020

        for col in religion_cols:
            pct = row[col]
            if pd.isna(pct):
                continue

            religion_id = religion_ids[col]

            # Skip if already loaded from this source
            cur.execute("""
                SELECT COUNT(*) FROM fact_religious_population
                WHERE country_id = %s AND religion_id = %s AND year_id = %s AND source = %s
            """, (country_id, religion_id, year_id, SOURCE))
            if cur.fetchone()[0] > 0:
                skipped += 1
                continue

            # OWID gives %, not raw count — store pct only; affiliated_count = NULL
            cur.execute("""
                INSERT INTO fact_religious_population
                    (country_id, religion_id, year_id, affiliated_count,
                     affiliated_pct_country, source, is_projection)
                VALUES (%s, %s, %s, NULL, %s, %s, %s)
            """, (country_id, religion_id, year_id, float(pct), SOURCE, is_proj))
            inserted += 1

    conn.commit()
    print(f"\nDone: {inserted} inserted, {skipped} skipped")

    # Quick check
    print("\n── Sample: dominant religion by country (2010) ──────────────────")
    cur.execute("""
        SELECT dc.country_name, dc.iso3, dr.religion_name, frp.affiliated_pct_country
        FROM fact_religious_population frp
        JOIN dim_country  dc ON frp.country_id  = dc.country_id
        JOIN dim_religion dr ON frp.religion_id = dr.religion_id
        JOIN dim_year     dy ON frp.year_id     = dy.year_id
        WHERE frp.source = %s
          AND dy.year = 2010
          AND frp.affiliated_pct_country = (
              SELECT MAX(frp2.affiliated_pct_country)
              FROM fact_religious_population frp2
              JOIN dim_year dy2 ON frp2.year_id = dy2.year_id
              WHERE frp2.country_id = frp.country_id
                AND frp2.source = %s
                AND dy2.year = 2010
          )
        ORDER BY dc.country_name
        LIMIT 20
    """, (SOURCE, SOURCE))
    for r in cur.fetchall():
        print(f"  {r[1]}  {r[0]:<35} {r[2]:<20} {r[3]:.1f}%")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
