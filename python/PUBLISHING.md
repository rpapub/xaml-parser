# Publishing Guide: TestPyPI and PyPI

This guide walks through publishing the xaml-parser package to TestPyPI (for testing) and PyPI (for production).

## Prerequisites

### 1. Create Accounts

**TestPyPI Account** (for testing):
- Register at https://test.pypi.org/account/register/
- Verify your email
- Enable 2FA (required)

**PyPI Account** (for production):
- Register at https://pypi.org/account/register/
- Verify your email
- Enable 2FA (required)

### 2. Create API Tokens

**TestPyPI Token**:
1. Go to https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `xaml-parser-testpypi`
4. Scope: "Entire account" (for first upload) or "Project: xaml-parser" (after first upload)
5. Copy token (starts with `pypi-...`) - **save it securely, you can't see it again**

**PyPI Token** (do this later, after TestPyPI success):
1. Go to https://pypi.org/manage/account/token/
2. Same process as above
3. Save token securely

### 3. Configure Tokens

Create `~/.pypirc` file:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-PRODUCTION-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
```

**Security**: Set file permissions: `chmod 600 ~/.pypirc`

---

## Pre-Publication Checklist

### ✅ 1. Version & Metadata

- [ ] Version in `pyproject.toml` is correct (`0.2.0`)
- [ ] Version in `__version__.py` matches
- [ ] CHANGELOG.md is up to date
- [ ] README.md is accurate
- [ ] LICENSE files present (LICENSE-APACHE, LICENSE-CC-BY)
- [ ] Authors and email correct in `pyproject.toml`

### ✅ 2. Package Structure

- [ ] `py.typed` file exists in `xaml_parser/`
- [ ] All required files in package:
  ```bash
  cd python
  find xaml_parser -name "*.py" | head -5  # Check modules exist
  ls xaml_parser/py.typed                   # Check marker exists
  ls xaml_parser/templates/                 # Check templates exist
  ```

### ✅ 3. Dependencies

- [ ] Only essential dependency: `defusedxml>=0.7.1`
- [ ] Optional dependencies in `[project.optional-dependencies]`
- [ ] No version conflicts

### ✅ 4. Code Quality

Run full quality checks:

```bash
cd python

# Format code
uv run ruff format xaml_parser/

# Lint
uv run ruff check xaml_parser/ --fix

# Type check
uv run mypy xaml_parser/

# Run tests
uv run pytest tests/ -v --cov=xaml_parser
```

All checks must pass.

### ✅ 5. Documentation

- [ ] README.md renders correctly (check on GitHub)
- [ ] All code examples in README work
- [ ] API documentation complete
- [ ] No broken links

---

## Building the Package

### 1. Clean Previous Builds

```bash
cd python
rm -rf dist/ build/ *.egg-info
```

### 2. Build Distribution

```bash
# Using uv (recommended)
uv build

# Or using build directly
python -m build
```

This creates:
- `dist/xaml_parser-0.2.0-py3-none-any.whl` (wheel)
- `dist/xaml-parser-0.2.0.tar.gz` (source distribution)

### 3. Verify Build

```bash
# Check package contents
tar -tzf dist/xaml-parser-0.2.0.tar.gz | head -20

# Check wheel contents
unzip -l dist/xaml_parser-0.2.0-py3-none-any.whl | head -20

# Verify metadata
tar -xzOf dist/xaml-parser-0.2.0.tar.gz xaml-parser-0.2.0/PKG-INFO | head -30
```

**Check for**:
- [ ] `py.typed` included in wheel
- [ ] All `.py` files present
- [ ] Templates included
- [ ] No `.pyc` or `__pycache__` files
- [ ] LICENSE files included

### 4. Validate Package

```bash
# Install twine if not already
uv pip install twine

