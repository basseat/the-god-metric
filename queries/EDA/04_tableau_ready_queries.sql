-- =============================================================================
-- TABLEAU-READY QUERIES — THE GOD METRIC
-- =============================================================================
-- These are the exact queries to use as Custom SQL in Tableau.
-- Connect Tableau → PostgreSQL → god_metric database → New Custom SQL
-- Paste each query below as a separate data source or sheet.
--
-- Tableau connection settings:
--   Server:   localhost
--   Port:     5432
--   Database: god_metric
--   Username: postgres
-- =============================================================================


-- ════════════════════════════════════════════════════════════════════════════
-- DASHBOARD 1: THE BIG PICTURE (H1)
-- Sheet 1a: World map — % religious by country (2020)
-- Sheet 1b: Slope chart — religiosity change 2010 vs 2020 by region
-- Sheet 1c: Bar chart — top 10 most & least religious countries
-- ════════════════════════════════════════════════════════════════════════════

-- [TABLEAU SOURCE: tableau_H1_world_map]
-- Use for: Filled map (country = ISO3, colour = pct_religious_2020)
--          Dual-axis: 2010 vs 2020 to show change

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)           AS pct_religious,
    frp.source
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Any Religion'
  AND frp.source       = 'owid_pew_aggregate'
  AND dy.year IN (2010, 2020)
  AND dc.iso3 NOT IN ('OWID_WRL', '')
  AND LENGTH(dc.iso3) = 3
ORDER BY dy.year, dc.iso3;


-- [TABLEAU SOURCE: tableau_H1_region_slope]
-- Use for: Slope chart / line chart showing regional religiosity trend

SELECT
    COALESCE(dc.region, 'Unknown')                          AS region,
    dy.year,
    ROUND(AVG(frp.affiliated_pct_country)::NUMERIC, 1)     AS avg_pct_religious,
    COUNT(DISTINCT dc.country_id)                           AS country_count
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Any Religion'
  AND frp.source       = 'owid_pew_aggregate'
  AND dy.year IN (2010, 2020)
GROUP BY dc.region, dy.year
ORDER BY dy.year, avg_pct_religious DESC;


-- ════════════════════════════════════════════════════════════════════════════
-- DASHBOARD 2: THE GREAT MIGRATION (H2)
-- Sheet 2a: Stacked area — regional share of global Christians 1910→2050
-- Sheet 2b: World map — % Christian by country (2010)
-- Sheet 2c: World map — % Christian by country (2050 projection)
-- Sheet 2d: Slope chart — Africa vs Europe 1910→2050
-- ════════════════════════════════════════════════════════════════════════════

-- [TABLEAU SOURCE: tableau_H2_regional_share]
-- Use for: Stacked area chart (Year on X, % on Y, Region as colour)
-- This is the HERO visualisation for the article.

WITH regional AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.country_name ILIKE '%sub-saharan%'
              OR dc.region ILIKE '%africa%'                 THEN 'Sub-Saharan Africa'
            WHEN dc.country_name ILIKE '%europe%'
              OR dc.region ILIKE '%europe%'                 THEN 'Europe'
            WHEN dc.country_name ILIKE '%latin%'
              OR dc.country_name ILIKE '%caribbean%'
              OR dc.region ILIKE '%latin%'                  THEN 'Latin America & Caribbean'
            WHEN dc.country_name ILIKE '%north america%'
              OR dc.region ILIKE '%north america%'          THEN 'North America'
            WHEN dc.country_name ILIKE '%asia%'
              OR dc.region ILIKE '%asia%'
              OR dc.region ILIKE '%pacific%'                THEN 'Asia-Pacific'
            WHEN dc.country_name ILIKE '%middle east%'
              OR dc.region ILIKE '%middle east%'            THEN 'Middle East & North Africa'
            ELSE 'Other'
        END                                                 AS region_group,
        SUM(frp.affiliated_count)                           AS christians,
        BOOL_OR(frp.is_projection)                          AS is_projection
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
    GROUP BY dy.year, region_group
),
world AS (
    SELECT year, SUM(christians) AS world_total
    FROM regional
    GROUP BY year
)
SELECT
    r.year,
    r.region_group,
    r.christians,
    ROUND(r.christians::NUMERIC / NULLIF(w.world_total, 0) * 100, 1) AS pct_of_world_christians,
    r.is_projection
