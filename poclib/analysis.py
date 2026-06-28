"""Attribute summaries and minimalist plots for amplified-publication sets.

Functions take tidy DataFrames (typically the exploded output of
sql/pub_attributes.sql joined to the Congress roster) and produce share tables
and publication-ready figures following the project plotting conventions.
"""
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from . import config

PARTY_COLORS = {"Democrat": "#2E86AB", "Republican": "#BC4749", "Independent": "#6A994E"}
ACCENT = "#2E86AB"


def all_grid_ids(attributes: pd.DataFrame) -> list[str]:
    """Unique GRID ids across the funder_grids + research_grids array columns."""
    ids: set[str] = set()
    for column in ("funder_grids", "research_grids"):
        for arr in attributes[column].dropna():
            ids.update(x for x in arr if x)
    return sorted(ids)


def all_grant_ids(attributes: pd.DataFrame) -> list[str]:
    """Unique Dimensions grant ids across the supporting_grant_ids array column."""
    ids: set[str] = set()
    for arr in attributes["supporting_grant_ids"].dropna():
        ids.update(x for x in arr if x)
    return sorted(ids)


def attach_org_names(attributes: pd.DataFrame, org_lookup: pd.DataFrame) -> pd.DataFrame:
    """Resolve funder/research GRID ids to names + funder types via a lookup table.

    Keeps the heavy publications scan to one pass by doing name resolution
    client-side from the small organizations lookup (org_names.sql output).
    """
    id_to_name = dict(zip(org_lookup["id"], org_lookup["name"]))
    id_to_types = dict(zip(org_lookup["id"], org_lookup["types"]))

    def names(ids) -> list[str]:
        return [id_to_name[i] for i in (ids if ids is not None else []) if i in id_to_name]

    def types(ids) -> list[str]:
        out: set[str] = set()
        for i in ids if ids is not None else []:
            out.update(id_to_types.get(i) or [])
        return sorted(out)

    result = attributes.copy()
    result["funder_names"] = result["funder_grids"].map(names)
    result["funder_types"] = result["funder_grids"].map(types)
    result["research_org_names"] = result["research_grids"].map(names)
    return result


def institutions_long(attributes: pd.DataFrame, org_lookup: pd.DataFrame) -> pd.DataFrame:
    """One row per (publication x affiliated institution) with name, ROR, country.

    Built from the paper-level research_grids (author-affiliation GRID ids) and
    the organizations lookup. The `ror` column is the join key to an external
    institutional-prestige dataset.
    """
    cols = ["id", "name", "ror", "country_code"]
    lookup = org_lookup[cols].rename(columns={"id": "grid_id", "name": "institution_name"})
    exploded = (
        attributes[["pub_id", "research_grids"]]
        .drop_duplicates("pub_id")
        .explode("research_grids")
        .rename(columns={"research_grids": "grid_id"})
        .dropna(subset=["grid_id"])
    )
    result = exploded.merge(lookup, on="grid_id", how="left")
    # bare ROR id (after ror.org/) so it joins prestige data in either URL/id form
    result["ror_id"] = result["ror"].str.rsplit("/", n=1).str[-1]
    return result


def load_prestige(filename: str = "ror_to_institution_prestige.csv") -> pd.DataFrame:
    """Load the ROR-keyed institutional-prestige crosswalk from input-data/."""
    return pd.read_csv(config.INPUT_DIR / filename)


def attach_prestige(institutions: pd.DataFrame, prestige: pd.DataFrame,
                    left_on: str = "ror", right_on: str = "ror_id") -> pd.DataFrame:
    """Join an external ROR-keyed prestige table onto the institutions table.

    Defaults match input-data/ror_to_institution_prestige.csv (full-URL ROR in a
    `ror_id` column + `normalized_ordinal_prestige`). Unmatched rows keep NaN.
    """
    return institutions.merge(prestige, left_on=left_on, right_on=right_on, how="left",
                              suffixes=("", "_prestige"))


