-- =============================================================================
-- Track A — Publications amplified by US members of Congress
-- =============================================================================
-- Purpose:
--   Find Dimensions publications mentioned by social-media / news accounts that
--   belong to current US senators and representatives. Uses the Altmetric
--   three-table model: attention_sources (the account) -> posts (one row per
--   mention, carrying the Dimensions publication ids it references).
--
-- Data model (confirmed via schema discovery):
--   attention_sources : one row per source account
--       .id, .type (tw|bsk|fb|rdt|blog|msm|policy|podcast|...),
--       .social_media.screen_name (the handle), .social_media.followers,
--       .country
--   posts             : one row per mention
--       .attention_source_id -> attention_sources.id
--       .date, .type
--       .identifiers.dimensions.publication_ids (ARRAY<STRING> of Dimensions
--        publication ids)
--
-- Parameters:
--   {altmetric_dataset} — project.dataset holding attention_sources + posts
--   {handles_list}      — quoted, lowercased handles e.g. 'sensanders', 'repaoc'
--   {row_limit}         — LIMIT for the development sample
--
-- Source tables:
--   {altmetric_dataset}.attention_sources
--   {altmetric_dataset}.posts
--
-- Output columns:
--   pub_id       — Dimensions publication id (join key to publications)
--   screen_name  — amplifying account handle (lowercased)
--   channel      — source type (tw=X, bsk=Bluesky, msm=news, blog, policy, ...)
--   followers    — follower count of the account at capture
--   mention_date — date of the post
--
-- Output grain: one row per (publication x amplifying account x post)
-- =============================================================================
WITH congress_sources AS (
  -- accounts whose handle belongs to a member of Congress
  SELECT
    a.id AS attention_source_id,
    LOWER(a.social_media.screen_name) AS screen_name,
    a.type AS channel,
    a.social_media.followers AS followers
  FROM
    `{altmetric_dataset}.attention_sources` AS a
  WHERE
    a.social_media.screen_name IS NOT NULL
    AND LOWER(a.social_media.screen_name) IN ({handles_list})
)
SELECT
  pub_id,
  cs.screen_name AS screen_name,
  cs.channel AS channel,
  cs.followers AS followers,
  pst.date AS mention_date
FROM
  congress_sources AS cs
INNER JOIN
  `{altmetric_dataset}.posts` AS pst
  ON pst.attention_source_id = cs.attention_source_id
-- one row per referenced Dimensions publication; posts referencing only
-- clinical trials / datasets (empty array) are dropped by the inner unnest
CROSS JOIN
  UNNEST(pst.identifiers.dimensions.publication_ids) AS pub_id
LIMIT {row_limit};
