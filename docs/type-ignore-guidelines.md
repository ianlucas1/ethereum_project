# Type Ignore Guidelines

> Every `# type: ignore` must include an **inline justification** of why it's required.

## Allowed usages

1. **Missing or untyped external libraries**
   ```python
   import requests  # type: ignore[import]  # no types-requests stub installed
   ```

2. **Dynamic or generated modules**
   ```python
   from settings import DATA_DIR  # type: ignore  # dynamic settings module, no stubs
   ```

3. **Intentional signature overrides**
   ```python
   display = _display_plain  # type: ignore[argassignment]  # override signature for plain output
   ```

4. **Temporary fallback imports**
   ```python
   try:
       import fast_parser  # type: ignore[import]  # optional C extension
   except ImportError:
       from pure_python import parser
   ```

5. **Any other mypy-specific edge case**, but always target the **specific error code** when possible.

## Style guidelines

- **Scope**: suppress only the needed error (e.g. `# type: ignore[call-overload]`).
- **Justification**: after the ignore, add `# ` then a brief reason.
- **No blanket ignores**: avoid `# type: ignore` without codes unless absolutely necessary.
- **Review**: flag any lingering generic ignores for later typing improvements.

_See `mypy.ini` for global and per-module overrides._ 