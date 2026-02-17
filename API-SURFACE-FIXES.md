# API Surface Fixes - Record Format Now First-Class ✅

## Summary

Made "record" format a first-class API surface by:
1. ✅ Adding "record" to `ProjectSession.emit()` signature
2. ✅ Supporting RecordRenderer in string-output path
3. ✅ Bypassing filters for record format in all code paths

---

## Issue #1: ProjectSession.emit() didn't allow format="record" ✅

### Problem
The method signature restricted format to `Literal["json", "yaml", "mermaid", "doc"]`, excluding "record".

### Root Cause
Type annotation wasn't updated when EmitterConfig added "record" support.

### Fix Applied

**Updated signature** to include "record":

```python
# Before
def emit(
    self,
    format: Literal["json", "yaml", "mermaid", "doc"] = "json",  # Missing "record"
    ...
) -> PipelineResult | str:

# After
def emit(
    self,
    format: Literal["json", "yaml", "mermaid", "doc", "record"] = "json",  # Now included
    ...
) -> PipelineResult | str:
```

**Updated docstring** to document record format and kinds parameter:

```python
Args:
    format: Output format (json, yaml, mermaid, doc, record)
    ...
    **options: Additional emitter options:
        ...
        - kinds: Record kinds to include for record format (default: ["workflow"])

Example:
    >>> # Emit records with multiple kinds
    >>> records_jsonl = session.emit("record", kinds=["workflow", "activity"])
```

**Files Modified**: `python/cpmf_uips_xaml/api/session.py`

---

## Issue #2: String-output path lacked RecordRenderer ✅

### Problem
When `output_path is None` (string output), renderer creation only handled json/mermaid/doc, raising ValueError for "record".

### Root Cause
RecordRenderer was only wired into the file-output path (via emit_workflows), not the string-output path.

### Fix Applied

**Added RecordRenderer import**:

```python
from ..stages.emit.renderers.record_renderer import RecordRenderer
```

**Added record format case**:

```python
# Build renderer based on format
if format == "json":
    renderer = JsonRenderer()
elif format == "mermaid":
    renderer = MermaidRenderer()
elif format == "doc":
    renderer = DocRenderer()
elif format == "record":
    renderer = RecordRenderer()  # NEW
else:
    raise ValueError(f"Unsupported format for string output: {format}")
```

**Bypassed filters for record format** (string-output path):

```python
# Apply filters (same as pipeline does)
# CRITICAL: Bypass filters for record format to prevent schema validation failures
filters = []
if format != "record":  # Skip filters for record format
    if emitter_config.exclude_none:
        filters.append(NoneFilter())
    if emitter_config.field_profile != "full":
        filters.append(FieldFilter(profile=emitter_config.field_profile))
```

**Files Modified**: `python/cpmf_uips_xaml/api/session.py`

---

## Verification

### Test Coverage

**Created 4 new tests** in `test_session_record_emit.py`:

```
✅ test_session_emit_record_string_output - String output works
✅ test_session_emit_record_with_project - Project records included
✅ test_session_emit_record_multi_kind - Multiple kinds support
✅ test_session_emit_record_no_filters - Filters bypassed for record format
```

**All 15 record/schema tests passing**:

```
✅ test_record_renderer_through_pipeline
✅ test_record_kinds_parameter
✅ test_record_export_smoke
✅ test_record_serialization
✅ test_all_schemas_exist
✅ test_dependency_record_contract
✅ test_invocation_record_contract
✅ test_issue_record_contract
✅ test_project_record_contract
✅ test_filter_bypass_for_record_format
✅ test_workflow_record_validates
✅ test_session_emit_record_string_output (NEW)
✅ test_session_emit_record_with_project (NEW)
✅ test_session_emit_record_multi_kind (NEW)
✅ test_session_emit_record_no_filters (NEW)
```

### API Usage Examples

**String output (no file)**:

```python
from cpmf_uips_xaml import load

session = load(project_path)

# Return JSONL string directly
records_jsonl = session.emit("record", kinds=["workflow", "activity"])

# Parse and use
for line in records_jsonl.strip().split("\n"):
    record = json.loads(line)
    print(record["kind"], record["payload"]["name"])
```

**File output**:

```python
# Write to file
result = session.emit(
    "record",
    output_path=Path("output.jsonl"),
    kinds=["project", "workflow", "activity", "invocation"],
)
print(f"Written {result.metadata['record_count']} records")
```

**With project records**:

```python
# Project info automatically extracted and included
records = session.emit(
    "record",
    kinds=["project", "workflow"],  # Project type derived from project.json
)
```

**Filter bypass (automatic)**:

```python
# Filters ignored for record format (schema compliance preserved)
records = session.emit(
    "record",
    field_profile="minimal",  # Ignored
    exclude_none=True,  # Ignored
    kinds=["workflow"],
)
```

---

## Code Paths Now Consistent

### Before (Inconsistent)

```
session.emit("record") → ValueError ❌
session.emit("record", output_path=Path("x")) → Works via emit_workflows ✅
```

### After (Consistent)

```
session.emit("record") → Returns JSONL string ✅
session.emit("record", output_path=Path("x")) → Writes JSONL file ✅
```

Both paths:
- ✅ Support RecordRenderer
- ✅ Bypass field filters
- ✅ Populate project_info automatically
- ✅ Honor kinds parameter

---

## Architecture

### Dual Output Paths (Now Consistent)

```
ProjectSession.emit(format="record")
│
├─ output_path is None (STRING OUTPUT) ✅
│  ├─ Build RecordRenderer (NEW)
│  ├─ Convert workflows to dicts
│  ├─ Bypass filters (format != "record") (NEW)
│  ├─ Render to JSONL string
│  └─ Return string
│
└─ output_path provided (FILE OUTPUT) ✅
   ├─ Build EmitterConfig with project_info
   ├─ Call emit_workflows()
   ├─ Create RecordRenderer
   ├─ Bypass filters (format == "record")
   ├─ Write to file via pipeline
   └─ Return PipelineResult
```

---

## Files Modified Summary

### Implementation (1 file)

**python/cpmf_uips_xaml/api/session.py**
1. Updated emit() signature: Added "record" to Literal
2. Updated docstring: Documented record format and kinds parameter
3. Added RecordRenderer import
4. Added format == "record" case in string-output branch
5. Bypassed filters when format == "record" in string-output branch

### Tests (1 file)

**tests/integration/test_session_record_emit.py** (NEW)
- 4 comprehensive tests validating string-output path
- Verified project records, multi-kind, filter bypass

---

## Status

**RECORD FORMAT IS NOW FIRST-CLASS** ✅

- ✅ Included in ProjectSession.emit() signature
- ✅ Works for both string output and file output
- ✅ Consistent filter bypass in all code paths
- ✅ Documented in API docstring
- ✅ Full test coverage (15/15 tests passing)

The record export system is now fully integrated into the public API with excellent usability.
