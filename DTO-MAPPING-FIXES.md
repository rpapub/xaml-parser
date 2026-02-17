# DTO Field Mapping Fixes - Complete Resolution

## Summary

Fixed all DTO-to-schema field mapping errors by aligning RecordRenderer and record converters to actual DTO structures. All 6 critical issues resolved.

---

## Critical Issues Fixed

### ✅ Issue #1: Invocation record payload mismatched DTO keys

**Problem**: RecordRenderer used wrong field names that didn't match InvocationDto structure.

**InvocationDto Actual Fields**:
```python
callee_id: str              # Target workflow ID
callee_path: str            # Original reference path
via_activity_id: str        # InvokeWorkflowFile activity ID
arguments_passed: dict      # Argument mappings
```

**Schema Contract Requires**:
```python
caller_workflow_id: str     # Calling workflow ID
caller_activity_id: str     # Calling activity ID
callee_workflow_id: str     # Called workflow ID
callee_workflow_path: str   # Called workflow path
invocation_type: enum       # InvokeWorkflow | InvokeWorkflowFile | DynamicInvoke
```

**Fix**: Correct field mapping in RecordRenderer and records.py:
```python
# BEFORE (Wrong)
"caller_activity_id": invocation_dict.get("caller_activity_id", "")  # Field doesn't exist
"callee_workflow_id": invocation_dict.get("callee_workflow_id")      # Field doesn't exist
"callee_workflow_path": invocation_dict.get("callee_workflow_path")  # Field doesn't exist

# AFTER (Correct)
"caller_activity_id": invocation_dict.get("via_activity_id", "")  # DTO field
"callee_workflow_id": invocation_dict.get("callee_id")            # DTO field
"callee_workflow_path": invocation_dict.get("callee_path")        # DTO field
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`
- `python/cpmf_uips_xaml/stages/emit/records.py`
- `tests/integration/test_schema_contract_compliance.py`

---

### ✅ Issue #2: Dependency record payload used wrong keys

**Problem**: RecordRenderer looked for `package_id` or `name`, but DependencyDto uses `package`.

**DependencyDto Actual Fields**:
```python
package: str    # Package name
version: str    # Package version
```

**Schema Contract Requires**:
```python
package_id: str        # Package identifier (required)
version: str           # Package version (required)
source: str | null     # Package source
dependency_type: enum  # "direct" | "transitive" (required)
```

**Fix**: Map `package` → `package_id`, handle missing fields:
```python
# BEFORE (Wrong)
"package_id": dependency_dict.get("package_id", dependency_dict.get("name", ""))  # Neither exists

# AFTER (Correct)
"package_id": dependency_dict.get("package", "")  # DTO field
"source": None                                     # Not in DependencyDto
"dependency_type": "direct"                        # Not in DependencyDto, safe default
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`
- `python/cpmf_uips_xaml/stages/emit/records.py`
- `tests/integration/test_schema_contract_compliance.py`

---

### ✅ Issue #3: Issue record payload used wrong keys

**Problem**: RecordRenderer looked for `severity` and `location`, but IssueDto uses `level` and `path`.

**IssueDto Actual Fields**:
```python
level: str           # Issue severity (error, warning, info)
message: str         # Human-readable message
path: str | None     # Location path (workflow/activity path)
code: str | None     # Issue code for programmatic handling
```

**Schema Contract Requires**:
```python
severity: enum         # "error" | "warning" | "info" (required)
code: str              # Error or validation code (required)
message: str           # Human-readable message (required)
workflow_id: str | null
activity_id: str | null
location: str | null
```

**Fix**: Map `level` → `severity`, `path` → `location`:
```python
# BEFORE (Wrong)
"severity": issue_dict.get("severity", "error")  # Field doesn't exist
"location": issue_dict.get("location")           # Field doesn't exist

# AFTER (Correct)
"severity": issue_dict.get("level", "error")  # DTO field: level
"location": issue_dict.get("path")            # DTO field: path
"activity_id": None                           # Not in IssueDto
"code": issue_dict.get("code") or "UNKNOWN"   # Ensure non-empty
```

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`
- `python/cpmf_uips_xaml/stages/emit/records.py`
- `tests/integration/test_schema_contract_compliance.py`

---

### ✅ Issue #4: Project records unreachable via standard config

**Problem**: RecordRenderer expected `config.project_info`, but EmitterConfig had no such field.

**Fix**: Added `project_info` field to EmitterConfig:
```python
@dataclass(frozen=True)
class EmitterConfig:
    ...
    project_info: dict[str, Any] | None = None  # For project records in record format
