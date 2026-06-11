# The God Metric

**Everyone says religion is dying. Most of the world didn't get that memo.**

The secularisation thesis — the idea that as societies modernise, religion fades — is one of the most widely repeated frameworks in social science and media. It shows up in think pieces, policy debates, and demographic forecasts. It is also, when you look at the data globally, a description of a fairly specific set of countries mostly located in Western Europe.

That gap between the story and the data is what this project is about.

**[→ View the Tableau dashboard on Tableau Public](#)** *(link to be added)*

---

## What the data actually shows

Three hypotheses. Three verdicts.

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | As countries modernise, religious affiliation declines | **Partially supported — but only in specific regions** |
| H2 | Christianity is a predominantly European religion | **Does not survive the data** |
| H3 | Access to modern media and the internet accelerates secularisation | **Complicated — the opposite may be true in the Global South** |

### H1 — Secularisation is real, but local

Across 199 countries (OWID/Pew, 2010 vs 2020), the global average share of the population affiliated with any religion sits above 80% and is stable. Decline is real — but concentrated in Western Europe, parts of East Asia, Australia, and Canada. The majority of the world, by both country count and population, is holding steady or growing more religious.

The secularisation thesis holds in the places where most of its proponents live and write. Applied to the whole planet, it doesn't hold.

*Caveat: self-reported religious affiliation is a blunt instrument. Intensity of belief and practice are harder to measure and may diverge from affiliation trends.*

### H2 — The centre of Christianity has moved

This is the finding that surprised me most when the data came together.

In 1910, roughly 72% of the world's Christians lived in Europe. By 2010, Sub-Saharan Africa had already overtaken Europe in absolute Christian population. By 2050, Africa is projected to hold approximately 40% of all Christians on Earth — while Europe holds under 20%.

| Year | Africa | Europe | Who leads |
|------|--------|--------|-----------|
| 1910 | ~9M | ~400M | Europe |
| 1970 | ~143M | ~479M | Europe |
| 2010 | **~434M** | ~392M | **Africa** ← crossover |
| 2050 | **~1.15B** (projected) | ~201M | **Africa** |

The crossover already happened. The picture most people carry — Christianity as a Western or European religion — is describing a world that no longer exists by the data's own accounting.

### H3 — Media and religion in the Global South

The intuitive assumption is that more media access means more exposure to secular worldviews and therefore less religiosity. The data in Sub-Saharan Africa doesn't obviously support that.

Nigeria went from near-zero mobile penetration in 1999 to over 70 subscriptions per 100 people by 2010. Over that same decade, Pentecostal and Evangelical Christianity expanded significantly across the country. The same pattern — media wave followed by, or coinciding with, religious growth rather than decline — appears in Kenya, Ghana, and parts of Latin America.

This doesn't prove causation. But it complicates the assumption that media access and secularisation move together everywhere.

*Caveat: the pentecostal growth data is incomplete. H3 is the weakest of the three findings and needs richer denominational data to strengthen.*

---

## Why this matters

The secularisation narrative has real consequences — it shapes how media covers religion, how policymakers think about demographic change, and how institutions forecast the future. When that narrative is built primarily on Western European data and then applied globally, it misrepresents what is actually happening in the places where most of the world's population lives.

A more accurate framing: religion is not declining. It is moving. The geography of faith is shifting south and east, and the numbers involved are large enough that missing this shift is a significant analytical error.

---

## Data sources

| Source | What's captured |
|---|---|
| Pew Research Center — *Global Religious Futures* (2015) | Religious affiliation by region and country, 1910–2050 projections |
| Our World in Data / Pew (2025) | Aggregate % religious by country, 199 countries, 2010 and 2020 |
| World Bank Development Indicators API | Radio, TV, mobile, and internet penetration by country, 1960–2023 |
| World Values Survey — Time-Series (Waves 1–7, 1981–2022) | Religiosity intensity: importance of religion, attendance, self-identified atheism |

---

## Project structure

```
god_metric/
├── README.md
├── setup/
│   └── 01_create_schema.sql        ← PostgreSQL star schema (run first)
├── etl/
│   ├── 02_load_pew.py              ← Pew regional seed data
│   ├── 03_load_worldbank.py        ← World Bank media penetration (API)
│   ├── 04_load_wvs.py              ← World Values Survey (manual download)
│   ├── 05_load_owid_religion.py    ← OWID aggregate religiosity (API)
│   └── 06_seed_country_religion.py ← Country-level Pew data for Tableau maps
├── queries/
│   └── EDA/
│       ├── 00_religion_trends_over_time.sql ← All religions, full timeline
│       ├── 01_H1_secularisation_test.sql
│       ├── 02_H2_christianity_migration.sql
│       ├── 03_H3_media_religion.sql
│       └── 04_tableau_ready_queries.sql     ← Custom SQL for Tableau
├── validate/
│   └── 05_validate.sql
└── data/
    └── raw/                        ← Source files (gitignored)
        ├── owid/
        ├── worldbank/
        └── wvs/
```

---

## Running the project

**Requirements:** PostgreSQL 18, Python 3.9+

```bash
pip install psycopg2-binary pandas requests openpyxl pyarrow
```

**Set environment variables:**
```bash
export PGDATABASE=god_metric
export PGUSER=postgres
export PGPASSWORD=your_password
export PGHOST=localhost
export PGPORT=5432
```

**Run the ETL in order:**
```bash
psql -U postgres -d god_metric -f setup/01_create_schema.sql
python3 etl/02_load_pew.py
python3 etl/03_load_worldbank.py
python3 etl/05_load_owid_religion.py
python3 etl/06_seed_country_religion.py
python3 etl/04_load_wvs.py          # requires manual WVS download (see below)
```

**World Values Survey** (registration required):
1. Go to [worldvaluessurvey.org](https://www.worldvaluessurvey.org/WVSContents.jsp)
2. Download *WVS Time-Series (1981–2022)* as CSV
3. Save to `data/raw/WVS_TimeSeries_1981_2022_csv_v4_0.csv`

Then load any of the queries in `queries/EDA/04_tableau_ready_queries.sql` as Custom SQL in Tableau (connect to `localhost:5432 / god_metric`).

---

## Limitations

- **Affiliation vs belief** — religious self-identification is not the same as active practice or theological conviction. Someone who ticks "Christian" on a census and someone who attends church weekly are counted the same way here.
- **Projection uncertainty** — the 2050 Pew figures are demographic projections based on fertility and migration models, not forecasts. They assume no major shifts in conversion patterns.
- **H3 is underspecified** — media penetration and Christianity growth are correlated in the data, but the causal mechanism is unclear, and pentecostal/evangelical sub-data is not comprehensive enough to make a strong claim.
- **Country coverage gaps** — the country-level religion data covers ~85 countries. Regions with sparse data (Central Asia, Pacific Island states) are underrepresented in map visualisations.

---

## Related research

- Pew Research Center — *The Future of World Religions: Population Growth Projections 2010–2050* (2015)
- Philip Jenkins — *The Next Christendom* (2002)
- Pippa Norris & Ronald Inglehart — *Sacred and Secular: Religion and Politics Worldwide* (2004)
- World Values Survey — [worldvaluessurvey.org](https://www.worldvaluessurvey.org)
- Our World in Data — *Religion* topic page

---

*Basit Ayoade · Data Analytics Portfolio · 2026*
