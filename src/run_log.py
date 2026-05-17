"""Structured console output for playlist runs."""

from dataclasses import dataclass, field
from datetime import datetime


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


@dataclass
class SkipBucket:
    """Counts skips by reason for one release."""

    duplicate: int = 0
    quality: int = 0
    manual: int = 0
    quality_examples: list[str] = field(default_factory=list)
    manual_examples: list[str] = field(default_factory=list)
    duplicate_examples: list[str] = field(default_factory=list)

    MAX_EXAMPLES = 2

    def add_duplicate(self, track_name: str) -> None:
        self.duplicate += 1
        if len(self.duplicate_examples) < self.MAX_EXAMPLES:
            self.duplicate_examples.append(track_name)

    def add_quality(self, track_name: str, reason: str) -> None:
        self.quality += 1
        if len(self.quality_examples) < self.MAX_EXAMPLES:
            self.quality_examples.append(f"{track_name} ({reason})")

    def add_manual(self, track_name: str, reason: str) -> None:
        self.manual += 1
        if len(self.manual_examples) < self.MAX_EXAMPLES:
            self.manual_examples.append(f"{track_name} ({reason})")

    def has_skips(self) -> bool:
        return self.duplicate + self.quality + self.manual > 0

    def format_lines(self) -> list[str]:
        lines = []
        if self.duplicate:
            extra = self.duplicate - len(self.duplicate_examples)
            ex = "; ".join(self.duplicate_examples)
            suffix = f" (+{extra} more)" if extra > 0 else ""
            lines.append(f"  skip {self.duplicate} already on playlist — e.g. {ex}{suffix}")
        if self.quality:
            extra = self.quality - len(self.quality_examples)
            ex = "; ".join(self.quality_examples)
            suffix = f" (+{extra} more)" if extra > 0 else ""
            lines.append(f"  skip {self.quality} quality filter — e.g. {ex}{suffix}")
        if self.manual:
            extra = self.manual - len(self.manual_examples)
            ex = "; ".join(self.manual_examples)
            suffix = f" (+{extra} more)" if extra > 0 else ""
            lines.append(f"  skip {self.manual} not a main track — e.g. {ex}{suffix}")
        return lines


@dataclass
class RunTotals:
    releases_before_cutoff: int = 0
    releases_checked: int = 0
    tracks_added: int = 0
    skip_duplicate: int = 0
    skip_quality: int = 0
    skip_manual: int = 0

    def absorb_release(self, added: int, bucket: SkipBucket) -> None:
        self.releases_checked += 1
        self.tracks_added += added
        self.skip_duplicate += bucket.duplicate
        self.skip_quality += bucket.quality
        self.skip_manual += bucket.manual


def format_artists(track: dict) -> str:
    names = [a["name"] for a in track.get("artists", [])]
    return ", ".join(names) if names else "Unknown"
