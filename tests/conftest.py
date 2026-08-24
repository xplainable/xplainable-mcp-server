"""
Test environment setup.

server.py loads config at import time (and exits without credentials), and
both server.py and client_manager.py call load_dotenv() at import — which can
pick up an ambient .env from a parent directory. Pin the env here, before any
test module (and hence the server) is imported, so the suite is hermetic.
load_dotenv(override=False) will not clobber these.
"""

import os

os.environ.setdefault("XPLAINABLE_API_KEY", "test-api-key")
os.environ["ENABLE_WRITE_TOOLS"] = "true"
# Keep the tool surface deterministic: tests assume the direct-mode default.
os.environ.pop("XPLAINABLE_ADVANCED_TOOLS", None)
os.environ.pop("XPLAINABLE_GUIDED_TOOLS", None)
