# Contributing to ArgusLM

Thank you for your interest in contributing to ArgusLM! We welcome contributions from the community to help make this project better.

## How to Contribute

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and ensure they follow the code style.
4. Run tests to verify your changes.
5. Submit a Pull Request with a clear description of your changes.

## Development Setup

### Backend
- **Requirements**: Python 3.11+
- **Setup**:
  ```bash
  pip install -e ".[dev]"
  alembic upgrade head
  ```
- **Run Tests**:
  ```bash
  pytest
  ```

### Frontend
- **Requirements**: Node 18+
- **Setup**:
  ```bash
  cd frontend
  npm install
  ```
- **Development**:
  ```bash
  npm run dev
  ```
- **Build**:
  ```bash
  npm run build
  ```

## Code Style

### Python
We use `ruff` for linting and formatting.
- **Check**: `ruff check`
- **Format**: `ruff format`

### Frontend
Follow standard TypeScript and React best practices.

## Issues

If you find a bug or have a feature request, please open an issue on GitHub:
https://github.com/bluet/arguslm/issues

## Pull Requests

- Keep PRs focused on a single change.
- Provide a clear title and description.
- Ensure all tests pass before submitting.

## License

By contributing to ArgusLM, you agree that your contributions will be licensed under the Apache License 2.0.
