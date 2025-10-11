# CLI Implementation Instructions - Python with Typer

This document provides comprehensive instructions for implementing a professional CLI for the xaml-parser Python package using Typer and Rich.

## Why Typer + Rich?

**Typer**:
- Type hints driven - matches our existing codebase
- Automatic help generation
- Subcommands support
- Great argument/option handling
- Built on Click (battle-tested)

**Rich**:
- Beautiful terminal output
- Tables, trees, syntax highlighting
- Progress bars for batch operations
- Color support with graceful fallback
- Plays well with Typer

## Architecture Decision: Hybrid Approach

```bash
# Single command for quick usage
xaml-parser workflow.xaml                    # Parse and pretty print

# Options for filtering
xaml-parser workflow.xaml --json             # JSON output
xaml-parser workflow.xaml --arguments        # Show only arguments

# Subcommands for advanced operations
xaml-parser analyze workflow.xaml            # Deep analysis
xaml-parser validate workflow.xaml           # Validation only
xaml-parser batch *.xaml --summary           # Batch processing
```

**Rationale**: Most users need simple parsing (single command), but power users need advanced features (subcommands).

## Implementation Phases

### Phase 1: Minimal Viable CLI (1-2 hours)

**Goal**: Basic parse command with JSON output

**Features**:
- Parse single XAML file
- Output JSON to stdout or file
- Error handling with exit codes
- Basic help text

**Files to create**:
- `python/xaml_parser/cli.py` - Main CLI module
- Update `python/pyproject.toml` - Add dependencies and entry point

**Deliverable**: Users can run `xaml-parser workflow.xaml --json`

### Phase 2: Pretty Output with Rich (1-2 hours)

**Goal**: Human-readable formatted output

**Features**:
- Colorized output
- Tables for arguments/variables
- Tree view for activities
- Success/error indicators

**Files to modify**:
- `python/xaml_parser/cli.py` - Add formatting functions

**Deliverable**: Beautiful terminal output by default

### Phase 3: Filtering & Selection (1 hour)

**Goal**: Show only what user needs

**Features**:
- `--arguments` - Show arguments only
- `--activities` - Show activities only
- `--variables` - Show variables only
- `--tree` - Show activity tree

**Deliverable**: Selective output for specific use cases

### Phase 4: Batch Processing (1-2 hours)

**Goal**: Process multiple files efficiently

**Features**:
- Accept multiple files
- Glob pattern support
- `--summary` mode
- Progress bar for large batches

**Deliverable**: `xaml-parser *.xaml --summary`

### Phase 5: Advanced (Optional, based on needs)

**Features**:
- Validation subcommand
- Query/filter syntax
- Configuration files
- Watch mode

## Code Structure

### Option A: Single Module (Recommended for start)

```
python/xaml_parser/
├── __init__.py
├── cli.py              # All CLI code here
├── parser.py
├── models.py
└── ...
```

**When to use**: Phases 1-3 (< 500 lines of CLI code)

### Option B: Modular (Scale to this)

```
python/xaml_parser/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py         # Typer app entry point
│   ├── commands/
│   │   ├── parse.py    # Parse command
│   │   ├── analyze.py  # Analyze subcommand
│   │   ├── validate.py # Validate subcommand
│   │   └── batch.py    # Batch processing
│   ├── formatters/
│   │   ├── json.py     # JSON output
│   │   ├── pretty.py   # Pretty formatted
│   │   ├── tree.py     # Tree view
│   │   └── table.py    # Table view
│   └── utils.py        # Shared CLI utilities
├── parser.py
└── ...
```

**When to use**: Phase 4+ (> 500 lines, multiple subcommands)

## Phase 1 Implementation: Minimal CLI

### 1. Add Dependencies

**File**: `python/pyproject.toml`

```toml
dependencies = [
    "defusedxml>=0.7.1",
    "typer>=0.9.0",        # CLI framework
    "rich>=13.0.0",        # Terminal output
]
```

### 2. Create CLI Entry Point

**File**: `python/pyproject.toml`

```toml
[project.scripts]
xaml-parser = "xaml_parser.cli:main"
```

### 3. Create CLI Module

**File**: `python/xaml_parser/cli.py`