FROM regional r
JOIN world    w USING (year)
WHERE r.region_group NOT IN ('', 'Unknown', 'Other')
ORDER BY r.year, pct_of_world_christians DESC;


-- [TABLEAU SOURCE: tableau_H2_country_map]
-- Use for: Filled map (choropleth) — one row per country per year
-- Filter in Tableau by Year (2010 or 2050) to create two map views

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    frp.affiliated_count                                    AS christian_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)          AS christian_pct,
    frp.is_projection,
    CASE WHEN dy.year = 2050 THEN 'Projection' ELSE 'Actual' END AS data_type
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source       = 'pew_2015_seed'
  AND dy.year IN (2010, 2050)
  AND LENGTH(dc.iso3) = 3
ORDER BY dy.year, frp.affiliated_count DESC NULLS LAST;


-- [TABLEAU SOURCE: tableau_H2_africa_europe_duel]
-- Use for: Side-by-side bar or dumbbell chart showing the crossover
-- Year on X-axis, two bars (Africa vs Europe), diverging from centre

SELECT
    dy.year,
    'Sub-Saharan Africa'                                    AS region,
    SUM(frp.affiliated_count)                               AS christian_count,
    ROUND(SUM(frp.affiliated_count)::NUMERIC / 1e6, 0)     AS christian_count_M,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
  AND (dc.region ILIKE '%africa%' OR dc.country_name ILIKE '%africa%')
  AND dc.iso3 != 'WLD'
GROUP BY dy.year, frp.is_projection

UNION ALL

SELECT
    dy.year,
    'Europe',
    SUM(frp.affiliated_count),
    ROUND(SUM(frp.affiliated_count)::NUMERIC / 1e6, 0),
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
  AND (dc.region ILIKE '%europe%' OR dc.country_name ILIKE '%europe%')
  AND dc.iso3 != 'WLD'
GROUP BY dy.year, frp.is_projection

ORDER BY year, region;


-- ════════════════════════════════════════════════════════════════════════════
-- DASHBOARD 3: THE MEDIA WAVE (H3)
-- Sheet 3a: Line chart — media penetration over time for SSA countries
-- Sheet 3b: Scatter — mobile penetration vs Christianity %
-- Sheet 3c: Small multiples — Nigeria / Kenya / Ghana / Ethiopia media timelines
-- ════════════════════════════════════════════════════════════════════════════

-- [TABLEAU SOURCE: tableau_H3_media_timeline]
-- Use for: Line chart — 4 lines (radio/TV/mobile/internet) per country, over time

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    ROUND(fmp.radio_per_100::NUMERIC, 1)                    AS radio_per_100,
    ROUND(fmp.tv_per_100::NUMERIC, 1)                       AS tv_per_100,
    ROUND(fmp.mobile_per_100::NUMERIC, 1)                   AS mobile_per_100,
    ROUND(fmp.internet_pct::NUMERIC, 1)                     AS internet_pct
FROM fact_media_penetration fmp
JOIN dim_country dc ON fmp.country_id = dc.country_id
JOIN dim_year    dy ON fmp.year_id    = dy.year_id
WHERE (dc.region ILIKE '%africa%'
       OR dc.iso3 IN ('BRA','COL','MEX','GBR','USA','DEU'))
  AND dy.year BETWEEN 1960 AND 2023
  AND (fmp.radio_per_100 IS NOT NULL
       OR fmp.tv_per_100  IS NOT NULL
       OR fmp.mobile_per_100 IS NOT NULL
       OR fmp.internet_pct IS NOT NULL)
ORDER BY dc.country_name, dy.year;


-- [TABLEAU SOURCE: tableau_H3_scatter]
-- Use for: Scatter plot — X = mobile penetration 2010, Y = Christianity %
-- Colour = Region, Size = absolute Christian population

