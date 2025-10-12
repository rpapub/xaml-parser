# INSTRUCTIONS: Implementing Nested Activity Output

**Target Audience:** Junior developers
**Estimated Time:** 8-12 hours
**Difficulty:** Intermediate
**Status:** Not yet implemented

---

## Problem Statement

### What's Wrong?

The XAML parser currently outputs activities in a **flat list** structure. Here's actual output from parsing `myEntrypointOne.xaml`:

```json
{
  "activities": [
    {
      "id": "act:sha256:e97581dc136f0418",
      "type": "Sequence",
      "type_short": "Sequence",
      "display_name": "Main Sequence",
      "parent_id": "act:sha256:7504082df4a9113e",
      "children": [
        "act:sha256:540341343fd80059",
        "act:sha256:a0a18f98fe8a22b4",
        "act:sha256:a1012431753af1c4",
        "act:sha256:26bdbc5ad9143735"
      ],
      "depth": 1
    },
    {
      "id": "act:sha256:540341343fd80059",
      "type": "LogMessage",
      "type_short": "LogMessage",
      "display_name": "Log Message INFO begin",
      "parent_id": "act:sha256:e97581dc136f0418",
      "children": [],
      "depth": 2
    },
    {
      "id": "act:sha256:a0a18f98fe8a22b4",
      "type": "InvokeWorkflowFile",
      "type_short": "InvokeWorkflowFile",
      "display_name": "InitAllSettings - Invoke Workflow File",
      "parent_id": "act:sha256:e97581dc136f0418",
      "children": [],
      "depth": 2,
      "properties": {
        "WorkflowFileName": "Framework\\InitAllSettings.xaml"
      }
    },
    {
      "id": "act:sha256:a1012431753af1c4",
      "type": "Sequence",
      "type_short": "Sequence",
      "display_name": null,
      "parent_id": "act:sha256:e97581dc136f0418",
      "children": [
        "act:sha256:89235c3ef581d644"
      ],
      "depth": 2
    },
    {
      "id": "act:sha256:89235c3ef581d644",
      "type": "Comment",
      "type_short": "Comment",
      "display_name": null,
      "parent_id": "act:sha256:a1012431753af1c4",
      "children": [],
      "depth": 3,
      "properties": {
        "Text": "This sequence intentionally left blank"
      }
    }
  ]
}
```

**Problems:**
1. **Not "exact"**: Original XAML has clear nesting (Sequence > LogMessage > InvokeWorkflowFile > nested Sequence > Comment), we flatten it
2. **Harder to read**: Human/LLM must mentally reconstruct that Comment is inside nested Sequence inside Main Sequence
3. **Verbose**: Activity IDs repeated everywhere (parent_id + children list + separate activity entries)
4. **Conceptual mismatch**: The flat list doesn't show that there's a nested Sequence with a Comment inside it
5. **Navigation difficulty**: To understand workflow structure, you must:
   - Find parent by matching IDs
   - Find children by matching IDs in children array
   - Reconstruct tree mentally or programmatically

### What We Want

**Nested output** that mirrors the original XAML structure AND traverses the call graph:

```json
{
  "activities": [
    {
      "id": "act:sha256:e97581dc136f0418",
      "type": "Sequence",
      "type_short": "Sequence",
      "display_name": "Main Sequence",
      "depth": 1,
      "children": [
        {
          "id": "act:sha256:540341343fd80059",
          "type": "LogMessage",
          "display_name": "Log Message INFO begin",
          "properties": {
            "Message": "Going to process myEntrypointOne"
          },
          "children": []
        },
        {
          "id": "act:sha256:a0a18f98fe8a22b4",
          "type": "InvokeWorkflowFile",
          "display_name": "InitAllSettings - Invoke Workflow File",
          "properties": {
            "WorkflowFileName": "Framework\\InitAllSettings.xaml"
          },
          "children": [
            {
              "id": "act:sha256:...",
              "type": "Sequence",
              "display_name": "Initialize All Settings",
              "children": [
                {
                  "type": "LogMessage",
                  "display_name": "Log Message (Initialize All Settings)",
                  "properties": {"Message": "Initializing settings..."},
                  "children": []
                },
                {
                  "type": "Assign",
                  "display_name": "Assign out_Config (initialization)",
                  "children": []
                },
                {
                  "type": "ForEach",
                  "display_name": "For each configuration sheet",
                  "children": [
                    {
                      "type": "Sequence",
                      "display_name": "Get local settings and constants",
                      "children": [
                        {
                          "type": "ReadRange",
                          "display_name": "Read range (Settings and Constants sheets)",
                          "children": []
                        },
                        {
                          "type": "ForEachRow",
                          "display_name": "For each configuration row",
                          "children": [
                            {
                              "type": "If",
                              "display_name": "If configuration row is not empty",
                              "children": [
                                {
                                  "type": "Assign",
                                  "display_name": "Add Config key/value pair",
                                  "children": []
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "TryCatch",
                  "display_name": "Try initializing assets",
                  "children": [
                    {
                      "type": "Sequence",
                      "display_name": "Get Orchestrator assets",
                      "children": [
                        {"type": "ReadRange", "display_name": "Read range (Assets sheet)", "children": []},
                        {
                          "type": "ForEachRow",
                          "display_name": "For each asset row",
                          "children": [
                            {
                              "type": "TryCatch",
                              "children": [
                                {
                                  "type": "Sequence",
                                  "display_name": "Get asset from Orchestrator",
                                  "children": [
                                    {"type": "GetRobotAsset", "children": []},
                                    {"type": "Assign", "display_name": "Assign asset value in Config", "children": []}
                                  ]
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "id": "act:sha256:a1012431753af1c4",
          "type": "Sequence",
          "children": [
            {
              "id": "act:sha256:89235c3ef581d644",
              "type": "Comment",
              "properties": {
                "Text": "This sequence intentionally left blank"
              },
              "children": []
            }
          ]
        },
        {
          "type": "InvokeWorkflowFile",
          "display_name": "myEmptyWorkflow - Invoke Workflow File",
          "properties": {
            "WorkflowFileName": "Foo\\myEmptyWorkflow.xaml"
          },
          "children": []
        },
        {
          "type": "LogMessage",
          "display_name": "Log Message TRACE end",
          "properties": {
            "Message": "Finished processing myEntrypointOne"
          },
          "children": []
        }
      ]
    }
  ]
}
```

**Benefits:**
- Shows FULL call graph traversal (InvokeWorkflowFile expanded with invoked workflow content)
- Mirrors actual execution flow
- More human/LLM readable - see the entire process at once
- Less verbose - no need to manually chase InvokeWorkflowFile references
- Only root activities at top level
- Clear visual hierarchy that matches actual XAML + call graph structure

### Why Not Change DTOs?

**DTOs stay flat** for good reasons:
1. **Analytics-friendly**: Flat lists easier for SQL/pandas/data lakes
2. **Deterministic ordering**: Easy to sort all activities alphabetically by ID
3. **Graph traversal**: Parent/child IDs enable efficient graph algorithms
4. **Backward compatibility**: Existing consumers expect flat structure

**Solution:** Nesting is a **presentation concern**, not a data model concern. We transform flat -> nested during JSON serialization.

---

## Architecture Overview

```
+---------------------------------------------------------------+
|                     Parsing & Normalization                   |
|                 (Existing - No Changes Needed)                |
+-------------------------------+-------------------------------+
                                |
                                v
                      +-------------------+
                      | WorkflowCollection|
                      | (multiple files)  |  <--- All workflows parsed
                      | + invocations     |      (flat lists)
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |dataclasses.asdict()|
                      +---------+---------+
                                |
                +---------------+---------------+
                |                               |
                v                               v
    +-----------------+             +---------------------+
    |   Flat Mode     |             |   Nested Mode       |
    |   (existing)    |             |   (NEW)             |
    |                 |             |                     |
    | Return dict     |             | 1. build_activity_  |
    | as-is           |             |    tree() per file  |
    |                 |             | 2. traverse_call_   |
    |                 |             |    graph()          |
    |                 |             | 3. expand_invoked_  |
    |                 |             |    workflows()      |
    +---------+-------+             +-----------+---------+
              |                                 |
              |                                 v
              |                     +-----------------------+
              |                     | For each Invoke:      |
              |                     | 1. Find callee by ID  |
              |                     | 2. Get callee tree    |
              |                     | 3. Set as children[]  |
              |                     +-----------+-----------+
              |                                 |
              +---------------+-----------------+
                              |
                              v
                  +------------------------+
                  |    JSON output         |
                  |  (flat or nested with  |
                  |   call graph)          |
                  +------------------------+
```

**Key Design Decisions:**