```python
"""Command-line interface for XAML Parser."""

import sys
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .parser import XamlParser
from .models import ParseResult

# Typer app instance
app = typer.Typer(
    name="xaml-parser",
    help="Parse UiPath XAML workflow files and extract metadata",
    add_completion=False,
)

# Rich console for output
console = Console()


@app.command()
def main(
    file: Path = typer.Argument(
        ...,
        help="XAML workflow file to parse",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    json_format: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--compact",
        help="Pretty print JSON output",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output with diagnostics",
    ),
):
    """Parse a UiPath XAML workflow file.

    Examples:

        # Parse and show summary
        $ xaml-parser Main.xaml

        # Output as JSON
        $ xaml-parser Main.xaml --json

        # Save to file
        $ xaml-parser Main.xaml --json -o output.json

        # Verbose with diagnostics
        $ xaml-parser Main.xaml -v
    """
    try:
        # Parse file
        parser = XamlParser()
        result = parser.parse_file(file)

        # Handle errors
        if not result.success:
            console.print("[bold red]Parsing failed:[/bold red]")
            for error in result.errors:
                console.print(f"  [red]✗[/red] {error}")

            if result.warnings:
                console.print("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in result.warnings:
                    console.print(f"  [yellow]⚠[/yellow] {warning}")

            sys.exit(1)

        # Output
        if json_format:
            output_json(result, output, pretty)
        else:
            output_summary(result, verbose)

        sys.exit(0)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


def output_json(result: ParseResult, output: Optional[Path], pretty: bool):
    """Output result as JSON."""
    # Convert to dict (assumes models have to_dict or are dataclasses)
    data = {
        "success": result.success,
        "content": result.content.__dict__ if result.content else None,
        "errors": result.errors,
        "warnings": result.warnings,
        "parse_time_ms": result.parse_time_ms,
        "file_path": str(result.file_path) if result.file_path else None,
    }

    # Format JSON
    if pretty:
        json_str = json.dumps(data, indent=2, default=str)
    else:
        json_str = json.dumps(data, default=str)

    # Output
    if output:
        output.write_text(json_str)
        console.print(f"[green]✓[/green] Written to {output}")
    else:
        print(json_str)


def output_summary(result: ParseResult, verbose: bool):
    """Output human-readable summary."""
    content = result.content

    console.print(f"[bold green]✓[/bold green] Parsed successfully")
    console.print(f"  File: {result.file_path}")
    console.print(f"  Parse time: {result.parse_time_ms:.2f}ms")
    console.print()

    # Counts
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Arguments:  {len(content.arguments)}")
    console.print(f"  Variables:  {len(content.variables)}")
    console.print(f"  Activities: {len(content.activities)}")
    console.print()

    # Show arguments
    if content.arguments:
        console.print(f"[bold]Arguments:[/bold]")
        for arg in content.arguments:
            direction = arg.direction.upper()
            console.print(f"  [{direction}] {arg.name}: {arg.type}")
            if arg.annotation:
                console.print(f"      → {arg.annotation}")

    # Verbose: Show diagnostics
    if verbose and result.diagnostics:
        console.print(f"\n[bold]Diagnostics:[/bold]")
        diag = result.diagnostics
        console.print(f"  Total elements: {diag.total_elements_processed}")
        console.print(f"  Activities found: {diag.activities_found}")
        console.print(f"  XML depth: {diag.xml_depth}")


if __name__ == "__main__":
    app()
```

### 4. Install and Test

```bash
cd python

# Install in editable mode with CLI
uv pip install -e .

# Test it
xaml-parser --help
xaml-parser path/to/workflow.xaml
xaml-parser path/to/workflow.xaml --json
xaml-parser path/to/workflow.xaml -o output.json
```

### 5. Exit Codes

```python
# Success
sys.exit(0)

# Parsing failed
sys.exit(1)

# Validation failed
sys.exit(2)

# File not found (handled by Typer)
sys.exit(2)
```

## Phase 2 Implementation: Rich Output

### 1. Add Rich Formatting Functions

**File**: `python/xaml_parser/cli.py`

```python
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

def output_pretty(result: ParseResult):
    """Pretty formatted output with Rich."""
    content = result.content

    # Header
    console.print(Panel(
        f"[bold green]✓ Successfully parsed[/bold green]\n"
        f"File: {result.file_path}\n"
        f"Parse time: {result.parse_time_ms:.2f}ms",
        title="XAML Parser",
        border_style="green",
    ))

    # Arguments table
    if content.arguments:
        table = Table(title="Workflow Arguments", show_header=True)
        table.add_column("Direction", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Annotation", style="yellow")

        for arg in content.arguments:
            table.add_row(
                arg.direction.upper(),
                arg.name,
                arg.type,
                arg.annotation or "",
            )

        console.print(table)
        console.print()

    # Activities summary
    console.print(f"[bold]Activities:[/bold] {len(content.activities)} found")

    # Top-level activities
    for activity in content.activities[:5]:  # Show first 5
        indent = "  " * activity.depth_level
        console.print(f"{indent}[cyan]●[/cyan] {activity.tag}: {activity.display_name or '(unnamed)'}")

    if len(content.activities) > 5:
        console.print(f"  ... and {len(content.activities) - 5} more")
```

