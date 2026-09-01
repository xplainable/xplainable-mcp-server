"""Pin env before any test imports xplainable_mcp.server (which exits without config).

Mirrors tests/conftest.py: server.py loads config at import time (and exits
without credentials), and load_dotenv() can pick up an ambient .env from a
parent directory. Pin the env here so `pytest evals/tests` is hermetic
regardless of collection order.
"""

import os

os.environ.setdefault("XPLAINABLE_API_KEY", "test-api-key")
os.environ["ENABLE_WRITE_TOOLS"] = "true"