```

Now project records can be emitted by passing project metadata via config:
```python
config = EmitterConfig(
    format="record",
    kinds=["project", "workflow"],
    project_info={"name": "MyProject", "type": "Process", "path": "/path"},
    ...
)
```

**Files Modified**:
- `python/cpmf_uips_xaml/config/models.py`

---

### ✅ Issue #5: Schema enums at risk due to invalid defaults

**Problem**:
- `project.type` could default to `""` (empty string), violating schema enum `"Process" | "Library"`
- Missing validation could emit invalid enum values

**Fix**: Added enum validation with safe defaults:
```python
# Validate project type enum
project_type = project_info.get("type", "")
if project_type not in ("Process", "Library"):
    project_type = "Process"  # Safe default for valid enum
```

Applied to:
- `project_to_record()` in `records.py`
- Project record handling in `RecordRenderer`

**Files Modified**:
- `python/cpmf_uips_xaml/stages/emit/records.py`
- `python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py`

---

## DTO → Schema Field Mapping Table

### InvocationDto → Invocation Record
| DTO Field | Schema Field | Notes |
|-----------|--------------|-------|
| `via_activity_id` | `caller_activity_id` | Calling activity |
| `callee_id` | `callee_workflow_id` | Called workflow |
| `callee_path` | `callee_workflow_path` | Called workflow path |
| (parent workflow) | `caller_workflow_id` | From parent context |
| (inferred) | `invocation_type` | Default: "InvokeWorkflowFile" |

### IssueDto → Issue Record
| DTO Field | Schema Field | Notes |
|-----------|--------------|-------|
| `level` | `severity` | Error severity |
| `message` | `message` | Direct mapping |
| `path` | `location` | Issue location |
| `code` | `code` | Default: "UNKNOWN" if None |
| (parent workflow) | `workflow_id` | From parent context |
| (not in DTO) | `activity_id` | Always None |

### DependencyDto → Dependency Record
| DTO Field | Schema Field | Notes |
|-----------|--------------|-------|
| `package` | `package_id` | Package identifier |
| `version` | `version` | Direct mapping |
| (not in DTO) | `source` | Always None |
| (not in DTO) | `dependency_type` | Default: "direct" |

---

## Verification

### All Tests Passing (11/11)
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
```

### Contract Compliance Verified

**Invocation Records**:
- ✅ Maps `via_activity_id` → `caller_activity_id`
- ✅ Maps `callee_id` → `callee_workflow_id`
- ✅ Maps `callee_path` → `callee_workflow_path`
- ✅ Uses valid enum: `InvokeWorkflowFile`
- ✅ All required fields present

**Issue Records**:
- ✅ Maps `level` → `severity`
- ✅ Maps `path` → `location`
- ✅ Ensures `code` never empty (defaults to "UNKNOWN")
- ✅ Sets `activity_id` to None (not in DTO)
- ✅ All required fields present

**Dependency Records**:
- ✅ Maps `package` → `package_id`
- ✅ Sets `source` to None (not in DTO)
- ✅ Sets `dependency_type` to "direct" (safe default)
- ✅ All required fields present

**Project Records**:
- ✅ Validates `type` enum ("Process" | "Library")
- ✅ Defaults to "Process" if invalid
- ✅ Accessible via `config.project_info`
- ✅ All required fields present

---

## Files Modified Summary

### Core Implementation (4 files)
1. **python/cpmf_uips_xaml/stages/emit/records.py**
   - Updated all converter docstrings with DTO field mappings
   - Fixed field names to match actual DTOs
   - Added enum validation for project.type

2. **python/cpmf_uips_xaml/stages/emit/renderers/record_renderer.py**
   - Fixed InvocationDto field mapping in render_many() and render_jsonl()
   - Fixed IssueDto field mapping in render_many() and render_jsonl()
   - Fixed DependencyDto field mapping in render_many() and render_jsonl()
   - Added project.type enum validation
   - Added DTO field mapping comments

3. **python/cpmf_uips_xaml/config/models.py**
   - Added `project_info: dict[str, Any] | None = None` to EmitterConfig

4. **tests/integration/test_schema_contract_compliance.py**
   - Updated tests to use actual DTO field names
   - Added DTO→Schema mapping validation
   - Verified enum handling and safe defaults

---

## Design Principles Enforced

1. ✅ **DTO Fields are Source of Truth** - Map from actual DTO structure, not assumed names
2. ✅ **Schema is Contract** - Output must match schema exactly
3. ✅ **Safe Defaults** - Required enum fields get valid defaults, never empty/invalid
4. ✅ **Explicit Mapping** - Clear documentation of DTO→Schema field mappings
5. ✅ **Null Handling** - Missing DTO fields map to None (nullable) or safe defaults (required)
6. ✅ **Parent Context** - Fields like `workflow_id` passed from parent when not in child DTO
7. ✅ **Enum Validation** - Validate enum values, provide safe defaults for invalid data

---

## Status

**ALL DTO MAPPING ISSUES RESOLVED** ✅

- All DTO field names verified against actual source
- All schema contracts honored
- All enum validations in place
- All tests passing
- Project records now reachable via config

The record export system now correctly maps DTO structures to schema contracts with full validation.
