from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


MODEL_TO_FILENAME = {
    "auth.user": "01-auth-user.json",
    "api.stock": "02-api-stock.json",
    "api.syncjoblock": "03-api-syncjoblock.json",
    "api.stockdata": "04-api-stockdata.json",
    "api.wishlist": "05-api-wishlist.json",
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python scripts/split_neon_fixture.py <input_json> <output_dir>",
            file=sys.stderr,
        )
        return 1

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as infile:
        payload = json.load(infile)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in payload:
        model = item.get("model")
        filename = MODEL_TO_FILENAME.get(model)
        if filename:
            grouped[filename].append(item)

    for filename, items in grouped.items():
        output_path = output_dir / filename
        with output_path.open("w", encoding="utf-8") as outfile:
            json.dump(items, outfile, indent=2)
        print(f"Wrote {len(items)} records to {output_path}")

    missing = [
        model
        for model in sorted({item.get("model") for item in payload})
        if model not in MODEL_TO_FILENAME
    ]
    if missing:
        print("Skipped models:", ", ".join(missing))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
