# 🤝 Contributing to One Piece Mods

First off, thank you for considering contributing to One Piece Mods! It's people like you that make this cog better for the entire Red-DiscordBot community.

## 🏴‍☠️ Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Style Guidelines](#style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Community and Support](#community-and-support)

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Harassment, trolling, or derogatory comments
- Publishing others' private information without consent
- Any conduct which could reasonably be considered inappropriate

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.8 or higher
- Git installed and configured
- A Discord account and server for testing
- Basic knowledge of Discord.py and Red-DiscordBot
- Familiarity with async/await programming

### Understanding the Project

One Piece Mods is a Red-DiscordBot cog that provides One Piece themed moderation functionality. Key components include:

- **Core Moderation**: Kick, ban, mute, warn commands with One Piece theming
- **Impel Down System**: Multi-level punishment system
- **Configuration Management**: Advanced settings and validation
- **Webhook Logging**: Enhanced logging capabilities
- **Analytics**: Moderation statistics and insights


## 🤝 How to Contribute

### Types of Contributions

We welcome several types of contributions:

1. **🐛 Bug Reports** - Help us identify and fix issues
2. **✨ Feature Requests** - Suggest new functionality
3. **📖 Documentation** - Improve docs, examples, and guides
4. **🔧 Code Contributions** - Bug fixes, features, optimizations
5. **🧪 Testing** - Write tests, test new features
6. **🎨 Design** - UI/UX improvements, better embeds
7. **🌍 Localization** - Translations and internationalization

### Before You Start

1. **Check existing issues** to avoid duplicate work
2. **Create an issue** for major changes to discuss approach
3. **Keep changes focused** - one feature/fix per PR
4. **Follow our style guide** and coding conventions

## 📝 Style Guidelines

### Python Code Style

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

```python
# Use Black for formatting
black onepiecemods/

# Use flake8 for linting
flake8 onepiecemods/

# Use isort for import sorting
isort onepiecemods/
```

### Code Conventions

#### Function and Variable Names
```python
# Use descriptive snake_case names
async def check_user_permissions(ctx, member):
    user_warnings = await get_user_warnings(guild, member)
    escalation_level = calculate_escalation_level(user_warnings)
```

#### Class Names
```python
# Use PascalCase for classes
class ConfigManager:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
```

#### Constants
```python
# Use UPPER_SNAKE_CASE for constants
MAX_WARNING_LEVEL = 6
DEFAULT_ESCALATION_RULES = {
    3: {"level": 1, "duration": 30}
}
```

#### Type Hints
```python
# Use type hints for better code clarity
from typing import Optional, Dict, List, Union

async def add_warning(
    self, 
    guild: discord.Guild, 
    user: discord.Member, 
    mod: discord.Member, 
    reason: str
) -> int:
    """Add a warning and return the new warning count."""
    # Implementation here
```

#### Docstrings
```python
def format_time_duration(minutes: int, detailed: bool = False) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
        detailed: Whether to include detailed breakdown
        
    Returns:
        str: Formatted duration string
        
    Examples:
        >>> format_time_duration(90)
        "1 hour and 30 minutes"
        >>> format_time_duration(1440)
        "1 day"
    """
```

### Commit Message Guidelines

