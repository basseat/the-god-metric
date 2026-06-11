-- =============================================================================
-- H3: MEDIA INFRASTRUCTURE DROVE RELIGIOUS GROWTH IN THE GLOBAL SOUTH
-- =============================================================================
-- Hypothesis: The spread of radio (1950s-70s), TV (1980s-90s), and mobile
-- (2000s-present) correlates with Pentecostal/Evangelical growth in
-- Sub-Saharan Africa and Latin America. Media enabled mass religious
-- broadcasting at the exact moment Africa's Christian population exploded.
-- =============================================================================


-- ── Q1. Media penetration trajectory: Sub-Saharan Africa ─────────────────────
-- Shows the three waves of media technology arriving in Africa.
-- Radio → TV → Mobile → Internet: each enabled new forms of religious broadcast.

SELECT
    dc.country_name,
    dc.iso3,
    dy.year,
    ROUND(fmp.radio_per_100::NUMERIC, 1)                       AS radio_per_100,
    ROUND(fmp.tv_per_100::NUMERIC, 1)                          AS tv_per_100,
    ROUND(fmp.mobile_per_100::NUMERIC, 1)                      AS mobile_per_100,
    ROUND(fmp.internet_pct::NUMERIC, 1)                        AS internet_pct
FROM fact_media_penetration fmp
JOIN dim_country dc ON fmp.country_id = dc.country_id
JOIN dim_year    dy ON fmp.year_id    = dy.year_id
WHERE dc.iso3 IN ('NGA','GHA','KEN','ZAF','ETH','TZA','UGA','CMR','SEN')
  AND dy.year IN (1960, 1970, 1980, 1990, 2000, 2005, 2010, 2015, 2020)
ORDER BY dc.country_name, dy.year;


-- ── Q2. Mobile penetration milestone years ────────────────────────────────────
-- For each country: the first year mobile subscriptions crossed 10%, 50%, 100%.
-- Cross-reference with Christianity growth to test H3.

WITH milestones AS (
    SELECT
        dc.country_name,
        dc.iso3,
        dc.region,
        MIN(dy.year) FILTER (WHERE fmp.mobile_per_100 >= 10)  AS year_10pct_mobile,
        MIN(dy.year) FILTER (WHERE fmp.mobile_per_100 >= 50)  AS year_50pct_mobile,
        MIN(dy.year) FILTER (WHERE fmp.mobile_per_100 >= 100) AS year_100pct_mobile,
        MAX(fmp.mobile_per_100)                               AS peak_mobile_per_100
    FROM fact_media_penetration fmp
    JOIN dim_country dc ON fmp.country_id = dc.country_id
    JOIN dim_year    dy ON fmp.year_id    = dy.year_id
    WHERE dc.region ILIKE '%africa%'
       OR dc.iso3 IN ('BRA','COL','MEX','PER','PHL','IND','IDN')
    GROUP BY dc.country_name, dc.iso3, dc.region
)
SELECT *
FROM milestones
WHERE year_10pct_mobile IS NOT NULL
ORDER BY year_10pct_mobile;


-- ── Q3. The media-growth correlation setup ────────────────────────────────────
-- For each African country: compare media penetration to Christianity growth.
-- This is the core scatter-plot for H3 in Tableau.

WITH christian_growth AS (
    SELECT
        dc.iso3,
        dc.country_name,
        dc.region,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2010) AS christian_pct_2010,
        MAX(frp.affiliated_count)       FILTER (WHERE dy.year = 2010) AS christian_count_2010,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2050) AS christian_pct_2050,
        MAX(frp.affiliated_count)       FILTER (WHERE dy.year = 2050) AS christian_count_2050
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Christianity'
      AND frp.source       = 'pew_2015_seed'
    GROUP BY dc.iso3, dc.country_name, dc.region
),
media_2010 AS (
    SELECT
        dc.iso3,
        AVG(fmp.mobile_per_100)  AS mobile_2010,
        AVG(fmp.tv_per_100)      AS tv_2010,
        AVG(fmp.internet_pct)    AS internet_2010
    FROM fact_media_penetration fmp
    JOIN dim_country dc ON fmp.country_id = dc.country_id
    JOIN dim_year    dy ON fmp.year_id    = dy.year_id
    WHERE dy.year BETWEEN 2008 AND 2012
    GROUP BY dc.iso3
)
SELECT
    cg.country_name,
    cg.iso3,
    cg.region,
    ROUND(cg.christian_pct_2010::NUMERIC, 1)    AS christian_pct_2010,
    ROUND(cg.christian_pct_2050::NUMERIC, 1)    AS christian_pct_2050,
    ROUND((cg.christian_pct_2050 - cg.christian_pct_2010)::NUMERIC, 1) AS pct_point_growth,
    ROUND(m.mobile_2010::NUMERIC, 1)             AS mobile_per_100_2010,
    ROUND(m.tv_2010::NUMERIC, 1)                 AS tv_per_100_2010,
    ROUND(m.internet_2010::NUMERIC, 1)           AS internet_pct_2010
