# Contributing to Cloudify

Thank you for considering contributing to Cloudify! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and collaborative environment.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Logs or error messages

### Suggesting Enhancements

Feature requests are welcome! Please create an issue with:
- Clear description of the feature
- Use cases and benefits
- Potential implementation approach
- Any examples from similar tools

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/cloudify.git
   cd cloudify
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clean, readable code
   - Follow the existing code style
   - Add type hints
   - Include docstrings
   - Update tests

4. **Test your changes**
   ```bash
   # Run unit tests
   pytest tests/unit -v

   # Run linting
   ruff check .
   black --check .
   mypy .
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test changes
   - `refactor:` for code refactoring
   - `chore:` for maintenance tasks

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots if applicable
   - Ensure CI checks pass

## Development Setup

### Prerequisites
- Python 3.10+
- Poetry or pip
- Docker
- GCP SDK

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/cloudify.git
cd cloudify

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_code_analyzer.py

# Run with coverage
pytest --cov=agents --cov-report=html

# Run integration tests (requires GCP credentials)
pytest tests/integration -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .

# All checks
black . && ruff check . && mypy . && pytest
```

## Project Structure

```
Cloudify/
├── agents/           # Agent implementations
├── utils/            # Utility modules
├── templates/        # Deployment templates
├── tests/            # Test files
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
└── migration_orchestrator.py  # Main CLI
```

## Agent Development Guidelines

### Creating a New Agent

1. Inherit from `BaseAgent`
2. Implement `_execute_impl()` method
3. Use event bus for communication
4. Add comprehensive error handling
5. Include logging
6. Write unit tests

Example:

```python
from agents.base_agent import BaseAgent, AgentResult, AgentStatus

class MyNewAgent(BaseAgent):
    def __init__(self, event_bus, config, claude_api_key):
        super().__init__(
            name="MyNewAgent",
            event_bus=event_bus,
            config=config,
            claude_api_key=claude_api_key,
        )

    async def _execute_impl(self) -> AgentResult:
        try:
            # Your implementation here

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={"key": "value"},
            )
        except Exception as e:
            return AgentResult(
                status=AgentStatus.FAILED,
                data={},
                errors=[str(e)],
            )
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Include inline comments for complex logic
- Update configuration examples

## Testing Guidelines

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Use pytest fixtures
- Aim for >80% code coverage

### Integration Tests
- Test end-to-end workflows
- Use real (or containerized) services
- Clean up resources after tests
- Mark as slow tests: `@pytest.mark.slow`

## Style Guide

### Python Style
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use descriptive variable names
- Prefer f-strings over format()

### Docstring Format
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something is wrong
    """
    pass
```

## Release Process

1. Update version in `setup.py`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Publish to PyPI (maintainers only)

## Questions?

- Open an issue for questions
- Join our Discord (coming soon)
- Email: team@cloudify.dev

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Cloudify! 🚀
