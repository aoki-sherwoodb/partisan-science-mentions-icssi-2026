---
name: dsl
description: Conventions for writing Dimensions Search Language (DSL) queries for the Dimensions Analytics API. Use when writing, reviewing, or debugging DSL queries, or working with Dimcli in Python.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Dimensions Search Language (DSL) Skill

## Overview

The DSL is a purpose-built query language for the Dimensions scholarly research database. It is not SQL. Queries follow a `search ... return ...` structure and are accessed via the Dimensions Analytics API, typically through the Dimcli Python client.

## Resources
- [dimcli](https://digital-science.github.io/dimcli/index.html)
- [Dimensions Search Language](https://docs.dimensions.ai/dsl/)
- [API-LAB](https://api-lab.dimensions.ai/)

## Query Structure

- Every DSL query requires both a `search` phrase and at least one `return` phrase
- The `search` phrase defines the document set; the `return` phrase defines what to retrieve
- Whitespace and line breaks are ignored — use indentation for readability

```
search publications
  for "bibliometrics"
  where year >= 2020
return publications [doi + title + year]
```

## File Conventions

- Write DSL queries in dedicated `.sql` files (same convention as GBQ queries)
- Use descriptive filenames (e.g., `pubs_by_org_and_year.sql`, `expert_identification.sql`)
- Include a comment at the top describing the query's purpose and any parameters

## Searching

- Use `for "term"` for full-text relevance-ranked searching
- Use `where` filters for exact field matching (year, DOI, funder acronym, etc.)
- `where` and `for` can be combined in either order — `where` filters are applied first, then `for` scoring is applied to the filtered set
- Use `in title_abstract_only` when full-text search across all fields is unnecessary — it is faster and more precise
- Boolean operators (`AND`, `OR`, `NOT`) can be used within `for` search terms
- Wildcards (`*`) and proximity searches (`~N`) are supported in `for` terms

## Returning Results

- When returning source documents, specify only the fields needed rather than relying on defaults:
  `return publications [doi + title + year]`
- Use fieldsets like `[basics]` or `[extras]` as shorthand for common field groups
- Use facet returns (`return year`, `return funders`, `return research_orgs`) for aggregated counts rather than pulling all records and aggregating in Python — it is faster and uses less API quota
- Multiple `return` phrases can be used in a single query to get different views of the same data

## Pagination and Limits

- Source results can be paginated up to 50,000 rows using `limit` and `skip`
- Facet results are capped at 1,000 rows
- Default return is 20 results — always set an explicit `limit` when you need more
- For extractions exceeding 50,000 records, use iterative/looped queries via Dimcli

## Data Sources

The DSL supports these primary sources: `publications`, `grants`, `patents`, `clinical_trials`, `policy_documents`, `datasets`, `researchers`, `organizations`, `reports`

Each source has its own set of searchable fields, filterable fields, and facets. If an unsupported field name is used, the DSL returns an error with a list of valid fields.

## Dimcli Usage

- Use `dimcli.Dsl().query()` for single queries
- Use Dimcli's loop utilities for batch extractions that exceed single-query limits
- Results convert to pandas DataFrames via `.as_dataframe()` and specialized methods like `.as_dataframe_authors()` and `.as_dataframe_concepts()`
- Use Jupyter magic commands (`%dsl`, `%%dsl`) for interactive exploration in notebooks
- Use `extract_concepts` to identify relevant terms before building concept-based search queries

## MCP Alternative

** NOT FUNCTIONAL!! **

** The MCP Remote is not working. Do not use the MCP if this line is present. ** 

The `dimensions-remote` MCP server is available as an alternative to Dimcli for running DSL
queries and structured searches interactively — no Python environment needed.

**When to prefer MCP over Dimcli:**
- Quick ad-hoc lookups without a notebook or Python session
- Interactive exploration before building a full Dimcli pipeline
- Tasks where you want structured tool outputs rather than raw API responses

**Key tools:**
- `execute_dsl` — run any DSL query string directly
- `search_publications`, `search_grants`, `search_researchers`, `search_patents`,
  `search_organizations`, `search_clinical_trials`, `search_policy_documents` — structured
  searches with built-in filters
- `semantic_search_publications` — embedding-based similarity search

**Field discovery:**
Use the `dimensions://fields/{entityType}` MCP resource (e.g., `dimensions://fields/publications`)
to discover valid field names, aliases, and sort options before writing a query. This is the
fastest way to avoid field-not-found errors without checking the docs.

Dimcli and the MCP server are complementary: use MCP for exploration and one-off queries, Dimcli
for batch extractions, loop patterns, and notebook workflows.

---

## Common Patterns

- **Expert identification**: Extract concepts from a text, then use those concepts to search for researchers
- **Citation analysis**: Retrieve publication IDs, then search for publications that cite them using `reference_ids`
- **Enrichment workflows**: Start with one source (e.g., grants), extract linked IDs (e.g., publication_ids), then query the linked source for metadata