### 2. Add Options

```python
@app.command()
def main(
    # ... existing parameters ...
    format: str = typer.Option(
        "pretty",
        "--format",
        "-f",
        help="Output format: pretty, json, tree, table",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
    ),
):
    """Parse a UiPath XAML workflow file."""

    # Disable color if requested
    if no_color:
        console = Console(no_color=True)

    # ... rest of implementation
```

## Phase 3 Implementation: Filtering

### Add Filtering Options

```python
@app.command()
def main(
    # ... existing parameters ...
    arguments_only: bool = typer.Option(
        False,
        "--arguments",
        help="Show only arguments",
    ),
    activities_only: bool = typer.Option(
        False,
        "--activities",
        help="Show only activities",
    ),
    variables_only: bool = typer.Option(
        False,
        "--variables",
        help="Show only variables",
    ),
    tree_view: bool = typer.Option(
        False,
        "--tree",
        help="Show activity tree",
    ),
):
    """Parse with filtering options."""

    # ... parse file ...

    # Filtered output
    if arguments_only:
        output_arguments_only(result)
    elif activities_only:
        output_activities_only(result)
    elif variables_only:
        output_variables_only(result)
    elif tree_view:
        output_activity_tree(result)
    else:
        output_pretty(result)


def output_activity_tree(result: ParseResult):
    """Display activities as tree."""
    tree = Tree("[bold]Activity Tree[/bold]")

    # Build tree structure
    root_activities = [a for a in result.content.activities if a.depth_level == 0]

    for activity in root_activities:
        add_activity_to_tree(tree, activity, result.content.activities)

    console.print(tree)


def add_activity_to_tree(parent, activity, all_activities):
    """Recursively add activities to tree."""
    label = f"[cyan]{activity.tag}[/cyan]: {activity.display_name or '(unnamed)'}"

    if activity.annotation:
        label += f" [dim]- {activity.annotation}[/dim]"

    branch = parent.add(label)

    # Add children
    children = [a for a in all_activities if a.parent_activity_id == activity.activity_id]
    for child in children:
        add_activity_to_tree(branch, child, all_activities)
```

## Phase 4 Implementation: Batch Processing

### Add Batch Command

```python
from typing import List
from rich.progress import Progress, SpinnerColumn, TextColumn

@app.command()
def batch(
    files: List[Path] = typer.Argument(
        ...,
        help="XAML files to parse (supports globs)",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-d",
        help="Output directory for JSON files",
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="Show summary only",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Stop on first error",
    ),
):
    """Process multiple XAML files in batch.

    Examples:

        # Parse all workflows
        $ xaml-parser batch *.xaml --summary

        # Save all to directory
        $ xaml-parser batch *.xaml --output-dir results/

        # Process with glob
        $ xaml-parser batch "workflows/**/*.xaml" --summary
    """
    parser = XamlParser()
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(files))

        for file_path in files:
            progress.update(task, description=f"Parsing {file_path.name}")

            try:
                result = parser.parse_file(file_path)
                results.append((file_path, result))

                if not result.success and fail_fast:
                    console.print(f"[red]Failed:[/red] {file_path}")
                    sys.exit(1)

                # Save individual result
                if output_dir:
                    output_file = output_dir / f"{file_path.stem}.json"
                    output_json(result, output_file, pretty=True)

            except Exception as e:
                console.print(f"[red]Error processing {file_path}:[/red] {e}")
                if fail_fast:
                    sys.exit(1)

            progress.advance(task)

    # Summary
    if summary:
        output_batch_summary(results)


def output_batch_summary(results):
    """Display batch processing summary."""
    table = Table(title="Batch Processing Summary")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Arguments", justify="right")
    table.add_column("Activities", justify="right")

    for file_path, result in results:
        status = "✓" if result.success else "✗"
        args = len(result.content.arguments) if result.content else 0
        acts = len(result.content.activities) if result.content else 0

        table.add_row(
            file_path.name,
            status,
            str(args),
            str(acts),
        )

    console.print(table)

    # Overall stats
    total = len(results)
    success = sum(1 for _, r in results if r.success)
    failed = total - success

    console.print(f"\n[bold]Total:[/bold] {total} files")
    console.print(f"[green]Success:[/green] {success}")
    if failed:
        console.print(f"[red]Failed:[/red] {failed}")
```

## Testing the CLI

### Unit Tests

**File**: `python/tests/test_cli.py`

