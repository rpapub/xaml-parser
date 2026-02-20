# Analysis: XAML Metadata and Activity Namespace Parsing

**Date**: 2025-10-12
**Status**: Proposal for implementation

## Executive Summary

Current implementation lacks proper XAML metadata extraction and activity namespace information. This document proposes:
1. Revising WorkflowMetadata to capture true XAML metadata (xmlns, imported namespaces, assembly references)
2. Adding namespace information to ActivityDto to disambiguate activity types from different packages

## Current State

### WorkflowMetadata Issues

1. **project_name**: Duplicates project_info.name (unnecessary)
2. **namespace**: Currently null - should be extracted from XAML `x:Class` attribute
3. **expression_language**: Already extracted correctly
4. **annotation**: Root workflow annotation - correctly extracted
5. **display_name**: Workflow display name - correctly extracted
6. **description**: Workflow description - correctly extracted

### Activity Type Issues

Activities only have short type name without namespace information:
- **Current**: `type: "LogMessage"`, `type_short: "LogMessage"`
- **Problem**: Cannot distinguish between:
  - `UiPath.Core.Activities.LogMessage` (ui: prefix)
  - `System.Activities.Statements.Sequence` (no prefix)
  - Custom third-party activities with same names

## XAML Metadata Structure

Based on analysis of test corpus XAML files, true XAML metadata includes:

### 1. xmlns Declarations (Root Activity Element)

```xml
<Activity
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:s="clr-namespace:System;assembly=System.Private.CoreLib"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
  x:Class="Main">
```

### 2. x:Class Attribute

Defines the workflow class name (e.g., "Main", "Performer", "InitAllSettings")

### 3. TextExpression.NamespacesForImplementation

Imported .NET namespaces for VisualBasic/CSharp expressions:

```xml
<TextExpression.NamespacesForImplementation>
  <sco:Collection x:TypeArguments="x:String">
    <x:String>System.Activities</x:String>
    <x:String>System.Activities.Statements</x:String>
    <x:String>UiPath.Core</x:String>
    <x:String>UiPath.Core.Activities</x:String>
    ...
  </sco:Collection>
</TextExpression.NamespacesForImplementation>
```

### 4. TextExpression.ReferencesForImplementation

Assembly references required for VB/C# expressions:

```xml
<TextExpression.ReferencesForImplementation>
  <sco:Collection x:TypeArguments="AssemblyReference">
    <AssemblyReference>UiPath.System.Activities</AssemblyReference>
    <AssemblyReference>UiPath.UiAutomation.Activities</AssemblyReference>
    <AssemblyReference>System.Private.CoreLib</AssemblyReference>
    ...
  </sco:Collection>
</TextExpression.ReferencesForImplementation>
```

### What is NOT Metadata

These are business logic configuration (already captured correctly):
- `DisplayName`, `Level`, `Message`, etc. → Already in `properties`
- Arguments and Variables → Already in `arguments` and `variables`
- Annotations → Already in `annotation` field

## Recommendations

### 1. Revise WorkflowMetadata

**Remove:**
- `project_name` (duplicates project_info.name)

**Keep:**
- `expression_language` (VisualBasic or CSharp)
- `annotation` (root workflow annotation)
- `display_name` (user-visible workflow name)
- `description` (workflow description)

**Add:**
- `xaml_class`: x:Class attribute value
- `xmlns_declarations`: Dict of namespace prefix → URI mappings
- `imported_namespaces`: List of .NET namespaces from TextExpression.NamespacesForImplementation
- `assembly_references`: List of assembly names from TextExpression.ReferencesForImplementation

**Proposed Structure:**