# Check package
twine check dist/*
```

Expected output:
```
Checking dist/xaml-parser-0.2.0.tar.gz: PASSED
Checking dist/xaml_parser-0.2.0-py3-none-any.whl: PASSED
```

---

## Upload to TestPyPI

### 1. Upload

```bash
cd python

# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

You'll see:
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading xaml_parser-0.2.0-py3-none-any.whl
Uploading xaml-parser-0.2.0.tar.gz
```

### 2. Verify Upload

Visit: https://test.pypi.org/project/xaml-parser/

Check:
- [ ] Version `0.2.0` is listed
- [ ] README renders correctly
- [ ] Metadata is correct
- [ ] License is shown
- [ ] Dependencies listed correctly

---

## Test Installation from TestPyPI

### 1. Create Test Environment

```bash
# Create fresh virtual environment
cd /tmp
python -m venv test-xaml-parser
source test-xaml-parser/bin/activate  # On Windows: test-xaml-parser\Scripts\activate
```

### 2. Install from TestPyPI

```bash
# Install from TestPyPI (note: need --index-url for dependencies)
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    xaml-parser
```

The `--extra-index-url` allows installing `defusedxml` from real PyPI.

### 3. Test Basic Functionality

```bash
# Test CLI
xaml-parser --help

# Test Python API
python << EOF
from cpmf_uips_xaml import XamlParser, __version__
print(f"Version: {__version__}")
parser = XamlParser()
print(f"Parser created: {parser}")
EOF
```

### 4. Test Type Hints

```bash
# Create test script
cat > test_types.py << 'EOF'
from cpmf_uips_xaml import XamlParser, ParseResult
from pathlib import Path

def test_typing() -> None:
    parser: XamlParser = XamlParser()
    # Type checker should recognize parse_file returns ParseResult
    result: ParseResult = parser.parse_file(Path("test.xaml"))
    print("Type hints working!")

test_typing()
EOF

# Run mypy on it
pip install mypy
mypy test_types.py
```

Expected: **No mypy errors** (proves `py.typed` works)

### 5. Test Installation with Extras

```bash
# Test extras installation
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    'xaml-parser[extras]'

# Verify optional deps installed
python -c "import psutil; import rich; print('Extras installed!')"
```

---

## Common Issues & Fixes

### Issue 1: "File already exists"

**Problem**: Can't re-upload same version to TestPyPI

**Solution**: Bump version in `pyproject.toml`:
```toml
version = "0.2.0.post1"  # Add post-release suffix for testing
```

Then rebuild and re-upload.

### Issue 2: py.typed not included

**Problem**: Type hints don't work after installation

**Fix**: Check `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel]
packages = ["xaml_parser"]

[tool.hatch.build.targets.wheel.force-include]
"xaml_parser/py.typed" = "xaml_parser/py.typed"
```

### Issue 3: Dependencies from TestPyPI fail

**Problem**: `defusedxml` not found

**Solution**: Always use `--extra-index-url https://pypi.org/simple/` when installing from TestPyPI

### Issue 4: README not rendering

**Problem**: README has syntax errors

**Fix**: Test locally:
```bash
pip install readme-renderer
python -m readme_renderer README.md -o /tmp/README.html
# Open /tmp/README.html in browser
```

---

## Publishing to Production PyPI

⚠️ **ONLY after successful TestPyPI testing**

### 1. Final Pre-Flight Checks

- [ ] TestPyPI package tested thoroughly
- [ ] All tests pass
- [ ] Documentation reviewed
- [ ] Version is final (no `.post1` suffix)
- [ ] Git tag created: `git tag v0.2.0 && git push --tags`

### 2. Upload to PyPI

```bash
cd python

# Upload to production PyPI
twine upload dist/*
```

### 3. Verify on PyPI

Visit: https://pypi.org/project/xaml-parser/

### 4. Test Installation

```bash
# Fresh environment
python -m venv test-prod
source test-prod/bin/activate

# Install from production PyPI
pip install xaml-parser

# Test
xaml-parser --help
python -c "from cpmf_uips_xaml import XamlParser; print('Success!')"
```

### 5. Announce

- [ ] Update README badges (add PyPI version badge)
- [ ] Create GitHub release
- [ ] Update documentation
- [ ] Announce on relevant channels

---

## Version Bumping for Next Release

After successful publication:

```bash
# Update version for next development cycle
# In pyproject.toml:
version = "0.2.1"  # or 0.3.0 for minor, 1.0.0 for major

# Update __version__.py to match

# Add to CHANGELOG.md:
## [Unreleased]

## [0.2.0] - 2025-12-03
...
```

---

## Quick Reference

### TestPyPI Commands

```bash
# Build
uv build

# Upload
twine upload --repository testpypi dist/*

# Install for testing
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ xaml-parser
```

### PyPI Commands

```bash
# Build
uv build

# Upload
twine upload dist/*

# Install
pip install xaml-parser
```

---

## Automation (Future)

Consider GitHub Actions workflow:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install build twine
      - name: Build package
        run: python -m build
        working-directory: python
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
        working-directory: python
```

**Setup**: Add `PYPI_TOKEN` secret in GitHub repo settings.

---

## Support

- **TestPyPI**: https://test.pypi.org/help/
- **PyPI**: https://pypi.org/help/
- **Packaging Guide**: https://packaging.python.org/
- **Twine Docs**: https://twine.readthedocs.io/
