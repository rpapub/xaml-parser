# Claude Code Instructions for xaml-parser

## Logging and Output Standards

- **DO NOT use Unicode characters** in logging output (✓, ✗, →, etc.)
- **USE simple ASCII** like `[OK]`, `[FAIL]`, `[INFO]`, `[WARN]`, `[ERROR]`
- **Professional, consistent formatting** for all console output

### Good Examples
```
[OK] Parsed 10 workflows in 234ms
[FAIL] File not found: project.json
[INFO] Generating Mermaid diagrams...
```

### Bad Examples
```
✓ Parsed 10 workflows
✗ File not found
🚀 Starting...
```

## Project Structure Notes

- Monorepo with Python and (future) Go implementations
- Test corpus is a git submodule at `test-corpus/`
- Ephemeral test outputs go to `.test-artifacts/python/`
- Golden baselines are committed in `python/tests/corpus/golden/`
- Always use `uv` for Python package management

## Testing Philosophy

- Unit tests are fast and run by default
- Corpus tests are slow and skipped by default (`-m "not corpus"`)
- CORE category projects are "guaranteed-to-work" examples
- Use golden baseline testing for regression detection
