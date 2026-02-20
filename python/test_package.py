#!/usr/bin/env python3
"""Test script to validate the cpmf-uips-xaml package before publishing."""

import sys
from pathlib import Path


def test_imports() -> bool | None:
    """Test that all public APIs can be imported."""
    print("Testing imports...")
    try:
        from cpmf_uips_xaml import (
            ProjectParser,
            XamlParser,
            __author__,
            __version__,
        )

        print(f"  [OK] Version: {__version__}")
        print(f"  [OK] Author: {__author__}")
        print(f"  [OK] XamlParser: {XamlParser}")
        print(f"  [OK] ProjectParser: {ProjectParser}")
        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def test_version_sync() -> bool | None:
    """Test that versions are synced across files."""
    print("\nTesting version sync...")
    try:
        from cpmf_uips_xaml import __version__

        # Check pyproject.toml
        pyproject = Path("pyproject.toml").read_text()
        if f'version = "{__version__}"' in pyproject:
            print(f"  [OK] pyproject.toml version matches: {__version__}")
        else:
            print("  [FAIL] pyproject.toml version mismatch")
            return False

        # Check CHANGELOG.md
        changelog = Path("CHANGELOG.md").read_text()
        if f"## [{__version__}]" in changelog:
            print(f"  [OK] CHANGELOG.md has version: {__version__}")
        else:
            print(f"  [FAIL] CHANGELOG.md missing version: {__version__}")
            return False

        return True
    except Exception as e:
        print(f"  [FAIL] Version sync check failed: {e}")
        return False


def test_dependencies() -> bool | None:
    """Test that dependencies match expectations."""
    print("\nTesting dependencies...")
    try:
        import tomllib

        pyproject = Path("pyproject.toml").read_text()
        config = tomllib.loads(pyproject)

        deps = config["project"]["dependencies"]
        print(f"  [OK] Runtime dependencies: {len(deps)}")
        for dep in deps:
            print(f"    - {dep}")

        if len(deps) == 1 and deps[0].startswith("defusedxml"):
            print("  [OK] Single runtime dependency (defusedxml)")
        else:
            print(f"  [FAIL] Expected 1 dependency, got {len(deps)}")
            return False

        # Check extras
        extras = config["project"]["optional-dependencies"].get("extras", [])
        print(f"  [OK] Optional extras: {len(extras)}")
        for extra in extras:
            print(f"    - {extra}")

        return True
    except Exception as e:
        print(f"  [FAIL] Dependency check failed: {e}")
        return False


def test_files_exist() -> bool:
    """Test that required files exist."""
    print("\nTesting required files...")
    required_files = [
        "cpmf_uips_xaml/py.typed",
        "LICENSE-APACHE",
        "LICENSE-CC-BY",
        "README.md",
        "CHANGELOG.md",
        "pyproject.toml",
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [FAIL] Missing: {file_path}")
            all_exist = False

    return all_exist


def test_build_artifacts() -> bool:
    """Test that built packages exist and are valid."""
    print("\nTesting build artifacts...")
    dist_dir = Path("dist")

    if not dist_dir.exists():
        print("  [FAIL] dist/ directory not found - run 'uv build' first")
        return False

    wheel = list(dist_dir.glob("*.whl"))
    sdist = list(dist_dir.glob("*.tar.gz"))

    if not wheel:
        print("  [FAIL] No wheel (.whl) found in dist/")
        return False

    if not sdist:
        print("  [FAIL] No source distribution (.tar.gz) found in dist/")
        return False

    print(f"  [OK] Wheel: {wheel[0].name} ({wheel[0].stat().st_size // 1024} KB)")
    print(f"  [OK] Source: {sdist[0].name} ({sdist[0].stat().st_size // 1024} KB)")

    return True


def test_readme_no_monorepo() -> bool:
    """Test that README doesn't reference monorepo."""
    print("\nTesting README for monorepo references...")
    readme = Path("README.md").read_text()

    forbidden = ["monorepo", "Monorepo"]
    found = []
    for word in forbidden:
        if word in readme:
            found.append(word)

    if found:
        print(f"  [FAIL] Found monorepo references: {found}")
        return False
    else:
        print("  [OK] No monorepo references")
        return True


def test_license_info() -> bool | None:
    """Test that license information is correct."""
    print("\nTesting license information...")
    try:
        import tomllib

        pyproject = Path("pyproject.toml").read_text()
        config = tomllib.loads(pyproject)

        license_text = config["project"]["license"]["text"]
        if "Apache-2.0 AND CC-BY-4.0" in license_text:
            print(f"  [OK] License: {license_text}")
        else:
            print(f"  [FAIL] Unexpected license: {license_text}")
            return False

        # Check README mentions both licenses
        readme = Path("README.md").read_text()
        if "Apache" in readme and "Creative Commons" in readme:
            print("  [OK] README mentions both licenses")
        else:
            print("  [FAIL] README missing license information")
            return False

        return True
    except Exception as e:
        print(f"  [FAIL] License check failed: {e}")
        return False


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("XAML-Parser Package Validation")
    print("=" * 60)

    tests = [
        test_imports,
        test_version_sync,
        test_dependencies,
        test_files_exist,
        test_build_artifacts,
        test_readme_no_monorepo,
        test_license_info,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n[FAIL] Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if all(results):
        print("\n[OK] ALL TESTS PASSED - Package ready for TestPyPI!")
        return 0
    else:
        print("\n[FAIL] SOME TESTS FAILED - Fix issues before publishing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
