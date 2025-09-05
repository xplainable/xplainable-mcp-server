"""
MCP Tools for xplainable-client.

This module auto-imports all service-specific tool modules.
"""

# Import all service tools
from . import autotrain
from . import collections
from . import datasets
from . import deployments
from . import gpt
from . import inference
from . import misc
from . import models
from . import preprocessing

# All tools are automatically registered via the @mcp.tool() decorators
