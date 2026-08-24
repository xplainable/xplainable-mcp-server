# Xplainable MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server for the
[Xplainable](https://www.xplainable.io) platform. It lets an LLM agent
(Claude, or any MCP client) train, deploy, optimise, and explain
transparent machine-learning models. The agent is the orchestrator: it
inspects the data, decides features and preprocessing, trains, reads the
metrics, and iterates.

Training always runs server-side on the Xplainable platform — the MCP
host never fits a model locally.

## Two Ways to Use It

1. **Hosted** — connect your MCP client to `https://mcp.xplainable.io`
   (OAuth login, no installation).
2. **Local** — run the server yourself over stdio with an Xplainable API
   key. This is what the rest of this README covers.

## Quick Start (Local)

### 1. Get an API key

Create one at [platform.xplainable.io](https://platform.xplainable.io).

### 2a. Claude Code

```bash
claude mcp add xplainable \
  -e XPLAINABLE_API_KEY=your-api-key-here \
  -- uvx --from git+https://github.com/xplainable/xplainable-mcp-server.git xplainable-mcp
```

### 2b. Claude Desktop

Add to your MCP settings file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "xplainable": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/xplainable/xplainable-mcp-server.git", "xplainable-mcp"],
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

No `uv`? Clone and install instead:

```bash
git clone https://github.com/xplainable/xplainable-mcp-server.git
cd xplainable-mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

then use `"command": "/path/to/xplainable-mcp-server/.venv/bin/xplainable-mcp"`
(no args) in the config above.

### 3. Try it

Ask your agent: *"What models and datasets do I have?"* — it should call
`workflow_list_assets`.

## The Iterate Loop

The default (direct-mode) surface puts the agent in control of every
training decision:

1. `workflow_list_assets` — see the team's datasets, models, and
   deployments
2. `datasets_preview_dataset_json(dataset_id)` — inspect columns, types,
   and sample rows; decide the target, columns to drop, and whether
   preprocessing is needed
3. (Optional) `preprocessing_list_available_transformers` →
   `preprocessing_create_preprocessor_from_spec` →
   `preprocessing_preview_from_data` to verify transformed output
4. `models_train_model(dataset_id, target_column, model_name, ...)` —
   synchronous server-side training; returns model/version IDs,
   train/test metrics, and feature importances
5. Inspect: `models_get_feature_info` / `workflow_explain_model`; compare
   train vs test metrics
6. Iterate: `models_refit_model` for hyperparameter tuning, or train
   again with different features / preprocessing
7. `workflow_deploy_model(model_id)` — deploy once satisfied
8. Act on the model: `workflow_predict` (no deployment needed) /
   `workflow_optimise_model` / `workflow_create_report` (+ poll
   `reports_get_job_status`)

## Tool Surface

Tools are generated at server startup from `@mcp_tool`-decorated methods
in the [xplainable-client](https://pypi.org/project/xplainable-client/)
package — there are no checked-in generated files. Each tool carries tags
(`curated`, `guided`, `read`, `write`, ...) that drive a three-tier
surface:

| Tier | Env | Tools | What you get |
|---|---|---|---|
| **Direct** (default) | — | 33 | The iterate loop above: curated training, preprocessing, read, and team-selection tools |
| **Guided** | `XPLAINABLE_GUIDED_TOOLS=1` | 36 | Adds `workflow_train_model` / `workflow_wait_for_update` / `workflow_decide` — a hands-off run of the same agentic pipeline that powers the platform UI |
| **Advanced** | `XPLAINABLE_ADVANCED_TOOLS=1` | ~107 | The full registry, adding write/admin tools for monitors, GPT reports, inference, and low-level agentic run control |

Env values `1`, `true`, and `yes` are accepted; advanced wins if both are
set.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `XPLAINABLE_API_KEY` | yes (local) | API key from platform.xplainable.io |
| `XPLAINABLE_HOST` / `XPLAINABLE_HOSTNAME` | no | Platform host override (defaults to `https://platform.xplainable.io`). Set **both** to the same value. |
| `XPLAINABLE_ORG_ID` / `XPLAINABLE_TEAM_ID` | no | Org/team binding, if your API key is not bound to a team |
| `XPLAINABLE_GUIDED_TOOLS` | no | `1`/`true`/`yes` adds the guided workflow trio (36 tools) |
| `XPLAINABLE_ADVANCED_TOOLS` | no | `1`/`true`/`yes` exposes the full ~107-tool surface |
| `MCP_TRANSPORT` | no | `stdio` (default) or `streamable-http` |
| `LOG_LEVEL` | no | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

See [.env.example](.env.example). The API key is read from the environment
only and is never exposed through a tool.

## CLI

```bash
xplainable-mcp-cli list-tools            # list all available tools
xplainable-mcp-cli validate-config       # check env configuration
xplainable-mcp-cli test-connection       # test API connectivity
xplainable-mcp-cli generate-docs         # generate tool documentation
```

## Docker (HTTP mode)

```bash
cp .env.example .env   # fill in your API key
docker compose up --build
```

The container serves streamable-HTTP on port 8000 with a `/health`
endpoint. For anything beyond localhost, terminate TLS at a reverse proxy.

## Development

```bash
git clone https://github.com/xplainable/xplainable-mcp-server.git
cd xplainable-mcp-server
pip install -e ".[dev]"

pytest            # run tests
ruff check .      # lint
```

### Runtime tool generation

Client-backed tools are generated at import time by
`xplainable_mcp/runtime_tools.py` from the `@mcp_tool` registry in
xplainable-client — there is no sync step. Upgrading the pinned
`xplainable-client` version is all it takes to pick up new or changed
tools; the test suite (`tests/test_surface.py`) pins the per-tier tool
counts so surface changes are always deliberate.

## Compatibility

| MCP Server | xplainable-client | fastmcp |
|---|---|---|
| current (main) | >=1.13.0 | >=2.0.0,<3.0.0 |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).
