"""Command-line interface for XAML Parser."""

import argparse
import glob
import io
import json
import sys
from pathlib import Path
from typing import Any

from .models import ParseResult
from .parser import XamlParser
from .project import ProjectParser, ProjectResult

# Fix stdout encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def format_pretty(result: ParseResult, file_path: str | None = None) -> str:
    """Format result as human-readable output."""
    lines = []

    if file_path:
        lines.append(f"File: {file_path}")
        lines.append("")

    if not result.success:
        lines.append("[!] Parsing FAILED")
        lines.append("")
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  • {error}")
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  • {warning}")
        return "\n".join(lines)

    content = result.content
    if not content:
        return "\n".join(lines)

    lines.append("[OK] Parsing succeeded")
    lines.append("")

    # Summary
    if content.display_name or content.root_annotation:
        lines.append("Workflow:")
        if content.display_name:
            lines.append(f"  Name: {content.display_name}")
        if content.root_annotation:
            lines.append(f"  Description: {content.root_annotation}")
        lines.append("")

    lines.append("Summary:")
    lines.append(f"  Arguments: {len(content.arguments)}")
    lines.append(f"  Variables: {len(content.variables)}")
    lines.append(f"  Activities: {len(content.activities)}")
    lines.append(f"  Parse Time: {result.parse_time_ms:.2f}ms")

    # Arguments
    if content.arguments:
        lines.append("")
        lines.append("Arguments:")
        for arg in content.arguments:
            direction = arg.direction.upper()
            lines.append(f"  {direction}: {arg.name} ({arg.type})")
            if arg.annotation:
                lines.append(f"      → {arg.annotation}")

    # Variables (first 10)
    if content.variables:
        lines.append("")
        lines.append(f"Variables: ({len(content.variables)} total)")
        for var in content.variables[:10]:
            lines.append(f"  {var.name} ({var.type}) - scope: {var.scope}")
        if len(content.variables) > 10:
            lines.append(f"  ... and {len(content.variables) - 10} more")

    # Activities (summary)
    if content.activities:
        lines.append("")
        lines.append(f"Activities: ({len(content.activities)} total)")
        activity_types: dict[str, int] = {}
        for activity in content.activities:
            activity_types[activity.activity_type] = (
                activity_types.get(activity.activity_type, 0) + 1
            )

        for activity_type, count in sorted(
            activity_types.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            lines.append(f"  {activity_type}: {count}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def format_arguments(result: ParseResult) -> str:
    """Format only arguments."""
    if not result.success or not result.content:
        return f"Error: {', '.join(result.errors)}" if result.errors else "No content"

    lines = []
    for arg in result.content.arguments:
        direction = arg.direction.upper()
        lines.append(f"{direction}: {arg.name} ({arg.type})")
        if arg.annotation:
            lines.append(f"  → {arg.annotation}")
        if arg.default_value:
            lines.append(f"  Default: {arg.default_value}")

    return "\n".join(lines) if lines else "No arguments found"


def format_activities(result: ParseResult) -> str:
    """Format only activities."""
    if not result.success or not result.content:
        return f"Error: {', '.join(result.errors)}" if result.errors else "No content"

    lines = []
    for activity in result.content.activities:
        name = activity.display_name or "(unnamed)"
        lines.append(f"{activity.activity_type}: {name}")
        if activity.annotation:
            lines.append(f"  → {activity.annotation}")

    return "\n".join(lines) if lines else "No activities found"


def format_tree(result: ParseResult) -> str:
    """Format activities as a tree."""
    if not result.success or not result.content:
        return f"Error: {', '.join(result.errors)}" if result.errors else "No content"

    lines = []
    for activity in result.content.activities:
        indent = "  " * activity.depth
        name = activity.display_name or "(unnamed)"
        lines.append(f"{indent}{activity.activity_type}: {name}")
        if activity.annotation:
            lines.append(f"{indent}  → {activity.annotation}")

    return "\n".join(lines) if lines else "No activities found"


def format_summary(results: list[tuple[str, ParseResult]]) -> str:
    """Format summary for multiple files."""
    lines = []

    total_success = sum(1 for _, r in results if r.success)
    total_failed = len(results) - total_success

    lines.append(f"Processed {len(results)} file(s)")
    lines.append(f"  [OK] Succeeded: {total_success}")
    if total_failed > 0:
        lines.append(f"  [!] Failed: {total_failed}")
    lines.append("")

    for file_path, result in results:
        status = "[OK]" if result.success else "[!]"
        lines.append(f"{status} {file_path}")

        if result.success and result.content:
            content = result.content
            lines.append(
                f"    Arguments: {len(content.arguments)}, "
                f"Variables: {len(content.variables)}, "
                f"Activities: {len(content.activities)}"
            )
        else:
            lines.append(f"    Errors: {', '.join(result.errors[:2])}")

    return "\n".join(lines)


def format_project_summary(project_result: ProjectResult) -> str:
    """Format project parsing summary."""
    lines = []

    if not project_result.project_config:
        lines.append("Project: (config not loaded)")
        lines.append(f"Directory: {project_result.project_dir}")
        lines.append("")
        lines.append("[!] Project parsing FAILED")
        for error in project_result.errors:
            lines.append(f"  • {error}")
        return "\n".join(lines)

    lines.append(f"Project: {project_result.project_config.name}")
    lines.append(f"Directory: {project_result.project_dir}")
    lines.append("")

    if not project_result.success:
        lines.append("[!] Project parsing FAILED")
        lines.append("")
        lines.append("Errors:")
        for error in project_result.errors:
            lines.append(f"  • {error}")
        return "\n".join(lines)

    lines.append("[OK] Project parsing succeeded")
    lines.append("")

    # Project configuration
    lines.append("Configuration:")
    if project_result.project_config.main:
        lines.append(f"  Main: {project_result.project_config.main}")
    lines.append(f"  Expression Language: {project_result.project_config.expression_language}")
    if project_result.project_config.dependencies:
        lines.append(f"  Dependencies: {len(project_result.project_config.dependencies)}")
    lines.append("")

    # Entry points
    entry_points = project_result.get_entry_points()
    if entry_points:
        lines.append(f"Entry Points: ({len(entry_points)} total)")
        for ep in entry_points:
            status = "[OK]" if ep.parse_result.success else "[!]"
            lines.append(f"  {status} {ep.relative_path}")
        lines.append("")

    # Workflows summary
    lines.append(f"Workflows: ({project_result.total_workflows} total)")
    success_count = sum(1 for w in project_result.workflows if w.parse_result.success)
    lines.append(f"  Successfully parsed: {success_count}")
    failed = project_result.get_failed_workflows()
    if failed:
        lines.append(f"  Failed to parse: {len(failed)}")
    lines.append(f"  Total parse time: {project_result.total_parse_time_ms:.2f}ms")
    lines.append("")

    # Workflow list (first 10)
    lines.append("Workflows:")
    for workflow in project_result.workflows[:10]:
        status = "[OK]" if workflow.parse_result.success else "[!]"
        ep_marker = " (entry)" if workflow.is_entry_point else ""
        lines.append(f"  {status} {workflow.relative_path}{ep_marker}")

        if workflow.parse_result.success and workflow.parse_result.content:
            content = workflow.parse_result.content
            lines.append(
                f"      Args: {len(content.arguments)}, "
                f"Vars: {len(content.variables)}, "
                f"Acts: {len(content.activities)}"
            )

    if len(project_result.workflows) > 10:
        lines.append(f"  ... and {len(project_result.workflows) - 10} more")

    if project_result.warnings:
        lines.append("")
        lines.append(f"Warnings: ({len(project_result.warnings)} total, showing first 5)")
        for warning in project_result.warnings[:5]:
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def format_dependency_graph(project_result: ProjectResult) -> str:
    """Format project dependency graph."""
    lines = []

    project_name = (
        project_result.project_config.name if project_result.project_config else "(unknown)"
    )
    lines.append(f"Project: {project_name}")
    lines.append("Dependency Graph:")
    lines.append("")

    if not project_result.dependency_graph:
        lines.append("No dependencies found")
        return "\n".join(lines)

    for workflow_path, dependencies in sorted(project_result.dependency_graph.items()):
        lines.append(f"{workflow_path}")
        if dependencies:
            for dep in dependencies:
                lines.append(f"  -> {dep}")
        else:
            lines.append("  (no dependencies)")
        lines.append("")

    return "\n".join(lines)


def format_performance_report(parse_result: ParseResult) -> str:
    """Format performance profiling report (ASCII only, no Unicode).

    Displays timing breakdown, memory usage, and bottleneck analysis
    from ParseDiagnostics.performance_metrics.

    Args:
        parse_result: ParseResult with diagnostics containing performance_metrics

    Returns:
        Formatted ASCII report string

    Example output:
        [INFO] Performance Report
        ----------------------------------------
        Timing Breakdown:
          Operation                    Total      Count  Avg      %
          -----------------------------------------------------------
          activities_extract           125.3ms    1      125.3    58.2%
          xml_parse                    45.2ms     1      45.2     21.0%
          variables_extract            18.5ms     1      18.5     8.6%
          ...

        Memory Usage:
          Peak: 12.5 MB
          Delta: +8.2 MB
          Per Activity: ~0.15 MB

        Bottlenecks:
          [WARN] activities_extract took 58.2% of total time
          [INFO] Consider optimizing activity extraction
    """
    lines = []

    # Check if profiling data exists
    if not parse_result.diagnostics or not parse_result.diagnostics.performance_metrics:
        lines.append("[INFO] Performance profiling not enabled or no data collected")
        return "\n".join(lines)

    metrics = parse_result.diagnostics.performance_metrics

    lines.append("")
    lines.append("[INFO] Performance Report")
    lines.append("-" * 60)
    lines.append("")

    # Section 1: Timing Breakdown
    lines.append("Timing Breakdown:")
    lines.append(f"  {'Operation':<28} {'Total':<10} {'Count':<6} {'Avg':<8} {'%':<6}")
    lines.append("  " + "-" * 58)

    # Collect timing operations (those ending in _total_ms)
    timing_ops = []
    for key in sorted(metrics.keys()):
        if key.endswith("_total_ms"):
            op_name = key.replace("_total_ms", "")
            total_ms = metrics.get(key, 0.0)
            count = metrics.get(f"{op_name}_count", 0)
            avg_ms = metrics.get(f"{op_name}_avg_ms", 0.0)

            # Calculate percentage of total_profiled_ms
            total_profiled = metrics.get("total_profiled_ms", 0.0)
            if total_profiled > 0:
                pct = (total_ms / total_profiled) * 100.0
            else:
                pct = 0.0

            timing_ops.append((op_name, total_ms, count, avg_ms, pct))

    # Sort by percentage descending
    timing_ops.sort(key=lambda x: x[4], reverse=True)

    # Display timing operations
    for op_name, total_ms, count, avg_ms, pct in timing_ops:
        lines.append(f"  {op_name:<28} {total_ms:<10.2f} {count:<6} {avg_ms:<8.2f} {pct:<6.1f}%")

    # Add total
    total_profiled = metrics.get("total_profiled_ms", 0.0)
    lines.append("  " + "-" * 58)
    lines.append(f"  {'TOTAL':<28} {total_profiled:<10.2f}")
    lines.append("")

    # Section 2: Memory Usage
    lines.append("Memory Usage:")

    memory_peak_mb = metrics.get("memory_peak_mb", 0.0)
    memory_delta_mb = metrics.get("memory_delta_mb", 0.0)
    psutil_peak_mb = metrics.get("psutil_peak_mb", 0.0)
    psutil_delta_mb = metrics.get("psutil_delta_mb", 0.0)

    # Tracemalloc metrics (Python objects)
    lines.append(f"  Peak (Python objects): {memory_peak_mb:.2f} MB")
    lines.append(f"  Delta (Python objects): {memory_delta_mb:+.2f} MB")

    # Psutil metrics (process RSS) if available
    if psutil_peak_mb > 0:
        lines.append(f"  Peak (Process RSS): {psutil_peak_mb:.2f} MB")
        lines.append(f"  Delta (Process RSS): {psutil_delta_mb:+.2f} MB")

    # Per-activity estimate
    if parse_result.content and parse_result.content.total_activities > 0:
        per_activity_kb = (memory_delta_mb * 1024) / parse_result.content.total_activities
        lines.append(f"  Per Activity: ~{per_activity_kb:.2f} KB")

    lines.append("")

    # Section 3: Bottleneck Analysis
    bottlenecks = []
    threshold_pct = 10.0

    for op_name, _total_ms, _count, _avg_ms, pct in timing_ops:
        if pct >= threshold_pct:
            bottlenecks.append((op_name, pct))

    if bottlenecks:
        lines.append("Bottlenecks (>10% of total time):")
        for op_name, pct in bottlenecks:
            lines.append(f"  [WARN] {op_name} took {pct:.1f}% of total time")

        # Add optimization suggestions
        if any(op == "activities_extract" for op, _ in bottlenecks):
            lines.append("  [INFO] Consider using --no-expressions for faster parsing")
        if any(op == "xml_parse" for op, _ in bottlenecks):
            lines.append("  [INFO] XML parsing is I/O bound - file size matters")
    else:
        lines.append("Bottlenecks: None (all operations < 10% of total)")

    lines.append("")

    return "\n".join(lines)


def parse_files(patterns: list[str], config: dict[str, Any]) -> list[tuple[str, ParseResult]]:
    """Parse multiple files from glob patterns."""
    parser = XamlParser(config)
    results = []

    files = set()
    for pattern in patterns:
        # Handle wildcards
        if "*" in pattern or "?" in pattern:
            matched = glob.glob(pattern, recursive=True)
            files.update(matched)
        else:
            files.add(pattern)

    for file_path in sorted(files):
        path = Path(file_path)
        if not path.exists():
            # Create a fake error result
            result = ParseResult(
                content=None,
                success=False,
                errors=[f"File not found: {file_path}"],
                warnings=[],
                parse_time_ms=0,
                file_path=file_path,
                diagnostics=None,
                config_used=config,
            )
        else:
            result = parser.parse_file(path)

        results.append((file_path, result))

    return results


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="xaml-parser",
        description="Parse UiPath projects and XAML workflow files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Project parsing (default/primary mode)
  xaml-parser project.json                 # Parse entire project
  xaml-parser /path/to/project.json        # Absolute path
  xaml-parser /path/to/project             # Directory containing project.json
  xaml-parser project.json --graph         # Show dependency graph
  xaml-parser project.json --entry-points-only  # Parse only entry points

  # Project with views (graph-based output)
  xaml-parser project.json --dto --view flat         # Flat view (default, backward compatible)
  xaml-parser project.json --dto --view execution    # Call graph traversal from main
  xaml-parser project.json --dto --view execution --entry Main.xaml  # Custom entry point
  xaml-parser project.json --dto --view slice --focus act:sha256:abc123  # Activity context

  # Single workflow file parsing
  xaml-parser Main.xaml                    # Pretty print summary
  xaml-parser Main.xaml --json             # JSON output
  xaml-parser Main.xaml --arguments        # List arguments only
  xaml-parser Main.xaml --activities       # List activities
  xaml-parser Main.xaml --tree             # Activity tree view
  xaml-parser Main.xaml -o output.json     # Save JSON to file

  # Multiple workflow files
  xaml-parser *.xaml --summary             # Summary for multiple files
  xaml-parser **/*.xaml --summary          # Recursive search
        """,
    )

    parser.add_argument(
        "input",
        nargs="+",
        help="project.json, directory with project.json, or XAML file(s) to parse",
    )

    # Project parsing options
    parser.add_argument(
        "--entry-points-only",
        action="store_true",
        help="[Project mode] Only parse entry points (no recursive discovery)",
    )
    parser.add_argument(
        "--graph", action="store_true", help="[Project mode] Show workflow dependency graph"
    )

    # Output format options
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument("--json", action="store_true", help="Output as JSON")
    format_group.add_argument(
        "--dto",
        action="store_true",
        help="Output as WorkflowDto JSON (with stable IDs, edges, full normalization)",
    )
    format_group.add_argument("--arguments", action="store_true", help="Show only arguments")
    format_group.add_argument("--activities", action="store_true", help="Show only activities")
    format_group.add_argument("--tree", action="store_true", help="Show activity tree")
    format_group.add_argument(
        "--summary", action="store_true", help="Show summary for multiple files"
    )

    parser.add_argument("-o", "--output", help="Output file (default: stdout)")

    # DTO output options
    parser.add_argument(
        "--profile",
        choices=["full", "minimal", "mcp", "datalake"],
        default="full",
        help="DTO field profile (default: full) [requires --dto]",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine multiple workflows into single file [requires --dto]",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help=(
            "Sort all collections deterministically "
            "(default: preserve source order) [requires --dto]"
        ),
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Calculate quality metrics (complexity, size, quality score) [requires --dto]",
    )
    parser.add_argument(
        "--anti-patterns",
        action="store_true",
        help="Detect anti-patterns and code smells [requires --dto]",
    )

    # View options (Phase 6)
    parser.add_argument(
        "--view",
        choices=["flat", "execution", "slice"],
        default="flat",
        help=(
            "View type: flat (default), execution (call graph), or slice (context) [requires --dto]"
        ),
    )
    parser.add_argument(
        "--entry",
        help="Entry point workflow for execution view (path or ID) [requires --view=execution]",
    )
    parser.add_argument(
        "--focus",
        help="Focal activity ID for slice view [requires --view=slice]",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=2,
        help="Context radius for slice view (default: 2) [requires --view=slice]",
    )

    # Parser configuration
    parser.add_argument(
        "--no-expressions", action="store_true", help="Skip expression extraction (faster)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict mode (fail on any error)"
    )
    parser.add_argument(
        "--max-depth", type=int, default=50, help="Maximum activity nesting depth (default: 50)"
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Enable detailed performance profiling (timing and memory usage). Report shown with --verbose.",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bars for multi-file operations (requires rich library)",
    )

    # Logging options
    logging_group = parser.add_argument_group("logging options")
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose diagnostic logging to stderr",
    )
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO, or from config/env)",
    )
    logging_group.add_argument(
        "--log-dir",
        type=Path,
        help="Directory for log files (default: ~/.xaml-parser/logs)",
    )
    logging_group.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (performance mode)",
    )

    args = parser.parse_args()

    # Load config file if it exists (for logging and provenance)
    from .provenance import load_config

    config_file = load_config()
    logging_config = config_file.get("logging", {}) if config_file else {}

    # Setup logging (before any operations)
    from .logging_config import setup_logging

    setup_logging(
        log_level=args.log_level or logging_config.get("level", "INFO"),
        log_dir=args.log_dir,
        enable_file_logging=not args.no_log_file,
        verbose=args.verbose,
        config_dict=logging_config,
    )

    # Build parser config
    config = {
        "extract_expressions": not args.no_expressions,
        "strict_mode": args.strict,
        "max_depth": args.max_depth,
        "enable_profiling": args.performance,  # v0.2.11
    }

    # Detect mode: project vs file parsing
    first_input = args.input[0]
    input_path = Path(first_input)

    # Determine if this is project mode
    is_project_mode = False
    project_dir = None

    # Check if input is project.json file
    if first_input.endswith("project.json") or input_path.name == "project.json":
        is_project_mode = True
        if input_path.is_file():
            project_dir = input_path.parent
        else:
            print(f"Error: File not found: {first_input}", file=sys.stderr)
            sys.exit(1)

    # Check if input is a directory containing project.json
    elif input_path.is_dir():
        project_json = input_path / "project.json"
        if project_json.exists():
            is_project_mode = True
            project_dir = input_path
        else:
            print(f"Error: No project.json found in directory: {first_input}", file=sys.stderr)
            sys.exit(1)

    # Validate: project mode options only work in project mode
    if not is_project_mode:
        if args.entry_points_only:
            print("Error: --entry-points-only only works with project.json", file=sys.stderr)
            sys.exit(1)
        if args.graph:
            print("Error: --graph only works with project.json", file=sys.stderr)
            sys.exit(1)

    # Handle project parsing mode
    if is_project_mode:
        if len(args.input) > 1:
            print("Error: Cannot specify multiple inputs in project mode", file=sys.stderr)
            sys.exit(1)

        if not project_dir:
            print("Error: Could not determine project directory", file=sys.stderr)
            sys.exit(1)

        project_parser = ProjectParser(config)
        project_result = project_parser.parse_project(
            project_dir,
            recursive=not args.entry_points_only,
            entry_points_only=args.entry_points_only,
            show_progress=args.progress,  # v0.2.12
        )

        # Format project output
        if args.dto:
            # DTO mode for projects: use views if requested
            from .project import analyze_project

            # Build ProjectIndex
            index = analyze_project(project_result)

            # Render view
            from .views import ExecutionView, NestedView, SliceView, View

            view: View
            if args.view == "execution":
                # Validate entry point
                if not args.entry:
                    # Use main workflow from project config as default
                    if project_result.project_config and project_result.project_config.main:
                        entry_point = project_result.project_config.main
                    else:
                        print("Error: --entry required for execution view", file=sys.stderr)
                        sys.exit(1)
                else:
                    entry_point = args.entry

                view = ExecutionView(entry_point=entry_point, max_depth=args.max_depth)
                view_output = view.render(index)

            elif args.view == "slice":
                # Validate focus
                if not args.focus:
                    print("Error: --focus required for slice view", file=sys.stderr)
                    sys.exit(1)

                view = SliceView(focus=args.focus, radius=args.radius)
                view_output = view.render(index)

            else:  # flat view (default) - uses NestedView for hierarchical structure
                view = NestedView()
                view_output = view.render(index)

            # Write output
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = Path("workflows.json")

            # Write JSON
            output_path.write_text(json.dumps(view_output, indent=2), encoding="utf-8")
            print(f"[OK] Wrote {args.view} view to {output_path}")
            sys.exit(0)

        elif args.graph:
            output = format_dependency_graph(project_result)
        elif args.json:
            # JSON output for projects
            output = json.dumps(
                {
                    "project_name": project_result.project_config.name
                    if project_result.project_config
                    else "(unknown)",
                    "project_dir": str(project_result.project_dir),
                    "success": project_result.success,
                    "total_workflows": project_result.total_workflows,
                    "errors": project_result.errors,
                },
                indent=2,
            )
        else:
            output = format_project_summary(project_result)

        # Write output (only for non-DTO modes)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Output written to: {args.output}")
        else:
            print(output)

        # Exit code
        sys.exit(0 if project_result.success else 1)

    # Handle file parsing mode
    results = parse_files(args.input, config)

    # Handle no files matched
    if not results:
        print(f"Error: No files matched pattern(s): {', '.join(args.input)}", file=sys.stderr)
        sys.exit(1)

    # Handle DTO output mode
    if args.dto:
        from .control_flow import ControlFlowExtractor
        from .emitters import EmitterConfig
        from .emitters.json_emitter import JsonEmitter
        from .id_generation import IdGenerator
        from .normalization import Normalizer

        # Normalize all successful parse results to DTOs
        id_generator = IdGenerator()
        flow_extractor = ControlFlowExtractor(id_generator)
        normalizer = Normalizer(id_generator, flow_extractor)

        workflows = []
        for file_path, parse_result in results:
            if parse_result.success:
                workflow_name = Path(file_path).stem
                workflow_dto = normalizer.normalize(
                    parse_result,
                    workflow_name=workflow_name,
                    sort_output=args.sort,
                    calculate_metrics=getattr(args, "metrics", False),
                    detect_anti_patterns=getattr(args, "anti_patterns", False),
                )
                workflows.append(workflow_dto)

        if not workflows:
            print("Error: No workflows parsed successfully", file=sys.stderr)
            sys.exit(1)

        # Emit using JSON emitter
        emitter = JsonEmitter()
        emitter_config = EmitterConfig(
            field_profile=args.profile,
            combine=args.combine,
            pretty=True,
            exclude_none=True,
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        elif args.combine:
            output_path = Path("workflows.json")
        else:
            output_path = Path(".")

        # Emit
        emit_result = emitter.emit(workflows, output_path, emitter_config)

        if emit_result.success:
            if args.output:
                print(f"✓ Wrote {len(emit_result.files_written)} file(s) to {args.output}")
            else:
                for written_path in emit_result.files_written:
                    print(f"✓ Wrote: {written_path}")
            sys.exit(0)
        else:
            print("✗ Emission failed:", file=sys.stderr)
            for error in emit_result.errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

    # Format output
    if args.summary or len(results) > 1:
        output = format_summary(results)
    elif len(results) == 1:
        file_path, parse_result = results[0]

        if args.json:
            # Convert result to dict for JSON serialization
            output_dict = {
                "file_path": file_path,
                "success": parse_result.success,
                "errors": parse_result.errors,
                "warnings": parse_result.warnings,
                "parse_time_ms": parse_result.parse_time_ms,
            }

            if parse_result.success and parse_result.content:
                output_dict["content"] = {
                    "arguments": [
                        {
                            "name": arg.name,
                            "type": arg.type,
                            "direction": arg.direction,
                            "annotation": arg.annotation,
                            "default_value": arg.default_value,
                        }
                        for arg in parse_result.content.arguments
                    ],
                    "variables": [
                        {
                            "name": var.name,
                            "type": var.type,
                            "scope": var.scope,
                            "default_value": var.default_value,
                        }
                        for var in parse_result.content.variables
                    ],
                    "activities": [
                        {
                            "activity_type": act.activity_type,
                            "activity_id": act.activity_id,
                            "display_name": act.display_name,
                            "annotation": act.annotation,
                            "depth": act.depth,
                        }
                        for act in parse_result.content.activities
                    ],
                    "display_name": parse_result.content.display_name,
                    "root_annotation": parse_result.content.root_annotation,
                    "total_arguments": parse_result.content.total_arguments,
                    "total_variables": parse_result.content.total_variables,
                    "total_activities": parse_result.content.total_activities,
                }

            output = json.dumps(output_dict, indent=2)
        elif args.arguments:
            output = format_arguments(parse_result)
        elif args.activities:
            output = format_activities(parse_result)
        elif args.tree:
            output = format_tree(parse_result)
        else:
            output = format_pretty(parse_result, file_path)
    else:
        output = ""

    # Add performance report if requested (v0.2.11)
    # Show only when BOTH --performance AND --verbose are set
    if args.performance and args.verbose and len(results) == 1:
        _, parse_result = results[0]
        if parse_result.success:
            perf_report = format_performance_report(parse_result)
            output += "\n" + perf_report

    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Output written to: {args.output}")
    else:
        print(output)

    # Exit code based on success
    if all(result.success for _, result in results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
