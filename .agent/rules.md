# Google Antigravity Rules & Standards

## Code Style Guidelines

- **PEP 8 Compliance**: All Python code must strictly adhere to PEP 8 standards.
- **Documentation**: Every function and class must have a docstring explaining its purpose, arguments, and return values.
- **Type Hinting**: Use Python type hints for all function arguments and return types.

## Architecture Guide

- **Entry Point**: `main.py` or `App.jsx` is for orchestration only. It should strictly call functions from other modules.
- **No Logic in Main**: Do not define business logic functions inside `main.py`.
- **Modularity**: Always create a new file (e.g., `utils.py`, `feature_x.py`) for new functionality and import it.

## The Security Mandate

**Security Non-Negotiables**

1. **No Hardcoded Secrets**: NEVER output API keys, passwords, or tokens in code. Use `os.getenv()`.
2. **Input Validation**: All user inputs (CLI args, HTTP requests) must be validated and sanitized.
3. **Safe Imports**: Do not use `eval()` or `exec()` under any circumstances.

## Error Handling Standards

- **No Bare Excepts**: Never use `except:` without an exception type. Catch specific errors (e.g., `except ValueError:`).
- **Structured Logging**: Do not use `print()`. Use the logging library for all outputs.
- **Fail Gracefully**: Scripts should never crash with a stack trace visible to the user. Wrap main execution in a `try/except` block.

## Frontend Stack Guidelines

- **Functional Components**: All React components must be Functional Components using Hooks. Class components are forbidden.
- **Styling**: Use Tailwind CSS utility classes. Do not use inline styles or separate CSS files.
- **Naming**: Use PascalCase for component filenames (e.g., `UserProfile.tsx`) and use glassmorphism style.

## Type Safety Rules

- **Strict Typing**: All function signatures must have type annotations.
- **No Any**: Avoid using `Any` type. Define data classes or interfaces for complex structures.
- **Return Types**: Always specify the return type, even if it is `None` or `void`.
- **Test It**: Ask the agent: "Create a function that processes a list of user dictionaries."
  - **Result**: Instead of generic Dicts, define a User TypedDict or dataclass and use `List[User]` in the signature.
