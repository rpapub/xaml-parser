#!/usr/bin/env python3
"""Developer test script to generate DTO outputs from test-corpus projects.

This script is NOT part of the pytest suite. It's for manual inspection
of DTO outputs to validate the implementation.

Usage:
    uv run python developer-tests/test_corpus_output.py

Output:
    developer-tests/output/
    ├── CORE_00000001/
    │   ├── flat_view.json
    │   ├── execution_view.json
    │   ├── slice_view_<activity_id>.json
    │   ├── workflows/
    │   │   └── <workflow_name>.json
    │   └── activities/
    │       └── <activity_id>.json
    └── CORE_00000010/
        └── ... (same structure)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from xaml_parser import ProjectParser, analyze_project
from xaml_parser.views import ExecutionView, FlatView, SliceView


def main():
    """Generate DTO outputs for test-corpus projects."""
    print("=" * 80)
    print("XAML Parser - Developer Test Output Generator")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test corpus projects
    corpus_root = Path(__file__).parent.parent / "test-corpus"
    projects = [
        ("CORE_00000001", corpus_root / "c25v001_CORE_00000001"),
        ("CORE_00000010", corpus_root / "c25v001_CORE_00000010"),
    ]

    # Output directory
    output_root = Path(__file__).parent / "output"
    output_root.mkdir(exist_ok=True)

    for project_name, project_path in projects:
        print(f"\n{'=' * 80}")
        print(f"Processing: {project_name}")
        print(f"Path: {project_path}")
        print(f"{'=' * 80}\n")

        if not project_path.exists():
            print(f"[ERROR] Project not found: {project_path}")
            continue

        # Create output directory for this project
        project_output = output_root / project_name
        project_output.mkdir(exist_ok=True)

        try:
            # Parse project
            print("[1/6] Parsing project...")
            parser = ProjectParser()
            result = parser.parse_project(project_path, recursive=True)

            if not result.success:
                print(f"[ERROR] Parsing failed:")
                for error in result.errors:
                    print(f"  - {error}")
                continue

            print(f"      [OK] Parsed {result.total_workflows} workflows in {result.total_parse_time_ms:.0f}ms")

            # Analyze project
            print("[2/6] Building graph index...")
            index = analyze_project(result)
            print(f"      [OK] Index built:")
            print(f"        - Workflows: {index.total_workflows}")
            print(f"        - Activities: {index.total_activities}")
            print(f"        - Entry points: {len(index.entry_points)}")

            # Generate FlatView output
            print("[3/6] Generating FlatView output...")
            flat_view = FlatView()
            flat_output = flat_view.render(index)
            flat_file = project_output / "flat_view.json"
            flat_file.write_text(json.dumps(flat_output, indent=2), encoding="utf-8")
            print(f"      [OK] Saved: {flat_file}")

            # Generate ExecutionView output (from first entry point)
            print("[4/6] Generating ExecutionView output...")
            if index.entry_points:
                entry_point = index.entry_points[0]
                exec_view = ExecutionView(entry_point=entry_point, max_depth=10)
                exec_output = exec_view.render(index)
                exec_file = project_output / "execution_view.json"
                exec_file.write_text(json.dumps(exec_output, indent=2), encoding="utf-8")
                print(f"      [OK] Saved: {exec_file}")
                print(f"        - Entry point: {entry_point}")
                print(f"        - Workflows traversed: {len(exec_output['workflows'])}")
            else:
                print("      [WARN] No entry points found, skipping ExecutionView")

            # Generate SliceView output (for first few activities)
            print("[5/6] Generating SliceView outputs...")
            activity_ids = list(index.activities.nodes())[:3]  # First 3 activities
            if activity_ids:
                for i, activity_id in enumerate(activity_ids, 1):
                    slice_view = SliceView(focus=activity_id, radius=2)
                    slice_output = slice_view.render(index)
                    slice_file = project_output / f"slice_view_{i}.json"
                    slice_file.write_text(json.dumps(slice_output, indent=2), encoding="utf-8")
                    print(f"      [OK] Saved: {slice_file}")
                    print(f"        - Focus: {activity_id[:24]}...")
            else:
                print("      [WARN] No activities found, skipping SliceView")

            # Generate individual workflow DTOs
            print("[6/6] Generating individual object outputs...")
            workflows_dir = project_output / "workflows"
            workflows_dir.mkdir(exist_ok=True)

            for wf_id in index.workflows.nodes():
                workflow = index.get_workflow(wf_id)
                if workflow:
                    # Use workflow name for filename
                    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in workflow.name)
                    wf_file = workflows_dir / f"{safe_name}.json"
                    wf_dict = {
                        "id": workflow.id,
                        "name": workflow.name,
                        "source": {
                            "path": workflow.source.path,
                            "hash": workflow.source.hash,
                            "size_bytes": workflow.source.size_bytes,
                        },
                        "metadata": {
                            "expression_language": workflow.metadata.expression_language,
                            "annotation": workflow.metadata.annotation,
                            "display_name": workflow.metadata.display_name,
                        },
                        "argument_count": len(workflow.arguments),
                        "variable_count": len(workflow.variables),
                        "activity_count": len(workflow.activities),
                        "edge_count": len(workflow.edges),
                        "invocation_count": len(workflow.invocations),
                        "issues": [
                            {"level": issue.level, "message": issue.message}
                            for issue in workflow.issues
                        ],
                    }
                    wf_file.write_text(json.dumps(wf_dict, indent=2), encoding="utf-8")
            print(f"      [OK] Saved {len(list(workflows_dir.glob('*.json')))} workflow summaries to: {workflows_dir}")

            # Generate individual activity DTOs (sample)
            activities_dir = project_output / "activities"
            activities_dir.mkdir(exist_ok=True)

            activity_sample = list(index.activities.nodes())[:5]  # First 5 activities
            for activity_id in activity_sample:
                activity = index.get_activity(activity_id)
                if activity:
                    # Use short ID for filename
                    short_id = activity_id.replace("act:sha256:", "")[:16]
                    act_file = activities_dir / f"{short_id}.json"
                    act_dict = {
                        "id": activity.id,
                        "type": activity.type,
                        "type_short": activity.type_short,
                        "display_name": activity.display_name,
                        "parent_id": activity.parent_id,
                        "children": activity.children,
                        "depth": activity.depth,
                        "annotation": activity.annotation,
                        "properties": activity.properties,
                        "expressions": activity.expressions,
                        "variables_referenced": activity.variables_referenced,
                    }
                    act_file.write_text(json.dumps(act_dict, indent=2), encoding="utf-8")
            print(f"      [OK] Saved {len(list(activities_dir.glob('*.json')))} activity samples to: {activities_dir}")

            print(f"\n[SUCCESS] All outputs generated for {project_name}")

        except Exception as e:
            print(f"\n[ERROR] processing {project_name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("Output generated in: developer-tests/output/")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