```python
@dataclass
class WorkflowMetadata:
    """Workflow-level metadata.

    Attributes:
        xaml_class: XAML class name from x:Class attribute
        xmlns_declarations: XML namespace prefix → URI mappings
        expression_language: Expression language (VisualBasic or CSharp)
        imported_namespaces: .NET namespaces imported for expressions
        assembly_references: Required assemblies for expressions
        annotation: Root workflow annotation
        display_name: User-visible workflow name
        description: Workflow description
    """

    xaml_class: str | None = None
    xmlns_declarations: dict[str, str] = field(default_factory=dict)
    expression_language: str = "VisualBasic"
    imported_namespaces: list[str] = field(default_factory=list)
    assembly_references: list[str] = field(default_factory=list)
    annotation: str | None = None
    display_name: str | None = None
    description: str | None = None
```

### 2. Add Namespace Information to ActivityDto

**Current Structure:**
```python
type: str  # "LogMessage" (just local name)
type_short: str  # "LogMessage" (same as type)
```

**Proposed Structure:**
```python
type: str  # Fully-qualified: "{http://schemas.uipath.com/workflow/activities}LogMessage"
type_short: str  # Local name only: "LogMessage"
type_namespace: str | None = None  # "http://schemas.uipath.com/workflow/activities"
type_prefix: str | None = None  # "ui"
```

**Alternative formats for `type` field:**
- **Option A**: `"{http://schemas.uipath.com/workflow/activities}LogMessage"` (XML namespace format)
- **Option B**: `"UiPath.Core.Activities.LogMessage"` (if .NET type can be resolved)
- **Option C**: `"ui:LogMessage"` (prefix:local format)

**Recommendation**: Use Option A (XML namespace format) for accuracy, add Option B as separate field if resolvable.

### 3. Implementation Changes

#### a. Extract xmlns Declarations

**File**: `python/xaml_parser/parser.py`

```python
def _extract_root_metadata(self, root: ET.Element) -> dict[str, Any]:
    """Extract root-level XAML metadata."""
    xmlns = {}

    # Extract xmlns declarations
    for key, value in root.attrib.items():
        if key.startswith("xmlns:"):
            prefix = key[6:]  # Remove "xmlns:" prefix
            xmlns[prefix] = value
        elif key == "xmlns":
            xmlns[""] = value  # Default namespace

    # Extract x:Class
    x_ns = xmlns.get("x", "http://schemas.microsoft.com/winfx/2006/xaml")
    xaml_class = root.get(f"{{{x_ns}}}Class")

    return {
        "xaml_class": xaml_class,
        "xmlns_declarations": xmlns,
    }
```

#### b. Extract TextExpression Metadata

**File**: `python/xaml_parser/extractors.py` (MetadataExtractor)

```python
@staticmethod
def extract_imported_namespaces(root: ET.Element) -> list[str]:
    """Extract .NET namespaces from TextExpression.NamespacesForImplementation."""
    namespaces = []

    for elem in root.iter():
        if elem.tag.endswith("NamespacesForImplementation"):
            # Find Collection child
            for collection in elem:
                # Find all x:String children
                for ns_elem in collection:
                    if ns_elem.text:
                        namespaces.append(ns_elem.text.strip())

    return namespaces

@staticmethod
def extract_assembly_references_from_text_expression(root: ET.Element) -> list[str]:
    """Extract assembly names from TextExpression.ReferencesForImplementation.

    Note: These are .NET assemblies for expression evaluation, NOT package dependencies.
    Package dependencies come from project.json.
    """
    references = []

    for elem in root.iter():
        if elem.tag.endswith("ReferencesForImplementation"):
            # Find Collection child
            for collection in elem:
                # Find all AssemblyReference children
                for ref_elem in collection:
                    if ref_elem.text:
                        references.append(ref_elem.text.strip())

    return references
```

#### c. Update Activity Type Extraction

**File**: `python/xaml_parser/extractors.py`

Store full tag including namespace in Activity model, then parse in normalization:

```python
# In ActivityExtractor._extract_single_activity_instance()
# Already done - element.tag contains full namespace
activity = Activity(
    activity_type=element.tag,  # Keep full tag: "{http://...}LogMessage"
    ...
)
```

#### d. Update Normalization

**File**: `python/xaml_parser/normalization.py`

