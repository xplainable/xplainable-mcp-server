# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously at Xplainable. If you discover a security vulnerability, please follow these steps:

1. **DO NOT** open a public issue
2. Email security@xplainable.io with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

We will acknowledge receipt within 48 hours and provide a detailed response within 5 business days.

## Security Best Practices

### API Key Management

- **Never** commit API keys to version control
- Store API keys in environment variables or secure secret stores
- Rotate API keys regularly
- Use separate API keys for development and production

### Transport Security

- Always use TLS for production deployments
- Validate Origin/Host headers to prevent DNS rebinding
- Use a reverse proxy (nginx, Caddy) for TLS termination

### Authentication

- Enable token-based authentication for all MCP connections
- Use mTLS for enhanced security in private deployments
- Implement rate limiting to prevent abuse

### Deployment

- Run the server as a non-root user
- Use minimal base images for containers
- Keep dependencies up to date
- Enable audit logging for all operations

### Environment Variables

Required security-related environment variables:

```bash
# API Key (required, never expose)
XPLAINABLE_API_KEY=your-secure-key

# Enable/disable write operations
ENABLE_WRITE_TOOLS=false

# Enable rate limiting
RATE_LIMIT_ENABLED=true
```

## Security Features

### Built-in Protection

- Input validation using Pydantic models
- Rate limiting per tool and per principal
- Audit logging of all operations
- Automatic secret redaction in logs
- Request size limits

### Recommended Configuration

For production deployments:

1. Use TLS everywhere
2. Enable rate limiting
3. Disable write tools unless necessary
4. Use token authentication
5. Run behind a reverse proxy
6. Enable comprehensive logging
7. Regular security updates

## Compliance

This server is designed to help meet common compliance requirements:

- SOC 2 Type II
- GDPR
- HIPAA (with appropriate configuration)

For specific compliance questions, contact compliance@xplainable.io