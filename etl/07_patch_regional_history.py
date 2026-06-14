"""
Patch: Add missing 1910 and 1970 regional Christian population data
for North America, Latin America & Caribbean, Asia-Pacific, and
Middle East & North Africa.

Source: Pew Research Center — The Future of World Religions (2015)
        Global Christianity report (2011)
"""
import os
import psycopg2

conn = psycopg2.connect(
    dbname=os.environ.get("PGDATABASE", "god_metric"),
    user=os.environ.get("PGUSER", "postgres"),
    password=os.environ.get("PGPASSWORD", ""),
    host=os.environ.get("PGHOST", "localhost"),
    port=os.environ.get("PGPORT", "5432"),
)
cur = conn.cursor()

# ── Pew regional Christian population data (millions → raw count) ─────────────
# Source: Pew 2015 Future of World Religions + Global Christianity 2011
# Figures in millions of people

REGIONAL_DATA = [
    # (country_name_exact, iso3, year, christians_millions, pct_of_region)
    # North America — already has 1910, only 1970 needed
    ("North America",    "NAM", 1970, 225.0,  88.0),
    # Latin America — exists in dim_country as "Latin America" (LAM)
    ("Latin America",    "LAM", 1970, 264.0,  92.0),
    # Asia-Pacific — needs to be created in dim_country
    ("Asia-Pacific",     "ASP", 1910,  28.0,   2.0),
    ("Asia-Pacific",     "ASP", 1970, 100.0,   3.0),
    # Middle East-North Africa — needs to be created in dim_country
    ("Middle East-North Africa", "MEN", 1910,   4.0,   4.0),
    ("Middle East-North Africa", "MEN", 1970,  15.0,   4.0),
]

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

def get_religion_id(name="Christianity"):
    cur.execute("SELECT religion_id FROM dim_religion WHERE religion_name = %s", (name,))
    row = cur.fetchone()
    return row[0] if row else None

def get_or_create_country(country_name, iso3):
    cur.execute("SELECT country_id FROM dim_country WHERE country_name = %s", (country_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    # Create missing regional entry
    cur.execute(
        "INSERT INTO dim_country (country_name, iso3, region) VALUES (%s, %s, %s) RETURNING country_id",
        (country_name, iso3, country_name)
    )
    print(f"  CREATED dim_country entry: {country_name} ({iso3})")
    return cur.fetchone()[0]

def main():
    religion_id = get_religion_id("Christianity")
    if not religion_id:
        print("ERROR: Christianity not found in dim_religion")
        return

    inserted = 0
    skipped = 0

    for (country_name, iso3, year, christians_M, pct) in REGIONAL_DATA:
        country_id = get_or_create_country(country_name, iso3)

        year_id = get_or_create_year(year)

        # Check if already exists
        cur.execute("""
            SELECT COUNT(*) FROM fact_religious_population
            WHERE country_id = %s AND religion_id = %s AND year_id = %s
              AND source = 'pew_key_figures'
        """, (country_id, religion_id, year_id))
        if cur.fetchone()[0] > 0:
            print(f"  SKIP (exists) — {country_name} {year}")
            skipped += 1
            continue

        count = int(christians_M * 1_000_000)
        cur.execute("""
            INSERT INTO fact_religious_population
                (country_id, religion_id, year_id, affiliated_count,
                 affiliated_pct_country, source, is_projection)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (country_id, religion_id, year_id, count, pct,
              'pew_key_figures', False))
        print(f"  INSERTED — {country_name} {year}: {christians_M}M Christians")
        inserted += 1

    conn.commit()
    print(f"\nDone: {inserted} inserted, {skipped} skipped")

    # Quick check
    print("\n── Regional Christianity 1910 & 1970 ──────────────────────────────")
    cur.execute("""
        SELECT dc.country_name, dy.year,
               ROUND(frp.affiliated_count::NUMERIC/1e6, 0) AS christians_M
        FROM fact_religious_population frp
        JOIN dim_country  dc ON frp.country_id  = dc.country_id
        JOIN dim_religion dr ON frp.religion_id = dr.religion_id
        JOIN dim_year     dy ON frp.year_id     = dy.year_id
        WHERE dr.religion_name = 'Christianity'
          AND frp.source = 'pew_key_figures'
          AND dy.year IN (1910, 1970)
          AND dc.iso3 != 'WLD'
        ORDER BY dy.year, christians_M DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[1]}  {row[0]:<35} {row[2]}M")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