```python
def _transform_activity(self, activity: Activity) -> ActivityDto:
    """Transform Activity to ActivityDto with namespace information."""

    # Parse namespace from tag
    tag = activity.activity_type

    if '}' in tag:
        # Has namespace: "{http://schemas.uipath.com/workflow/activities}LogMessage"
        namespace_uri, local_name = tag.split('}', 1)
        namespace_uri = namespace_uri[1:]  # Remove leading '{'
        full_type = tag
        type_short = local_name

        # Determine prefix by looking up in xmlns_declarations
        # (would need to pass xmlns_map from workflow metadata)
        prefix = self._lookup_namespace_prefix(namespace_uri)
    else:
        # No namespace
        full_type = tag
        type_short = tag
        namespace_uri = None
        prefix = None

    # Extract input/output arguments
    in_args: dict[str, str] = {}
    out_args: dict[str, str] = {}
    # ... (existing argument extraction logic)

    return ActivityDto(
        id=activity.activity_id,
        type=full_type,  # Full qualified name with namespace
        type_short=type_short,  # Short name only
        type_namespace=namespace_uri,  # NEW
        type_prefix=prefix,  # NEW
        display_name=activity.display_name,
        parent_id=activity.parent_activity_id,
        children=activity.child_activities,
        depth=activity.depth,
        properties=activity.properties,
        in_args=in_args,
        out_args=out_args,
        annotation=activity.annotation,
        expressions=activity.expressions,
        variables_referenced=activity.variables_referenced,
        selectors=activity.selectors if activity.selectors else None,
    )
```

## Benefits

1. **Disambiguation**: Can distinguish `UiPath.Core.Activities.LogMessage` from `MyCompany.Activities.LogMessage`
2. **Package Attribution**: Know which package provides each activity (UiPath.System.Activities vs third-party)
3. **Proper XAML Metadata**: Captures actual XAML structure information, not business logic
4. **Expression Context**: Understand available .NET namespaces for expression evaluation
5. **Assembly Dependencies**: Know which .NET assemblies are required for VB/C# expressions
6. **Stable IDs**: Full type names help with more stable activity IDs
7. **Schema Compliance**: Aligns with XAML Workflow Foundation / UiPath Studio structure
8. **Future-Proof**: Enables package dependency analysis and activity catalog generation

## Migration Strategy

1. **Phase 1**: Add new fields to WorkflowMetadata with defaults (backward compatible)
2. **Phase 2**: Add new fields to ActivityDto with defaults (backward compatible)
3. **Phase 3**: Update extractors to capture new metadata
4. **Phase 4**: Update normalization to populate new fields
5. **Phase 5**: Bump schema version to 1.1.0
6. **Phase 6**: Regenerate test baselines

This approach maintains backward compatibility while adding richer metadata for downstream consumers.

## Open Questions

1. Should `type` field use XML namespace format `{uri}name` or prefix format `ui:LogMessage`?
   - **Recommendation**: XML namespace format for accuracy, prefix for readability
   - **Solution**: Use XML namespace format in `type`, add prefix in `type_prefix`

2. Should we attempt to resolve .NET type names (e.g., `UiPath.Core.Activities.LogMessage`)?
   - **Recommendation**: Add as optional field `type_dotnet` if resolvable via assembly reflection
   - **Complexity**: Requires loading assemblies, may not be available in all environments

3. How to handle custom activity packages not in standard UiPath libraries?
   - **Solution**: xmlns declarations capture all namespaces, including custom ones

4. Should xmlns_declarations be at workflow level or project level?
   - **Current**: Workflow level (each XAML has its own xmlns declarations)
   - **Rationale**: Different workflows may import different namespaces

## References

- XAML Workflow Foundation: https://learn.microsoft.com/en-us/dotnet/framework/windows-workflow-foundation/
- UiPath Studio XAML structure: https://docs.uipath.com/studio/docs/about-xaml-in-studio
- XML Namespaces: https://www.w3.org/TR/xml-names/
- Test corpus: `test-corpus/c25v001_CORE_00000001/myEntrypointOne.xaml`
- Test corpus: `test-corpus/c25v001_CORE_00000010/Main.xaml`
