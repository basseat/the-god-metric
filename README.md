# The God Metric
### Against the Narrative — No. 3

> *Is religion actually declining? Or is that just a Western story?*

This is the data pipeline behind the third investigation in the **Against the Narrative** Substack series. It stress-tests the secularisation thesis — the widely-held idea that modernisation causes religion to decline — using 110+ years of global religious affiliation data.

**The short answer the data gives: the secularisation thesis is real, but local. It describes Western Europe and parts of East Asia. It does not describe the world.**

---

## The Three Hypotheses

The starting point for each investigation is the conventional claim — the narrative. The data either confirms it, complicates it, or kills it.

**H1 — "As countries modernise, religious affiliation declines"**
This is the secularisation thesis: the idea that economic development, education, and urbanisation systematically erode religion. It is the dominant framework in Western sociology and the implicit assumption behind most media coverage of religion. We test whether it holds at a global level, or whether it describes only a specific set of countries.

**H2 — "Christianity is a predominantly European religion"**
This is the assumption embedded in phrases like "Western Christianity" and "Christian Europe." Most people, if asked to place the global centre of Christianity, would point to Europe or North America. We test whether that picture is still accurate — or whether it ever was, by the time the data begins.

**H3 — "Access to modern media and the internet accelerates secularisation"**
The intuition here is common: more information, more exposure to different worldviews, less religious certainty. We test whether that relationship holds in the Global South, or whether media technology played a different role entirely in regions where religion was already the dominant social fabric.

---

## What the Data Shows

**H1** — Partially confirmed, but only in specific regions. The OWID dataset (199 countries, 2010 vs 2020) shows the global average share of the population affiliated with religion is above 80% and stable. Decline is real — but concentrated in Western Europe, parts of East Asia, and Anglophone countries. The secularisation thesis holds locally. It does not hold globally.

**H2** — Does not survive contact with the data. Africa surpassed Europe in absolute Christian population *by 2010*. In 1910, Sub-Saharan Africa held roughly 9% of the world's Christians. By 2050, that figure is projected at ~40%. Europe goes from ~72% to ~17% over the same period.

| Year | Africa (Christians) | Europe (Christians) | Who leads |
|------|--------------------|--------------------|-----------|
| 1910 | ~9M | ~400M | Europe |
| 1970 | ~143M | ~479M | Europe |
| 2010 | **~434M** | ~392M | **Africa** ← crossover |
| 2050 | **~1.15B** (projected) | ~201M | **Africa** |

**H3** — Complicated. The data does not support a simple secularisation-via-media story in the Global South. Sub-Saharan Africa's media penetration curves — radio in the 1970s, TV in the 1990s, mobile explosion from 2000–2010 — coincide with periods of rapid religious *growth*, not decline. Nigeria went from near-zero mobile penetration in 1999 to over 70 per 100 by 2010, the same decade Pentecostalism expanded dramatically across the country. The relationship between media and religion appears to run in the opposite direction to what the hypothesis assumed.

---

## Data Sources

| Source | What it covers | How it's loaded |
|--------|----------------|-----------------|
| **Pew Research Center** (2015) | Regional populations 1910–2050 by religion | Hardcoded seed — `etl/02_load_pew.py` |
| **Pew Research Center** (2015) | Country-level religion shares, 85 countries, 2010 + 2050 | Hardcoded seed — `etl/06_seed_country_religion.py` |
| **Our World in Data / Pew** (2025) | % religious by country, 199 countries, 2010 + 2020 | Auto-downloaded — `etl/05_load_owid_religion.py` |
| **World Bank** | Radio, TV, mobile, internet penetration 1960–2023 | Auto-fetched via API — `etl/03_load_worldbank.py` |
| **World Values Survey** (Waves 1–7) | Religiosity intensity, attendance, atheism rates | Manual download — `etl/04_load_wvs.py` |

---

## Project Structure

