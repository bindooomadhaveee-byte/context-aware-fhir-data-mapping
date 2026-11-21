"""Resolve a canonical field from a raw record, tolerating different header names."""
import difflib
import re


def _norm(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def resolve(record, aliases, cutoff=0.8):
    """Exact alias match first, then fuzzy match on the normalised column names."""
    normed = {_norm(k): v for k, v in record.items()}
    for alias in aliases:
        value = normed.get(alias)
        if value not in (None, ""):
            return value
    for alias in aliases:
        for match in difflib.get_close_matches(alias, list(normed), n=1, cutoff=cutoff):
            if normed[match] not in (None, ""):
                return normed[match]
    return None
