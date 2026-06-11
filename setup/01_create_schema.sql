-- =============================================================
-- THE GOD METRIC — Star Schema
-- Against the Narrative | No. 3
-- PostgreSQL 14+
-- =============================================================

-- Drop and recreate the database (run this as superuser if needed)
-- CREATE DATABASE god_metric;
-- \c god_metric

-- =============================================================
-- DIMENSIONS
-- =============================================================

CREATE TABLE IF NOT EXISTS dim_country (
    country_id      SERIAL PRIMARY KEY,
    iso3            CHAR(3)         NOT NULL UNIQUE,   -- ISO 3166-1 alpha-3
    iso2            CHAR(2),                            -- ISO 3166-1 alpha-2
    country_name    VARCHAR(100)    NOT NULL,
    region          VARCHAR(60),    -- e.g. 'Sub-Saharan Africa', 'Western Europe'
    sub_region      VARCHAR(60),    -- e.g. 'West Africa', 'Northern Europe'
    wb_income_group VARCHAR(30),    -- World Bank: Low, Lower-middle, Upper-middle, High
    created_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE dim_country IS
    'Country dimension. ISO codes are the join key to World Bank and Pew data.';

-- ------------------------------------

CREATE TABLE IF NOT EXISTS dim_religion (
    religion_id         SERIAL PRIMARY KEY,
    religion_name       VARCHAR(60)  NOT NULL UNIQUE,  -- e.g. 'Christianity', 'Islam'
    religion_family     VARCHAR(40),                   -- 'Abrahamic', 'Dharmic', 'Indigenous', 'Unaffiliated'
    propagation_model   VARCHAR(40),                   -- 'Universalising', 'Ethnic', 'Syncretic', 'None'
    has_conversion_mandate BOOLEAN DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE dim_religion IS
    'Religion dimension. propagation_model is core to H1 framework: how does each religion travel?';

-- ------------------------------------

CREATE TABLE IF NOT EXISTS dim_year (
    year_id     SERIAL PRIMARY KEY,
    year        SMALLINT    NOT NULL UNIQUE,
    decade      SMALLINT    GENERATED ALWAYS AS (year - (year % 10)) STORED,
    century     SMALLINT    GENERATED ALWAYS AS (year - (year % 100)) STORED,
    is_projection BOOLEAN   DEFAULT FALSE  -- TRUE for Pew 2030/2050 projections
);

COMMENT ON TABLE dim_year IS
    'Year dimension. is_projection flags Pew forward estimates vs historical data.';


-- =============================================================
-- FACT TABLES
-- =============================================================

-- H1 & H2 — Global religious population by country, religion, year
CREATE TABLE IF NOT EXISTS fact_religious_population (
    pop_id                  BIGSERIAL PRIMARY KEY,
    country_id              INT         NOT NULL REFERENCES dim_country(country_id),
    religion_id             INT         NOT NULL REFERENCES dim_religion(religion_id),
    year_id                 INT         NOT NULL REFERENCES dim_year(year_id),

    -- Core measures
    affiliated_count        BIGINT,                 -- Absolute headcount
    affiliated_pct_country  NUMERIC(6,3),           -- % of that country's population
    country_total_pop       BIGINT,                 -- Total country population that year

    -- Derivable but pre-computed for query speed
    -- affiliated_pct_of_religion_global is computed in views, not stored

    -- Metadata
    source                  VARCHAR(50) NOT NULL,   -- 'pew_2015', 'pew_2025_update', 'gordon_conwell'
    is_projection           BOOLEAN     DEFAULT FALSE,
    notes                   TEXT,
    loaded_at               TIMESTAMP   DEFAULT NOW(),

    UNIQUE (country_id, religion_id, year_id, source)
);

CREATE INDEX idx_frp_country   ON fact_religious_population(country_id);
CREATE INDEX idx_frp_religion  ON fact_religious_population(religion_id);
CREATE INDEX idx_frp_year      ON fact_religious_population(year_id);
CREATE INDEX idx_frp_source    ON fact_religious_population(source);

COMMENT ON TABLE fact_religious_population IS
    'Core population fact. One row per country × religion × year × source.
     Powers H1 (global trend) and H2 (geographic shift of Christianity).';

-- ------------------------------------

-- H1 — World Values Survey religiosity intensity
CREATE TABLE IF NOT EXISTS fact_wvs_religiosity (
    wvs_id                  BIGSERIAL PRIMARY KEY,
    country_id              INT         NOT NULL REFERENCES dim_country(country_id),
    year_id                 INT         NOT NULL REFERENCES dim_year(year_id),
    wave                    SMALLINT    NOT NULL,    -- WVS wave number (1–7)

    -- Key WVS variables (all as % of respondents in that country/wave)
    pct_religion_very_important     NUMERIC(5,2),   -- Q: importance of religion = "very important"
    pct_religion_rather_important   NUMERIC(5,2),
    pct_religion_not_very           NUMERIC(5,2),
    pct_religion_not_at_all         NUMERIC(5,2),

    pct_attend_weekly               NUMERIC(5,2),   -- Weekly religious service attendance
    pct_attend_monthly              NUMERIC(5,2),
    pct_self_religious              NUMERIC(5,2),   -- Self-identifies as religious person
    pct_convinced_atheist           NUMERIC(5,2),

    sample_size                     INT,
    source                          VARCHAR(30) DEFAULT 'wvs',
    loaded_at                       TIMESTAMP   DEFAULT NOW(),

    UNIQUE (country_id, year_id, wave)
);

CREATE INDEX idx_wvs_country ON fact_wvs_religiosity(country_id);
CREATE INDEX idx_wvs_wave    ON fact_wvs_religiosity(wave);

COMMENT ON TABLE fact_wvs_religiosity IS
    'WVS religiosity intensity. Complements fact_religious_population by measuring
     HOW religious people are, not just what they identify as.
     Key for H1: does intensity track the same direction as affiliation?';

-- ------------------------------------

-- H3 — Media / technology penetration by country & year
CREATE TABLE IF NOT EXISTS fact_media_penetration (
    media_id            BIGSERIAL PRIMARY KEY,
    country_id          INT         NOT NULL REFERENCES dim_country(country_id),
    year_id             INT         NOT NULL REFERENCES dim_year(year_id),

    -- Indicators (all from World Bank / ITU)
    radio_per_100       NUMERIC(7,2),   -- IT.RAD.SETS.PC  (discontinued after ~2000)
    tv_per_100          NUMERIC(7,2),   -- IT.TVS.SETS.PC
    mobile_per_100      NUMERIC(7,2),   -- IT.CEL.SETS.P2
    internet_pct        NUMERIC(6,2),   -- IT.NET.USER.ZS

    source              VARCHAR(30) DEFAULT 'world_bank',
    loaded_at           TIMESTAMP   DEFAULT NOW(),

    UNIQUE (country_id, year_id, source)
);

CREATE INDEX idx_media_country ON fact_media_penetration(country_id);
CREATE INDEX idx_media_year    ON fact_media_penetration(year_id);

COMMENT ON TABLE fact_media_penetration IS
    'World Bank media/technology penetration. Used in H3 to test whether radio → TV → mobile
     expansion correlates with Pentecostal growth in sub-Saharan Africa.';

-- ------------------------------------

-- H3 supplement — Pentecostal membership snapshots
-- (Gordon-Conwell / ARDA data — more granular than fact_religious_population)
CREATE TABLE IF NOT EXISTS fact_pentecostal_growth (
    pent_id             BIGSERIAL PRIMARY KEY,
    country_id          INT         NOT NULL REFERENCES dim_country(country_id),
    year_id             INT         NOT NULL REFERENCES dim_year(year_id),

    movement            VARCHAR(80),        -- e.g. 'Pentecostal', 'Charismatic', 'Neo-Charismatic'
    adherents           BIGINT,
    pct_of_country_pop  NUMERIC(6,3),
    pct_of_christians   NUMERIC(6,3),       -- Share of Christians in that country

    source              VARCHAR(50) NOT NULL,
    notes               TEXT,
    loaded_at           TIMESTAMP   DEFAULT NOW(),

    UNIQUE (country_id, year_id, movement, source)
);

CREATE INDEX idx_pent_country ON fact_pentecostal_growth(country_id);

COMMENT ON TABLE fact_pentecostal_growth IS
    'Pentecostal/Charismatic sub-breakdown. Separate from fact_religious_population
     because source granularity differs and we need the movement sub-type for H3.';


-- =============================================================
-- SEED DATA — dim_religion
-- =============================================================

INSERT INTO dim_religion (religion_name, religion_family, propagation_model, has_conversion_mandate, notes)
VALUES
    ('Christianity',        'Abrahamic',    'Universalising',   TRUE,   'Active conversion mandate (Great Commission). Spread via missionaries, media, diaspora.'),
    ('Islam',               'Abrahamic',    'Universalising',   TRUE,   'Active conversion mandate (Dawah). Spread via trade routes, conquest, demographic growth.'),
    ('Hinduism',            'Dharmic',      'Ethnic',           FALSE,  'No missionary tradition. Identity tied to birth and caste. Spreads through diaspora, not conversion.'),
    ('Buddhism',            'Dharmic',      'Syncretic',        FALSE,  'Spread through trade routes and royal patronage (Ashoka). Blends with local cultures rather than replacing them.'),
    ('Folk/Indigenous',     'Indigenous',   'Ethnic',           FALSE,  'Localised traditional religions. Pew category: Folk Religions.'),
    ('Judaism',             'Abrahamic',    'Ethnic',           FALSE,  'Predominantly ethnic. Limited active proselytisation.'),
    ('Other Religion',      'Other',        NULL,               FALSE,  'Pew catch-all for Sikhs, Baha''i, Jains, Taoists, Confucianists, etc.'),
    ('Unaffiliated',        'None',         NULL,               FALSE,  'No religious affiliation. Includes atheists, agnostics, and "nothing in particular".')
ON CONFLICT (religion_name) DO NOTHING;


-- =============================================================
-- SEED DATA — dim_year  (1900–2050 in Pew's reporting intervals)
-- =============================================================

INSERT INTO dim_year (year, is_projection)
VALUES
    (1900, FALSE), (1910, FALSE), (1920, FALSE), (1930, FALSE),
    (1940, FALSE), (1950, FALSE), (1960, FALSE), (1970, FALSE),
    (1980, FALSE), (1990, FALSE), (2000, FALSE), (2010, FALSE),
    (2015, FALSE), (2020, FALSE),
    (2030, TRUE),  (2050, TRUE)
ON CONFLICT (year) DO NOTHING;

-- Also insert WVS survey years
INSERT INTO dim_year (year, is_projection)
SELECT y, FALSE
FROM unnest(ARRAY[1981,1982,1984,1990,1991,1993,1994,1995,1996,
                  1997,1998,1999,2000,2001,2002,2003,2004,2005,
                  2006,2007,2008,2009,2010,2011,2012,2013,2014,
                  2017,2018,2019,2021,2022]) AS y
ON CONFLICT (year) DO NOTHING;


-- =============================================================
-- ANALYTICAL VIEWS
-- =============================================================

-- V1: Global religious affiliation trend (H1)
CREATE OR REPLACE VIEW v_global_affiliation_trend AS
SELECT
    dy.year,
    dr.religion_name,
    dr.religion_family,
    dr.propagation_model,
    SUM(frp.affiliated_count)                               AS global_count,
    ROUND(
        SUM(frp.affiliated_count)::NUMERIC
        / NULLIF(SUM(SUM(frp.affiliated_count)) OVER (PARTITION BY dy.year), 0) * 100
    , 2)                                                    AS pct_of_world,
    dy.is_projection,
    frp.source
FROM fact_religious_population frp
JOIN dim_year     dy ON frp.year_id    = dy.year_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
GROUP BY dy.year, dy.is_projection, dr.religion_name, dr.religion_family,
         dr.propagation_model, frp.source
ORDER BY dy.year, global_count DESC;

COMMENT ON VIEW v_global_affiliation_trend IS
    'H1: Is the world becoming more or less religious over time?
     Aggregates all countries by religion and year to show global shares.';

-- ------------------------------------

-- V2: Christianity geographic shift (H2)
CREATE OR REPLACE VIEW v_christianity_by_region AS
SELECT
    dy.year,
    dc.region,
    SUM(frp.affiliated_count)                               AS christian_count,
    ROUND(
        SUM(frp.affiliated_count)::NUMERIC
        / NULLIF(SUM(SUM(frp.affiliated_count)) OVER (PARTITION BY dy.year), 0) * 100
    , 2)                                                    AS pct_of_global_christians,
    dy.is_projection,
    frp.source
FROM fact_religious_population frp
JOIN dim_year     dy ON frp.year_id    = dy.year_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_country  dc ON frp.country_id  = dc.country_id
WHERE dr.religion_name = 'Christianity'
GROUP BY dy.year, dy.is_projection, dc.region, frp.source
ORDER BY dy.year, christian_count DESC;

COMMENT ON VIEW v_christianity_by_region IS
    'H2: Tracks the geographic migration of Christianity 1900→2050.
     The headline figure: Africa goes from ~1% to ~31% of global Christians.';

-- ------------------------------------

-- V3: Media penetration vs Pentecostal growth, sub-Saharan Africa (H3)
CREATE OR REPLACE VIEW v_media_vs_pentecostal AS
SELECT
    dc.country_name,
    dc.sub_region,
    dy.year,
    fmp.radio_per_100,
    fmp.tv_per_100,
    fmp.mobile_per_100,
    fmp.internet_pct,
    fpg.movement,
    fpg.adherents                                           AS pentecostal_adherents,
    fpg.pct_of_country_pop                                  AS pentecostal_pct
FROM fact_media_penetration fmp
JOIN dim_country  dc  ON fmp.country_id = dc.country_id
JOIN dim_year     dy  ON fmp.year_id    = dy.year_id
LEFT JOIN fact_pentecostal_growth fpg
       ON fpg.country_id = fmp.country_id
      AND fpg.year_id    = fmp.year_id
WHERE dc.region = 'Sub-Saharan Africa'
ORDER BY dc.country_name, dy.year;

COMMENT ON VIEW v_media_vs_pentecostal IS
    'H3: Side-by-side view of media infrastructure expansion and Pentecostal growth
     across sub-Saharan African countries. Used to test the media-as-missionary hypothesis.';

-- ------------------------------------

-- V4: WVS religiosity intensity by region over time (H1 supplement)
CREATE OR REPLACE VIEW v_wvs_intensity_by_region AS
SELECT
    dc.region,
    dy.year,
    fw.wave,
    ROUND(AVG(fw.pct_religion_very_important), 2)           AS avg_pct_very_important,
    ROUND(AVG(fw.pct_attend_weekly), 2)                     AS avg_pct_weekly_attendance,
    ROUND(AVG(fw.pct_self_religious), 2)                    AS avg_pct_self_religious,
    ROUND(AVG(fw.pct_convinced_atheist), 2)                 AS avg_pct_atheist,
    COUNT(DISTINCT fw.country_id)                           AS country_count
FROM fact_wvs_religiosity fw
JOIN dim_country dc ON fw.country_id = dc.country_id
JOIN dim_year    dy ON fw.year_id    = dy.year_id
GROUP BY dc.region, dy.year, fw.wave
ORDER BY dy.year, dc.region;

COMMENT ON VIEW v_wvs_intensity_by_region IS
    'H1 supplement: Does religiosity intensity (WVS) track the same direction as affiliation?
     Key question: Western Europe declining in both. Global South stable or rising in both?';
