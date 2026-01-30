---
description: Generate unit tests for Python files
---

# Unit Test Generation Workflow

## Trigger

When the user invokes this workflow.

## Instructions

1. **Analyze Context**: Analyze all Python files in the current active context.
2. **Create Test File**: For every file (e.g., `utils.py`), create a corresponding test file (e.g., `test_utils.py`).
3. **Framework**: Use the `pytest` framework.
4. **Coverage**: Ensure every function has at least one positive test case and one edge case.
