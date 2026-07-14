# Changelog

All notable changes to the Xplainable MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- XGM v2 as the primary training workflow: 9 `agentic_*` lifecycle tools
  (`agentic_start_run` defaults to `algorithm="xgm"` and `auto_mode=True`,
  polling via `agentic_get_run_state`, decisions, chat, cancel, skip,
  phases, retrain) — training runs server-side on Xplainable's agentic
  pipeline
- 8 optimiser tools (policies / versions / batch runs)

### Changed
- Server instructions and README now feature the v2 workflow; legacy v1
  tools (`models_train_model`, `models_refit_model`) remain for the
  opensource path
- Bumped `xplainable-client` pin to >=1.7.0

### Removed
- `models_create_model_v2` tool (raw-blob persistence stays an internal
  client method; exposing it would bypass server-side-only v2 training)

### Added (initial release)
- Initial implementation of Xplainable MCP Server
- FastMCP-based server architecture
- Read-only tools for models, deployments, preprocessors, and collections
- Optional write tools (disabled by default)
- Comprehensive security features including rate limiting and audit logging
- Docker support with multi-stage builds
- Client synchronization utilities to track API compatibility
- Comprehensive test suite with mocked client
- Quick start script for easy setup
- Claude Desktop configuration example

### Security
- Token-based authentication support
- Environment-based API key management
- Rate limiting per tool and principal
- Audit logging for all operations
- Input validation using Pydantic models

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