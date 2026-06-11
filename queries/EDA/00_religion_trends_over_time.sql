-- =============================================================================
-- THE BIG PICTURE: HOW ALL MAJOR RELIGIONS HAVE MOVED 1910 → 2050
-- =============================================================================
-- Scene-setting queries. Not tied to a specific hypothesis — this is the
-- opening view that gives the reader the full picture before we zoom in.
--
-- Two lenses:
--   A) All major religions — absolute numbers and % of world population
--   B) Christianity only — how its composition has shifted by region
-- =============================================================================


-- ════════════════════════════════════════════════════════════════════════════
-- PART A: ALL MAJOR RELIGIONS OVER TIME
-- ════════════════════════════════════════════════════════════════════════════

-- ── A1. Global adherents by religion 1910 → 2050 (absolute + % of world) ─────
-- The foundational chart. Shows every religion's trajectory on one canvas.
-- Source: Pew 2015 world-level aggregates.
-- Use for: Multi-line chart in Tableau (Year on X, adherents or % on Y, Religion as colour)

SELECT
    dy.year,
    dr.religion_name,
    frp.affiliated_count                                        AS global_adherents,
    ROUND(frp.affiliated_count::NUMERIC / 1e6, 0)              AS adherents_millions,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)              AS pct_of_world,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3  = 'WLD'
  AND frp.source = 'pew_key_figures'
  AND dr.religion_name NOT IN ('Any Religion')
ORDER BY dy.year, frp.affiliated_count DESC NULLS LAST;


-- ── A2. Religion share of world population — the race ────────────────────────
-- Which religions are growing as a share of humanity? Which are shrinking?
-- Key tension: Islam + Christianity both growing. Unaffiliated is tiny globally.

WITH world_pop AS (
    -- Use the sum across religions as a proxy for world population per year
    SELECT dy.year, SUM(frp.affiliated_count) AS total
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dc.iso3      = 'WLD'
      AND frp.source   = 'pew_key_figures'
    GROUP BY dy.year
)
SELECT
    dy.year,
    dr.religion_name,
    frp.affiliated_count                                              AS adherents,
    ROUND(frp.affiliated_count::NUMERIC / NULLIF(wp.total,0) * 100, 1) AS pct_of_world,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
JOIN world_pop    wp ON dy.year         = wp.year
WHERE dc.iso3      = 'WLD'
  AND frp.source   = 'pew_key_figures'
  AND dr.religion_name NOT IN ('Any Religion', 'Other Religion')
ORDER BY dy.year, pct_of_world DESC;


-- ── A3. Growth index — how many times larger is each religion in 2050 vs 1910? ─
-- Single number per religion: 2050 adherents / 1910 adherents.
-- Instantly shows which religions are expanding and which are holding.

WITH anchors AS (
    SELECT
        dr.religion_name,
        MAX(frp.affiliated_count) FILTER (WHERE dy.year = 1910) AS count_1910,
        MAX(frp.affiliated_count) FILTER (WHERE dy.year = 2010) AS count_2010,
        MAX(frp.affiliated_count) FILTER (WHERE dy.year = 2050) AS count_2050
    FROM fact_religious_population frp
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dc.iso3    = 'WLD'
      AND frp.source = 'pew_key_figures'
    GROUP BY dr.religion_name
)
SELECT
    religion_name,
    ROUND(count_1910::NUMERIC / 1e6, 0)                            AS adherents_1910_M,
    ROUND(count_2010::NUMERIC / 1e6, 0)                            AS adherents_2010_M,
    ROUND(count_2050::NUMERIC / 1e6, 0)                            AS adherents_2050_M,
    ROUND(count_2050::NUMERIC / NULLIF(count_1910, 0), 1)          AS growth_multiple_1910_to_2050,
    ROUND((count_2050 - count_1910)::NUMERIC / 1e6, 0)             AS net_new_adherents_M
FROM anchors
WHERE count_1910 IS NOT NULL AND count_2050 IS NOT NULL
ORDER BY growth_multiple_1910_to_2050 DESC;


-- ── A4. Islam vs Christianity: the two-religion race ─────────────────────────
-- Both are universalising religions with conversion mandates.
-- By 2050 Pew projects Islam to be close to Christianity in total numbers.
-- This is a striking standalone chart for the article.

SELECT
    dy.year,
    MAX(frp.affiliated_count) FILTER (WHERE dr.religion_name = 'Christianity')  AS christian_count,
    MAX(frp.affiliated_count) FILTER (WHERE dr.religion_name = 'Islam')         AS muslim_count,
    ROUND(MAX(frp.affiliated_count) FILTER (WHERE dr.religion_name = 'Christianity')::NUMERIC / 1e9, 2) AS christians_B,
    ROUND(MAX(frp.affiliated_count) FILTER (WHERE dr.religion_name = 'Islam')::NUMERIC / 1e9, 2)        AS muslims_B,
    BOOL_OR(frp.is_projection)                                                   AS is_projection
FROM fact_religious_population frp
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3      = 'WLD'
  AND frp.source   = 'pew_key_figures'
  AND dr.religion_name IN ('Christianity', 'Islam')
GROUP BY dy.year
ORDER BY dy.year;


-- ════════════════════════════════════════════════════════════════════════════
-- PART B: CHRISTIANITY DEEP DIVE — MOVEMENT OVER TIME
-- ════════════════════════════════════════════════════════════════════════════

