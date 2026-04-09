# Contributing to Audio Quality Checker

Thank you for your interest in contributing! This project is currently maintained by [UsergyAI](https://usergy.ai).

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists in [Issues](https://github.com/Usergy-ops/audio-quality-checker/issues)
2. If not, create a new issue with:
   - Clear title describing the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Audio file details (format, size, duration) if relevant
   - Environment (OS, Python version)

### Suggesting Features

Open an issue with the `enhancement` label describing:
- The use case
- Proposed solution
- Any alternatives considered

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and small

### Testing

- Add tests for new features
- Ensure existing tests pass
- Test with various audio formats

## Development Setup

```bash
git clone https://github.com/Usergy-ops/audio-quality-checker.git
cd audio-quality-checker/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest  # for testing
uvicorn app.main:app --reload
```

## Questions?

- Open an issue
- Email: connect@usergy.ai

## License

By contributing, you agree that your contributions will be licensed under the project's license.
