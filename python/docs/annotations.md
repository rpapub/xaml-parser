# Annotation Schema Reference

Annotations in UiPath XAML workflows provide human-readable documentation and metadata using structured tags. The parser extracts these from `sap2010:Annotation.AnnotationText` attributes and transforms them into first-class structured data.

**Based on**: workflow-annotation-syntax.md for UiPath Workflow Analyzer static code analysis rules.

---

## Supported Tags

### Workflow Classification

Annotations that categorize workflows by their architectural role.

- **`@unit`** - Atomic unit of work (boolean flag)
  - Must have primitive inputs only
  - Must have exactly one of: `out Result` (Dictionary) or `io TransactionItem` (QueueItem)
  - Example: `@unit`

- **`@module`** - Reusable library workflow (boolean flag)
  - No UI interactions
  - No Orchestrator dependencies
  - Designed for composition
  - Example: `@module`

- **`@process`** - Top-level orchestration workflow (boolean flag)
  - Entry point for execution
  - Example: `@process`

- **`@dispatcher`** - Queue item producer (boolean flag)
  - Generates work items for downstream performers
  - Example: `@dispatcher`

- **`@performer`** - Queue item consumer (boolean flag)
  - Processes items from a queue
  - Example: `@performer`

- **`@test`** - Test workflow (boolean flag)
  - Excluded from production analysis rules
  - Example: `@test`

- **`@deprecated`** - Marked for removal (boolean flag or with message)
  - Triggers warnings when invoked by other workflows
  - Example: `@deprecated` or `@deprecated Use V2 instead`

- **`@pathkeeper`** - Object Repository selector traversal (boolean flag)
  - Traverses Object Repository selectors read-only
  - Example: `@pathkeeper`

### Rule Control

Annotations that control how analyzer rules are applied.

- **`@ignore <RuleId>`** - Suppress a specific rule for this element
  - Example: `@ignore CPRIMA-NMG-001`
  - Can be repeated for multiple rules

- **`@ignore-all`** - Suppress all rules for this element (boolean flag)
  - Use sparingly
  - Example: `@ignore-all`

- **`@strict`** - Enable stricter validation (boolean flag)
  - Enables stricter validation than project defaults
  - Example: `@strict`

- **`@nowarn <RuleId>`** - Alias for `@ignore`
  - Familiar syntax from C#
  - Example: `@nowarn CPRIMA-TAP-002`

### Documentation & Intent

Annotations that provide metadata and documentation.

- **`@author <name>`** - Workflow author or maintainer
  - Example: `@author jdoe`
  - Can be repeated for multiple authors

- **`@since <version>`** - Version when workflow was introduced
  - Example: `@since 2.0.0`
  - Tracks feature history

- **`@see <workflow>`** - Cross-reference to related workflow
  - Example: `@see Process_Main.xaml`

- **`@todo`** - Marks incomplete implementation (boolean flag)
  - Flags for review
  - Example: `@todo`

- **`@review`** - Requires manual code review (boolean flag)
  - Requires manual code review before deployment
  - Example: `@review`

### Architectural Constraints

Annotations that enforce design contracts and constraints.

- **`@pure`** - No side effects (boolean flag)
  - No file, database, queue, or external writes
  - Example: `@pure`

- **`@idempotent`** - Safe to retry (boolean flag)
  - Multiple executions produce the same result
  - Example: `@idempotent`

- **`@transactional`** - Must be wrapped in transaction (boolean flag)
  - Must be wrapped in transaction handling by caller
  - Example: `@transactional`

- **`@internal`** - Not for external invocation (boolean flag)
  - Implementation detail
  - Example: `@internal`

- **`@public`** - Public API contract (boolean flag)
  - Breaking changes require versioning
  - Example: `@public`

### Extensibility

- **`@custom:<tag> <value>`** - Custom user-defined tags
  - Example: `@custom:priority high`
  - Unknown tags automatically prefixed with `custom:`

---

## Parsing Rules

### Tag Format

1. **Tag Start**: Lines must start with `@` followed by tag name
   ```
   @module ProcessInvoice
   ```

2. **Value Separators**: Two formats supported
   - Space-separated: `@tag value`
   - Colon-separated: `@tag: value`
   ```
   @author John Doe
   @module: ProcessInvoice
   ```

3. **Boolean Flags**: Tags without values
   ```
   @public
   @test
   @ignore
   ```

### Multi-Line Values

Values continue until the next `@tag` or end of annotation:

```
@description This is a long description
that spans multiple lines
and continues here until the next tag

@author John Doe
```

### Unknown Tags

Tags not in the standard list are automatically prefixed with `custom:`:

```
@myTag value           →  tag="custom:myTag", value="value"
@priority high         →  tag="custom:priority", value="high"
@custom:reviewed-by X  →  tag="custom:reviewed-by", value="X"
```

**Note**: You can explicitly use `@custom:tagname` format, and it will be preserved as-is.

### HTML Entity Decoding

**Important**: HTML entity decoding happens in the **extractor layer** before the annotation text reaches the parser. The parser expects already-decoded text.

```xml
<Sequence sap2010:Annotation.AnnotationText="Author: John &amp; Jane&#xA;Version: 2.0">
```

Is decoded by the extractor to:
```
Author: John & Jane
Version: 2.0
```

Then passed to `parse_annotation()`.

### Ordering and Preservation

- Tag ordering is preserved
- Raw annotation text is retained alongside parsed tags
- Line numbers are tracked for each tag (1-indexed)
- Leading/trailing whitespace of the entire annotation block is preserved
- Blank lines within multi-line tag values are preserved

