from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


def _ensure_ingestion_service_package() -> None:
    # Allow running tests without installing `ingestion_service` into the active environment.
    if "ingestion_service" in sys.modules:
        return

    package_root = Path(__file__).resolve().parents[1] / "src"
    module = types.ModuleType("ingestion_service")
    module.__file__ = str(package_root / "__init__.py")
    module.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["ingestion_service"] = module


def _ensure_bt_common_package() -> None:
    # Allow running tests without installing `bt_common` into the active environment.
    if "bt_common" in sys.modules:
        return

    repo_root = Path(__file__).resolve().parents[3]
    package_root = repo_root / "packages" / "bt_common" / "src"
    module = types.ModuleType("bt_common")
    module.__file__ = str(package_root / "__init__.py")
    module.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["bt_common"] = module


_ensure_ingestion_service_package()
_ensure_bt_common_package()


@pytest.fixture
def anyio_backend() -> str:
    # Ensure `pytest.mark.anyio` runs on asyncio (not trio) since the code under
    # test uses `asyncio` primitives.
    return "asyncio"
