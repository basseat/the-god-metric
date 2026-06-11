-- =============================================================================
-- H1: THE SECULARISATION THESIS IS WESTERN, NOT GLOBAL
-- =============================================================================
-- Hypothesis: Religion is declining in Western Europe and North America,
-- but growing or stable everywhere else. The "decline of religion" narrative
-- is a projection of Western experience onto the whole world.
-- =============================================================================


-- ── Q1. Global headline: Is religion rising or falling? ──────────────────────
-- Uses OWID aggregate (2010 → 2020) — best for the opening statement
-- Expected: global average stays above 80%, Western outliers pull average down

SELECT
    dy.year,
    ROUND(AVG(frp.affiliated_pct_country)::NUMERIC, 1)    AS avg_pct_religious_globally,
    COUNT(DISTINCT frp.country_id)                         AS countries_in_sample,
    ROUND(MIN(frp.affiliated_pct_country)::NUMERIC, 1)    AS least_religious_country_pct,
    ROUND(MAX(frp.affiliated_pct_country)::NUMERIC, 1)    AS most_religious_country_pct,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
          (ORDER BY frp.affiliated_pct_country)::NUMERIC, 1) AS median_pct
FROM fact_religious_population frp
JOIN dim_year     dy  ON frp.year_id     = dy.year_id
JOIN dim_religion dr  ON frp.religion_id = dr.religion_id
WHERE dr.religion_name = 'Any Religion'
  AND frp.source       = 'owid_pew_aggregate'
  AND dy.year IN (2010, 2020)
GROUP BY dy.year
ORDER BY dy.year;


-- ── Q2. Change by country: Who got more religious, who got less? ──────────────
-- Compares each country's 2010 vs 2020 aggregate religiosity.
-- This is the single most important table for H1 — shows the direction of change.

WITH pivoted AS (
    SELECT
        dc.country_name,
        dc.iso3,
        dc.region,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2010) AS pct_2010,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2020) AS pct_2020
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    WHERE dr.religion_name = 'Any Religion'
      AND frp.source       = 'owid_pew_aggregate'
      AND dy.year IN (2010, 2020)
    GROUP BY dc.country_name, dc.iso3, dc.region
)
SELECT
    country_name,
    iso3,
    region,
    ROUND(pct_2010::NUMERIC, 1)                              AS pct_religious_2010,
    ROUND(pct_2020::NUMERIC, 1)                              AS pct_religious_2020,
    ROUND((pct_2020 - pct_2010)::NUMERIC, 1)                 AS change_pp,
    CASE
        WHEN (pct_2020 - pct_2010) > 1  THEN 'Growing'
        WHEN (pct_2020 - pct_2010) < -1 THEN 'Declining'
        ELSE 'Stable'
    END                                                       AS direction
FROM pivoted
WHERE pct_2010 IS NOT NULL AND pct_2020 IS NOT NULL
ORDER BY (pct_2020 - pct_2010) DESC;


-- ── Q3. Secularisation scorecard by region ────────────────────────────────────
-- Aggregate the country-level changes into a regional summary.
-- Expected: Western Europe / North America declining; Africa, MENA stable/rising.

WITH pivoted AS (
    SELECT
        dc.region,
        dc.country_id,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2010) AS pct_2010,
        MAX(frp.affiliated_pct_country) FILTER (WHERE dy.year = 2020) AS pct_2020
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    WHERE dr.religion_name = 'Any Religion'
      AND frp.source       = 'owid_pew_aggregate'
      AND dy.year IN (2010, 2020)
    GROUP BY dc.region, dc.country_id
)
SELECT
    COALESCE(region, 'Unknown')                                AS region,
    COUNT(*)                                                   AS country_count,
    ROUND(AVG(pct_2010)::NUMERIC, 1)                          AS avg_pct_2010,
    ROUND(AVG(pct_2020)::NUMERIC, 1)                          AS avg_pct_2020,
    ROUND(AVG(pct_2020 - pct_2010)::NUMERIC, 2)               AS avg_change_pp,
    COUNT(*) FILTER (WHERE (pct_2020 - pct_2010) > 1)         AS countries_growing,
    COUNT(*) FILTER (WHERE (pct_2020 - pct_2010) < -1)        AS countries_declining,
    COUNT(*) FILTER (WHERE ABS(pct_2020 - pct_2010) <= 1)     AS countries_stable