```python
import pytest
from typer.testing import CliRunner
from pathlib import Path

from xaml_parser.cli import app

runner = CliRunner()


def test_cli_help():
    """Test help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Parse UiPath XAML workflow files" in result.stdout


def test_parse_valid_file(tmp_path):
    """Test parsing a valid XAML file."""
    # Create test file
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(VALID_XAML_CONTENT)

    result = runner.invoke(app, [str(xaml_file)])
    assert result.exit_code == 0
    assert "✓" in result.stdout


def test_parse_json_output(tmp_path):
    """Test JSON output."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(VALID_XAML_CONTENT)

    result = runner.invoke(app, [str(xaml_file), "--json"])
    assert result.exit_code == 0
    assert '"success": true' in result.stdout


def test_parse_to_file(tmp_path):
    """Test saving to output file."""
    xaml_file = tmp_path / "test.xaml"
    output_file = tmp_path / "output.json"
    xaml_file.write_text(VALID_XAML_CONTENT)

    result = runner.invoke(app, [str(xaml_file), "--json", "-o", str(output_file)])
    assert result.exit_code == 0
    assert output_file.exists()


def test_parse_invalid_file():
    """Test parsing non-existent file."""
    result = runner.invoke(app, ["nonexistent.xaml"])
    assert result.exit_code != 0


def test_arguments_only_flag(tmp_path):
    """Test --arguments flag."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(VALID_XAML_CONTENT)

    result = runner.invoke(app, [str(xaml_file), "--arguments"])
    assert result.exit_code == 0
    assert "Arguments" in result.stdout
```

### Integration Tests

Test with actual XAML files from testdata:

```python
def test_parse_golden_files():
    """Test parsing golden freeze test files."""
    testdata_dir = Path(__file__).parent.parent / "testdata" / "golden"

    for xaml_file in testdata_dir.glob("*.xaml"):
        result = runner.invoke(app, [str(xaml_file), "--json"])
        assert result.exit_code == 0
```

## Documentation Updates

### 1. Update README.md

Add CLI section:

```markdown
## Command-Line Usage

### Installation

```bash
pip install xaml-parser
```

### Basic Usage

```bash
# Parse and display summary
xaml-parser workflow.xaml

# Output as JSON
xaml-parser workflow.xaml --json

# Save to file
xaml-parser workflow.xaml --json -o output.json

# Show only arguments
xaml-parser workflow.xaml --arguments

# Batch processing
xaml-parser batch *.xaml --summary
```

### CLI Options

```
--json              Output as JSON
--output, -o        Save to file
--arguments         Show arguments only
--activities        Show activities only
--tree              Show activity tree
--verbose, -v       Verbose output
--no-color          Disable colors
```
```

### 2. Update python/README.md

Add detailed CLI documentation with all options and examples.

## Common Patterns

### Pattern 1: Pipe to jq

```bash
xaml-parser workflow.xaml --json | jq '.content.arguments'
```

### Pattern 2: CI/CD Validation

```bash
#!/bin/bash
if xaml-parser workflow.xaml --no-color > /dev/null; then
    echo "Workflow valid"
    exit 0
else
    echo "Workflow invalid"
    exit 1
fi
```

### Pattern 3: Batch with Custom Processing

```python
from pathlib import Path
from xaml_parser.cli import app
from typer.testing import CliRunner

runner = CliRunner()

for file in Path("workflows").glob("*.xaml"):
    result = runner.invoke(app, [str(file), "--json"])
    # Process result...
```

## Performance Considerations

1. **Batch Processing**: Use progress bar for > 10 files
2. **Large Files**: Stream JSON output for very large results
3. **Memory**: Don't load all results in memory for batch
4. **Caching**: Consider caching parsed results

## Next Steps After Implementation

1. **Test with Real Workflows**: Your actual UiPath projects
2. **Gather Feedback**: What features are actually used?
3. **Iterate**: Add features based on real usage patterns
4. **Document**: Update docs with real examples
5. **Decide on Go**: Once CLI design is validated

## Troubleshooting

### Import Error

```bash
# Make sure installed in editable mode
cd python
uv pip install -e .
```

### Command Not Found

```bash
# Check installation
uv pip list | grep xaml-parser

# Reinstall entry point
uv pip install --force-reinstall -e .
```

### Rich Not Rendering

```bash
# Test terminal support
python -c "from rich.console import Console; Console().print('[bold red]Test[/bold red]')"

# Use --no-color flag
xaml-parser workflow.xaml --no-color
```

## Future Enhancements (Post-MVP)

1. **Config Files**: `.xaml-parser.yaml` for project settings
2. **Watch Mode**: Auto-parse on file changes
3. **Interactive Mode**: TUI for exploring workflows
4. **Plugins**: Allow custom output formatters
5. **Language Server**: IDE integration
6. **Web API**: RESTful API wrapper

---

This is a living document. Update it as you implement and discover better patterns!
