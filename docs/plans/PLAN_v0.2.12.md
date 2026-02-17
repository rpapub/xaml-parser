# PLAN v0.2.12: Enhanced CLI with Progress Indication

## Todo List

- [ ] **Implement progress reporter**: Progress bars with rich library
- [ ] **Add colorized output**: Format functions with color coding
- [ ] **Implement interactive mode**: REPL for exploring workflows
- [ ] **Implement watch mode**: Auto-reparse on file changes
- [ ] **Integrate with project parser**: Progress during project parsing
- [ ] **CLI flag integration**: Add --progress, --interactive, --watch flags
- [ ] **Graceful degradation**: Fallback when rich/watchdog unavailable
- [ ] **Add optional dependencies**: Update pyproject.toml
- [ ] **Write tests**: Test CLI features
- [ ] **Update CHANGELOG**: Document CLI enhancements

---

## Status
**Planned** - Ready for Implementation

## Priority
**MEDIUM** - Improves user experience

## Version
0.2.12

---

## Problem Statement

### Current Limitations

- No progress indication for large projects
- Projects with 100+ workflows parse silently
- No intermediate status updates
- No interactive mode
- No watch mode for development
- Plain text output (no colors)

### Why This Matters

- **User Experience**: Users don't know if parser is stuck or working
- **Long-Running Operations**: Large projects take minutes to parse
- **Development Workflow**: Manual reparse on file changes is tedious
- **Professional Feel**: Colorized output improves usability

---

## Features to Implement

### 1. Progress Bars

**For Project Parsing:**
- Show progress bar: `[=====>    ] 45/100 workflows parsed`
- Update in real-time as workflows parse
- Show current file being parsed
- Show ETA for completion

**For Large Files:**
- Show spinner for files > 1MB
- Indicate activity: "Parsing activities... extracting expressions..."

### 2. Interactive Mode

**Features:**
- REPL interface for exploring workflows
- Commands: `parse <file>`, `info`, `tree`, `activities`, `variables`, `exit`
- Tab completion for file paths
- Command history

### 3. Watch Mode

**Features:**
- Monitor directory for changes
- Auto-reparse on file modification
- Debounce: Wait 500ms after last change
- Show diff between parse results

### 4. Colorized Output

**Color Scheme:**
- `[OK]` in green
- `[FAIL]` in red
- `[WARN]` in yellow
- `[INFO]` in blue
- Activity types color-coded
- Variable names highlighted

---

## Implementation Approach

### Phase 1: Progress Bars with Rich

**Dependencies:**
- `rich` library for terminal UI (optional dependency)

**File**: `python/xaml_parser/progress.py` (NEW)

```python
"""Progress indication for CLI."""

from pathlib import Path

try:
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn,
        BarColumn, TaskProgressColumn, TimeRemainingColumn
    )
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class ProgressReporter:
    """Reports parsing progress to console."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and RICH_AVAILABLE
        self.console = Console() if RICH_AVAILABLE else None
        self.progress = None
        self.current_task = None

    def start_project(self, total_workflows: int):
        """Start project-level progress."""
        if not self.enabled:
            return

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        self.progress.start()
        self.current_task = self.progress.add_task(
            "Parsing workflows...",
            total=total_workflows
        )

    def update_workflow(self, workflow_path: Path, success: bool = True):
        """Update progress for single workflow."""
        if not self.enabled or not self.progress:
            return

        status = "[green]OK[/green]" if success else "[red]FAIL[/red]"
        self.progress.update(
            self.current_task,
            advance=1,
            description=f"Parsing {workflow_path.name} {status}"
        )

    def finish(self):
        """Complete progress reporting."""
        if self.enabled and self.progress:
            self.progress.stop()
```

**Integration**: `python/xaml_parser/project.py` (UPDATE)

```python
class ProjectParser:
    def parse_project(
        self,
        project_path: Path,
        recursive: bool = True,
        entry_points_only: bool = False,
        show_progress: bool = False,  # NEW
    ) -> ProjectResult:
        """Parse project with optional progress reporting."""

        progress = ProgressReporter(enabled=show_progress)
        workflow_files = self._discover_workflows(project_path, recursive)
        progress.start_project(len(workflow_files))

        for workflow_file in workflow_files:
            result = self.parser.parse_file(workflow_file)
            progress.update_workflow(workflow_file, success=result.success)

        progress.finish()
        return project_result
```

### Phase 2: Colorized Output

**File**: `python/xaml_parser/cli.py` (UPDATE)

```python
try:
    from rich.console import Console
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def format_pretty_rich(result: ParseResult) -> str:
    """Format with rich colors."""
    if not RICH_AVAILABLE:
        return format_pretty(result)  # Fallback

    console = Console()

    # Status with color
    if result.success:
        console.print(f"[green][OK][/green] Parsing succeeded")
    else:
        console.print(f"[red][FAIL][/red] Parsing failed")

    # Workflow info
    console.print(f"\n[bold]Workflow:[/bold] {result.content.display_name}")

    # Arguments with colors
    if result.content.arguments:
        console.print(f"\n[bold]Arguments:[/bold] ({len(result.content.arguments)} total)")
        for arg in result.content.arguments[:5]:
            direction_color = {
                'in': 'blue',
                'out': 'yellow',
                'inout': 'magenta'
            }.get(arg.direction, 'white')
            console.print(f"  [{direction_color}]{arg.direction.upper()}[/{direction_color}]: {arg.name}")
```

### Phase 3: Interactive Mode

