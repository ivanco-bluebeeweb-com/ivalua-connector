"""Ivalua Connector entrypoint for Imperal CLI and web kernel."""
from __future__ import annotations

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

for _module in ("app", "schemas", "ivalua_client", "handlers", "panels", "panels_settings"):
    sys.modules.pop(_module, None)

from app import chat, ext  # noqa: E402,F401
import handlers  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
