# Contributing

Thank you for your interest in contributing to Agent Replay Bundle.

## How to contribute

1. Fork the repository and create a branch.
2. Make your changes with clear, focused commits.
3. Ensure all tests pass: `pytest`
4. Open a pull request with a clear description of your changes.

## Development setup

```bash
pip install -e ".[dev]"
pytest
```

## Guidelines

- Keep changes focused and minimal.
- Add tests for new behavior.
- Follow the existing code style.
- Do not introduce heavy dependencies; use the standard library where possible.
- Ensure no prohibited private or internal terminology appears in any file.

## Schema changes

Changes to JSON schemas should be accompanied by updates to the Pydantic models and tests.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 license.
