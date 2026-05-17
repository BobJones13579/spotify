"""Parse Spotify release_date strings for reliable comparisons."""

from datetime import date


def parse_release_date(date_str: str) -> date:
    """
    Spotify uses YYYY, YYYY-MM, or YYYY-MM-DD.
    Year-only → Dec 31 (latest day in year for cutoff comparisons).
    Year-month → last day of month (approximated as day 28 for safety).
    """
    if not date_str:
        return date(1900, 1, 1)

    parts = date_str.split("-")
    try:
        if len(parts) == 1:
            return date(int(parts[0]), 12, 31)
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            return date(y, m, 28)
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return date(y, m, d)
    except (ValueError, IndexError):
        return date(1900, 1, 1)


def is_after_cutoff(release_date_str: str, cutoff_str: str) -> bool:
    """True if release_date is strictly after the cutoff date."""
    if not cutoff_str:
        return True
    return parse_release_date(release_date_str) > parse_release_date(cutoff_str)
