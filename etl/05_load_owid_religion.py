"""
ETL: Our World in Data — Country-Level Religious Affiliation
============================================================
Downloads country-level religion share data (sourced from Pew) via the
Our World in Data API and loads into fact_religious_population.

This gives us the country-level granularity needed for Tableau map charts.

No manual download needed — fetches directly.

USAGE:
------
  python3 etl/05_load_owid_religion.py

REQUIREMENTS:
-------------
  pip install psycopg2-binary pandas requests
"""

import os
import sys
import logging
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from io import StringIO

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

CACHE_DIR = Path(__file__).parent.parent / "data" / "raw" / "owid"

# OWID religion share CSV — country × year × % religious (any religion)
# Source: Pew Research Center (2025) via OWID
# Chart slug: religious-composition  (confirmed from OWID Data API tab)
OWID_RELIGION_URL = (
    "https://ourworldindata.org/grapher/religious-composition.csv"
    "?v=1&csvType=full&useColumnShortNames=true&religion=any_religion&indicator=share"
)

# Per-religion breakdown URLs (Christianity, Islam, etc.)
OWID_PER_RELIGION_URLS = {
    "Christianity": (
        "https://ourworldindata.org/grapher/religious-composition.csv"
        "?v=1&csvType=full&useColumnShortNames=true&religion=christianity&indicator=share"
    ),
    "Islam": (
        "https://ourworldindata.org/grapher/religious-composition.csv"
        "?v=1&csvType=full&useColumnShortNames=true&religion=islam&indicator=share"
    ),
    "Hinduism": (
        "https://ourworldindata.org/grapher/religious-composition.csv"
        "?v=1&csvType=full&useColumnShortNames=true&religion=hinduism&indicator=share"
    ),
    "Buddhism": (
        "https://ourworldindata.org/grapher/religious-composition.csv"
        "?v=1&csvType=full&useColumnShortNames=true&religion=buddhism&indicator=share"
    ),
    "Unaffiliated": (
        "https://ourworldindata.org/grapher/religious-composition.csv"
        "?v=1&csvType=full&useColumnShortNames=true&religion=unaffiliated&indicator=share"
    ),
}

# OWID total population (for computing absolute counts from shares)
OWID_POPULATION_URL = (
    "https://ourworldindata.org/grapher/population.csv"
    "?v=1&csvType=full&useColumnShortNames=false"
)

# Map OWID column names → our dim_religion names
RELIGION_COL_MAP = {
    "Christians (% of population)":              "Christianity",
    "Muslims (% of population)":                 "Islam",
    "Hindus (% of population)":                  "Hinduism",
    "Buddhists (% of population)":               "Buddhism",
    "Folk religionists (% of population)":       "Folk/Indigenous",
    "Jews (% of population)":                    "Judaism",
    "Other religions (% of population)":         "Other Religion",
    "Unaffiliated (% of population)":            "Unaffiliated",
    # Alternate column name formats
    "Share of population that are Christians":   "Christianity",
    "Share of population that are Muslims":      "Islam",
    "Share of population that are Hindus":       "Hinduism",
    "Share of population that are Buddhists":    "Buddhism",
    "Share of population that are folk religionists": "Folk/Indigenous",
    "Share of population that are Jewish":       "Judaism",
    "Share of population with other religions":  "Other Religion",
    "Share of population unaffiliated":          "Unaffiliated",
    # Short name variants
    "Christians":    "Christianity",
    "Muslims":       "Islam",
    "Hindus":        "Hinduism",
    "Buddhists":     "Buddhism",
    "Folk Religions": "Folk/Indigenous",
    "Jews":          "Judaism",
    "Other Religions": "Other Religion",
    "Unaffiliated":  "Unaffiliated",
}

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


def download_csv(url: str, cache_path: Path, label: str) -> pd.DataFrame:
    if cache_path.exists():
        log.info("Loading %s from cache", label)
        return pd.read_csv(cache_path)

    log.info("Downloading %s …", label)
    resp = requests.get(url, timeout=60)
    if resp.status_code != 200:
        log.error("HTTP %d fetching %s", resp.status_code, url)
        return pd.DataFrame()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(resp.content)
    log.info("Saved to %s (%d bytes)", cache_path, len(resp.content))
    return pd.read_csv(StringIO(resp.text))


def build_lookups(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT religion_name, religion_id FROM dim_religion")
        religion_map = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT year, year_id FROM dim_year")
        year_map = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT iso3, iso2, country_id, country_name FROM dim_country")
        rows = cur.fetchall()
        iso3_map  = {r[0]: r[2] for r in rows}
        iso2_map  = {r[1]: r[2] for r in rows if r[1]}
        name_map  = {r[3].lower(): r[2] for r in rows}

    return religion_map, year_map, iso3_map, iso2_map, name_map


def ensure_year(conn, year: int, year_map: dict) -> int:
    if year in year_map:
        return year_map[year]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO dim_year (year, is_projection) VALUES (%s, %s) "
            "ON CONFLICT (year) DO NOTHING",
            (year, year in PROJECTION_YEARS)
        )
        conn.commit()
        cur.execute("SELECT year_id FROM dim_year WHERE year = %s", (year,))
        yid = cur.fetchone()[0]
    year_map[year] = yid
    return yid


