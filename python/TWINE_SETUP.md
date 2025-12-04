# Twine Setup Guide - Quick Reference

**Goal**: Upload xaml-parser 0.2.0 to TestPyPI, then PyPI

---

## Step 1: Install Twine

```bash
cd python

# Already installed via uv
uv run twine --version

# Or install globally
pip install twine
```

**Current status**: ✅ Already installed

---

## Step 2: Create TestPyPI Account

### Register
1. Go to: **https://test.pypi.org/account/register/**
2. Fill in:
   - Username: (your choice)
   - Email: (your email)
   - Password: (strong password)
3. **Verify email** - Check inbox and click verification link
4. **Enable 2FA** (REQUIRED):
   - Go to: https://test.pypi.org/manage/account/
   - Add 2FA app (like Google Authenticator, Authy)
   - Save recovery codes

---

## Step 3: Create TestPyPI API Token

### Generate Token
1. Go to: **https://test.pypi.org/manage/account/token/**
2. Click **"Add API token"**
3. Token name: `xaml-parser-testpypi`
4. Scope: **"Entire account"** (for first upload)
   - After first upload, can create project-specific token
5. Click **"Add token"**
6. **COPY THE TOKEN** - Starts with `pypi-...`
   - ⚠️ You can only see this ONCE
   - Save it securely (password manager, secure note)

Example token format:
```
pypi-AgEIcHlwaS5vcmcCJDAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMAACKlszLCJxxx...
```

---

## Step 4: Configure ~/.pypirc

### Create Configuration File

**Location**:
- Linux/Mac: `~/.pypirc` (`/home/username/.pypirc`)
- Windows: `%USERPROFILE%\.pypirc` (`C:\Users\username\.pypirc`)

**Create the file**:

```ini
[distutils]
index-servers =
    testpypi
    pypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-PRODUCTION-PYPI-TOKEN-HERE-LATER
```

**Replace**: `pypi-YOUR-TESTPYPI-TOKEN-HERE` with your actual token

**Security** (Linux/Mac only):
```bash
chmod 600 ~/.pypirc
```

### Windows Users: Create .pypirc

**Option 1 - PowerShell**:
```powershell
@"
[distutils]
index-servers =
    testpypi
    pypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TOKEN-HERE

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-PRODUCTION-TOKEN-LATER
"@ | Out-File -FilePath "$env:USERPROFILE\.pypirc" -Encoding ASCII
```

**Option 2 - Manual**:
1. Open Notepad
2. Paste the configuration above
3. Save as: `C:\Users\YourUsername\.pypirc`
4. **Important**: Save as "All Files", not ".txt"

---

## Step 5: Verify Package is Ready

```bash
cd python

# Check files exist
ls -la dist/
# Should show:
#   xaml_parser-0.2.0.tar.gz
#   xaml_parser-0.2.0-py3-none-any.whl

# Validate packages
uv run twine check dist/*
# Expected: PASSED for both
```

---

## Step 6: Upload to TestPyPI (DRY RUN)

### Test with --dry-run first (safe, no actual upload)

```bash
cd python

# Dry run (checks auth but doesn't upload)
twine upload --repository testpypi dist/* --verbose
```

**What happens**:
- Twine reads `~/.pypirc`
- Finds `[testpypi]` section
- Uses token for authentication
- Uploads to TestPyPI

**Expected output**:
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading xaml_parser-0.2.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 134.2/134.2 kB • 00:01 • ?
Uploading xaml_parser-0.2.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 183.5/183.5 kB • 00:01 • ?

View at:
https://test.pypi.org/project/xaml-parser/0.2.0/
```

### If Upload Fails

**Common Issues**:

**1. Authentication Failed**
```
HTTP Error 403: Invalid or non-existent authentication information
```
**Fix**: Check token in `~/.pypirc`, make sure it starts with `pypi-` and is complete

**2. File Already Exists**
```
HTTP Error 400: File already exists
```
**Fix**: TestPyPI doesn't allow re-uploading same version. Options:
- Use a different version: `0.2.0.post1`, `0.2.0a1`, etc.
- Or wait and use this version for production PyPI

**3. Invalid Package Name**
```
HTTP Error 400: Invalid package name
```
**Fix**: Check `pyproject.toml` has valid name (lowercase, hyphens ok)

---

## Step 7: Verify Upload on TestPyPI

### Check the Website
1. Visit: **https://test.pypi.org/project/xaml-parser/**
2. Check:
   - ✅ Version 0.2.0 listed
   - ✅ README renders correctly
   - ✅ License shown (Apache-2.0 AND CC-BY-4.0)
   - ✅ Dependencies listed (defusedxml)
   - ✅ Optional extras shown

---

## Step 8: Test Installation from TestPyPI

### Create Test Environment

```bash
# Create fresh virtual environment
cd /tmp  # or any temp directory
python -m venv test-xaml-parser
source test-xaml-parser/bin/activate  # Windows: test-xaml-parser\Scripts\activate
```

### Install from TestPyPI

```bash
# Install (note: need both index URLs)
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    xaml-parser

# Why two URLs?
# - TestPyPI has xaml-parser
# - Real PyPI has defusedxml (dependency)
```

**Expected output**:
```
Looking in indexes: https://test.pypi.org/simple/, https://pypi.org/simple/
Collecting xaml-parser
  Downloading https://test-files.pythonhosted.org/packages/.../xaml_parser-0.2.0-py3-none-any.whl
Collecting defusedxml>=0.7.1
  Downloading https://files.pythonhosted.org/packages/.../defusedxml-0.7.1-py2.py3-none-any.whl
