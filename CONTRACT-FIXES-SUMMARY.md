# Schema Contract Alignment - All Issues Fixed

## Summary

All 6 critical contract breaks between v2 schemas and code implementation have been resolved. The record export system now strictly adheres to the "schema is authoritative" principle.

---

## Critical Issues Fixed

### ✅ Issue #1: Missing schema file for project records

**Problem**: `records.py` emitted project records but `schemas/v2/project-record.schema.json` didn't exist.

**Fix**: Created authoritative schema at `schemas/v2/project-record.schema.json` with required contract:
```json
{
  "name": "string (required)",
  "type": "Process" | "Library" (required),
  "path": "string (required)",
  "version": "string | null",
  "description": "string | null"
}
```

**Files Created**:
- `schemas/v2/project-record.schema.json`

---

### ✅ Issue #2: Dependency record payload doesn't match schema

**Problem**: Schema required `package_id, version, source, dependency_type`. Implementation emitted `name, version, source, workflow_id`.

**Fix**: Aligned `dependency_to_record()` to schema contract:
- Changed `name` → `package_id` (with fallback for backward compatibility)
- Removed `workflow_id` (not in schema)
- Added `dependency_type` field with valid enum values: `"direct" | "transitive"`
- Default to `"direct"` if not specified

**Schema Contract**:
```json
{
  "package_id": "string (required)",
  "version": "string (required)",
  "source": "string | null",
  "dependency_type": "direct" | "transitive" (required)
}
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/records.py`

---

### ✅ Issue #3: Invocation record payload doesn't match schema

**Problem**:
- Schema expected `caller_activity_id`, implementation used wrong key `activity_id`
- Schema required enum `InvokeWorkflow | InvokeWorkflowFile | DynamicInvoke`, implementation used invalid `"static"`
- Missing `callee_workflow_path` field

**Fix**: Aligned `invocation_to_record()` to schema contract:
- Changed `activity_id` → `caller_activity_id` (with fallback)
- Changed default invocation_type from `"static"` → `"InvokeWorkflow"` (valid enum)
- Added `callee_workflow_path` field
- Added `callee_workflow_id` (nullable)

**Schema Contract**:
```json
{
  "caller_workflow_id": "string (required)",
  "caller_activity_id": "string (required)",
  "callee_workflow_id": "string | null",
  "callee_workflow_path": "string | null",
  "invocation_type": "InvokeWorkflow" | "InvokeWorkflowFile" | "DynamicInvoke" (required)
}
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/records.py`

---

### ✅ Issue #4: Issue record payload mismatches schema field names

**Problem**:
- Schema required `activity_id` field, implementation didn't emit it
- Schema required non-empty `code` field, implementation could emit null/empty

**Fix**: Aligned `issue_to_record()` to schema contract:
- Added `activity_id` field (nullable, for activity-level issues)
- Added default `code = "UNKNOWN"` to ensure required field is never empty
- Reordered fields to match schema: `severity, code, message, workflow_id, activity_id, location`

**Schema Contract**:
```json
{
  "severity": "error" | "warning" | "info" (required),
  "code": "string (required)",
  "message": "string (required)",
  "workflow_id": "string | null",
  "activity_id": "string | null",
  "location": "string | null"
}
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/records.py`

---

## High Priority Issues Fixed

### ✅ Issue #5: RecordRenderer ignores the new converters

**Problem**: `RecordRenderer` only emitted workflow/activity/argument records. Project, invocation, issue, dependency converters were never used.

**Fix**: Updated `RecordRenderer.render_many()` and `render_jsonl()` to support all 7 record kinds:
- **workflow** - Workflow records (existing)
- **activity** - Activity records (existing)
- **argument** - Argument records (existing)
- **invocation** - Workflow invocation records (NEW)
- **issue** - Parse/validation issue records (NEW)
- **dependency** - Package dependency records (NEW)
- **project** - Project metadata records (NEW, via config.project_info)

