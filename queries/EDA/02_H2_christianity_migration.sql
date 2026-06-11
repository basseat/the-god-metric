-- =============================================================================
-- H2: CHRISTIANITY MIGRATED FROM EUROPE TO AFRICA
-- =============================================================================
-- Hypothesis: In 1910, ~72% of the world's Christians lived in Europe.
-- By 2050, Africa will hold ~40% while Europe holds <20%.
-- This is the single most counterintuitive finding in the dataset.
-- =============================================================================


-- ── Q1. The century-long migration: Regional share of global Christians ────────
-- THE MONEY SHOT. Run this first. Maps perfectly to a stacked area chart.
-- Expected: Europe line falls from 72% → <20%; Africa line rises from 9% → 40%+

WITH regional AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.country_name ILIKE '%africa%'
              OR dc.region ILIKE '%africa%'                    THEN 'Sub-Saharan Africa'
            WHEN dc.country_name ILIKE '%europe%'
              OR dc.region ILIKE '%europe%'                    THEN 'Europe'
            WHEN dc.country_name ILIKE '%latin%'
              OR dc.country_name ILIKE '%caribbean%'
              OR dc.region ILIKE '%latin%'                     THEN 'Latin America & Caribbean'
            WHEN dc.country_name ILIKE '%north america%'
              OR dc.region ILIKE '%north america%'             THEN 'North America'
            WHEN dc.country_name ILIKE '%asia%'
              OR dc.region ILIKE '%asia%'
              OR dc.region ILIKE '%pacific%'                   THEN 'Asia-Pacific'
            WHEN dc.country_name ILIKE '%middle east%'
              OR dc.region ILIKE '%middle east%'               THEN 'Middle East & North Africa'
            ELSE dc.region
        END                                                    AS region_group,
        SUM(frp.affiliated_count)                              AS christians
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'        -- exclude pre-aggregated world row
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
      AND region_group IS NOT NULL
      AND region_group != ''
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
    w.world_total
FROM regional r
JOIN world    w USING (year)
WHERE r.region_group NOT IN ('', 'Unknown')
ORDER BY r.year, pct_of_world_christians DESC;


-- ── Q2. The crossover point — when did Africa overtake Europe? ────────────────
-- Find the exact decade where African Christians exceeded European Christians.

SELECT
    dy.year,
    SUM(frp.affiliated_count) FILTER (
        WHERE dc.region ILIKE '%africa%'
           OR dc.country_name ILIKE '%africa%'
    )                                                          AS africa_christians,
    SUM(frp.affiliated_count) FILTER (
        WHERE dc.region ILIKE '%europe%'
           OR dc.country_name ILIKE '%europe%'
    )                                                          AS europe_christians,
    CASE
        WHEN SUM(frp.affiliated_count) FILTER (
                WHERE dc.region ILIKE '%africa%'
                   OR dc.country_name ILIKE '%africa%')
           > SUM(frp.affiliated_count) FILTER (
                WHERE dc.region ILIKE '%europe%'
                   OR dc.country_name ILIKE '%europe%')
        THEN 'Africa leads'
        ELSE 'Europe leads'
    END                                                        AS who_leads
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND dc.iso3 != 'WLD'
  AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
GROUP BY dy.year
ORDER BY dy.year;


-- ── Q3. Country-level Christian population 2010 — map data ────────────────────
-- For the Tableau world map: each country's Christian count and % in 2010.
-- Colour by % (choropleth), size bubbles by absolute count.

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    frp.affiliated_count                                       AS christian_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)             AS christian_pct,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source       = 'pew_2015_seed'
  AND dy.year IN (2010, 2050)
  AND dc.iso3 NOT IN ('WLD', 'SSA', 'EUR', 'NAM', 'LAM', 'MEA', 'ASP')
ORDER BY dy.year, frp.affiliated_count DESC NULLS LAST;


-- ── Q4. African countries: absolute Christian growth trajectory ───────────────
-- Shows the sheer scale of African Christianity's growth 2010 → 2050.

SELECT
    dc.country_name,
    dc.iso3,
    frp.affiliated_count                                       AS christian_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)             AS christian_pct,
    dy.year,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source       = 'pew_2015_seed'
  AND (dc.region ILIKE '%africa%' OR dc.iso3 IN ('NGA','COD','ETH','TZA','KEN','UGA','ZAF','GHA','ZWE','MOZ','AGO','CMR','RWA','ZMB','MWI'))
  AND dy.year IN (2010, 2050)
ORDER BY frp.affiliated_count DESC NULLS LAST, dy.year;


-- ── Q5. The de-Europeanisation index ─────────────────────────────────────────
-- A single metric: ratio of African to European Christians over time.
-- At 1:1 = crossover. Above 1 = Africa leads.

WITH by_bloc AS (
    SELECT
        dy.year,
        SUM(frp.affiliated_count) FILTER (
            WHERE dc.region ILIKE '%africa%'
               OR dc.country_name ILIKE '%africa%'
        )                                                      AS africa_total,
        SUM(frp.affiliated_count) FILTER (
            WHERE dc.region ILIKE '%europe%'
               OR dc.country_name ILIKE '%europe%'
        )                                                      AS europe_total
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
    GROUP BY dy.year
)
SELECT
    year,
    ROUND(africa_total::NUMERIC / 1e6, 0)                     AS africa_christians_M,
    ROUND(europe_total::NUMERIC / 1e6, 0)                     AS europe_christians_M,
    ROUND(africa_total::NUMERIC / NULLIF(europe_total, 0), 2) AS africa_to_europe_ratio,
    CASE
        WHEN africa_total > europe_total THEN '🌍 Africa leads'
        WHEN africa_total = europe_total THEN '= Crossover'
        ELSE '🇪🇺 Europe leads'
    END                                                        AS status
FROM by_bloc
ORDER BY year;


-- ── Q6. Islam's parallel growth story ────────────────────────────────────────
-- Islam is also shifting geographically. Sub-Saharan Africa is one of the
-- fastest-growing Muslim regions. Contextualises H2 as not just a Christian story.

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    frp.affiliated_count                                       AS muslim_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)             AS muslim_pct,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Islam'
  AND frp.source       = 'pew_2015_seed'
  AND dy.year IN (2010, 2050)
ORDER BY frp.affiliated_count DESC NULLS LAST, dy.year;


-- ── Q7. Religion composition comparison: Top 20 countries full breakdown ───────
-- Multi-religion view for the most populous countries — for the "stacked bar" chart.

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    dr.religion_name,
    frp.affiliated_count,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)             AS pct_of_population
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE frp.source = 'pew_2015_seed'
  AND dy.year = 2010
  AND dc.iso3 IN (
    -- Top Christian: USA, BRA, MEX, COD, RUS, PHL, NGA, ETH, DEU, GBR
    'USA','BRA','MEX','COD','RUS','PHL','NGA','ETH','DEU','GBR',
    -- Top Muslim: IDN, PAK, BGD, EGY, IRN, TUR, NGA, IND, DZA, MAR
    'IDN','PAK','BGD','EGY','IRN','TUR','IND','DZA','MAR',
    -- Top Hindu / Buddhist: IND, CHN, THA, JPN
    'CHN','THA','JPN'
  )
ORDER BY dc.country_name, frp.affiliated_count DESC NULLS LAST;