Installing collected packages: defusedxml, xaml-parser
Successfully installed defusedxml-0.7.1 xaml-parser-0.2.0
```

### Test Basic Functionality

```bash
# Test CLI
xaml-parser --help
# Should show help text

# Test Python API
python << 'EOF'
from xaml_parser import XamlParser, __version__
print(f"Version: {__version__}")
print(f"Parser: {XamlParser}")
print("SUCCESS: Package works!")
EOF
```

**Expected output**:
```
Version: 0.2.0
Parser: <class 'xaml_parser.parser.XamlParser'>
SUCCESS: Package works!
```

### Test Type Hints (Important!)

```bash
# Install mypy
pip install mypy

# Create test script
cat > test_types.py << 'EOF'
from xaml_parser import XamlParser, ParseResult
from pathlib import Path

def test() -> None:
    parser: XamlParser = XamlParser()
    # This should type-check correctly
    print("Type hints work!")

test()
EOF

# Run mypy
mypy test_types.py
```

**Expected**: `Success: no issues found in 1 source file`

If mypy complains about missing types, the `py.typed` marker isn't working.

### Test Optional Extras

```bash
# Install with extras
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    'xaml-parser[extras]'

# Verify extras installed
python -c "import psutil; import rich; print('Extras work!')"
```

---

## Step 9: Production PyPI (After TestPyPI Success)

### Only proceed after TestPyPI validation passes!

### Create Production PyPI Account
1. Go to: **https://pypi.org/account/register/**
2. Same process as TestPyPI
3. Enable 2FA (REQUIRED)

### Create Production API Token
1. Go to: **https://pypi.org/manage/account/token/**
2. Token name: `xaml-parser-pypi`
3. Scope: **"Entire account"** (first upload)
4. Copy token

### Update ~/.pypirc

Edit `~/.pypirc` and add production token:
```ini
[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-YOUR-PRODUCTION-TOKEN-HERE
```

### Upload to Production PyPI

```bash
cd python

# Final check
uv run twine check dist/*

# Upload to PRODUCTION
twine upload dist/*
# (No --repository flag = uses [pypi] by default)
```

### Verify Production Upload

1. Visit: **https://pypi.org/project/xaml-parser/**
2. Test install: `pip install xaml-parser`
3. Create git tag: `git tag v0.2.0 && git push --tags`

---

## Quick Command Reference

### TestPyPI
```bash
# Upload
twine upload --repository testpypi dist/*

# Install
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    xaml-parser
```

### Production PyPI
```bash
# Upload
twine upload dist/*

# Install
pip install xaml-parser
```

---

## Troubleshooting

### "twine: command not found"
```bash
pip install twine
# or
uv pip install twine
```

### "~/.pypirc not found"
- Windows: Use `%USERPROFILE%\.pypirc`
- Check file exists: `cat ~/.pypirc` (Linux/Mac) or `type %USERPROFILE%\.pypirc` (Windows)

### "Invalid authentication"
- Double-check token starts with `pypi-`
- Make sure entire token copied (usually 200+ characters)
- Check no extra spaces/newlines in .pypirc

### "Package already exists"
For TestPyPI testing, bump version:
```toml
# pyproject.toml
version = "0.2.0.post1"  # or .post2, .post3, etc.
```
Then rebuild: `uv build`

### "README doesn't render"
- Test locally: `pip install readme-renderer`
- Run: `python -m readme_renderer README.md`

---

## Security Best Practices

1. **Never commit .pypirc** to git
2. **Use API tokens**, not passwords
3. **Create project-specific tokens** after first upload
4. **Rotate tokens** periodically
5. **Delete unused tokens** from account settings
6. **Use 2FA** on both TestPyPI and PyPI

---

## Next Steps After Upload

1. ✅ Verify package on TestPyPI
2. ✅ Test installation in clean environment
3. ✅ Check README renders correctly
4. ✅ Verify type hints work (mypy test)
5. ✅ Test CLI command
6. ✅ Test Python API
7. ✅ Test with extras
8. ⏭️ If all pass, proceed to production PyPI
9. ⏭️ Create GitHub release
10. ⏭️ Update documentation with PyPI badge

---

## Success Checklist

### Pre-Upload
- [ ] Package built (`dist/` folder exists)
- [ ] `twine check dist/*` passes
- [ ] `test_package.py` passes
- [ ] TestPyPI account created
- [ ] 2FA enabled on TestPyPI
- [ ] API token created and saved
- [ ] `~/.pypirc` configured

### Upload
- [ ] `twine upload --repository testpypi dist/*` succeeds
- [ ] Package visible on https://test.pypi.org/project/xaml-parser/

### Post-Upload Validation
- [ ] Install from TestPyPI works
- [ ] CLI command works
- [ ] Python imports work
- [ ] Type hints work (mypy passes)
- [ ] Optional extras install correctly
- [ ] README renders correctly on web

### Production (After TestPyPI)
- [ ] PyPI account created
- [ ] Production API token created
- [ ] Upload to production succeeds
- [ ] Install from production works
- [ ] Git tag created (`v0.2.0`)
- [ ] GitHub release created

---

## Support

- **TestPyPI Help**: https://test.pypi.org/help/
- **PyPI Help**: https://pypi.org/help/
- **Twine Docs**: https://twine.readthedocs.io/
- **Packaging Guide**: https://packaging.python.org/

---

**Ready to upload?**

```bash
cd python
twine upload --repository testpypi dist/*
```