---

## Usage Examples

### Simple Annotation

```xml
<Sequence DisplayName="Process Invoice"
          sap2010:Annotation.AnnotationText="@module&#xA;@author jdoe">
```

Parsed structure:
```python
AnnotationBlock(
    raw="@module\n@author jdoe",
    tags=[
        AnnotationTag(tag="module", value=None, line_number=1),
        AnnotationTag(tag="author", value="jdoe", line_number=2)
    ]
)
```

### Complete Workflow Classification

```xml
<Activity sap2010:Annotation.AnnotationText="@unit
@module
@pure
@idempotent
@author jdoe
@since 2.0.0
@see Process_Main.xaml">
```

### Rule Suppression

```xml
<Workflow sap2010:Annotation.AnnotationText="@ignore CPRIMA-NMG-001
@ignore CPRIMA-TAP-002">
```

### Boolean Flags

```xml
<Workflow sap2010:Annotation.AnnotationText="@test
@pathkeeper
@public">
```

### Custom Tags

```xml
<Sequence sap2010:Annotation.AnnotationText="@priority high
@category finance
@compliance SOX
@custom:reviewed-by Jane Smith">
```

All become `custom:` tags:
- `custom:priority: high`
- `custom:category: finance`
- `custom:compliance: SOX`
- `custom:reviewed-by: Jane Smith`

---

## API Access

### Structured Access

```python
from cpmf_uips_xaml import load

session = load(project_path)

# Get workflow annotation
workflow = session.workflow("Main.xaml")
if workflow.metadata.annotation_block:
    block = workflow.metadata.annotation_block

    # Get specific tags
    module = block.get_tag("module")
    if module:
        print(f"Module: {module.value}")

    # Get all authors
    authors = block.get_tags("author")
    for author in authors:
        print(f"Author: {author.value}")

    # Check boolean flags
    if block.is_unit:
        print("This is an atomic unit of work")

    if block.is_module:
        print("This is a reusable module")

    if block.is_pathkeeper:
        print("This is a pathkeeper (Object Repository read-only)")

    if block.is_public_api:
        print("This is a public API")

    if block.is_test:
        print("This is a test workflow")
```

### Querying Annotations

```python
# Get all workflows with specific tag
public_workflows = session.workflows_with_tag("public")
test_workflows = session.workflows_with_tag("test")

# Group by module
modules = session.modules()
for module_name, workflows in modules.items():
    print(f"{module_name}: {len(workflows)} workflows")

# Query all annotations
all_annotations = session.annotations()
author_annotations = session.annotations(tag="author")
```

### Raw Text (Backward Compatibility)

```python
# Raw annotation text still available
if workflow.metadata.annotation:
    print(workflow.metadata.annotation)  # Plain string

# Both representations coexist
assert workflow.metadata.annotation == workflow.metadata.annotation_block.raw
```

---

## Implementation Details

### Data Structures

```python
@dataclass
class AnnotationTag:
    """Single parsed annotation tag."""
    tag: str                    # Tag name without @ prefix
    value: str | None = None    # Tag value/content
    raw: str | None = None      # Original line(s)
    line_number: int = 0        # Line number (1-indexed)

@dataclass
class AnnotationBlock:
    """Structured annotation with parsed tags."""
    raw: str                              # Full text (HTML decoded)
    tags: list[AnnotationTag] = []        # Parsed tags

    # Helper methods
    def get_tag(self, tag_name: str) -> AnnotationTag | None
    def get_tags(self, tag_name: str) -> list[AnnotationTag]
    def has_tag(self, tag_name: str) -> bool

    # Properties
    @property
    def is_ignored(self) -> bool
    @property
    def is_public_api(self) -> bool
    @property
    def is_test(self) -> bool
```

### Performance

- **Parsing**: O(n) where n = number of lines in annotation
- **Tag Lookup**: O(m) where m = number of tags (typically < 20)
- **Minimal Overhead**: Only parses when annotation exists

### Field Profiles

- **`minimal`**: Excludes `annotation_block`
- **`mcp`**: Includes `annotation_block` (for LLM consumption)
- **`full`**: Includes `annotation_block` (all fields)
- **`datalake`**: Includes `annotation_block`

---

## Migration Guide

### Existing Code (Before)

```python
# Only raw text available
if workflow.metadata.annotation:
    if "test" in workflow.metadata.annotation.lower():
        print("Appears to be a test workflow")
```

### New Code (After)

```python
# Structured access
if workflow.metadata.annotation_block:
    if workflow.metadata.annotation_block.is_test:
        print("This is a test workflow")
```

### Backward Compatible

```python
# Both work simultaneously
old_way = workflow.metadata.annotation  # str | None
new_way = workflow.metadata.annotation_block  # AnnotationBlock | None

# Same content
if new_way:
    assert old_way == new_way.raw
```

---

## Best Practices

1. **Use Standard Tags**: Prefer standard tags over custom tags for interoperability
2. **Multi-Line Descriptions**: Use `@description` for detailed documentation
3. **Module Grouping**: Use `@module` to organize related workflows
4. **Public API Marking**: Use `@public` for workflows exposed to other teams
5. **Test Identification**: Use `@test` for test workflows to exclude from metrics
6. **Deprecation Notes**: Use `@deprecated` with migration instructions

---

## Related Documentation

- [Data Model Reference](./data-model.md) - WorkflowDto, ActivityDto structures
- [API Reference](./api-reference.md) - ProjectSession methods
- [Configuration](./configuration.md) - Field profiles and output settings
