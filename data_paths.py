"""Locate a processed quarter file, gzipped or plain.

The aggregates are stored gzipped so the repository stays small; pandas reads
either form transparently. Regenerating from the raw BTS ZIPs writes gzip too,
so a fresh run and a clone behave identically.
"""
from pathlib import Path


def quarter_file(directory: Path, year: int, quarter: int) -> Path:
    """Return the path to a processed quarter, preferring the gzipped copy."""
    stem = f"DB1BMarket_{year}_{quarter}"
    for suffix in (".csv.gz", ".csv"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Missing {stem}.csv.gz in {directory}; process the raw BTS quarter first")
