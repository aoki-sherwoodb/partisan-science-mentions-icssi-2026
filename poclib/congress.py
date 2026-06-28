"""Build the current US Congress roster with party and social-media handles.

Source: the public `unitedstates/congress-legislators` project. We join the
legislator records (name, party, chamber via most-recent term) to the
social-media file (Twitter/X, Bluesky handles) to get a table we can match
against Altmetric mention authors.
"""
import io

import pandas as pd
import requests
import yaml

from . import config

LEGISLATORS_URL = (
    "https://unitedstates.github.io/congress-legislators/legislators-current.yaml"
)
SOCIAL_MEDIA_URL = (
    "https://unitedstates.github.io/congress-legislators/legislators-social-media.yaml"
)

CHAMBER_BY_TERM_TYPE = {"sen": "Senate", "rep": "House"}


def _load_yaml_cached(url: str, cache_name: str, refresh: bool = False) -> list:
    """Download a YAML file, caching the raw bytes under OUTPUT_DIR."""
    cache_path = config.OUTPUT_DIR / cache_name
    if cache_path.exists() and not refresh:
        return yaml.safe_load(cache_path.read_text())
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    cache_path.write_text(response.text)
    return yaml.safe_load(io.StringIO(response.text))


def load_roster(refresh: bool = False) -> pd.DataFrame:
    """Return one row per current legislator with party, chamber, and handles.

    Columns: bioguide, full_name, party, chamber, state, twitter, twitter_id,
    bluesky. Handles are lowercased (twitter) for case-insensitive matching.
    """
    legislators = _load_yaml_cached(LEGISLATORS_URL, "legislators-current.yaml", refresh)
    social = _load_yaml_cached(SOCIAL_MEDIA_URL, "legislators-social-media.yaml", refresh)

    social_by_bioguide = {
        entry["id"]["bioguide"]: entry.get("social", {})
        for entry in social
        if "bioguide" in entry.get("id", {})
    }

    records = []
    for person in legislators:
        bioguide = person["id"].get("bioguide")
        if bioguide is None:
            continue
        latest_term = person["terms"][-1]
        handles = social_by_bioguide.get(bioguide, {})
        twitter = handles.get("twitter")
        bluesky = handles.get("bluesky")
        records.append(
            {
                "bioguide": bioguide,
                "full_name": person["name"].get("official_full")
                or f"{person['name'].get('first', '')} {person['name'].get('last', '')}".strip(),
                "party": latest_term.get("party"),
                "chamber": CHAMBER_BY_TERM_TYPE.get(latest_term.get("type"), latest_term.get("type")),
                "state": latest_term.get("state"),
                "twitter": twitter.lower() if isinstance(twitter, str) else None,
                "twitter_id": handles.get("twitter_id"),
                "bluesky": bluesky.lower() if isinstance(bluesky, str) else None,
            }
        )
    return pd.DataFrame(records)


def handle_party_map(roster: pd.DataFrame) -> dict[str, dict]:
    """Map each lowercased handle (twitter and bluesky) to member metadata.

    Lets the analysis label an Altmetric mention author with name/party/chamber.
    """
    mapping: dict[str, dict] = {}
    for _, row in roster.iterrows():
        member = {
            "bioguide": row["bioguide"],
            "full_name": row["full_name"],
            "party": row["party"],
            "chamber": row["chamber"],
            "state": row["state"],
        }
        for handle in (row["twitter"], row["bluesky"]):
            if handle:
                mapping[handle] = member
    return mapping


def lowercased_handle_set(roster: pd.DataFrame) -> set[str]:
    """All non-null twitter + bluesky handles, lowercased, for an IN(...) filter."""
    handles = set(roster["twitter"].dropna()) | set(roster["bluesky"].dropna())
    return {h for h in handles if h}
