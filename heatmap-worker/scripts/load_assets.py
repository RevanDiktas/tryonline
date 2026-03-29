#!/usr/bin/env python3
"""Local CLI: cd heatmap-worker && PYTHONPATH=. python scripts/load_assets.py --body-url ... --garment-url ..."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load_assets import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
