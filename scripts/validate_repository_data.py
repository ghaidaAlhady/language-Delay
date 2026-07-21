"""Validate normalized dataset formats without modifying source workbooks."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"


def main() -> None:
    with (DATASET / "dataset.json").open(encoding="utf-8") as handle:
        json_rows = json.load(handle)
    with (DATASET / "dataset.jsonl").open(encoding="utf-8") as handle:
        jsonl_rows = [json.loads(line) for line in handle if line.strip()]
    with (DATASET / "dataset.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    if not json_rows:
        raise ValueError("dataset.json is empty")
    if len(json_rows) != len(jsonl_rows) or len(json_rows) != len(csv_rows):
        raise ValueError(
            f"Dataset counts differ: json={len(json_rows)}, "
            f"jsonl={len(jsonl_rows)}, csv={len(csv_rows)}"
        )
    required_sources = {f"KB{i:02d}.xlsx" for i in range(1, 6)}
    actual_sources = {row.get("source") for row in json_rows}
    missing = required_sources - actual_sources
    if missing:
        raise ValueError(f"Missing knowledge-base sources: {sorted(missing)}")
    print(f"Validated {len(json_rows)} normalized records from KB01–KB05.")


if __name__ == "__main__":
    main()
