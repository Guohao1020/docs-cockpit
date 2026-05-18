"""pytest conftest · shared fixtures + sys.path insertion.

0.11.0-alpha.1:plan §11 Step 1 引入 pytest 测试基础。
"""

from __future__ import annotations

import pathlib
import sys

# 确保 docs_cockpit 可以 import 即使没 pip install -e
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
