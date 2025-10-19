# Contributing to LIPM

Thank you for your interest in contributing to LIPM! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Screenshots** if applicable
- **Environment details**: Windows version, Python version, etc.
- **Log files**: Relevant portions from `logs/lipm.log`

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide detailed description** of the proposed functionality
- **Explain why** this enhancement would be useful
- **List alternatives** you've considered

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `develop`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**:
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed
4. **Test your changes**:
   - Ensure application runs without errors
   - Test affected functionality thoroughly
5. **Commit your changes**:
   ```bash
   git commit -m "Add feature: description"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** to the `develop` branch

### Pull Request Guidelines

- **One feature per PR** - Keep changes focused
- **Update README** if adding user-facing features
- **Add comments** explaining complex code
- **Test thoroughly** before submitting
- **Follow Python style** - PEP 8 conventions
- **Update requirements.txt** if adding dependencies

## Development Setup

### Prerequisites
- Python 3.13+
- Git
- Virtual environment

### Setup
```powershell
# Clone your fork
git clone https://github.com/YOUR-USERNAME/LIPM.git
cd LIPM

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run application
python -m linkedin_post_monitor.main
```

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Maximum line length: 120 characters
- Use docstrings for functions/classes
- Keep functions focused and small

### Example
```python
def process_post(post_url: str, commentary: str) -> Optional[str]:
    """
    Process a LinkedIn post with commentary.
    
    Args:
        post_url: URL of the LinkedIn post
        commentary: AI-generated commentary text
        
    Returns:
        URL of the repost if successful, None otherwise
    """
    try:
        # Implementation
        return repost_url
    except Exception as e:
        logger.error(f"Failed to process post: {e}")
        return None
```

## Testing

Before submitting a PR:

1. **Manual Testing**
   - Test all affected features
   - Verify no errors in logs
   - Check GUI responsiveness

2. **Integration Testing**
   - Test LinkedIn scraping
   - Test Telegram bot commands
   - Test AI commentary generation
   - Test database operations

## Documentation

### Code Documentation
- Add docstrings to new functions/classes
- Update inline comments for complex logic
- Keep comments up-to-date with code changes

### User Documentation
- Update README.md for new features
- Add troubleshooting entries if needed
- Update command reference for new bot commands

## Project Structure

```
LIPM/
├── linkedin_post_monitor/
│   ├── main.py              # Entry point
│   ├── gui.py               # GUI components
│   ├── monitor.py           # Orchestration
│   ├── linkedin_scraper.py  # LinkedIn automation
│   ├── telegram_bot.py      # Telegram integration
│   ├── ai_commentary.py     # OpenAI integration
│   ├── post_database.py     # Data persistence
│   ├── config_manager.py    # Configuration
│   ├── encryption.py        # Security
│   └── utils.py             # Utilities
```

## Areas Needing Contribution

### High Priority
- [ ] Unit tests
- [ ] Integration tests
- [ ] Error handling improvements
- [ ] Performance optimizations
- [ ] Cross-platform support (Linux/Mac)

### Medium Priority
- [ ] Multi-company monitoring
- [ ] Post scheduling
- [ ] Analytics dashboard
- [ ] Export/import functionality
- [ ] Custom AI prompt templates

### Low Priority
- [ ] Dark mode toggle
- [ ] Notification sounds
- [ ] Keyboard shortcuts
- [ ] Custom themes
- [ ] Browser extension

## Questions?

- Open an issue for questions
- Start a discussion on GitHub Discussions
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to LIPM! 🎉
