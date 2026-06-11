-- =============================================================
-- THE GOD METRIC — ETL Validation Queries
-- Run after all ETL scripts complete
-- =============================================================

-- ── 1. Row counts ──────────────────────────────────────────────────────────

SELECT 'dim_country'                AS table_name, COUNT(*) AS row_count FROM dim_country
UNION ALL
SELECT 'dim_religion',                             COUNT(*) FROM dim_religion
UNION ALL
SELECT 'dim_year',                                 COUNT(*) FROM dim_year
UNION ALL
SELECT 'fact_religious_population',                COUNT(*) FROM fact_religious_population
UNION ALL
SELECT 'fact_wvs_religiosity',                     COUNT(*) FROM fact_wvs_religiosity
UNION ALL
SELECT 'fact_media_penetration',                   COUNT(*) FROM fact_media_penetration
UNION ALL
SELECT 'fact_pentecostal_growth',                  COUNT(*) FROM fact_pentecostal_growth
ORDER BY 1;


-- ── 2. H1 check: Global affiliation trend ─────────────────────────────────
-- Expected: religion does NOT decline globally 2010→2050
-- Christianity + Islam together grow; Unaffiliated shrinks as % of world

SELECT year, religion_name, global_count, pct_of_world, is_projection
FROM v_global_affiliation_trend
WHERE source = 'pew_key_figures'
ORDER BY year, pct_of_world DESC;


-- ── 3. H2 check: Christianity's geographic migration ──────────────────────
-- Expected: Africa grows from ~9% (1910) → ~31% (2020) → ~35% (2050)
-- Europe shrinks from ~70% → ~22% → <20%

SELECT year, region, christian_count, pct_of_global_christians, is_projection
FROM v_christianity_by_region
WHERE source = 'pew_key_figures'
ORDER BY year, pct_of_global_christians DESC;


-- ── 4. Key figure verification ────────────────────────────────────────────
-- Spot-check the most-cited numbers from the Pew 2015 report

SELECT
    dc.country_name,
    dr.religion_name,
    dy.year,
    frp.affiliated_count,
    frp.affiliated_pct_country,
    frp.source
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3 IN ('WLD', 'SSA', 'EUR', 'NAM', 'LAM')
  AND dr.religion_name IN ('Christianity', 'Islam', 'Unaffiliated')
  AND dy.year IN (1910, 2010, 2020, 2050)
ORDER BY dy.year, dc.country_name, frp.affiliated_count DESC;


-- ── 5. H3 check: Media penetration coverage for Sub-Saharan Africa ─────────
-- Expected: mobile/internet data available from ~1990s onwards

SELECT
    dc.country_name,
    dy.year,
    fmp.radio_per_100,
    fmp.tv_per_100,
    fmp.mobile_per_100,
    fmp.internet_pct
FROM fact_media_penetration fmp
JOIN dim_country dc ON fmp.country_id = dc.country_id
JOIN dim_year    dy ON fmp.year_id    = dy.year_id
WHERE dc.iso3 IN ('NGA', 'GHA', 'KEN', 'ZAF', 'ETH')
  AND dy.year IN (1980, 1990, 2000, 2010, 2020)
ORDER BY dc.country_name, dy.year;


-- ── 6. Null checks ─────────────────────────────────────────────────────────
-- Flags any critical nulls

SELECT 'fact_religious_population: null counts' AS check_name,
       COUNT(*) FILTER (WHERE affiliated_count IS NULL) AS null_count,
       COUNT(*) AS total
FROM fact_religious_population

UNION ALL

SELECT 'fact_media_penetration: all 4 cols null',
       COUNT(*) FILTER (
           WHERE radio_per_100 IS NULL
             AND tv_per_100 IS NULL
             AND mobile_per_100 IS NULL
             AND internet_pct IS NULL
       ),
       COUNT(*)
FROM fact_media_penetration;


-- ── 7. WVS intensity: Does Western Europe diverge from Global South? ────────
-- Expected: WVS pct_very_important drops in Western Europe, stable/rising elsewhere

SELECT
    region,
    year,
    wave,
    avg_pct_very_important    AS pct_rel_very_important,
    avg_pct_weekly_attendance AS pct_attend_weekly,
    avg_pct_atheist           AS pct_atheist,
    country_count
FROM v_wvs_intensity_by_region
ORDER BY year, region;


-- ── 8. H2 narrative query: The one-century migration in a single view ───────
-- This is the "Against the Narrative" money shot

WITH regional_totals AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.region ILIKE '%africa%'          THEN 'Sub-Saharan Africa'
            WHEN dc.region ILIKE '%europe%'          THEN 'Europe'
            WHEN dc.region ILIKE '%latin%'
              OR dc.region ILIKE '%caribbean%'       THEN 'Latin America & Caribbean'
            WHEN dc.region ILIKE '%north america%'   THEN 'North America'
            WHEN dc.region ILIKE '%asia%'
              OR dc.region ILIKE '%pacific%'         THEN 'Asia-Pacific'
            ELSE dc.region
        END                                          AS region_group,
        SUM(frp.affiliated_count)                    AS christians
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'                           -- exclude the pre-aggregated "World" row
    GROUP BY dy.year, region_group
),
world_totals AS (
    SELECT year, SUM(christians) AS world_christians
    FROM regional_totals
    GROUP BY year
)
SELECT
    rt.year,
    rt.region_group,
    rt.christians,
    ROUND(rt.christians::NUMERIC / NULLIF(wt.world_christians, 0) * 100, 1) AS pct_of_world_christians
FROM regional_totals rt
JOIN world_totals wt USING (year)
ORDER BY rt.year, rt.christians DESC;


-- ── 9. H3 media-growth correlation setup ──────────────────────────────────
-- Countries where we have both media penetration AND pentecostal data

SELECT
    dc.country_name,
    COUNT(DISTINCT fmp.year_id)  AS media_years,
    COUNT(DISTINCT fpg.year_id)  AS pent_years,
    MIN(dy_m.year)               AS media_from,
    MAX(dy_m.year)               AS media_to
FROM dim_country dc
LEFT JOIN fact_media_penetration fmp ON fmp.country_id = dc.country_id
LEFT JOIN fact_pentecostal_growth fpg ON fpg.country_id = dc.country_id
LEFT JOIN dim_year dy_m ON fmp.year_id = dy_m.year_id
WHERE dc.region ILIKE '%africa%'
GROUP BY dc.country_name
HAVING COUNT(DISTINCT fmp.year_id) > 0
ORDER BY media_years DESC, pent_years DESC;
