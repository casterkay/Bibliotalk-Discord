from __future__ import annotations

import sys
import types
from pathlib import Path


def _ensure_agents_service_package() -> None:
    if "agents_service" in sys.modules:
        return

    package_root = Path(__file__).resolve().parents[1] / "src"
    module = types.ModuleType("agents_service")
    module.__file__ = str(package_root / "__init__.py")
    module.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["agents_service"] = module


_ensure_agents_service_package()
