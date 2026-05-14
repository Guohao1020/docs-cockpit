"""CLI 入口 · `python -m docs_cockpit ...`."""
from __future__ import annotations

import sys

from .build import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