1. **Work at dict level**, not ActivityDto level
   - Avoids recursive dataclass type issues
   - Easier to manipulate JSON structure

2. **Single source of truth**: Flat DTOs + invocations are canonical
   - Nesting is derived transformation
   - Call graph traversal done at serialization time

3. **Use existing invocations data**
   - WorkflowDto already has `invocations: list[InvocationDto]`
   - Maps caller activity ID -> callee workflow ID
   - No need to re-parse to find calls

4. **Opt-in feature**: `--nested` flag
   - Backward compatible (default: flat)
   - Users choose based on use case

5. **Two-phase nesting**:
   - Phase 1: Nest activities within each file (parent/child)
   - Phase 2: Expand InvokeWorkflowFile with callee content (call graph)

---

## Implementation Guide

**IMPORTANT: Two-Phase Nesting Approach**

This implementation has TWO distinct phases:

1. **Phase 1: Local Nesting** - Nest activities within each workflow file
   - Input: Flat list with parent_id/children references
   - Output: Nested tree per workflow
   - Complexity: Straightforward tree reconstruction

2. **Phase 2: Call Graph Expansion** - Expand InvokeWorkflowFile with callee content
   - Input: Nested trees + invocations data
   - Output: Nested tree with invoked workflows as children
   - Complexity: Requires workflow lookup, invocation matching, circular detection

**Recommendation:** Start with Phase 1 (local nesting) to get working nested output. Then add Phase 2 (call graph) as enhancement.

---

### Phase 1: Tree Builder Module (Local Nesting)

**File to create:** `python/xaml_parser/tree_builder.py`

#### Step 1.1: Understand the Algorithm

**Input:** Flat list of activity dicts with ID references
```python
[
  {"id": "a1", "parent_id": None, "children": ["a2", "a3"]},
  {"id": "a2", "parent_id": "a1", "children": ["a4"]},
  {"id": "a3", "parent_id": "a1", "children": []},
  {"id": "a4", "parent_id": "a2", "children": []},
]
```

**Output:** Nested tree with only root activities
```python
[
  {
    "id": "a1",
    "children": [
      {
        "id": "a2",
        "children": [
          {"id": "a4", "children": []}
        ]
      },
      {"id": "a3", "children": []}
    ]
  }
]
```

**Algorithm:**
1. Build lookup map: `id -> activity dict`
2. Identify root activities (no parent_id or parent_id is None)
3. For each activity, replace `children: list[str]` with `children: list[dict]`
4. Recursively nest children
5. Optionally remove `parent_id` field (redundant in nested output)

#### Step 1.2: Write the Code

Create `python/xaml_parser/tree_builder.py`:

```python
"""Tree reconstruction for nested activity output.

This module converts flat activity lists with ID references into
nested tree structures that mirror the original XAML hierarchy.

Design: INSTRUCTIONS-nesting.md
"""

from typing import Any


def build_activity_tree(
    activities: list[dict[str, Any]],
    remove_parent_id: bool = True,
) -> list[dict[str, Any]]:
    """Build nested activity tree from flat list.

    Converts flat activity list with ID references (parent_id, children: list[str])
    into nested tree structure (children: list[dict]).

    Args:
        activities: Flat list of activity dicts (from dataclasses.asdict)
        remove_parent_id: If True, remove parent_id field (redundant in nested output)

    Returns:
        List of root-level activity dicts with nested children

    Example:
        >>> activities = [
        ...     {"id": "a1", "parent_id": None, "children": ["a2"]},
        ...     {"id": "a2", "parent_id": "a1", "children": []},
        ... ]
        >>> tree = build_activity_tree(activities)
        >>> tree[0]["children"][0]["id"]
        'a2'

    Design notes:
        - Works at dict level to avoid recursive dataclass type issues
        - Handles missing/orphaned activities gracefully
        - Preserves all activity fields except parent_id (optional)
        - Returns only root activities (no parent_id or parent not found)
    """
    if not activities:
        return []

    # Step 1: Build lookup map for fast access by ID
    activity_map: dict[str, dict[str, Any]] = {}
    for activity in activities:
        activity_id = activity.get("id")
        if not activity_id:
            # Skip activities without IDs (shouldn't happen, but be defensive)
            continue
        # Deep copy to avoid modifying input
        activity_map[activity_id] = dict(activity)

    # Step 2: Build nested structure
    # Replace children: list[str] with children: list[dict]
    for activity in activity_map.values():
        child_ids = activity.get("children", [])
        nested_children = []

        for child_id in child_ids:
            if child_id in activity_map:
                # Recursively nest this child
                nested_child = _nest_activity(child_id, activity_map, remove_parent_id)
                nested_children.append(nested_child)
            else:
                # Child ID not found - log warning but continue
                # In production, you might want to collect these as issues
                pass

        # Replace children list with nested dicts
        activity["children"] = nested_children

        # Optionally remove parent_id (redundant in nested structure)
        if remove_parent_id and "parent_id" in activity:
            del activity["parent_id"]

    # Step 3: Identify and return only root activities
    roots = []
    for activity in activities:
        activity_id = activity.get("id")
        if not activity_id or activity_id not in activity_map:
            continue

        parent_id = activity.get("parent_id")

        # Root if: no parent_id, parent_id is None, or parent not found
        if parent_id is None or parent_id not in activity_map:
            roots.append(activity_map[activity_id])

    return roots


def _nest_activity(
    activity_id: str,
    activity_map: dict[str, dict[str, Any]],
    remove_parent_id: bool,
) -> dict[str, Any]:
    """Recursively nest an activity and its children.

    Args:
        activity_id: ID of activity to nest
        activity_map: Lookup map of all activities
        remove_parent_id: Whether to remove parent_id field

    Returns:
        Activity dict with nested children
    """
    activity = activity_map[activity_id]

    # Get child IDs
    child_ids = activity.get("children", [])

    # Recursively nest children
    nested_children = []
    for child_id in child_ids:
        if child_id in activity_map:
            nested_child = _nest_activity(child_id, activity_map, remove_parent_id)
            nested_children.append(nested_child)

    # Create result with nested children
    result = dict(activity)
    result["children"] = nested_children

    # Remove parent_id if requested
    if remove_parent_id and "parent_id" in result:
        del result["parent_id"]

    return result


def validate_tree(activities: list[dict[str, Any]]) -> list[str]:
    """Validate activity tree structure.

    Checks for common issues:
    - Circular references
    - Orphaned activities (parent not found)
    - Duplicate IDs

    Args:
        activities: Flat list of activities to validate

    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []

    # Check for duplicate IDs
    ids_seen: set[str] = set()
    for activity in activities:
        activity_id = activity.get("id")
        if not activity_id:
            warnings.append("Activity missing ID field")
            continue
        if activity_id in ids_seen:
            warnings.append(f"Duplicate activity ID: {activity_id}")
        ids_seen.add(activity_id)

    # Build parent-child map
    activity_map = {a.get("id"): a for a in activities if a.get("id")}

    # Check for orphaned activities
    for activity in activities:
        parent_id = activity.get("parent_id")
        if parent_id and parent_id not in activity_map:
            warnings.append(
                f"Orphaned activity {activity.get('id')}: "
                f"parent {parent_id} not found"
            )

    # Check for circular references using DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(activity_id: str) -> bool:
        visited.add(activity_id)
        rec_stack.add(activity_id)

        activity = activity_map.get(activity_id)
        if not activity:
            return False

        for child_id in activity.get("children", []):
            if child_id not in visited:
                if has_cycle(child_id):
                    return True
            elif child_id in rec_stack:
                return True

        rec_stack.remove(activity_id)
        return False

    for activity_id in activity_map:
        if activity_id not in visited:
            if has_cycle(activity_id):
                warnings.append(f"Circular reference detected involving {activity_id}")

    return warnings


__all__ = ["build_activity_tree", "validate_tree"]
```

#### Step 1.3: Test the Tree Builder

Create `python/tests/test_tree_builder.py` with comprehensive tests for:
- Simple parent-child relationships
- Deep nesting (5+ levels)
- Multiple siblings
- Multiple root activities
- Orphaned activities
- Missing children
- Preserving other fields
- Validation (duplicates, orphans, cycles)

Run tests:
```bash
cd python/
uv run pytest tests/test_tree_builder.py -v
```

---

### Phase 2: Call Graph Expansion Module

**File to modify:** `python/xaml_parser/tree_builder.py` (add new function)

This phase implements the SECOND level of nesting: expanding `InvokeWorkflowFile` activities with the content of the invoked workflows.

#### Step 2.1: Understand the Data

The parser already tracks invocations:

```python
@dataclass
class InvocationDto:
    """Workflow invocation (call graph edge)."""
    caller_activity_id: str      # ID of InvokeWorkflowFile activity
    caller_workflow_id: str      # ID of workflow containing the call
    callee_workflow_id: str      # ID of invoked workflow
    callee_path: str             # Relative path to invoked file
    arguments: dict[str, str]    # Arguments passed
```

**Strategy:**
1. Build workflow ID -> workflow dict lookup
2. Build caller activity ID -> callee workflow lookup (from invocations)
3. For each InvokeWorkflowFile activity, find its callee workflow
4. Replace empty children[] with callee's root activities
5. Detect circular invocations to avoid infinite recursion

#### Step 2.2: Add Call Graph Expansion Function

Add to `python/xaml_parser/tree_builder.py`:

```python
def expand_call_graph(
    workflows_dict: dict[str, Any],
    invocations: list[dict[str, Any]],
    max_depth: int = 10,
) -> dict[str, Any]:
    """Expand InvokeWorkflowFile activities with invoked workflow content.

    Args:
        workflows_dict: Dict with "workflows" list (from WorkflowCollectionDto)
        invocations: List of invocation dicts
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Modified workflows_dict with expanded call graph

    Example:
        After local nesting, you have:
        - myEntrypointOne with InvokeWorkflowFile (children=[])
        - InitAllSettings with Sequence -> activities

        After call graph expansion:
        - myEntrypointOne with InvokeWorkflowFile (children=[Sequence from InitAllSettings])
    """
    if not workflows_dict.get("workflows"):
        return workflows_dict

    # Build lookups
    workflow_by_id: dict[str, dict[str, Any]] = {}
    for wf in workflows_dict["workflows"]:
        if wf.get("id"):
            workflow_by_id[wf["id"]] = wf

    # Build invocation map: caller_activity_id -> callee_workflow_id
    invocation_map: dict[str, str] = {}
    for inv in invocations:
        caller_act_id = inv.get("caller_activity_id")
        callee_wf_id = inv.get("callee_workflow_id")
        if caller_act_id and callee_wf_id:
            invocation_map[caller_act_id] = callee_wf_id

    # Expand each workflow
    for workflow in workflows_dict["workflows"]:
        if workflow.get("activities"):
            _expand_invocations_recursive(
                workflow["activities"],
                workflow_by_id,
                invocation_map,
                visited_workflows=set(),
                depth=0,
                max_depth=max_depth,
            )

    return workflows_dict


def _expand_invocations_recursive(
    activities: list[dict[str, Any]],
    workflow_by_id: dict[str, dict[str, Any]],
    invocation_map: dict[str, str],
    visited_workflows: set[str],
    depth: int,
    max_depth: int,
) -> None:
    """Recursively expand InvokeWorkflowFile activities.

    Modifies activities in-place.
    """
    if depth > max_depth:
        # Prevent infinite recursion
        return

    for activity in activities:
        # Check if this is an InvokeWorkflowFile activity
        is_invoke = activity.get("type") == "InvokeWorkflowFile" or \
                   activity.get("type_short") == "InvokeWorkflowFile"

        if is_invoke:
            # Find the callee workflow
            activity_id = activity.get("id")
            callee_wf_id = invocation_map.get(activity_id)

            if callee_wf_id and callee_wf_id not in visited_workflows:
                callee_workflow = workflow_by_id.get(callee_wf_id)

                if callee_workflow and callee_workflow.get("activities"):
                    # Prevent circular calls
                    new_visited = visited_workflows | {callee_wf_id}

                    # Get root activities from callee
                    callee_roots = callee_workflow["activities"]

                    # Deep copy to avoid modifying original
                    callee_copy = [dict(act) for act in callee_roots]

                    # Recursively expand the callee's activities
                    _expand_invocations_recursive(
                        callee_copy,
                        workflow_by_id,
                        invocation_map,
                        new_visited,
                        depth + 1,
                        max_depth,
                    )

                    # Set callee activities as children of InvokeWorkflowFile
                    activity["children"] = callee_copy

        # Recursively process children
        if activity.get("children"):
            _expand_invocations_recursive(
                activity["children"],
                workflow_by_id,
                invocation_map,
                visited_workflows,
                depth,
                max_depth,
            )
```

#### Step 2.3: Test Call Graph Expansion

Create tests in `python/tests/test_tree_builder.py`:

```python
def test_expand_call_graph_simple():
    """Test expanding a simple InvokeWorkflowFile."""
    workflows = {
        "workflows": [
            {
                "id": "wf:main",
                "activities": [
                    {
                        "id": "act:1",
                        "type": "InvokeWorkflowFile",
                        "children": [],
                    }
                ],
            },
            {
                "id": "wf:callee",
                "activities": [
                    {
                        "id": "act:2",
                        "type": "LogMessage",
                        "children": [],
                    }
                ],
            },
        ]
    }
    invocations = [
        {
            "caller_activity_id": "act:1",
            "callee_workflow_id": "wf:callee",
        }
    ]

    result = expand_call_graph(workflows, invocations)

    # InvokeWorkflowFile should now have LogMessage as child
    invoke_act = result["workflows"][0]["activities"][0]
    assert len(invoke_act["children"]) == 1
    assert invoke_act["children"][0]["type"] == "LogMessage"


def test_expand_call_graph_circular():
    """Test that circular invocations are detected."""
    # wf:a calls wf:b, wf:b calls wf:a
    workflows = {
        "workflows": [
            {
                "id": "wf:a",
                "activities": [
                    {"id": "act:1", "type": "InvokeWorkflowFile", "children": []}
                ],
            },
            {
                "id": "wf:b",
                "activities": [
                    {"id": "act:2", "type": "InvokeWorkflowFile", "children": []}
                ],
            },
        ]
    }
    invocations = [
        {"caller_activity_id": "act:1", "callee_workflow_id": "wf:b"},
        {"caller_activity_id": "act:2", "callee_workflow_id": "wf:a"},
    ]

    # Should not raise, should handle gracefully
    result = expand_call_graph(workflows, invocations, max_depth=3)
    assert result is not None
```

---

### Phase 3: Configuration Extension

**Files to modify:** `python/xaml_parser/emitters/__init__.py`

Add `nested` field to `EmitterConfig`:

```python
@dataclass
class EmitterConfig:
    """Configuration for emitters."""

    field_profile: str = "full"  # full, minimal, mcp, datalake
    combine: bool = True          # Single file vs per-workflow
    pretty: bool = True           # Pretty-print JSON
    exclude_none: bool = True     # Exclude None values
    nested: bool = False          # NEW: Output nested structure (default: flat)
```

**Important:** Default is `False` to maintain backward compatibility.

---

### Phase 4: Emitter Integration

**Files to modify:** `python/xaml_parser/emitters/json_emitter.py`

1. Import tree builder functions:
```python
from ..tree_builder import build_activity_tree, expand_call_graph
```

2. Modify `_to_dict()` method to apply nesting:
```python
def _to_dict(self, dto: Any, config: EmitterConfig) -> dict[str, Any]:
    """Convert DTO to dict with field selection and optional nesting."""
    # Convert to dict
    data = dataclasses.asdict(dto)

    # Apply nesting BEFORE field profile
    if config.nested:
        data = self._apply_nesting(data)

    # Apply field profile
    if config.field_profile != "full":
        # ... existing code ...

    # Exclude None values
    if config.exclude_none:
        data = self._exclude_none(data)

    return data
```

3. Add `_apply_nesting()` method with TWO-PHASE nesting:
```python
def _apply_nesting(self, data: dict[str, Any]) -> dict[str, Any]:
    """Apply nested structure to activities (two-phase).

    Phase 1: Local nesting (parent/child within each file)
    Phase 2: Call graph expansion (InvokeWorkflowFile -> callee content)
    """
    # Handle WorkflowCollectionDto
    if "workflows" in data and isinstance(data["workflows"], list):
        # Phase 1: Nest activities within each workflow
        for workflow in data["workflows"]:
            if "activities" in workflow and isinstance(workflow["activities"], list):
                workflow["activities"] = build_activity_tree(workflow["activities"])

        # Phase 2: Expand call graph
        if "invocations" in data and isinstance(data["invocations"], list):
            data = expand_call_graph(data, data["invocations"])

    # Handle single WorkflowDto (no call graph expansion possible)
    elif "activities" in data and isinstance(data["activities"], list):
        data["activities"] = build_activity_tree(data["activities"])

    return data
```

---

### Phase 5: CLI Support

**Files to modify:** `python/xaml_parser/cli.py`

1. Add `--nested` flag:
```python
parser.add_argument(
    "--nested",
    action="store_true",
    default=False,
    help=(
        "Output nested activity structure (mirrors XAML hierarchy). "
        "Default is flat structure with ID references."
    ),
)
```

