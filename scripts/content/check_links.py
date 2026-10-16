"""Compatibility entry point: runs the live link-health check.

The implementation, options and CSV report live in scripts/content/link_health.py.

Usage: python scripts/content/check_links.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "link_health", Path(__file__).with_name("link_health.py")
)
assert spec and spec.loader
link_health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link_health)

if __name__ == "__main__":
    raise SystemExit(link_health.main(["--live"]))
