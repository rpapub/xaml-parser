"""Command-line interface for XAML Parser."""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List
import glob
import io

from .parser import XamlParser
from .models import ParseResult

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def format_pretty(result: ParseResult, file_path: Optional[str] = None) -> str:
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
    lines.append(f"  Expression Language: {content.expression_language}")
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
        activity_types = {}
        for activity in content.activities:
            activity_types[activity.activity_type] = activity_types.get(activity.activity_type, 0) + 1

        for activity_type, count in sorted(activity_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"  {activity_type}: {count}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def format_arguments(result: ParseResult) -> str:
    """Format only arguments."""
    if not result.success:
        return f"Error: {', '.join(result.errors)}"

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
    if not result.success:
        return f"Error: {', '.join(result.errors)}"

    lines = []
    for activity in result.content.activities:
        name = activity.display_name or "(unnamed)"
        lines.append(f"{activity.activity_type}: {name}")
        if activity.annotation:
            lines.append(f"  → {activity.annotation}")

    return "\n".join(lines) if lines else "No activities found"


def format_tree(result: ParseResult) -> str:
    """Format activities as a tree."""
    if not result.success:
        return f"Error: {', '.join(result.errors)}"

    lines = []
    for activity in result.content.activities:
        indent = "  " * activity.depth
        name = activity.display_name or "(unnamed)"
        lines.append(f"{indent}{activity.activity_type}: {name}")
        if activity.annotation:
            lines.append(f"{indent}  → {activity.annotation}")

    return "\n".join(lines) if lines else "No activities found"


def format_summary(results: List[tuple[str, ParseResult]]) -> str:
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

        if result.success:
            content = result.content
            lines.append(f"    Arguments: {len(content.arguments)}, "
                        f"Variables: {len(content.variables)}, "
                        f"Activities: {len(content.activities)}")
        else:
            lines.append(f"    Errors: {', '.join(result.errors[:2])}")

    return "\n".join(lines)


def parse_files(patterns: List[str], config: dict) -> List[tuple[str, ParseResult]]:
    """Parse multiple files from glob patterns."""
    parser = XamlParser(config)
    results = []

    files = set()
    for pattern in patterns:
        # Handle wildcards
        if '*' in pattern or '?' in pattern:
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
                config_used=config
            )
        else:
            result = parser.parse_file(path)

        results.append((file_path, result))

    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='xaml-parser',
        description='Parse UiPath XAML workflow files and extract metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xaml-parser Main.xaml                    # Pretty print summary
  xaml-parser Main.xaml --json             # JSON output
  xaml-parser Main.xaml --arguments        # List arguments only
  xaml-parser Main.xaml --activities       # List activities
  xaml-parser Main.xaml --tree             # Activity tree view
  xaml-parser Main.xaml -o output.json     # Save JSON to file
  xaml-parser *.xaml --summary             # Summary for multiple files
  xaml-parser **/*.xaml --summary          # Recursive search
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        help='XAML file(s) to parse (supports wildcards)'
    )

    # Output format options
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    format_group.add_argument(
        '--arguments',
        action='store_true',
        help='Show only arguments'
    )
    format_group.add_argument(
        '--activities',
        action='store_true',
        help='Show only activities'
    )
    format_group.add_argument(
        '--tree',
        action='store_true',
        help='Show activity tree'
    )
    format_group.add_argument(
        '--summary',
        action='store_true',
        help='Show summary for multiple files'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )

    # Parser configuration
    parser.add_argument(
        '--no-expressions',
        action='store_true',
        help='Skip expression extraction (faster)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict mode (fail on any error)'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=50,
        help='Maximum activity nesting depth (default: 50)'
    )

    # Misc options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Build parser config
    config = {
        'extract_expressions': not args.no_expressions,
        'strict_mode': args.strict,
        'max_depth': args.max_depth,
    }

    # Parse files
    results = parse_files(args.files, config)

    # Handle no files matched
    if not results:
        print(f"Error: No files matched pattern(s): {', '.join(args.files)}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.summary or len(results) > 1:
        output = format_summary(results)
    elif len(results) == 1:
        file_path, result = results[0]

        if args.json:
            # Convert result to dict for JSON serialization
            output_dict = {
                'file_path': file_path,
                'success': result.success,
                'errors': result.errors,
                'warnings': result.warnings,
                'parse_time_ms': result.parse_time_ms,
            }

            if result.success and result.content:
                output_dict['content'] = {
                    'arguments': [
                        {
                            'name': arg.name,
                            'type': arg.type,
                            'direction': arg.direction,
                            'annotation': arg.annotation,
                            'default_value': arg.default_value
                        }
                        for arg in result.content.arguments
                    ],
                    'variables': [
                        {
                            'name': var.name,
                            'type': var.type,
                            'scope': var.scope,
                            'default_value': var.default_value
                        }
                        for var in result.content.variables
                    ],
                    'activities': [
                        {
                            'activity_type': act.activity_type,
                            'activity_id': act.activity_id,
                            'display_name': act.display_name,
                            'annotation': act.annotation,
                            'depth': act.depth
                        }
                        for act in result.content.activities
                    ],
                    'display_name': result.content.display_name,
                    'root_annotation': result.content.root_annotation,
                    'expression_language': result.content.expression_language,
                    'total_arguments': result.content.total_arguments,
                    'total_variables': result.content.total_variables,
                    'total_activities': result.content.total_activities
                }

            output = json.dumps(output_dict, indent=2)
        elif args.arguments:
            output = format_arguments(result)
        elif args.activities:
            output = format_activities(result)
        elif args.tree:
            output = format_tree(result)
        else:
            output = format_pretty(result, file_path)
    else:
        output = ""

    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Output written to: {args.output}")
    else:
        print(output)

    # Exit code based on success
    if all(result.success for _, result in results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