WITH christian_2010 AS (
    SELECT
        dc.iso3,
        dc.country_name,
        dc.region,
        frp.affiliated_pct_country    AS christian_pct,
        frp.affiliated_count          AS christian_count
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND frp.source       = 'pew_2015_seed'
      AND dy.year          = 2010
),
media_2010 AS (
    SELECT
        dc.iso3,
        AVG(fmp.mobile_per_100)       AS mobile_per_100,
        AVG(fmp.tv_per_100)           AS tv_per_100,
        AVG(fmp.internet_pct)         AS internet_pct
    FROM fact_media_penetration fmp
    JOIN dim_country dc ON fmp.country_id = dc.country_id
    JOIN dim_year    dy ON fmp.year_id    = dy.year_id
    WHERE dy.year BETWEEN 2008 AND 2012
    GROUP BY dc.iso3
)
SELECT
    c.country_name,
    c.iso3,
    c.region,
    ROUND(c.christian_pct::NUMERIC, 1)     AS christian_pct_2010,
    c.christian_count                       AS christian_count_2010,
    ROUND(m.mobile_per_100::NUMERIC, 1)    AS mobile_per_100_2010,
    ROUND(m.tv_per_100::NUMERIC, 1)        AS tv_per_100_2010,
    ROUND(m.internet_pct::NUMERIC, 1)      AS internet_pct_2010
FROM christian_2010 c
LEFT JOIN media_2010 m ON c.iso3 = m.iso3
WHERE c.christian_pct IS NOT NULL
  AND m.mobile_per_100 IS NOT NULL
ORDER BY c.christian_count DESC NULLS LAST;


-- ════════════════════════════════════════════════════════════════════════════
-- DASHBOARD 4: RELIGION BY RELIGION BREAKDOWN
-- Sheet 4a: Multi-religion world map (filter by religion)
-- Sheet 4b: Treemap — world Christian/Muslim/Hindu/Buddhist by country
-- ════════════════════════════════════════════════════════════════════════════

-- [TABLEAU SOURCE: tableau_multi_religion_map]
-- Use for: Multi-religion map with Religion as a filter/page
-- One row per country × religion — filter in Tableau to switch religions

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dr.religion_name,
    dr.propagation_model,
    dy.year,
    frp.affiliated_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)           AS pct_of_country,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE frp.source = 'pew_2015_seed'
  AND dy.year    = 2010
  AND dr.religion_name NOT IN ('Any Religion')
  AND LENGTH(dc.iso3) = 3
ORDER BY dr.religion_name, frp.affiliated_count DESC NULLS LAST;


-- ════════════════════════════════════════════════════════════════════════════
-- DASHBOARD 5: THE NARRATIVE SUMMARY — KEY NUMBERS FOR CALLOUTS
-- These produce the exact statistics to cite in the Substack article.
-- ════════════════════════════════════════════════════════════════════════════

-- [Article stat 1] Global religious share — the counter to secularisation thesis
SELECT
    dy.year,
    ROUND(AVG(frp.affiliated_pct_country)::NUMERIC, 1) AS global_avg_pct_religious
FROM fact_religious_population frp
JOIN dim_year     dy ON frp.year_id     = dy.year_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
WHERE dr.religion_name = 'Any Religion'
  AND frp.source       = 'owid_pew_aggregate'
GROUP BY dy.year ORDER BY dy.year;

-- [Article stat 2] Africa vs Europe crossover: the single most powerful number
SELECT
    dy.year,
    ROUND(SUM(CASE WHEN dc.region ILIKE '%africa%' THEN frp.affiliated_count END)::NUMERIC / 1e6, 0) AS africa_christians_M,
    ROUND(SUM(CASE WHEN dc.region ILIKE '%europe%' THEN frp.affiliated_count END)::NUMERIC / 1e6, 0) AS europe_christians_M
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
  AND dc.iso3 != 'WLD'
  AND dy.year IN (1910, 1970, 2010, 2050)
GROUP BY dy.year ORDER BY dy.year;

-- [Article stat 3] Nigeria's Christian population 2010 vs 2050 — for the lede
SELECT
    dc.country_name, dy.year,
    ROUND(frp.affiliated_count::NUMERIC / 1e6, 0)     AS christian_count_M,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)     AS christian_pct
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3 = 'NGA'
  AND dr.religion_name IN ('Christianity', 'Islam')
  AND frp.source = 'pew_2015_seed'
  AND dy.year IN (2010, 2050)
ORDER BY dy.year, christian_count_M DESC;

-- [Article stat 4] Islam + Christianity as % of world 1910 → 2050
SELECT
    dy.year,
    dr.religion_name,
    frp.affiliated_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)     AS pct_of_world
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3 = 'WLD'
  AND dr.religion_name IN ('Christianity', 'Islam', 'Unaffiliated')
  AND frp.source = 'pew_key_figures'
  AND dy.year IN (1910, 2010, 2050)
ORDER BY dy.year, frp.affiliated_count DESC NULLS LAST;