**Implementation Details**:
- Extracts `invocations` from workflow dict
- Extracts `issues` from workflow dict
- Extracts `dependencies` from workflow dict
- Reads `project_info` from config for project records
- All payloads match schema contracts exactly

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`

---

### ✅ Issue #6: Filter stage can invalidate record schema

**Problem**: Pipeline field filters could remove required keys (arguments, edges, activity_ids) from record payloads, causing schema validation failures.

**Fix**: Bypass all filters when `format="record"`:
- Updated `emit_workflows()` to skip filter chain for record format
- Updated `create_pipeline()` to skip filter chain for record format
- Added critical comments explaining why filters break schema contracts

**Rationale**: Record payloads are curated to match schemas exactly. Field filtering would break the schema contract and cause validation failures.

**Files Modified**:
- `python/cpmf_uips_xaml/api/emit.py`

---

## Verification

### Schema Files (Complete)

All 8 v2 schemas present and valid:
```
✅ schemas/v2/record-envelope.schema.json
✅ schemas/v2/workflow-record.schema.json
✅ schemas/v2/activity-record.schema.json
✅ schemas/v2/argument-record.schema.json
✅ schemas/v2/invocation-record.schema.json
✅ schemas/v2/issue-record.schema.json
✅ schemas/v2/dependency-record.schema.json
✅ schemas/v2/project-record.schema.json
```

### Test Results

All record tests passing:
```
✅ test_record_renderer_through_pipeline - PASSED
✅ test_record_kinds_parameter - PASSED
✅ test_record_export_smoke - PASSED
✅ test_record_serialization - PASSED
```

### Contract Compliance

**Workflow Record**: ✅ Matches schema exactly
- All required fields present: id, name, path, annotation_tags, arguments, activity_ids, activity_count, edges
- Field types match schema definitions
- Nullable fields handled correctly

**Activity Record**: ✅ Matches schema exactly
- All required fields present: id, workflow_id, type, depth, children, annotation_tags
- Properties coerced to strings (Issue #5 from previous round)
- Line numbers default to 1 (Issue #4 from previous round)

**Argument Record**: ✅ Matches schema exactly
- All required fields present
- Direction enum validated

**Invocation Record**: ✅ Now matches schema
- Correct field names: caller_activity_id (not activity_id)
- Valid enum values: InvokeWorkflow/InvokeWorkflowFile/DynamicInvoke (not "static")
- All required fields present

**Issue Record**: ✅ Now matches schema
- activity_id field added
- code field guaranteed non-empty (defaults to "UNKNOWN")
- All required fields present

**Dependency Record**: ✅ Now matches schema
- package_id (not name)
- dependency_type enum validated (direct/transitive)
- All required fields present

**Project Record**: ✅ Schema created and implementation aligned
- All required fields present: name, type, path
- Type enum validated (Process/Library)

---

## Files Modified Summary

### Created (1 file)
1. `schemas/v2/project-record.schema.json` - Authoritative project record schema

### Modified (3 files)
1. `python/cpmf_uips_xaml/stages/emit/records.py`
   - Fixed dependency_to_record() payload (package_id, dependency_type)
   - Fixed invocation_to_record() payload (caller_activity_id, valid enum, callee_workflow_path)
   - Fixed issue_to_record() payload (activity_id, code default)
   - Added schema contract documentation to all converters

2. `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`
   - Added support for all 7 record kinds in render_many()
   - Added support for all 7 record kinds in render_jsonl()
   - Extracts invocations/issues/dependencies from workflow dicts
   - Handles project records via config.project_info

3. `python/cpmf_uips_xaml/api/emit.py`
   - Bypass field filters when format="record" in emit_workflows()
   - Bypass field filters when format="record" in create_pipeline()
   - Added critical comments explaining schema contract protection

---

## Design Principles Enforced

1. **Schema is Authoritative**: Code implementation matches schemas exactly, not vice versa
2. **No Filter Pollution**: Record output bypasses field filters to preserve schema compliance
3. **Explicit Defaults**: Required enum fields have valid defaults (not invalid placeholders)
4. **Nullable Fields**: Properly distinguished between required and optional fields
5. **Complete Coverage**: All 7 record kinds supported in renderer
6. **Backward Compatibility**: Fallbacks for renamed fields (name→package_id, activity_id→caller_activity_id)
7. **Fail-Safe Defaults**: Required fields with non-null constraints get safe defaults (code="UNKNOWN", dependency_type="direct")

---

## Status

**All 6 contract breaks RESOLVED** ✅

- ✅ Project schema created
- ✅ Dependency payload aligned to schema
- ✅ Invocation payload aligned to schema
- ✅ Issue payload aligned to schema
- ✅ RecordRenderer supports all 7 kinds
- ✅ Field filters bypassed for record format

The v2 record export system now has **tight schema compliance** with authoritative external contracts.