```
god_metric/
├── README.md
├── setup/
│   └── 01_create_schema.sql        ← Star schema DDL (run first)
├── etl/
│   ├── 02_load_pew.py              ← Pew regional aggregates + seed data
│   ├── 03_load_worldbank.py        ← World Bank media penetration via API
│   ├── 04_load_wvs.py              ← World Values Survey (manual download)
│   ├── 05_load_owid_religion.py    ← OWID aggregate religiosity via API
│   └── 06_seed_country_religion.py ← Country-level Pew data (Tableau maps)
├── queries/
│   └── EDA/
│       ├── 01_H1_secularisation_test.sql    ← H1 analysis
│       ├── 02_H2_christianity_migration.sql ← H2 analysis
│       ├── 03_H3_media_religion.sql         ← H3 analysis
│       └── 04_tableau_ready_queries.sql     ← Custom SQL for Tableau
├── validate/
│   └── 05_validate.sql             ← Post-ETL data quality checks
└── data/
    └── raw/                        ← Downloaded source files (gitignored)
        ├── owid/
        ├── worldbank/
        └── wvs/
```

---

## Schema

```
dim_country          ← ISO3/ISO2 codes, region, World Bank income group
dim_religion         ← Religion name, propagation model, conversion mandate
dim_year             ← 1900–2050, is_projection flag

fact_religious_population   ← H1, H2: country × religion × year → count + %
fact_wvs_religiosity        ← H1: religiosity intensity by country/wave
fact_media_penetration      ← H3: radio/TV/mobile/internet by country/year
fact_pentecostal_growth     ← H3: Pentecostal sub-breakdown (optional)

Views:
  v_global_affiliation_trend   ← H1 query-ready
  v_christianity_by_region     ← H2 query-ready
  v_media_vs_pentecostal       ← H3 query-ready
  v_wvs_intensity_by_region    ← H1 supplement
```

---

## Setup

### Requirements
- PostgreSQL 18 (tested with EDB installer on macOS — [download here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads))
- Python 3.9+

```bash
pip3 install psycopg2-binary pandas requests openpyxl pyarrow
```

### 1. Create the database

```bash
psql -U postgres -c "CREATE DATABASE god_metric;"
psql -U postgres -d god_metric -f setup/01_create_schema.sql
```

### 2. Set environment variables

```bash
export PGDATABASE=god_metric
export PGUSER=postgres
export PGPASSWORD=your_password
export PGHOST=localhost
export PGPORT=5432
```

### 3. Run the ETL in order

```bash
python3 etl/02_load_pew.py              # Pew regional seed data
python3 etl/03_load_worldbank.py        # World Bank media (auto API)
python3 etl/05_load_owid_religion.py    # OWID aggregate (auto API)
python3 etl/06_seed_country_religion.py # Country-level Pew + OWID
python3 etl/04_load_wvs.py             # WVS (after manual download)
```

### 4. World Values Survey (manual download required)

1. Go to [worldvaluessurvey.org](https://www.worldvaluessurvey.org/WVSContents.jsp)
2. Click **Data & Documentation** → **WVS Time-Series (1981–2022)**
3. Download CSV → save to `data/raw/WVS_TimeSeries_1981_2022_csv_v4_0.csv`

### 5. Validate

```bash
psql -U postgres -d god_metric -f validate/05_validate.sql
```

---

## Tableau

Connect Tableau to PostgreSQL (`localhost:5432` / database: `god_metric`) and use the queries in `queries/EDA/04_tableau_ready_queries.sql` as Custom SQL data sources. Each query is labelled with the dashboard and sheet it feeds.

**Planned dashboards:**
1. The Big Picture — global religiosity world map (H1)
2. The Great Migration — Christianity's shift from Europe to Africa (H2)
3. The Media Wave — media penetration vs religious growth in SSA (H3)
4. Religion by Religion — multi-religion world map
5. The Narrative Summary — key statistics for the article

---

## Part of the Against the Narrative Series

| No. | Title | Theme |
|-----|-------|-------|
| 1 | The Attention Paradox | Is screen time actually shortening attention spans? |
| 2 | The Green Miles Problem | Are electric vehicles actually greener? |
| **3** | **The God Metric** | **Is religion actually declining globally?** |

---

*Data journalism by Basit. Questions and feedback welcome.*
