# Xplainable MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server for the
[Xplainable](https://www.xplainable.io) platform. It lets an LLM agent
(Claude, or any MCP client) train, deploy, optimise, and explain
transparent machine-learning models through a small set of goal-oriented
`workflow_*` tools.

Training runs server-side on Xplainable's agentic pipeline — the MCP host
never fits a model locally.

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

## The Workflow Loop

The curated `workflow_*` tools cover the whole journey:

1. `workflow_list_assets` — find a dataset (and see existing models /
   deployments)
2. `workflow_train_model(dataset_id, goal, model_name)` — returns a `run_id`
3. Loop: `workflow_wait_for_update(run_id)` — narrate progress as events
   arrive; if a decision is pending, relay it to the user and submit their
   answer via `workflow_decide` (the run's two gates: label selection and
   training approval)
4. `workflow_deploy_model(model_id)` — deploy after the run completes
   (there is no deployment gate inside the run)
5. Act on the model: `workflow_optimise_model` / `workflow_predict`
   (scores rows with the trained model via the platform inference route —
   no deployment needed) / `workflow_explain_model` /
   `workflow_create_report`

## Tool Surface

By default the server registers the **curated surface: 28 tools** — the 9
`workflow_*` tools above, plus 16 curated read/health tools across
datasets, models, deployments, optimisers, runs, agentic state, and
gateway health, plus 3 team-selection tools (`list_user_teams`,
`set_active_team`, `select_team`).

Set `XPLAINABLE_ADVANCED_TOOLS=1` (accepted values: `1`, `true`, `yes`) to
register the **full surface (~104 tools)**, adding write/admin tools for
preprocessing, monitors, GPT reports, inference, and low-level agentic run
control.

Tool files under `xplainable_mcp/tools/` are auto-generated from
`@mcp_tool`-decorated client methods (see "Synchronization with
xplainable-client" below) — each tool carries tags (e.g. `curated`,
`workflow`, `read`, `write`) that drive this gating. Do not hand-edit
generated tool files.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `XPLAINABLE_API_KEY` | yes (local) | API key from platform.xplainable.io |
| `XPLAINABLE_HOST` / `XPLAINABLE_HOSTNAME` | no | Platform host override (defaults to `https://platform.xplainable.io`). Set **both** to the same value. |
| `XPLAINABLE_ORG_ID` / `XPLAINABLE_TEAM_ID` | no | Org/team binding, if your API key is not bound to a team |
| `XPLAINABLE_ADVANCED_TOOLS` | no | `1`/`true`/`yes` exposes the full ~104-tool surface |
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

### Synchronization with xplainable-client

Tool files are generated from the
[xplainable-client](https://pypi.org/project/xplainable-client/) package:

```bash
# Check if sync is needed / regenerate tool files
python scripts/sync_workflow.py --sync-files

# Generate a detailed report
python scripts/sync_workflow.py --markdown sync_report.md
```

See [`examples/SYNC_WORKFLOW.md`](examples/SYNC_WORKFLOW.md) and
[`examples/sync_scenarios.md`](examples/sync_scenarios.md) for the full
process. Run the sync with the pinned `xplainable-client` version
installed, and with Python 3.11+.

## Compatibility

| MCP Server | xplainable-client | fastmcp |
|---|---|---|
| current (main) | >=1.8.0 | >=2.0.0,<3.0.0 |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).