FROM christian_growth cg
LEFT JOIN media_2010 m ON cg.iso3 = m.iso3
WHERE cg.christian_pct_2010 IS NOT NULL
ORDER BY pct_point_growth DESC NULLS LAST;


-- ── Q4. Nigeria deep-dive: The model case for H3 ──────────────────────────────
-- Nigeria is the perfect laboratory: it is simultaneously the world's largest
-- Muslim country and one of the fastest-growing Christian nations.
-- Show full media penetration timeline for Nigeria alongside Christian growth.

SELECT
    dy.year,
    ROUND(fmp.radio_per_100::NUMERIC, 1)    AS radio_per_100,
    ROUND(fmp.tv_per_100::NUMERIC, 1)       AS tv_per_100,
    ROUND(fmp.mobile_per_100::NUMERIC, 1)   AS mobile_per_100,
    ROUND(fmp.internet_pct::NUMERIC, 1)     AS internet_pct
FROM fact_media_penetration fmp
JOIN dim_country dc ON fmp.country_id = dc.country_id
JOIN dim_year    dy ON fmp.year_id    = dy.year_id
WHERE dc.iso3 = 'NGA'
ORDER BY dy.year;


-- ── Q5. Internet penetration and religious change: quick correlation ───────────
-- High internet countries: are they more or less religious?
-- Tests whether digital connectivity correlates with secularisation.

WITH latest_media AS (
    SELECT
        dc.iso3,
        dc.country_name,
        dc.region,
        MAX(fmp.internet_pct)   AS internet_pct_2020,
        MAX(fmp.mobile_per_100) AS mobile_per_100_2020
    FROM fact_media_penetration fmp
    JOIN dim_country dc ON fmp.country_id = dc.country_id
    JOIN dim_year    dy ON fmp.year_id    = dy.year_id
    WHERE dy.year BETWEEN 2018 AND 2023
    GROUP BY dc.iso3, dc.country_name, dc.region
),
religiosity_2020 AS (
    SELECT
        dc.iso3,
        frp.affiliated_pct_country AS pct_religious_2020
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Any Religion'
      AND frp.source       = 'owid_pew_aggregate'
      AND dy.year = 2020
)
SELECT
    m.country_name,
    m.iso3,
    m.region,
    ROUND(m.internet_pct_2020::NUMERIC, 1)       AS internet_pct,
    ROUND(m.mobile_per_100_2020::NUMERIC, 1)     AS mobile_per_100,
    ROUND(r.pct_religious_2020::NUMERIC, 1)      AS pct_religious,
    CASE
        WHEN m.internet_pct_2020 > 75 AND r.pct_religious_2020 > 80
            THEN 'High tech + High faith'
        WHEN m.internet_pct_2020 > 75 AND r.pct_religious_2020 < 60
            THEN 'High tech + Low faith'
        WHEN m.internet_pct_2020 < 30 AND r.pct_religious_2020 > 80
            THEN 'Low tech + High faith'
        ELSE 'Mixed'
    END                                          AS tech_faith_quadrant
FROM latest_media m
JOIN religiosity_2020 r ON m.iso3 = r.iso3
WHERE m.internet_pct_2020 IS NOT NULL
  AND r.pct_religious_2020 IS NOT NULL
ORDER BY m.internet_pct_2020 DESC;


-- ── Q6. Sub-Saharan Africa: Media penetration summary table (for article) ──────
-- One clean table for the article showing the media technology timeline
-- across the five largest African Christian countries.

SELECT
    dc.country_name,
    dy.year,
    ROUND(fmp.mobile_per_100::NUMERIC, 0)     AS mobile_per_100,
    ROUND(fmp.tv_per_100::NUMERIC, 0)         AS tv_per_100,
    ROUND(fmp.internet_pct::NUMERIC, 0)       AS internet_pct
FROM fact_media_penetration fmp
JOIN dim_country dc ON fmp.country_id = dc.country_id
JOIN dim_year    dy ON fmp.year_id    = dy.year_id
WHERE dc.iso3 IN ('NGA','COD','ETH','KEN','ZAF')
  AND dy.year IN (1990, 1995, 2000, 2005, 2010, 2015, 2020)
  AND (fmp.mobile_per_100 IS NOT NULL
       OR fmp.tv_per_100 IS NOT NULL
       OR fmp.internet_pct IS NOT NULL)
ORDER BY dc.country_name, dy.year;
