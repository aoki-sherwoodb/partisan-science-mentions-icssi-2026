-- =============================================================================
-- Publication attributes — funders, authors, institutions, fields
-- =============================================================================
-- Purpose:
--   For a given set of Dimensions publication ids, explode the attributes of
--   interest: research field (ANZSRC FoR, first level), funder GRID ids, research
--   institution GRID ids, author surnames, source, and impact proxies. Returns
--   one row per (publication x first-level FoR field) so it can be joined to the
--   (publication x amplifying member) mention table for partisan-by-field analysis.
--
-- Cost: `publications` is 720+ GiB, range-partitioned by `year`, clustered by
--   (type, id). The data is egress-restricted (no TEMP TABLE / export), so this
--   is a single SELECT that references ONLY the leaf fields we use — notably
--   authors.last_name (not the whole authors record) and category_for.first_level
--   (not all categories). GRID ids are returned as-is and resolved to names with
--   the separate, cheap org_names.sql against the small organizations table.
--   The expensive table is scanned exactly once.
--
-- Parameters:
--   {pub_ids}            — quoted, comma-separated Dimensions publication ids
--   {min_year}          — minimum publication year; prunes year partitions to cut
--                         bytes scanned (e.g. 2010 ~ 44 GiB vs ~80 GiB unpruned).
--                         Amplified pubs older than this are excluded — check the
--                         returned coverage and lower if needed.
--   {dimensions_dataset} — project.dataset holding `publications`
--
-- Source tables:
--   {dimensions_dataset}.publications
--
-- Output columns:
--   pub_id, doi, title, year, source_title, times_cited, field_citation_ratio,
--   altmetric_score, n_authors, n_funders, n_research_orgs, for_code, for_name,
--   funder_grids, research_grids, supporting_grant_ids, author_last_names
--
-- Output grain: one row per (publication x first-level FoR field)
-- =============================================================================
SELECT
  p.id AS pub_id,
  p.doi AS doi,
  p.title.preferred AS title,
  p.year AS year,
  p.source.title AS source_title,
  p.metrics.times_cited AS times_cited,
  p.metrics.field_citation_ratio AS field_citation_ratio,
  p.altmetrics.score AS altmetric_score,
  ARRAY_LENGTH(p.authors) AS n_authors,
  ARRAY_LENGTH(p.funder_orgs) AS n_funders,
  ARRAY_LENGTH(p.research_orgs) AS n_research_orgs,
  for_field.code AS for_code,
  for_field.name AS for_name,
  p.funder_orgs AS funder_grids,
  p.research_orgs AS research_grids,
  p.supporting_grant_ids AS supporting_grant_ids,
  -- author surnames only (avoids scanning the full authors record)
  ARRAY(
    SELECT au.last_name FROM UNNEST(p.authors) AS au
    WHERE au.last_name IS NOT NULL LIMIT 25
  ) AS author_last_names
FROM
  `{dimensions_dataset}.publications` AS p
-- one row per publication x first-level FoR field
LEFT JOIN UNNEST(p.category_for.first_level.full) AS for_field
WHERE
  p.year >= {min_year}
  AND p.id IN ({pub_ids});
