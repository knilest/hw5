"""Reset the working database: copy data/campus_customs.db over data/campus_customs_new.db.

The original file is never changed. Run this before every full run.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "data" / "campus_customs.db"
WORKING = ROOT / "data" / "campus_customs_new.db"


def reset_db() -> Path:
    if not ORIGINAL.exists():
        raise FileNotFoundError(f"{ORIGINAL} is missing; unzip data.zip first.")
    shutil.copyfile(ORIGINAL, WORKING)
    return WORKING


if __name__ == "__main__":
    print(f"Reset {reset_db()} from {ORIGINAL.name}")
