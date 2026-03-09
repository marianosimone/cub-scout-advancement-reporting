"""
List adventure images that are missing under img/.
Naming: img/{den}-2024-{adventure_slug}.jpg (e.g. img/bears-2024-bobcat.jpg).
Run: uv run python list_missing_images.py
"""

import json
import os
import re

JSON_FILE = "requirements.json"
IMG_DIR = "img"
YEAR = "2024"

RANK_IMAGE_PREFIX = {
    "Lion": "lions",
    "Tiger": "tigers",
    "Wolf": "wolves",
    "Bear": "bears",
    "Webelos": "webelos",
    "Arrow of Light": "arrow_of_light",
}


def adventure_slug(adventure: str) -> str:
    """Slug for image filename: lowercase, underscores, parenthetical removed."""
    adv = re.sub(r"\s*\([^)]+\)\s*", " ", adventure).strip()
    adv = adv.replace("'", "").replace(",", "").replace(" ", "_").strip("_")
    return adv.lower() if adv else ""


def expected_image_path(rank: str, adventure: str) -> str:
    """Expected path: img/{den}-2024-{slug}.jpg."""
    den = RANK_IMAGE_PREFIX.get(rank, rank.lower().replace(" ", "_"))
    slug = adventure_slug(adventure)
    return os.path.join(IMG_DIR, f"{den}-{YEAR}-{slug}.jpg")


def main():
    with open(JSON_FILE) as f:
        data = json.load(f)

    missing = []
    for rank, adventures in data.items():
        for adventure_name, adventure_data in adventures.items():
            if not isinstance(adventure_data, dict):
                continue
            path = expected_image_path(rank, adventure_name)
            if not os.path.isfile(path):
                missing.append((rank, adventure_name, path))

    if not missing:
        print("All adventure images are present.")
        return

    print("Missing adventure images (expected path):\n")
    for rank, adventure, path in missing:
        print(f"  {rank} | {adventure}")
        print(f"    {path}")
    print(f"\nTotal missing: {len(missing)}")


if __name__ == "__main__":
    main()