Use the [Conventional Commits](https://conventionalcommits.org/) format:

```
type(scope): description

[optional body]

[optional footer]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples
```bash
feat(impeldown): add level 7 for extreme violations
fix(webhook): handle rate limiting properly
docs(readme): update installation instructions
test(hierarchy): add comprehensive permission tests
```

## 🧪 Testing Guidelines

### Writing Tests

We use pytest for testing. Tests should be:

1. **Comprehensive** - Cover normal and edge cases
2. **Isolated** - Each test should be independent
3. **Fast** - Tests should run quickly
4. **Clear** - Test names should describe what they test

#### Test Structure
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestDurationConverter:
    """Test the DurationConverter class"""
    
    @pytest.fixture
    def converter(self):
        return DurationConverter()
    
    @pytest.mark.asyncio
    async def test_plain_minutes(self, converter):
        """Test conversion of plain minute values"""
        result = await converter.convert(mock_ctx, "30")
        assert result == 1800  # 30 minutes * 60 seconds
        
    @pytest.mark.asyncio
    async def test_invalid_format(self, converter):
        """Test invalid duration format raises BadArgument"""
        with pytest.raises(commands.BadArgument):
            await converter.convert(mock_ctx, "invalid")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=onepiecemods

# Run specific test file
pytest tests/test_hierarchy.py

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

### Test Coverage

Aim for high test coverage:
- **Core functionality**: 95%+ coverage
- **Utility functions**: 90%+ coverage
- **Error handling**: Test all error paths
- **Edge cases**: Test boundary conditions

## 📋 Pull Request Process

### Before Submitting

1. **Update your fork** with the latest upstream changes
2. **Run tests** and ensure they pass
3. **Check code style** with Black and flake8
4. **Update documentation** if needed
5. **Add tests** for new functionality

### PR Checklist

- [ ] **Code follows style guidelines**
- [ ] **All tests pass**
- [ ] **New tests added for new functionality**
- [ ] **Documentation updated**
- [ ] **CHANGELOG.md updated**
- [ ] **No breaking changes** (or clearly documented)
- [ ] **PR title follows conventional commit format**

### PR Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated checks** must pass (tests, linting)
2. **Code review** by maintainers
3. **Testing** in development environment
4. **Documentation review** if applicable
5. **Final approval** and merge

## 🐛 Issue Guidelines

### Bug Reports

Use the bug report template and include:

- **Clear title** describing the issue
- **Steps to reproduce** the bug
- **Expected behavior** vs actual behavior
- **Environment details** (Python version, Red version, etc.)
- **Error messages** and logs if available
- **Screenshots** if applicable

### Feature Requests

Use the feature request template and include:

- **Clear description** of the feature
- **Use case** and motivation
- **Proposed implementation** if you have ideas
- **Alternative solutions** considered
- **Additional context** or examples

### Issue Labels

We use labels to categorize issues:

- `bug` - Something isn't working
- `enhancement` - New feature request
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `documentation` - Documentation improvements
- `question` - Further information requested

## 🌟 Development Tips

### One Piece Theming

When adding new features, maintain the One Piece theme:

- **Use One Piece terminology** (nakama, devil fruits, etc.)
- **Reference characters and locations** appropriately
- **Maintain the adventurous tone** in messages
- **Use appropriate emojis** (🏴‍☠️, ⚔️, 🌊, etc.)

### Discord.py Best Practices

- **Use async/await** properly
- **Handle API errors** gracefully
- **Respect rate limits** 
- **Check permissions** before actions
- **Use proper intents** and permissions

### Red-DiscordBot Integration

- **Follow Red's patterns** for cogs and commands
- **Use Red's Config** for data storage
- **Integrate with modlog** properly
- **Respect Red's architecture**

### Performance Considerations

- **Batch database operations** when possible
- **Use appropriate data structures**
- **Cache frequently accessed data**
- **Optimize background tasks**
- **Profile performance-critical code**

## 🎯 Areas Needing Help

We especially welcome contributions in these areas:

### High Priority
- **Mobile optimization** for embeds and interfaces
- **Advanced analytics** and reporting features
- **Integration testing** with other popular cogs
- **Performance optimization** for large servers

### Medium Priority  
- **Localization** for different languages
- **Advanced appeal system** for punishments
- **Custom punishment templates**
- **Voice channel moderation** features

### Nice to Have
- **Machine learning** integration for auto-moderation
- **Advanced role management** features
- **Custom embed designs**
- **Integration with external services**

## 💬 Community and Support

### Getting Help

- **Discord**: Join the [Red-DiscordBot Support Server](https://discord.gg/red)
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check our comprehensive README
- **Code**: Look at existing code for examples

### Communication

- **Be respectful** and professional
- **Ask questions** if you're unsure
- **Share ideas** and suggestions
- **Help others** when possible

### Recognition

Contributors will be:
- **Listed in README** acknowledgments
- **Mentioned in release notes** for significant contributions
- **Given credit** in commit messages and PR descriptions

## 🏆 Development Workflow

### Typical Workflow

1. **Choose an issue** or create one for discussion
2. **Fork the repository** and create a feature branch
3. **Implement changes** following our guidelines
4. **Write tests** and ensure they pass
5. **Update documentation** as needed
6. **Submit a pull request** with clear description
7. **Respond to review** feedback
8. **Celebrate** when your contribution is merged! 🎉

### Branch Naming

Use descriptive branch names:
- `feature/webhook-integration`
- `fix/hierarchy-check-bug`
- `docs/update-installation-guide`
- `test/add-duration-converter-tests`

## 📚 Resources

### Learning Resources
- [Red-DiscordBot Documentation](https://docs.discord.red/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Python Asyncio Guide](https://docs.python.org/3/library/asyncio.html)
- [pytest Documentation](https://pytest.org/)

### Development Tools
- [Black](https://black.readthedocs.io/) - Code formatting
- [flake8](https://flake8.pycqa.org/) - Linting
- [mypy](http://mypy-lang.org/) - Type checking
- [pytest](https://pytest.org/) - Testing framework

---

Thank you for your interest in contributing to One Piece Mods! Together, we can make Discord moderation as epic as the Grand Line adventure! 🏴‍☠️⚔️
