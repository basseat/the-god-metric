"""
ETL: World Values Survey — Religiosity Intensity
=================================================
Processes WVS cross-national data (Waves 1–7) and loads into
fact_wvs_religiosity.

DATA DOWNLOAD (manual — registration required):
-----------------------------------------------
1. Go to: https://www.worldvaluessurvey.org/WVSContents.jsp
2. Click "Data & Documentation"
3. Download the "WVS Time-Series (1981–2022)" aggregate file
   → Choose CSV or SPSS format
   → Save as: god_metric/data/raw/WVS_TimeSeries_1981_2022_csv_v4_0.csv
      (or whatever the current version filename is)

Alternatively, download individual waves:
   Wave 7 (2017–2022): WVS_Cross-National_Wave_7_csv_v5_0.csv
   Save all in: god_metric/data/raw/wvs/

The relevant WVS variable codes:
   Q6   — How important is God in your life (1–10)
   Q173 — How important is religion in your life
   Q6A  — Religious person (1=religious, 2=not religious, 3=convinced atheist)
   Q185 — How often do you attend religious services
   A006 — Importance of religion (older wave variable)

USAGE:
------
  python3 etl/04_load_wvs.py

REQUIREMENTS:
-------------
  pip install psycopg2-binary pandas
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

# ── WVS Variable mappings across waves ────────────────────────────────────────
# The WVS renaming is notoriously inconsistent across waves. These are the
# primary variable codes. The script tries them in order.

VAR_IMPORTANCE_RELIGION = ["Q173", "A006", "V9"]   # Importance of religion (1=very, 4=not at all)
VAR_RELIGIOUS_PERSON    = ["Q6A",  "F034", "V185"] # 1=religious, 2=not religious, 3=atheist
VAR_ATTEND_SERVICES     = ["Q171", "F028", "V186"] # Church attendance frequency
VAR_COUNTRY             = ["B_COUNTRY_ALPHA", "S003", "COUNTRY_ALPHA"]
VAR_YEAR                = ["A_YEAR", "S020", "YEAR"]
VAR_WAVE                = ["A_WAVE", "S002VS", "WAVE"]
VAR_WEIGHT              = ["W_WEIGHT", "S017", "WEIGHT_W"]

# Attendance codes → weekly/monthly buckets (WVS codes vary by wave)
ATTEND_WEEKLY_CODES  = {1}    # "More than once a week" or "weekly"
ATTEND_MONTHLY_CODES = {1, 2} # weekly + monthly
# Note: exact codes differ per wave; script normalises where possible

# Importance of religion codes → pct buckets
# Q173/A006: 1=Very important, 2=Rather important, 3=Not very important, 4=Not at all important
IMP_VERY_IMPORTANT   = {1}
IMP_RATHER_IMPORTANT = {2}
IMP_NOT_VERY         = {3}
IMP_NOT_AT_ALL       = {4}

# Religious person codes
# Q6A: 1=A religious person, 2=Not a religious person, 3=A convinced atheist
SELF_RELIGIOUS_CODE = {1}
ATHEIST_CODE        = {3}


# ── WVS country code to ISO3 mapping (partial — expand as needed) ─────────────
WVS_COUNTRY_TO_ISO3 = {
    "AND": "AND", "ARG": "ARG", "AUS": "AUS", "AUT": "AUT", "AZE": "AZE",
    "BLR": "BLR", "BGR": "BGR", "BOL": "BOL", "BRA": "BRA", "CAN": "CAN",
    "CHL": "CHL", "CHN": "CHN", "COL": "COL", "CRI": "CRI", "CYP": "CYP",
    "CZE": "CZE", "DEU": "DEU", "ECU": "ECU", "EGY": "EGY", "EST": "EST",
    "ETH": "ETH", "FIN": "FIN", "FRA": "FRA", "GBR": "GBR", "GEO": "GEO",
    "GHA": "GHA", "GTM": "GTM", "HKG": "HKG", "HND": "HND", "HRV": "HRV",
    "HUN": "HUN", "IDN": "IDN", "IND": "IND", "IRN": "IRN", "IRQ": "IRQ",
    "ITA": "ITA", "JOR": "JOR", "JPN": "JPN", "KAZ": "KAZ", "KEN": "KEN",
    "KGZ": "KGZ", "KOR": "KOR", "LBN": "LBN", "LBY": "LBY", "LTU": "LTU",
    "LVA": "LVA", "MAR": "MAR", "MDA": "MDA", "MEX": "MEX", "MKD": "MKD",
    "MLI": "MLI", "MNG": "MNG", "MOZ": "MOZ", "MYS": "MYS", "NGA": "NGA",
    "NIC": "NIC", "NLD": "NLD", "NOR": "NOR", "NZL": "NZL", "PAK": "PAK",
    "PER": "PER", "PHL": "PHL", "POL": "POL", "PRI": "PRI", "PSE": "PSE",
    "ROM": "ROU", "ROU": "ROU", "RUS": "RUS", "RWA": "RWA", "SAU": "SAU",
    "SCG": "SRB", "SEN": "SEN", "SLV": "SLV", "SRB": "SRB", "SVK": "SVK",
    "SVN": "SVN", "SWE": "SWE", "THA": "THA", "TJK": "TJK", "TTO": "TTO",
    "TUN": "TUN", "TUR": "TUR", "TWN": "TWN", "TZA": "TZA", "UGA": "UGA",
    "UKR": "UKR", "URY": "URY", "USA": "USA", "UZB": "UZB", "VEN": "VEN",
    "VNM": "VNM", "YEM": "YEM", "ZAF": "ZAF", "ZMB": "ZMB", "ZWE": "ZWE",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info("Connected to PostgreSQL")
        return conn
    except psycopg2.OperationalError as e:
        log.error("Cannot connect: %s", e)
        sys.exit(1)


def find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """Return the first candidate column that exists in df."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def pct_in_codes(series: pd.Series, codes: set) -> float | None:
    """Return % of non-null values matching the given codes."""
    valid = series.dropna()
    valid = valid[valid > 0]   # WVS uses negative values for missing
    if len(valid) == 0:
        return None
    return round(valid.isin(codes).sum() / len(valid) * 100, 2)