def ensure_country(conn, iso3: str, name: str, iso2: str = None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_country (iso3, iso2, country_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (iso3) DO NOTHING
            RETURNING country_id
            """,
            (iso3, iso2 or None, name)
        )
        row = cur.fetchone()
        if row:
            conn.commit()
            return row[0]
        cur.execute("SELECT country_id FROM dim_country WHERE iso3 = %s", (iso3,))
        return cur.fetchone()[0]


# ── Main processing ───────────────────────────────────────────────────────────

def process_owid(df_religion: pd.DataFrame, df_pop: pd.DataFrame,
                 conn, religion_map, year_map, iso3_map, iso2_map, name_map):
    """
    Merge religion shares with population to get absolute counts,
    then load into fact_religious_population.
    """
    log.info("Religion columns: %s", df_religion.columns.tolist()[:8])
    log.info("Religion shape: %s", df_religion.shape)

    # Identify country/year/code columns
    entity_col = next((c for c in df_religion.columns
                       if c.lower() in ("entity", "country", "location")), None)
    year_col   = next((c for c in df_religion.columns
                       if c.lower() in ("year", "time")), None)
    code_col   = next((c for c in df_religion.columns
                       if c.lower() in ("code", "iso_code", "countrycode")), None)

    if not entity_col or not year_col:
        log.error("Cannot identify entity/year columns in OWID data")
        return

    log.info("Using: entity=%s, year=%s, code=%s", entity_col, year_col, code_col)

    # Build population lookup: (entity, year) → total_pop
    pop_lookup = {}
    if not df_pop.empty:
        pop_entity = next((c for c in df_pop.columns
                           if c.lower() in ("entity", "country", "location")), None)
        pop_year   = next((c for c in df_pop.columns
                           if c.lower() in ("year", "time")), None)
        pop_val    = next((c for c in df_pop.columns
                           if "population" in c.lower() and c.lower() not in
                           ("entity", "country", "location")), None)
        if pop_entity and pop_year and pop_val:
            for _, row in df_pop.iterrows():
                key = (str(row[pop_entity]).strip(), int(row[pop_year]))
                try:
                    pop_lookup[key] = int(float(row[pop_val]))
                except (ValueError, TypeError):
                    pass
            log.info("Population lookup built: %d entries", len(pop_lookup))

    # Identify religion columns
    religion_cols = {}
    for col in df_religion.columns:
        for pattern, rel_name in RELIGION_COL_MAP.items():
            if pattern.lower() in col.lower() or col.lower() in pattern.lower():
                religion_cols[col] = rel_name
                break

    if not religion_cols:
        log.error("No religion columns found. Available: %s", df_religion.columns.tolist())
        return

    log.info("Found religion columns: %s", list(religion_cols.values()))

    rows_to_insert = []
    skipped = 0

    for _, row in df_religion.iterrows():
        entity  = str(row[entity_col]).strip()
        year_raw = row[year_col]
        code    = str(row[code_col]).strip().upper() if code_col else ""

        try:
            year = int(float(year_raw))
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Skip OWID aggregate rows (they have no ISO code or special codes)
        if not code or len(code) > 3 or code in ("OWID_WRL", ""):
            skipped += 1
            continue

        # Resolve country_id
        country_id = iso3_map.get(code) or iso2_map.get(code) or name_map.get(entity.lower())
        if not country_id:
            # Try to add the country if we have a valid 3-letter code
            if len(code) == 3 and code.isalpha():
                country_id = ensure_country(conn, code, entity)
                iso3_map[code] = country_id
            else:
                skipped += 1
                continue

        year_id = ensure_year(conn, year, year_map)

        # Get total population for this country/year
        total_pop = pop_lookup.get((entity, year))

        # One row per religion
        for col, rel_name in religion_cols.items():
            pct = row.get(col)
            if pd.isna(pct):
                continue
            try:
                pct_val = float(pct)
            except (ValueError, TypeError):
                continue

            religion_id = religion_map.get(rel_name)
            if not religion_id:
                continue

            # Compute absolute count from share if we have population
            abs_count = None
            if total_pop and pct_val:
                abs_count = int(total_pop * pct_val / 100)

            rows_to_insert.append((
                country_id,
                religion_id,
                year_id,
                abs_count,
                round(pct_val, 3),
                total_pop,
                "owid_pew",
                year in PROJECTION_YEARS,
            ))

    if rows_to_insert:
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
                    country_total_pop      = COALESCE(EXCLUDED.country_total_pop, fact_religious_population.country_total_pop),
                    loaded_at              = NOW()
                """,
                rows_to_insert,
            )
        conn.commit()
        log.info("Loaded %d rows (skipped %d) into fact_religious_population",
                 len(rows_to_insert), skipped)
    else:
        log.warning("No rows to insert (skipped %d)", skipped)


# ── Main ──────────────────────────────────────────────────────────────────────

def fetch_per_religion_wide(cache_dir: Path) -> pd.DataFrame:
    """
    Fetch per-religion share from OWID (Christianity, Islam, etc.) and merge
    into a wide DataFrame: entity | code | year | Christianity | Islam | ...
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "owid_per_religion_wide.csv"
    if cache_file.exists():
        log.info("Loading per-religion wide data from cache")
        return pd.read_csv(cache_file)

    frames = []
    for rel_name, url in OWID_PER_RELIGION_URLS.items():
        log.info("Fetching %s shares from OWID …", rel_name)
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            log.warning("HTTP %d fetching %s — skipping", resp.status_code, rel_name)
            continue
        df = pd.read_csv(StringIO(resp.text))
        log.info("  Got %d rows for %s, columns: %s", len(df), rel_name, df.columns.tolist()[:6])

        # Identify share column (non-standard names per religion)
        entity_col = next((c for c in df.columns if c.lower() in ("entity", "country", "location")), None)
        year_col   = next((c for c in df.columns if c.lower() in ("year", "time")), None)
        code_col   = next((c for c in df.columns if c.lower() in ("code", "iso_code", "countrycode")), None)
        # Share column is whatever's left after entity/year/code
        skip_cols  = {entity_col, year_col, code_col}
        share_cols = [c for c in df.columns if c not in skip_cols and c]
        if not share_cols:
            log.warning("No share column found for %s", rel_name)
            continue

        share_col = share_cols[0]
        df = df[[entity_col, code_col, year_col, share_col]].copy()
        df.columns = ["entity", "code", "year", rel_name]
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    # Merge all religions on entity+code+year
    df_wide = frames[0]
    for df_next in frames[1:]:
        df_wide = df_wide.merge(df_next, on=["entity", "code", "year"], how="outer")

    df_wide.to_csv(cache_file, index=False)
    log.info("Per-religion wide table: %d rows, %d columns", len(df_wide), len(df_wide.columns))
    return df_wide


def main():
    conn = get_connection()
    religion_map, year_map, iso3_map, iso2_map, name_map = build_lookups(conn)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Try per-religion breakdown first (best for Tableau maps)
    df_religion = fetch_per_religion_wide(CACHE_DIR)

    # 2. Fall back to aggregate "any religion" share if per-religion failed
    if df_religion.empty:
        local_religion = CACHE_DIR / "owid_religion_shares.csv"
        if local_religion.exists():
            log.info("Reading aggregate religion shares from cache")
            df_religion = pd.read_csv(local_religion)
        else:
            log.info("Fetching aggregate religion share from OWID …")
            df_religion = download_csv(OWID_RELIGION_URL, local_religion, "OWID religion shares")

    if df_religion.empty:
        log.error(
            "Could not fetch religion data from OWID.\n"
            "  → Check your internet connection and try again.\n"
            "  → If problem persists, download manually from:\n"
            "    https://ourworldindata.org/religion\n"
            "  → Click Download → Data → Download full data\n"
            "  → Save as: data/raw/owid/owid_religion_shares.csv"
        )
        conn.close()
        sys.exit(1)

    # 3. Population — for computing absolute counts from shares
    local_pop = CACHE_DIR / "owid_population.csv"
    if local_pop.exists():
        df_pop = pd.read_csv(local_pop)
    else:
        df_pop = download_csv(OWID_POPULATION_URL, local_pop, "OWID population")
        if df_pop.empty:
            log.warning("Population data unavailable — will load % shares only (no absolute counts)")

    # 4. Process and load
    process_owid(df_religion, df_pop, conn, religion_map, year_map,
                 iso3_map, iso2_map, name_map)

    # 5. Spot check — top countries by Christian population 2010
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dc.country_name, dy.year, frp.affiliated_count, frp.affiliated_pct_country
            FROM fact_religious_population frp
            JOIN dim_country  dc ON frp.country_id  = dc.country_id
            JOIN dim_religion dr ON frp.religion_id = dr.religion_id
            JOIN dim_year     dy ON frp.year_id     = dy.year_id
            WHERE dr.religion_name = 'Christianity'
              AND dy.year = 2010
              AND frp.source = 'owid_pew'
            ORDER BY frp.affiliated_count DESC NULLS LAST
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            log.info("Top 10 Christian populations 2010 (country-level):")
            for r in rows:
                log.info("  %-30s %d  → %s (%.1f%%)",
                         r[0], r[1],
                         f"{r[2]:,}" if r[2] else "pct only",
                         r[3] or 0)

    # 6. Count total country-level rows
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(DISTINCT country_id) AS countries,
                   COUNT(*) AS total_rows
            FROM fact_religious_population
            WHERE source = 'owid_pew'
        """)
        r = cur.fetchone()
        if r:
            log.info("Total: %d countries × religion × year rows (%d unique countries)",
                     r[1], r[0])

    conn.close()
    log.info("Done. ✓")


if __name__ == "__main__":
    main()
