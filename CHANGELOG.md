# Changelog

All notable changes to the Xplainable MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MCP `readOnlyHint`/`destructiveHint` tool annotations, derived from the
  client registry's read/write categories

### Changed
- Flat tool surface of 42 tools: 36 generated at runtime from the
  xplainable-client `@mcp_tool` registry, plus 3 team tools and 3 docs
  tools

### Removed
- 3-tier tag filtering: the `XPLAINABLE_ADVANCED_TOOLS` and
  `XPLAINABLE_GUIDED_TOOLS` environment variables are gone; all tools are
  always exposed
- `workflow_*` tools, `agentic_*` lifecycle tools,
  `workflow_get_run_charts`, `get_workflows`, and `list_tools`

## [0.1.0] - 2024-09-01

### Added
- Initial release with core functionality
- 10 read-only tools:
  - `get_connection_info` - Get connection diagnostics
  - `list_team_models` - List team models
  - `get_model` - Get model details
  - `list_model_versions` - List model versions
  - `list_deployments` - List deployments
  - `get_active_team_deploy_keys_count` - Get deploy key count
  - `list_preprocessors` - List preprocessors
  - `get_preprocessor` - Get preprocessor details
  - `get_collection_scenarios` - List collection scenarios
  - `misc_get_version_info` - Get version information
- 4 write tools (when enabled):
  - `generate_deploy_key` - Generate deployment keys
  - `activate_deployment` - Activate deployments
  - `deactivate_deployment` - Deactivate deployments
  - `gpt_generate_report` - Generate GPT reports
- Docker and docker-compose configuration
- Comprehensive documentation
- Security best practices implementation

### Dependencies
- fastmcp >= 0.2.0
- xplainable-client >= 1.0.0
- pydantic >= 2.0.0
- python-dotenv >= 1.0.0
- httpx >= 0.24.0

### Compatibility
- Python 3.9+
- Xplainable Client 1.0.0+
- MCP Protocol 1.0

[Unreleased]: https://github.com/xplainable/xplainable-mcp-server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/xplainable/xplainable-mcp-server/releases/tag/v0.1.0