---
paths:
  - "**/*.py"
---

# Python files

- Never type the minus sign `−` into Python: ruff refuses it (RUF001). Take the signs from the app: `from blattwerk.maths import SIGNS`. Where a test needs the character alone, write `"\N{MINUS SIGN}"`.
- Do not write `−` in an Edit: the tool turns it into the character, and the call fails with "old_string and new_string are exactly the same".