def grants_long(attributes: pd.DataFrame, grants: pd.DataFrame,
                org_lookup: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per (publication x supporting grant) with grant + funder details.

    Joins the publications' supporting_grant_ids to the grants lookup
    (grants_for_pubs.sql). If an organizations lookup is supplied, the funder GRID
    is resolved to a name.
    """
    exploded = (
        attributes[["pub_id", "supporting_grant_ids"]]
        .drop_duplicates("pub_id")
        .explode("supporting_grant_ids")
        .rename(columns={"supporting_grant_ids": "grant_id"})
        .dropna(subset=["grant_id"])
    )
    merged = exploded.merge(grants, on="grant_id", how="inner")
    if org_lookup is not None:
        id_to_name = dict(zip(org_lookup["id"], org_lookup["name"]))
        merged["funder_name"] = merged["funder_grid"].map(id_to_name)
    return merged


def extract_domain(url: pd.Series) -> pd.Series:
    """Bare registrable-ish domain from a URL (strip scheme, www., and path)."""
    return (
        url.fillna("")
        .str.replace(r"^https?://", "", regex=True)
        .str.replace(r"^www\.", "", regex=True)
        .str.split("/").str[0]
        .str.lower()
        .replace("", pd.NA)
    )


def load_media_bias(filename: str = "media_bias.csv") -> pd.DataFrame:
    """Load an outlet -> partisan-lean roster from input-data/ (user-supplied).

    Expected columns: an outlet key (`domain` and/or `outlet`) plus a `lean`
    column (e.g. left/center/right or a numeric score).
    """
    return pd.read_csv(config.INPUT_DIR / filename)


def attach_media_bias(news_policy: pd.DataFrame, bias: pd.DataFrame,
                      on: str = "domain") -> pd.DataFrame:
    """Join a media-bias roster onto news/policy mentions by domain (or outlet).

    `news_policy` is the output of news_policy_mentions.sql with a `domain` column
    (add it via extract_domain on the url). Matching is case-insensitive on `on`.
    """
    left = news_policy.copy()
    right = bias.copy()
    left[on] = left[on].astype("string").str.lower()
    right[on] = right[on].astype("string").str.lower()
    return left.merge(right, on=on, how="left", suffixes=("", "_bias"))


def set_plot_style() -> None:
    """Apply the minimalist style used across the project's figures."""
    plt.rcParams["font.size"] = 14
    plt.rcParams["axes.titlesize"] = 16
    plt.rcParams["axes.labelsize"] = 14
    plt.rcParams["axes.titleweight"] = "normal"
    plt.rcParams["axes.labelweight"] = "normal"
    sns.set_palette("colorblind")


def save_fig(fig, stem: str) -> None:
    """Save a figure as both PDF (vector) and PNG (raster) under OUTPUT_DIR."""
    for ext in ("pdf", "png"):
        fig.savefig(config.OUTPUT_DIR / f"{stem}.{ext}", dpi=300, bbox_inches="tight")


def share_table(df: pd.DataFrame, column: str, top_n: int = 15) -> pd.DataFrame:
    """Counts and shares of the values in a column, descending, top_n rows."""
    counts = df[column].dropna().value_counts()
    table = counts.to_frame("count")
    table["share"] = table["count"] / table["count"].sum()
    return table.head(top_n)


def plot_field_distribution(df: pd.DataFrame, field_column: str, top_n: int = 12,
                            title: str = "Fields of amplified research") -> plt.Figure:
    """Horizontal bar chart of the most common research fields."""
    set_plot_style()
    table = share_table(df, field_column, top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(table) + 1.5))
    ax.barh(table.index, table["share"], color=ACCENT, alpha=0.85)
    ax.set_xlabel("Share of amplified publications")
    ax.set_title(title)
    sns.despine(left=True)
    fig.tight_layout()
    return fig


def partisan_field_split(df: pd.DataFrame, field_column: str, party_column: str = "party",
                         top_n: int = 10) -> pd.DataFrame:
    """For each field, the share of amplifying mentions that are R vs D.

    Input grain: one row per (publication x amplifying member). Returns a
    field-by-party share matrix restricted to the most-amplified fields.
    """
    subset = df.dropna(subset=[field_column, party_column])
    top_fields = subset[field_column].value_counts().head(top_n).index
    subset = subset[subset[field_column].isin(top_fields)]
    counts = subset.groupby([field_column, party_column]).size().unstack(fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0)


def plot_partisan_field_split(split: pd.DataFrame,
                              title: str = "Partisan amplification by field") -> plt.Figure:
    """Stacked horizontal bars of party shares per field."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(split) + 1.5))
    left = pd.Series(0.0, index=split.index)
    for party in split.columns:
        color = PARTY_COLORS.get(party, None)
        ax.barh(split.index, split[party], left=left, label=party, color=color, alpha=0.85)
        left += split[party]
    ax.set_xlabel("Share of amplifying mentions")
    ax.set_xlim(0, 1)
    ax.set_title(title)
    ax.legend(loc="lower right", frameon=False, fontsize=11)
    sns.despine(left=True)
    fig.tight_layout()
    return fig