def process_wvs_file(filepath: Path) -> pd.DataFrame:
    """
    Process a WVS CSV file (time-series or single wave).
    Returns aggregated DataFrame: iso3 | year | wave | pct_* columns
    """
    log.info("Reading WVS file: %s", filepath)
    df = pd.read_csv(filepath, low_memory=False, encoding="utf-8-sig")
    log.info("Raw shape: %s", df.shape)

    # Find key columns
    col_country  = find_col(df, VAR_COUNTRY)
    col_year     = find_col(df, VAR_YEAR)
    col_wave     = find_col(df, VAR_WAVE)
    col_imp_rel  = find_col(df, VAR_IMPORTANCE_RELIGION)
    col_rel_pers = find_col(df, VAR_RELIGIOUS_PERSON)
    col_attend   = find_col(df, VAR_ATTEND_SERVICES)

    if not col_country:
        log.error("Cannot find country column. Available: %s", df.columns.tolist()[:20])
        return pd.DataFrame()

    log.info("Using columns: country=%s year=%s wave=%s importance=%s person=%s attend=%s",
             col_country, col_year, col_wave, col_imp_rel, col_rel_pers, col_attend)

    records = []

    # Group by country + year (or wave)
    group_cols = [col_country]
    if col_year:   group_cols.append(col_year)
    if col_wave:   group_cols.append(col_wave)

    for keys, group in df.groupby(group_cols):
        if len(group_cols) == 3:
            country_raw, year, wave = keys
        elif len(group_cols) == 2:
            country_raw, year = keys
            wave = None
        else:
            country_raw = keys
            year, wave = None, None

        iso3 = WVS_COUNTRY_TO_ISO3.get(str(country_raw).upper())
        if not iso3:
            continue

        try:
            year = int(float(year)) if year else None
        except (ValueError, TypeError):
            year = None

        record = {
            "iso3": iso3,
            "year": year,
            "wave": int(wave) if wave else None,
        }

        if col_imp_rel:
            s = group[col_imp_rel].replace({-1: None, -2: None, -3: None, -4: None, -5: None})
            record["pct_very_important"]   = pct_in_codes(s, IMP_VERY_IMPORTANT)
            record["pct_rather_important"] = pct_in_codes(s, IMP_RATHER_IMPORTANT)
            record["pct_not_very"]         = pct_in_codes(s, IMP_NOT_VERY)
            record["pct_not_at_all"]       = pct_in_codes(s, IMP_NOT_AT_ALL)

        if col_attend:
            s = group[col_attend].replace({-1: None, -2: None, -3: None, -4: None, -5: None})
            record["pct_weekly"]  = pct_in_codes(s, ATTEND_WEEKLY_CODES)
            record["pct_monthly"] = pct_in_codes(s, ATTEND_MONTHLY_CODES)

        if col_rel_pers:
            s = group[col_rel_pers].replace({-1: None, -2: None, -3: None, -4: None, -5: None})
            record["pct_self_religious"] = pct_in_codes(s, SELF_RELIGIOUS_CODE)
            record["pct_atheist"]        = pct_in_codes(s, ATHEIST_CODE)

        record["sample_size"] = len(group)
        records.append(record)

    df_agg = pd.DataFrame(records)
    log.info("Processed %d country-year records from WVS", len(df_agg))
    return df_agg