FROM pivoted
WHERE pct_2010 IS NOT NULL AND pct_2020 IS NOT NULL
GROUP BY region
ORDER BY avg_change_pp ASC;


-- ── Q4. Top 10 most & least religious countries (2020) ────────────────────────
-- For the "look at the map" moment in the article.

(
    SELECT 'Most religious' AS category, country_name, iso3, region,
           ROUND(affiliated_pct_country::NUMERIC, 1) AS pct_religious_2020
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Any Religion'
      AND frp.source       = 'owid_pew_aggregate'
      AND dy.year = 2020
    ORDER BY affiliated_pct_country DESC
    LIMIT 10
)
UNION ALL
(
    SELECT 'Least religious', country_name, iso3, region,
           ROUND(affiliated_pct_country::NUMERIC, 1)
    FROM fact_religious_population frp
    JOIN dim_country  dc ON frp.country_id  = dc.country_id
    JOIN dim_religion dr ON frp.religion_id = dr.religion_id
    JOIN dim_year     dy ON frp.year_id     = dy.year_id
    WHERE dr.religion_name = 'Any Religion'
      AND frp.source       = 'owid_pew_aggregate'
      AND dy.year = 2020
    ORDER BY affiliated_pct_country ASC
    LIMIT 10
)
ORDER BY category, pct_religious_2020 DESC;


-- ── Q5. Global Islam + Christianity combined trajectory ───────────────────────
-- From Pew regional aggregates: do the two largest religions together
-- account for MORE of the world in 2050 than in 2010?
-- Expected: YES — secularisation is losing ground globally even as it wins locally.

SELECT
    dy.year,
    dr.religion_name,
    SUM(frp.affiliated_count)                                    AS total_adherents,
    ROUND(AVG(frp.affiliated_pct_country)::NUMERIC, 1)           AS avg_pct_world,
    frp.is_projection
FROM fact_religious_population frp
JOIN dim_country  dc ON frp.country_id  = dc.country_id
JOIN dim_religion dr ON frp.religion_id = dr.religion_id
JOIN dim_year     dy ON frp.year_id     = dy.year_id
WHERE dc.iso3 = 'WLD'    -- world aggregate row
  AND dr.religion_name IN ('Christianity', 'Islam', 'Unaffiliated')
  AND frp.source = 'pew_key_figures'
  AND dy.year IN (1910, 1970, 2010, 2020, 2050)
GROUP BY dy.year, dr.religion_name, frp.is_projection
ORDER BY dy.year, total_adherents DESC NULLS LAST;


-- ── Q6. WVS intensity divergence: The West vs the Rest ───────────────────────
-- Even if affiliation % is stable, is *intensity* of belief declining in the West?
-- This supplements H1 with a qualitative dimension.
-- (Requires WVS data — skip if fact_wvs_religiosity is empty)

SELECT
    CASE
        WHEN dc.region ILIKE '%europe%'       THEN 'Western Europe'
        WHEN dc.region ILIKE '%north america%' THEN 'North America'
        WHEN dc.region ILIKE '%africa%'        THEN 'Sub-Saharan Africa'
        WHEN dc.region ILIKE '%latin%'
          OR dc.region ILIKE '%caribbean%'     THEN 'Latin America'
        WHEN dc.region ILIKE '%middle east%'
          OR dc.region ILIKE '%north africa%'  THEN 'Middle East & North Africa'
        WHEN dc.region ILIKE '%asia%'          THEN 'Asia'
        ELSE 'Other'
    END                                                         AS region_group,
    dy.year,
    fw.wave,
    ROUND(AVG(fw.pct_religion_very_important)::NUMERIC, 1)      AS avg_pct_religion_very_important,
    ROUND(AVG(fw.pct_attend_weekly)::NUMERIC, 1)                AS avg_pct_weekly_attendance,
    ROUND(AVG(fw.pct_convinced_atheist)::NUMERIC, 1)            AS avg_pct_atheist,
    COUNT(DISTINCT fw.country_id)                               AS countries_surveyed
FROM fact_wvs_religiosity fw
JOIN dim_country dc ON fw.country_id = dc.country_id
JOIN dim_year    dy ON fw.year_id    = dy.year_id
GROUP BY region_group, dy.year, fw.wave
HAVING COUNT(DISTINCT fw.country_id) >= 3
ORDER BY dy.year, avg_pct_religion_very_important DESC;
