Subject: Set up Python package (monorepo) for release-quality

Hi <Name>,

Context: We have a monorepo `xaml-parser`; Python implementation lives at `python/`. Goal: make it a high-quality, releasable package (uv + hatchling), CI-ready, publishable to MyGet (PyPI-compatible).

Scope (deliverables):

1. Structure

* `python/xaml_parser/` pkg with `__init__.py`, optional CLI in `__main__.py`
* `tests/`, `pyproject.toml`, `README.md`, `LICENSE`, `CHANGELOG.md`
* `ruff.toml`, `mypy.ini`, `pytest.ini`, `.pre-commit-config.yaml`, `.gitignore`

2. Tooling

* uv + hatchling
* pre-commit (ruff format/lint, mypy)

3. Quality gates

* ruff clean
* mypy strict passes
* pytest with coverage (target ≥90%)
* `twine check` clean

4. Build & publish

* `uv build` → wheel + sdist
* Twine upload to MyGet PyPI (CI on tag `v*`)

5. CI (GitHub Actions)

* `qa` on push/PR (lint, type-check, tests)
* `release` on tag (build + twine upload)
* `act` compatibility for local runs

Acceptance criteria:

* `uv run ruff check .` passes
* `uv run mypy .` passes
* `uv run pytest --cov=xaml_parser` ≥90%
* `uv build` produces valid artifacts; `twine check dist/*` OK
* PR with workflow + configs; README shows install + CLI usage
* Dry-run with `act push -j qa` succeeds

Reference configs to use (adapt names/emails):

* `pyproject.toml` with `[project] name="xaml-parser"`, `>=3.11`, hatchling backend
* `ruff.toml` (line-length 100; select E,F,I,UP,B,N,D,ANN; ignore D203,D212)
* `mypy.ini` (`strict = True`)
* `pytest.ini` (`--cov=xaml_parser`)
* `.pre-commit-config.yaml` (ruff + mypy)

CI secrets (provided separately):

* `MYGET_FEED`
* `MYGET_PYPI_USERNAME`
* `MYGET_PYPI_PASSWORD`

Command checklist (local):

```
cd python
uv sync
pre-commit install
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
uv build
uv run twine check dist/*
```

Open questions:

* Package summary/keywords?
* Author + license? (MIT recommended unless stated otherwise)
* CLI entry point name desired? (`xaml-parser` vs none)

Please estimate and proceed;




Below is a crisp, end-to-end checklist for turning
`D:\github.com\rpapub\xaml-parser\python\` into a high-quality package.

---

# 1) Layout (monorepo-safe)

```
xaml-parser/
  python/
    xaml_parser/               # src package
      __init__.py
      __main__.py              # optional CLI entry
    tests/
      test_basic.py
    pyproject.toml
    README.md
    LICENSE
    CHANGELOG.md
    .gitignore
    ruff.toml
    mypy.ini
    pytest.ini
    .pre-commit-config.yaml
```

---

# 2) Tooling (uv + hatchling)

```pwsh
cd D:\github.com\rpapub\xaml-parser\python
uv venv
uv pip install -U pip
uv add hatchling ruff mypy pytest pytest-cov twine
# optional: bandit cyclonedx-bom
```

---

# 3) `pyproject.toml` (minimal, wheels + CLI)

```toml
[project]
name = "xaml-parser"
version = "0.1.0"
description = "XAML parsing utilities"
readme = "README.md"
requires-python = ">=3.11"
license = { file = "LICENSE" }
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["xaml","parser","workflow"]
classifiers = [
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
]

dependencies = []  # add runtime deps if any

[project.scripts]
xaml-parser = "xaml_parser.__main__:main"  # remove if no CLI

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["xaml_parser"]
```

---

# 4) Code quality config

**`ruff.toml`**

```toml
line-length = 100
target-version = "py311"
lint.select = ["E","F","I","UP","B","N","D","ANN"]
lint.ignore = ["D203","D212"]
```

**`mypy.ini`**

```ini
[mypy]
python_version = 3.11
strict = True
warn_unused_configs = True
```

**`pytest.ini`**

```ini
[pytest]
addopts = -q --cov=xaml_parser --cov-report=term-missing
testpaths = tests
```

**`.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks: [{ id: ruff }, { id: ruff-format }]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks: [{ id: mypy }]
```

**`.gitignore`**

```
# Python
__pycache__/
*.pyc
.venv/
.dist-info/
build/
dist/
.coverage
.pytest_cache/
.mypy_cache/
```

---

# 5) Package stubs

**`xaml_parser/__init__.py`**

```python
__all__ = ["parse"]
__version__ = "0.1.0"

def parse(xaml: str) -> dict:
    # TODO: implement
    return {"ok": True}
```

**`xaml_parser/__main__.py`** (optional CLI)

```python
import argparse, json
from . import parse, __version__

def main() -> None:
    ap = argparse.ArgumentParser("xaml-parser")
    ap.add_argument("file")
    args = ap.parse_args()
    data = open(args.file, "r", encoding="utf-8").read()
    print(json.dumps(parse(data), ensure_ascii=False))
if __name__ == "__main__":
    main()
```

**`tests/test_basic.py`**

```python
from xaml_parser import parse
def test_parse_minimal():
    assert parse("<xaml/>")["ok"] is True
```

---

# 6) Local dev loop

```pwsh
uv sync
pre-commit install
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

---

# 7) Build & artifact checks

```pwsh
uv build            # produces dist/*.whl and *.tar.gz
uv run twine check dist/*
```

*(Optional hardening)*

```pwsh
uv add -D bandit cyclonedx-bom
uv run bandit -q -r xaml_parser
uv run cyclonedx-py --format xml --outfile sbom.xml
```

---

# 8) MyGet (PyPI feed) publish

```pwsh
$env:TWINE_USERNAME="myget-user"
$env:TWINE_PASSWORD="myget-pass"
uv run twine upload `
  --repository-url https://www.myget.org/F/<feed>/python/ `
  dist/*
```

---

# 9) CI (minimal; runs with GitHub + locally via `act`)

`.github/workflows/python.yml`

```yaml
name: python
on: [push, pull_request]
jobs:
  qa:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: python } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python -m pip install -U pip uv
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run mypy .
      - run: uv run pytest
  release:
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: python } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python -m pip install -U pip uv build twine
      - run: uv build
      - env:
          TWINE_USERNAME: ${{ secrets.MYGET_PYPI_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.MYGET_PYPI_PASSWORD }}
        run: twine upload --repository-url https://www.myget.org/F/${{ secrets.MYGET_FEED }}/python/ dist/*
```

**Local test with `act`**

```pwsh
# from repo root (has .github/workflows/python.yml)
act push -j qa -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-latest
```

---

# 10) Versioning & changelog (simple)

* Bump `version` in `pyproject.toml` (SemVer).
* Update `CHANGELOG.md` (Keep a Changelog style).
* Tag: `git tag v0.1.1 && git push --tags` → CI `release` job publishes.

*(Optional: adopt `hatch-vcs` / `setuptools_scm` for tag-derived versions.)*

---

# 11) Policy (quick)

* **Type hints required** (`mypy --strict` passes).
* **Lint clean** (ruff).
* **Tests ≥ 90%** coverage (`pytest --cov`).
* **Review checklist**: README badges, classifiers, LICENSE present, `twine check` clean.

---
