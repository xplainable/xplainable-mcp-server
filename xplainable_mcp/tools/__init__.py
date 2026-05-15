"""
MCP Tools for xplainable-client.

This module auto-imports all service-specific tool modules.
"""

# Import all service tools
from . import autotrain
from . import datasets
from . import deployments
from . import docs
from . import gpt
from . import inference
from . import misc
from . import models
from . import monitors
from . import preprocessing
from . import reports
from . import runs

# All tools are automatically registered via the @mcp.tool() decorators
