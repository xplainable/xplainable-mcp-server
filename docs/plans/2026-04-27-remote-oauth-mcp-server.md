# Remote Authenticated MCP Server for Claude Desktop Connectors

## Context

The current xplainable MCP server runs locally via stdio transport with a static API key. Users must manually configure it in `claude_desktop_config.json` with their API key.

To add xplainable as a connector in Claude Desktop (and eventually the Anthropic connectors directory), we need to convert it to a **remote MCP server** with **OAuth 2.1 authentication** over **Streamable HTTP transport**. This lets users connect to the production xplainable environment by just clicking "Add connector" and authenticating via their existing xplainable account (Auth0).

## What Needs to Change

| Current | Required |
|---------|----------|
| stdio transport (local process) | Streamable HTTP (public URL) |
| Static API key in env vars | OAuth 2.1 + PKCE |
| Runs on user's machine | Deployed as a public service |
| Manual config in JSON file | One-click connector in Claude Desktop |
| Single user per instance | Multi-user with per-session auth |

## Architecture

```
Claude Desktop / claude.ai
    ↓ (Streamable HTTP + Bearer token)
xplainable Remote MCP Server (public URL)
    ↓ (validates JWT, extracts user context)
xplainable API (platform.xplainable.io)
    ↓
MongoDB / services
```

## Key Requirements

### 1. Transport: Streamable HTTP

The MCP spec (2025-06-18) recommends Streamable HTTP over the deprecated SSE transport. FastMCP supports this natively.

- Single HTTP endpoint (e.g., `https://mcp.xplainable.io/mcp`)
- Bidirectional streaming
- Session management via `Mcp-Session-Id` header
- Works behind load balancers

### 2. Authentication: OAuth 2.1 with Auth0

xplainable already uses Auth0 for frontend authentication. The remote MCP server should use the same Auth0 tenant so users log in with their existing credentials.

**Flow:**
1. User adds connector in Claude Desktop with URL `https://mcp.xplainable.io`
2. Claude discovers OAuth metadata via `/.well-known/oauth-authorization-server`
3. Claude redirects user to Auth0 login (authorization code flow + PKCE)
4. User logs in with existing xplainable credentials
5. Auth0 issues access token (JWT)
6. Claude sends token with every MCP request
7. MCP server validates JWT and extracts user/team context
8. MCP server calls xplainable API on behalf of the authenticated user

### 3. Dynamic Client Registration (DCR)

Claude.ai requires DCR — the ability for Claude to programmatically register as an OAuth client without manual configuration.

**Endpoints needed:**
- `GET /.well-known/oauth-authorization-server` — Returns authorization server metadata
- `POST /register` — Dynamic client registration endpoint
- Standard Auth0 endpoints for authorize/token

FastMCP's `RemoteAuthProvider` handles most of this if Auth0 supports DCR, or the OAuth Proxy pattern can be used if it doesn't.

### 4. Per-User Client Initialization

The current `client_manager.py` creates a single global client with one API key. The remote server needs per-session/per-user clients:

- Extract user identity from the validated JWT
- Auto-generate a scoped API key for that user's session
- Initialize an `XplainableClient` with it
- Cache clients per session to avoid re-initialization on every request

### 5. Deployment

- Public HTTPS endpoint (e.g., `https://mcp.xplainable.io`)
- Could deploy on the same infrastructure as the API (DigitalOcean, etc.)
- Needs to be reachable from Anthropic's cloud infrastructure
- HTTPS is mandatory for OAuth

## Implementation Steps

### Step 1: Upgrade FastMCP and Add OAuth Dependencies

Update `pyproject.toml`:
```
fastmcp>=2.11.1    # Streamable HTTP + RemoteAuthProvider support
authlib             # JWT validation
httpx               # HTTP client for token introspection
```

### Step 2: Add OAuth Configuration

New environment variables:
```
AUTH0_DOMAIN=xplainable.au.auth0.com
AUTH0_AUDIENCE=https://api.xplainable.io
AUTH0_CLIENT_ID=...          # For DCR or pre-registered client
AUTH0_CLIENT_SECRET=...      # If using confidential client
MCP_SERVER_URL=https://mcp.xplainable.io
```

### Step 3: Implement Remote Auth Provider

Using FastMCP's `RemoteAuthProvider` pattern:

```python
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider

auth_provider = RemoteAuthProvider(
    issuer=f"https://{AUTH0_DOMAIN}/",
    audience=AUTH0_AUDIENCE,
    # If Auth0 supports DCR:
    dynamic_registration=True,
    # OR if using OAuth proxy pattern:
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
)

mcp = FastMCP(
    name="xplainable-mcp",
    version="1.0.0",
    auth=auth_provider,
    transport="streamable-http",
)
```

### Step 4: Per-User Client Manager

Replace global client with per-request user context:

```python
from fastmcp import Context

@mcp.tool()
async def models_list_team_models(ctx: Context):
    # Extract user from validated JWT
    user_token = ctx.access_token
    client = get_or_create_client(user_token)
    return client.models.list_team_models()
```

### Step 5: Add Discovery Endpoints

FastMCP handles these automatically when `auth` is configured:
- `GET /.well-known/oauth-authorization-server`
- `GET /.well-known/oauth-protected-resource`

### Step 6: Deploy as Public Service

Options:
- **DigitalOcean App Platform** (consistent with existing infra)
- **Docker + nginx** (using existing Docker setup as base)
- **Cloudflare Workers** (edge deployment)

### Step 7: Register with Claude Desktop

Users add via: Settings → Connectors → "Add custom connector"
- URL: `https://mcp.xplainable.io`
- OAuth Client ID: (auto-discovered via DCR, or pre-configured)

### Step 8: Submit to Anthropic Connectors Directory

Complete the "desktop extensions interest form" for review and listing in the official directory.

## Files to Modify/Create

| File | Action |
|------|--------|
| `pyproject.toml` | Update dependencies (fastmcp, authlib) |
| `xplainable_mcp/server.py` | Add auth provider, switch to streamable-http |
| `xplainable_mcp/client_manager.py` | Per-user client initialization from JWT |
| `xplainable_mcp/auth.py` | New — JWT validation, user context extraction |
| `xplainable_mcp/mcp_instance.py` | Update to include auth config |
| `xplainable_mcp/tools/*.py` | Add `ctx: Context` param to extract user |
| `Dockerfile` | Update for HTTP server (expose port) |
| `docker-compose.yml` | Update deployment config |

## Decisions Made

1. **API key mapping** — Auto-generate a scoped API key per OAuth session. When a user authenticates via Auth0, the MCP server calls the xplainable API to create a temporary API key for that user, then initializes an `XplainableClient` with it. Key is cached for the session duration.

2. **DCR support** — TBD (needs Auth0 tenant check). Plan supports both paths:
   - **If DCR available**: Use FastMCP's `RemoteAuthProvider` with DCR enabled
   - **If no DCR**: Pre-register Claude as an OAuth client in Auth0, use the OAuth proxy pattern with a fixed client_id/secret

## Remaining Considerations

1. **Existing tool signatures** — All 40+ tools currently call `get_client()` which returns the global client. They all need updating to accept a context parameter for per-user auth. This is mechanical but touches every tool file.

2. **Backward compatibility** — The server should still support stdio + API key mode for local development. FastMCP can support both transports — the auth provider is only active in HTTP mode.

3. **API key lifecycle** — Auto-generated session keys need an expiry and cleanup strategy. Could use the existing API key system with a short TTL, or create a dedicated "MCP session key" type.

## Effort Estimate

| Phase | Effort | Details |
|-------|--------|---------|
| FastMCP upgrade + HTTP transport | 1 day | Dependency update, transport switch |
| OAuth/Auth0 integration | 1-2 days | Auth provider, JWT validation, DCR |
| Per-user client manager | 1 day | Session-scoped clients, API key generation |
| Update 40+ tool functions | 1-2 days | Mechanical but thorough — add context param |
| Deployment + infrastructure | 1 day | Public HTTPS, DNS, Docker |
| E2E testing | 1 day | OAuth flow, MCP Inspector, Claude Desktop |
| **Total** | **~1-2 weeks** | |

## Verification

1. Start remote server locally: `uvicorn xplainable_mcp.server:app --port 8000`
2. Test OAuth flow with MCP Inspector
3. Add as custom connector in Claude Desktop with `http://localhost:8000`
4. Verify tools work with authenticated user context
5. Deploy to public URL and test from Claude Desktop
6. Submit to Anthropic connectors directory

## References

- [MCP Transports Specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [FastMCP Remote OAuth Documentation](https://gofastmcp.com/servers/auth/remote-oauth)
- [Claude Custom Connectors Guide](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
- [Anthropic Connectors Directory FAQ](https://support.claude.com/en/articles/11596036-anthropic-connectors-directory-faq)
