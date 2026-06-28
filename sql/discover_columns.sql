-- =============================================================================
-- Schema discovery — nested field paths for an arbitrary table
-- =============================================================================
-- Purpose:
--   Enumerate every (possibly nested) field of a table, with type and
--   description, by reading INFORMATION_SCHEMA. Used to confirm the structure
--   of the Altmetric `attention_sources` table, which is not in the bundled
--   YAML schemas.
--
-- Parameters:
--   {project} — GBQ project of the target dataset
--   {dataset} — dataset name (without project prefix)
--   {table}   — table name to describe
--
-- Source tables:
--   {project}.{dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS
--
-- Output columns:
--   field_path  — dotted path to the (nested) field
--   data_type   — BigQuery type, including STRUCT/ARRAY wrappers
--   description — field description if present
--
-- Output grain: one row per field path
-- =============================================================================
SELECT
  field_path,
  data_type,
  description
FROM
  `{project}.{dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
WHERE
  table_name = '{table}'
ORDER BY
  field_path;