**File**: `python/xaml_parser/interactive.py` (NEW)

```python
"""Interactive REPL for exploring workflows."""

import cmd
from pathlib import Path
from xaml_parser import XamlParser

class WorkflowExplorer(cmd.Cmd):
    """Interactive workflow explorer."""

    intro = "Welcome to XAML Parser Interactive Mode. Type 'help' for commands."
    prompt = "(xaml-parser) "

    def __init__(self):
        super().__init__()
        self.parser = XamlParser()
        self.current_result = None
        self.current_file = None

    def do_parse(self, arg):
        """Parse a workflow file: parse <path>"""
        file_path = Path(arg)

        if not file_path.exists():
            print(f"[!] File not found: {file_path}")
            return

        print(f"Parsing {file_path}...")
        self.current_result = self.parser.parse_file(file_path)
        self.current_file = file_path

        if self.current_result.success:
            print(f"[OK] Parsed successfully")
            print(f"  Activities: {len(self.current_result.content.activities)}")
        else:
            print(f"[FAIL] Parsing failed")

    def do_info(self, arg):
        """Show workflow info"""
        if not self.current_result:
            print("[!] No workflow parsed. Use 'parse <file>' first.")
            return

        content = self.current_result.content
        print(f"\nWorkflow: {content.display_name or 'Unnamed'}")
        print(f"Arguments: {len(content.arguments)}")
        print(f"Variables: {len(content.variables)}")
        print(f"Activities: {len(content.activities)}")

    def do_activities(self, arg):
        """List all activities"""
        if not self.current_result:
            return

        for activity in self.current_result.content.activities[:20]:
            print(f"  {activity.activity_type_short}: {activity.display_name or '(unnamed)'}")

    def do_exit(self, arg):
        """Exit interactive mode"""
        print("Goodbye!")
        return True

def run_interactive():
    """Start interactive mode."""
    WorkflowExplorer().cmdloop()
```

**CLI Integration**: Add flag in cli.py
```python
parser.add_argument('--interactive', '-i', action='store_true',
                   help='Start interactive mode')

if args.interactive:
    from xaml_parser.interactive import run_interactive
    run_interactive()
    return
```

### Phase 4: Watch Mode

**File**: `python/xaml_parser/watch.py` (NEW)

```python
"""Watch mode for auto-reparsing on file changes."""

import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

class XamlFileHandler(FileSystemEventHandler):
    """Handles XAML file changes."""

    def __init__(self, parser, callback):
        self.parser = parser
        self.callback = callback
        self.debounce_time = 0.5  # 500ms
        self.last_modified = {}

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix != '.xaml':
            return

        # Debounce
        now = time.time()
        if file_path in self.last_modified:
            if now - self.last_modified[file_path] < self.debounce_time:
                return

        self.last_modified[file_path] = now

        print(f"\n[INFO] File changed: {file_path.name}")
        print("Reparsing...")

        result = self.parser.parse_file(file_path)
        self.callback(file_path, result)

def watch_directory(directory: Path, parser):
    """Watch directory for XAML changes."""
    if not WATCHDOG_AVAILABLE:
        print("[!] watchdog library not installed. Install with: uv pip install watchdog")
        return

    print(f"Watching {directory} for changes...")
    print("Press Ctrl+C to stop")

    def on_parse_complete(file_path, result):
        if result.success:
            print(f"[OK] Parsed successfully")
        else:
            print(f"[FAIL] Parse errors: {len(result.errors)}")

    event_handler = XamlFileHandler(parser, on_parse_complete)
    observer = Observer()
    observer.schedule(event_handler, str(directory), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching")

    observer.join()
```

**CLI Integration**: Add flag
```python
parser.add_argument('--watch', '-w', action='store_true',
                   help='Watch for file changes and reparse')

if args.watch:
    from xaml_parser.watch import watch_directory
    watch_directory(Path(args.input).parent, XamlParser())
    return
```

---

## Dependencies

Add optional dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
cli = [
    "rich>=13.0.0",      # Progress bars, colors, trees
    "watchdog>=3.0.0",   # File system watching
]
```

Install with:
```bash
uv pip install -e ".[cli]"
```

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/progress.py` | NEW - Progress reporting with rich |
| `python/xaml_parser/interactive.py` | NEW - Interactive REPL |
| `python/xaml_parser/watch.py` | NEW - Watch mode |
| `python/xaml_parser/cli.py` | UPDATE - Colorized output, flags |
| `python/xaml_parser/project.py` | UPDATE - Progress integration |
| `python/pyproject.toml` | UPDATE - Add optional cli dependencies |

---

## Validation Criteria

- [ ] Progress bar shows for project parsing
- [ ] Colorized output works (with rich) and fallback works (without rich)
- [ ] Interactive mode starts and responds to commands
- [ ] Watch mode detects file changes and reparses
- [ ] Debouncing prevents excessive reparses
- [ ] All features gracefully degrade without optional dependencies
- [ ] Documentation updated

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement progress reporting | 2 hours |
| Colorized output with rich | 3 hours |
| Interactive mode | 3 hours |
| Watch mode | 2 hours |
| CLI integration | 1 hour |
| Graceful degradation | 1 hour |
| Testing | 2 hours |
| Documentation | 1 hour |
| **Total** | **~15 hours** |

---

## References

- rich library: https://rich.readthedocs.io/
- watchdog library: https://python-watchdog.readthedocs.io/
- Python cmd module: https://docs.python.org/3/library/cmd.html