-- ── B1. Christianity by region 1910 → 2050 (absolute + % of global Christians) ─
-- The full regional breakdown. This is the primary chart for H2 but also
-- works as a standalone "where is Christianity?" story.

WITH regional AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.country_name ILIKE '%sub-saharan%'
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
            ELSE NULL
        END                                                    AS region_group,
        SUM(frp.affiliated_count)                              AS christians,
        BOOL_OR(frp.is_projection)                             AS is_projection
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
      AND region_group IS NOT NULL
    GROUP BY dy.year, region_group
),
totals AS (
    SELECT year, SUM(christians) AS world_christians
    FROM regional GROUP BY year
)
SELECT
    r.year,
    r.region_group,
    ROUND(r.christians::NUMERIC / 1e6, 0)                          AS christians_M,
    ROUND(r.christians::NUMERIC / NULLIF(t.world_christians,0) * 100, 1) AS pct_of_world_christians,
    r.is_projection
FROM regional r
JOIN totals   t USING (year)
ORDER BY r.year, pct_of_world_christians DESC;


-- ── B2. Christianity's centre of gravity — a single annual metric ─────────────
-- For each decade, which region holds the plurality of the world's Christians?
-- Simple "who's the biggest" table that tells the migration story in one glance.

WITH regional AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.country_name ILIKE '%sub-saharan%'
              OR dc.region ILIKE '%africa%'                    THEN 'Sub-Saharan Africa'
            WHEN dc.country_name ILIKE '%europe%'
              OR dc.region ILIKE '%europe%'                    THEN 'Europe'
            WHEN dc.country_name ILIKE '%latin%'
              OR dc.region ILIKE '%latin%'                     THEN 'Latin America & Caribbean'
            WHEN dc.country_name ILIKE '%north america%'
              OR dc.region ILIKE '%north america%'             THEN 'North America'
            WHEN dc.country_name ILIKE '%asia%'
              OR dc.region ILIKE '%asia%'
              OR dc.region ILIKE '%pacific%'                   THEN 'Asia-Pacific'
            ELSE NULL
        END                                                    AS region_group,
        SUM(frp.affiliated_count)                              AS christians
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
      AND region_group IS NOT NULL
    GROUP BY dy.year, region_group
)
SELECT DISTINCT ON (year)
    year,
    region_group  AS leading_region,
    ROUND(christians::NUMERIC / 1e6, 0) AS christians_M
FROM regional
ORDER BY year, christians DESC;


-- ── B3. Top 10 Christian countries — 1910 vs 2010 vs 2050 ────────────────────
-- The country-level version of the migration story.
-- In 1910: Germany, Russia, USA, UK dominate. In 2050: Nigeria, DRC, Ethiopia.

SELECT
    dc.country_name,
    dc.iso3,
    dc.region,
    dy.year,
    ROUND(frp.affiliated_count::NUMERIC / 1e6, 0)              AS christians_M,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)              AS pct_of_country,
    frp.is_projection,
    RANK() OVER (
        PARTITION BY dy.year
        ORDER BY frp.affiliated_count DESC NULLS LAST
    )                                                          AS rank_that_year
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dr.religion_name = 'Christianity'
  AND frp.source IN ('pew_2015_seed', 'pew_key_figures')
  AND dy.year IN (2010, 2050)
  AND LENGTH(dc.iso3) = 3           -- exclude regional aggregates
  AND frp.affiliated_count IS NOT NULL
ORDER BY dy.year, rank_that_year
LIMIT 30;                           -- top 15 per year


-- ── B4. Tableau source: full religion timeline (all religions, all years) ──────
-- [TABLEAU SOURCE: tableau_all_religions_timeline]
-- Use for: Multi-line chart or stacked area — Year on X, value on Y,
--          Religion as colour. Add "is_projection" as a line style filter
--          (solid = actual, dashed = projection).

SELECT
    dy.year,
    dr.religion_name,
    dr.propagation_model,
    ROUND(frp.affiliated_count::NUMERIC / 1e6, 0)              AS adherents_millions,
    ROUND(frp.affiliated_pct_country::NUMERIC, 1)              AS pct_of_world,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3      = 'WLD'
  AND frp.source   = 'pew_key_figures'
  AND dr.religion_name NOT IN ('Any Religion', 'Other Religion')
ORDER BY dy.year, frp.affiliated_count DESC NULLS LAST;


-- ── B5. Tableau source: Christianity by region, full timeline ──────────────────
-- [TABLEAU SOURCE: tableau_christianity_by_region_timeline]
-- Use for: Stacked area chart — the hero H2 visualisation.
--          Year on X, Christians (millions) on Y, Region as colour stack.
--          Add a reference line at year=2010 to mark the Africa/Europe crossover.

WITH regional AS (
    SELECT
        dy.year,
        CASE
            WHEN dc.country_name ILIKE '%sub-saharan%'
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
            ELSE NULL
        END                                                    AS region_group,
        SUM(frp.affiliated_count)                              AS christians,
        BOOL_OR(frp.is_projection)                             AS is_projection
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND dc.iso3 != 'WLD'
      AND frp.source IN ('pew_key_figures', 'pew_2015_seed')
      AND region_group IS NOT NULL
    GROUP BY dy.year, region_group
)
SELECT
    year,
    region_group,
    ROUND(christians::NUMERIC / 1e6, 0)   AS christians_M,
    christians                             AS christians_exact,
    is_projection
FROM regional
ORDER BY year, christians DESC;
