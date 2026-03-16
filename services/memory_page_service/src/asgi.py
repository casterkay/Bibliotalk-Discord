from __future__ import annotations

from memory_page_service.app import create_app
from memory_page_service.config import load_runtime_config

# Uvicorn import target for production deployments (e.g. Cloud Run).
_config = load_runtime_config()
app = create_app(_config)
