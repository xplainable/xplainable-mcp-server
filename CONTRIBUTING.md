# Contributing to Xplainable MCP Server

Thank you for your interest in contributing to the Xplainable MCP Server! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept responsibility for mistakes

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear reproduction steps
4. Include relevant system information

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation as needed
7. Commit with clear messages
8. Push to your fork
9. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/xplainable/xplainable-mcp-server
cd xplainable-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=xplainable_mcp --cov-report=html

# Run specific test file
pytest tests/test_server.py

# Run with verbose output
pytest -v
```

### Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

Run these before submitting:

```bash
# Format code
black xplainable_mcp tests

# Lint code
ruff check xplainable_mcp tests

# Type check
mypy xplainable_mcp
```

### Adding New Tools

When adding new MCP tools:

1. Follow the existing pattern in `server.py`
2. Add comprehensive docstrings
3. Include type hints
4. Add tests for the new tool
5. Update the README with tool documentation
6. Consider security implications

Example:

```python
@mcp.tool()
def new_tool(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """
    Brief description of what the tool does.
    
    Args:
        param1: Description of param1
        param2: Optional description of param2
        
    Returns:
        Dictionary containing the result
    """
    try:
        client = get_client()
        result = client.module.method(param1, param2)
        logger.info(f"Executed new_tool with param1={param1}")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error in new_tool: {e}")
        raise
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Include type hints for better IDE support
- Update compatibility matrix when needed

### Commit Messages

Follow conventional commit format:

```
feat: Add new dataset listing tool
fix: Correct rate limiting calculation
docs: Update installation instructions
test: Add tests for deployment tools
refactor: Simplify error handling
```

### Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG.md
4. Request review from maintainers
5. Address review feedback
6. Squash commits if requested

## Synchronization with Xplainable Client

When the xplainable-client is updated:

1. Run the sync utility to check compatibility:
   ```bash
   python -m xplainable_mcp.sync_utils
   ```

2. Review missing tools and implement as needed

3. Update the compatibility matrix in README

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish to PyPI
5. Build and push Docker images

## Questions?

- Open a discussion for general questions
- Contact the maintainers for sensitive issues
- Join our community Discord for real-time help

Thank you for contributing!