def load_wvs_data(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        cur.execute("SELECT iso3, country_id FROM dim_country")
        country_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT year, year_id FROM dim_year")
        year_map = {r[0]: r[1] for r in cur.fetchall()}

    def ensure_year(year):
        if year in year_map:
            return year_map[year]
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dim_year (year) VALUES (%s) ON CONFLICT (year) DO NOTHING", (year,)
            )
            conn.commit()
            cur.execute("SELECT year_id FROM dim_year WHERE year = %s", (year,))
            yid = cur.fetchone()[0]
        year_map[year] = yid
        return yid

    rows = []
    skipped = 0

    for _, row in df.iterrows():
        iso3 = row.get("iso3")
        year = row.get("year")

        if iso3 not in country_map or not year:
            skipped += 1
            continue

        rows.append((
            country_map[iso3],
            ensure_year(int(year)),
            row.get("wave") or 0,
            row.get("pct_very_important"),
            row.get("pct_rather_important"),
            row.get("pct_not_very"),
            row.get("pct_not_at_all"),
            row.get("pct_weekly"),
            row.get("pct_monthly"),
            row.get("pct_self_religious"),
            row.get("pct_atheist"),
            row.get("sample_size"),
        ))

    if rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO fact_wvs_religiosity
                    (country_id, year_id, wave,
                     pct_religion_very_important, pct_religion_rather_important,
                     pct_religion_not_very, pct_religion_not_at_all,
                     pct_attend_weekly, pct_attend_monthly,
                     pct_self_religious, pct_convinced_atheist,
                     sample_size)
                VALUES %s
                ON CONFLICT (country_id, year_id, wave) DO UPDATE SET
                    pct_religion_very_important    = COALESCE(EXCLUDED.pct_religion_very_important, fact_wvs_religiosity.pct_religion_very_important),
                    pct_attend_weekly              = COALESCE(EXCLUDED.pct_attend_weekly, fact_wvs_religiosity.pct_attend_weekly),
                    pct_self_religious             = COALESCE(EXCLUDED.pct_self_religious, fact_wvs_religiosity.pct_self_religious),
                    pct_convinced_atheist          = COALESCE(EXCLUDED.pct_convinced_atheist, fact_wvs_religiosity.pct_convinced_atheist),
                    loaded_at                      = NOW()
                """,
                rows,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
        conn.commit()
        log.info("Loaded %d WVS rows (skipped %d)", len(rows), skipped)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_connection()

    # Find WVS files
    wvs_files = list(RAW_DIR.glob("WVS*.csv")) + list((RAW_DIR / "wvs").glob("*.csv"))

    if not wvs_files:
        log.warning(
            "No WVS files found.\n"
            "  → Download from: https://www.worldvaluessurvey.org/WVSContents.jsp\n"
            "  → Place CSV file in: %s\n"
            "  → File should start with 'WVS'",
            RAW_DIR
        )
        conn.close()
        return

    for filepath in sorted(wvs_files):
        log.info("Processing: %s", filepath.name)
        try:
            df = process_wvs_file(filepath)
            if not df.empty:
                load_wvs_data(conn, df)
        except Exception as e:
            log.error("Failed to process %s: %s", filepath.name, e)
            continue

    # Spot check
    with conn.cursor() as cur:
        cur.execute("""
            SELECT dc.region, dy.year, fw.wave,
                   fw.pct_religion_very_important,
                   fw.pct_attend_weekly,
                   fw.pct_convinced_atheist
            FROM fact_wvs_religiosity fw
            JOIN dim_country dc ON fw.country_id = dc.country_id
            JOIN dim_year    dy ON fw.year_id    = dy.year_id
            ORDER BY dy.year DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            log.info("Sample WVS records:")
            for r in rows:
                log.info("  %-30s %d (wave %s) | very_imp=%s weekly=%s atheist=%s",
                         r[0], r[1], r[2],
                         f"{r[3]:.1f}%" if r[3] else "-",
                         f"{r[4]:.1f}%" if r[4] else "-",
                         f"{r[5]:.1f}%" if r[5] else "-")

    conn.close()
    log.info("Done. ✓")


if __name__ == "__main__":
    main()
