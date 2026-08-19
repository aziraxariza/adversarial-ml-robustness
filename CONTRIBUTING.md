# Contributing

We welcome contributions! Here's how to get started:

## Setup Development Environment

```bash
git clone https://github.com/aziraxariza/adversarial-ml-robustness.git
cd adversarial-ml-robustness
pip install -e ".[dev]"
```

## Contribution Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Implement** your changes with tests
4. **Format** code: `black src/ && isort src/`
5. **Test**: `pytest tests/`
6. **Submit** pull request

## Types of Contributions

- 🐛 **Bug fixes**: Fix existing issues
- ✨ **New attacks**: Implement C&W, AutoAttack, etc.
- 🛡️ **New defenses**: Implement certified, detection methods
- 📊 **Evaluations**: Benchmark on new datasets
- 📚 **Documentation**: Improve docs, add examples
- 🧪 **Tests**: Improve test coverage

## Code Style

- Use Black for formatting
- Use isort for imports
- Maximum line length: 88
- Add docstrings to all functions

## Testing

```bash
pytest tests/ -v           # Run all tests
pytest tests/test_attacks.py -v  # Specific test file
pytest tests/ -k fgsm      # Tests matching pattern
```

## Pull Request Process

1. Update README if needed
2. Add entry to CHANGELOG
3. Ensure all tests pass
4. Request review
5. Address feedback
6. Merge!

---
