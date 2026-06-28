-- =============================================================================
-- Track B — Publications matching issue keywords
-- =============================================================================
-- Purpose:
--   Fallback to a topic-driven corpus: find publications whose TITLE matches an
--   issue keyword regex (e.g. gender-affirming care, climate/renewables, GMOs,
--   social welfare policy). Returns ids + aggregate Altmetric score so the same
--   pub_attributes.sql analysis can run, and so high- vs low-attention papers
--   can be compared.
--
-- Cost: title-only matching with a {start_year} partition filter scans ~7 GiB.
--   Adding the abstract (LOWER(p.abstract.preferred)) raises this ~10x (~70 GiB)
--   because the abstract column is very large; do that only deliberately, with a
--   higher cap. The {keyword_regex} appears once, keeping the scan to the title.
--
-- Parameters:
--   {keyword_regex}      — case-insensitive RE2 alternation, e.g.
--                          gender.affirming|transgender care|gmo|climate change
--   {dimensions_dataset} — project.dataset holding `publications`
--   {start_year}         — minimum publication year (prunes year partitions)
--   {row_limit}          — LIMIT for the development sample
--
-- Source tables:
--   {dimensions_dataset}.publications
--
-- Output columns:
--   pub_id, doi, title, year, altmetric_score
--
-- Output grain: one row per publication
-- =============================================================================
SELECT
  p.id AS pub_id,
  p.doi AS doi,
  p.title.preferred AS title,
  p.year AS year,
  p.altmetrics.score AS altmetric_score
FROM
  `{dimensions_dataset}.publications` AS p
WHERE
  p.year >= {start_year}
  AND REGEXP_CONTAINS(LOWER(p.title.preferred), r'{keyword_regex}')
LIMIT {row_limit};
