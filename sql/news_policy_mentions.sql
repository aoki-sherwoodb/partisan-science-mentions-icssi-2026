-- =============================================================================
-- News + policy mentions of a set of publications
-- =============================================================================
-- Purpose:
--   For a set of Dimensions publications, pull their news (msm) and policy
--   mentions with the outlet / body identity (name, url, country). The url domain
--   is the join key to an external media-bias roster so each news source can be
--   assigned a partisan lean (members of Congress have a party; outlets do not).
--
-- Cost: filtering on posts.type (a clustering key) prunes to the msm+policy
--   blocks (~5% of posts), so this is far cheaper than an unfiltered posts scan.
--
-- Parameters:
--   {altmetric_dataset} — project.dataset holding `posts`
--   {pub_ids}           — quoted, comma-separated Dimensions publication ids
--   {row_limit}         — LIMIT for the development sample
--
-- Source tables:
--   {altmetric_dataset}.posts
--
-- Output columns:
--   pub_id, channel (msm|policy), outlet_name, outlet_country, url, mention_date
--
-- Output grain: one row per (publication x news/policy mention)
-- =============================================================================
SELECT
  pub_id,
  pst.type AS channel,
  pst.attention_source.name AS outlet_name,
  pst.attention_source.country AS outlet_country,
  pst.url AS url,
  pst.date AS mention_date
FROM
  `{altmetric_dataset}.posts` AS pst
CROSS JOIN
  UNNEST(pst.identifiers.dimensions.publication_ids) AS pub_id
WHERE
  pst.type IN ('msm', 'policy')
  AND pub_id IN ({pub_ids})
LIMIT {row_limit};
