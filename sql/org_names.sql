-- =============================================================================
-- Organization name + type lookup
-- =============================================================================
-- Purpose:
--   Resolve a set of GRID organization ids (funders and research institutions
--   returned by pub_attributes.sql) to names, organization types, ROR ids, and
--   country. The ROR id is the join key to external institutional-prestige
--   datasets. The organizations table is small (~0.12 GiB) and clustered by id,
--   so a filtered lookup is cheap; resolution is done client-side to keep the
--   expensive publications scan to a single pass.
--
-- Parameters:
--   {org_ids}            — quoted, comma-separated GRID organization ids
--   {dimensions_dataset} — project.dataset holding `organizations`
--
-- Source tables:
--   {dimensions_dataset}.organizations
--
-- Output columns:
--   id           — GRID organization id
--   name         — organization name
--   types        — organization type tags (e.g. Government, Education, Nonprofit)
--   ror          — ROR id (preferred), for linking to external prestige data
--   country_code — ISO country code of the organization
--
-- Output grain: one row per organization id
-- =============================================================================
SELECT
  o.id AS id,
  o.name AS name,
  o.types AS types,
  o.external_ids.ror.preferred AS ror,
  o.address.country_code AS country_code
FROM
  `{dimensions_dataset}.organizations` AS o
WHERE
  o.id IN ({org_ids});
