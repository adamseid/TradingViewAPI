from __future__ import annotations

import json
import sys
from pathlib import Path


KEEP_MODELS = {
    "auth.user",
    "api.stock",
    "api.stockdata",
    "api.wishlist",
    "api.syncjoblock",
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python scripts/prepare_neon_fixture.py <input_json> <output_json>",
            file=sys.stderr,
        )
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    encodings = ("utf-8-sig", "utf-16", "utf-8")
    payload = None

    for encoding in encodings:
        try:
            with input_path.open("r", encoding=encoding) as infile:
                payload = json.load(infile)
            break
        except UnicodeError:
            continue

    if payload is None:
        print(
            f"Could not decode {input_path} with supported encodings: {encodings}",
            file=sys.stderr,
        )
        return 1

    filtered = [item for item in payload if item.get("model") in KEEP_MODELS]

    with output_path.open("w", encoding="utf-8") as outfile:
        json.dump(filtered, outfile, indent=2)

    print(
        f"Wrote {len(filtered)} records to {output_path} "
        f"from {len(payload)} total records."
    )
    print("Kept models:", ", ".join(sorted(KEEP_MODELS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