2. Pass to EmitterConfig:
```python
emitter_config = EmitterConfig(
    field_profile=args.profile,
    combine=args.combine,
    pretty=args.pretty,
    exclude_none=not args.include_none,
    nested=args.nested,  # NEW
)
```

---

### Phase 6: End-to-End Testing

#### Manual Testing

```bash
cd python/

# Test flat output (default)
uv run xaml-parser ../test-corpus/c25v001_CORE_00000001/myEntrypointOne.xaml --json -o /tmp/flat.json

# Test nested output
uv run xaml-parser ../test-corpus/c25v001_CORE_00000001/myEntrypointOne.xaml --json --nested -o /tmp/nested.json

# Compare outputs
code --diff /tmp/flat.json /tmp/nested.json
```

#### Integration Tests

Create `python/tests/test_nested_output.py` with tests for:
- Nested structure verification
- Flat vs nested ID consistency
- parent_id removal in nested mode
- Corpus tests with --nested flag

---

### Phase 7: Documentation Updates

1. **ADR-DTO-DESIGN.md**: Add section on flat vs nested output trade-offs
2. **CLAUDE.md**: Add examples of nested vs flat output
3. **architecture.md**: Document nesting as presentation concern
4. **README.md**: Add nested output example

---

## Verification Checklist

Before considering complete:

### Unit Tests
- [ ] test_simple_parent_child passes
- [ ] test_deep_nesting passes (5+ levels)
- [ ] test_multiple_siblings passes
- [ ] test_multiple_roots passes
- [ ] test_orphaned_activity passes
- [ ] test_missing_child passes
- [ ] test_empty_list passes
- [ ] test_preserve_other_fields passes
- [ ] All validation tests pass

### Integration Tests
- [ ] test_nested_output_structure passes
- [ ] test_nested_vs_flat_ids passes
- [ ] test_nested_no_parent_id passes
- [ ] Corpus tests pass with --nested flag

### Manual Testing
- [ ] CLI --nested flag works
- [ ] Flat output unchanged (backward compatibility)
- [ ] Nested output mirrors XAML structure
- [ ] Performance acceptable (<50ms overhead)

### Documentation
- [ ] ADR-DTO-DESIGN.md updated
- [ ] CLAUDE.md updated
- [ ] architecture.md updated
- [ ] README.md updated

### Code Quality
- [ ] ruff check passes
- [ ] ruff format passes
- [ ] mypy passes
- [ ] Test coverage >80%

---

## Common Pitfalls

### 1. Modifying Input Activities

**Problem:** Modifying activities in-place corrupts original DTOs.

**Solution:** Always work on copies.
```python
# GOOD
activity_map = {a["id"]: dict(a) for a in activities}  # Copy
```

### 2. Circular References

**Problem:** Malformed data might have circular parent-child relationships.

**Solution:** Add cycle detection (see `validate_tree()` function).

### 3. Incorrect Nesting Order

**Problem:** Applying field profiles before nesting excludes needed fields.

**Solution:** Always nest BEFORE applying field profiles.
```python
# CORRECT ORDER
data = dataclasses.asdict(dto)
if config.nested:
    data = apply_nesting(data)      # 1. Nest first
data = apply_profile(data)          # 2. Then filter fields
```

### 4. Type Issues with Recursive Dataclasses

**Problem:** Python type system struggles with recursive types.

**Solution:** Work at dict level, not ActivityDto level.

---

## Performance Considerations

**Expected overhead:**
- Tree reconstruction: O(n) where n = number of activities
- Memory: 2x (original flat + nested copy)
- Typical workflow (100 activities): ~10-20ms overhead
- Large workflow (1000 activities): ~50-100ms overhead

**Optimization opportunities:**
1. Lazy reconstruction (only nest on-demand)
2. In-place modification (if safe)
3. Caching (for repeated exports)

---

## Summary

This implementation adds nested output support while maintaining backward compatibility:

1. **New module**: `tree_builder.py` with reconstruction logic
2. **Config option**: `EmitterConfig.nested` flag
3. **CLI support**: `--nested` command-line flag
4. **Tests**: Comprehensive unit and integration tests
5. **Documentation**: Updated ADR, CLAUDE.md, architecture.md

The result: Users can choose between flat (analytics-friendly) and nested (human-friendly) output modes, achieving the "reduced but exact representation" goal.

**Estimated implementation time:** 8-12 hours for a junior developer following this guide.

Good luck!
