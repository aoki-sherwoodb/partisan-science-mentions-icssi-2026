-- =============================================================================
-- Grants supporting a set of publications
-- =============================================================================
-- Purpose:
--   Resolve the supporting_grant_ids of the amplified publications to grant
--   records: funder organization (GRID), funded amount (USD), active period, and
--   activity code. Feeds funder-type / funding-amount analysis and lets us link
--   amplified research back to who paid for it.
--
-- Cost: `grants` is ~39 GiB, range-partitioned by start_year, clustered by
--   (funding_currency, funder_org, id). We select only scalar columns and filter
--   by grant id; dry-run is not reported for linked datasets, so rely on the
--   run_guarded cap.
--
-- Parameters:
--   {grant_ids}          — quoted, comma-separated Dimensions grant ids
--   {dimensions_dataset} — project.dataset holding `grants`
--
-- Source tables:
--   {dimensions_dataset}.grants
--
-- Output columns:
--   grant_id, title, funder_grid, funding_usd, funding_currency,
--   start_year, end_year, activity_code
--
-- Output grain: one row per grant id
-- =============================================================================
SELECT
  g.id AS grant_id,
  g.title AS title,
  g.funder_org AS funder_grid,
  g.funding_usd AS funding_usd,
  g.funding_currency AS funding_currency,
  g.start_year AS start_year,
  g.end_year AS end_year,
  g.activity_code AS activity_code
FROM
  `{dimensions_dataset}.grants` AS g
WHERE
  g.id IN ({grant_ids});
