"""The ticker universe file and the resumable scan checkpoint."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_RE_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


@dataclass(frozen=True, slots=True)
class UniverseEntry:
    ticker: str
    name: str | None = None
    exchange: str | None = None


def load_universe(path: Path | str) -> list[UniverseEntry]:
    """Parse ``TICKER,Company Name,Exchange`` lines. Blank lines, comments and junk are skipped."""
    entries: list[UniverseEntry] = []
    seen: set[str] = set()
    for raw in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        ticker = parts[0].upper()
        if not _RE_TICKER.match(ticker) or ticker in seen:
            continue
        seen.add(ticker)
        entries.append(
            UniverseEntry(
                ticker=ticker,
                name=(parts[1] or None) if len(parts) > 1 else None,
                exchange=(parts[2] or None) if len(parts) > 2 else None,
            )
        )
    return entries


class Checkpoint:
    """Remembers how far a scan got so ``--resume`` can pick up where it stopped."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return set()
        return set(data.get("done", []))

    def save(self, done: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"done": sorted(done)}))

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
