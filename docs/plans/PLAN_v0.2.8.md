# PLAN v0.2.8: Additional Activity Detection Patterns

## Todo List

- [ ] **Compare**: Diff constants.py between rpax and standalone
- [ ] **Identify new patterns**: Activities discovered in production usage
- [ ] **Update SKIP_ELEMENTS**: Add any missing metadata elements
- [ ] **Update CORE_VISUAL_ACTIVITIES**: Add any missing activity types
- [ ] **Update INVISIBLE_ATTRIBUTE_PATTERNS**: Add technical attributes
- [ ] **Add unit tests**: Test pattern classification
- [ ] **Test corpus**: Verify classification on diverse workflows

---

## Status
**Completed** - Constants Already Synced

## Notes

The constants.py files between rpax and standalone xaml-parser are **already identical** (confirmed during v0.2.0 development). No sync needed at this time.

**Future Process for Pattern Updates:**
1. Monitor rpax production usage for unclassified activities
2. Review UiPath release notes quarterly for new activity types
3. Accept community contributions via GitHub issues
4. Update both rpax and standalone constants.py in sync
5. Run corpus tests to verify patterns work correctly

## Priority
**LOW**

## Version
0.2.8

---

## Current State Analysis

### Constants Files Are Identical!

Comparison of `rpax/src/xaml_parser/constants.py` and `python/xaml_parser/constants.py` shows they are **functionally identical** (only type hint syntax differs).

### Current Patterns

**SKIP_ELEMENTS** (44 entries):
```python
SKIP_ELEMENTS: set[str] = {
    # XAML structure
    'Members', 'Variables', 'Arguments', 'Imports',
    'NamespacesForImplementation', 'ReferencesForImplementation',
    'TextExpression', 'VisualBasic', 'Collection', 'AssemblyReference',

    # ViewState
    'ViewState', 'WorkflowViewState', 'WorkflowViewStateService',
    'VirtualizedContainerService', 'Annotation', 'HintSize', 'IdRef',

    # Property containers
    'Property', 'ActivityAction', 'DelegateInArgument', 'DelegateOutArgument',
    'InArgument', 'OutArgument', 'InOutArgument',

    # Container sub-elements
    'Then', 'Else', 'Catches', 'Catch', 'Finally', 'States', 'Transitions',
    'Body', 'Handler', 'Condition', 'Default', 'Case',

    # Technical metadata
    'Dictionary', 'Boolean', 'String', 'Int32', 'Double',
    'AssignOperation', 'BackupSlot', 'BackupValues'
}
```

**CORE_VISUAL_ACTIVITIES** (15 entries):
```python
CORE_VISUAL_ACTIVITIES: set[str] = {
    # Control flow
    'Sequence', 'Flowchart', 'StateMachine', 'TryCatch', 'Parallel',
    'ParallelForEach', 'ForEach', 'While', 'DoWhile', 'If', 'Switch',

    # Workflow operations
    'InvokeWorkflowFile', 'Assign', 'Delay', 'RetryScope',
    'Pick', 'PickBranch', 'MultipleAssign',

    # Common activities
    'LogMessage', 'WriteLine', 'InputDialog', 'MessageBox',

    # Method calls
    'InvokeMethod', 'InvokeCode'
}
```

---

## Problem Statement

While constants are identical now, production usage of rpax may have discovered:
1. **New activity types** from recent UiPath versions
2. **Edge case patterns** that cause misclassification
3. **New metadata elements** to skip
4. **Package-specific activities** (e.g., AI Center, Document Understanding)

This plan establishes a process for updating patterns based on real-world usage.

---

## Enhancement Plan

### 1. Research New UiPath Activities

Survey recent UiPath packages for new activity types:

**UiPath 2023.10+ Activities:**
- `InvokeProcess` - External process invocation
- `Comment` - Workflow comments (should skip?)
- `GlobalHandler` - Global exception handler
- `TransactionItem` - REFramework transactions
- `ShouldStop` - Orchestrator stop check
- `BulkAddQueueItems` - Queue operations
- `AddDataRow`, `FilterDataTable` - Data manipulation
- `HttpClient` - REST API calls

**AI/ML Activities:**
- `MLSkill` - AI Center ML skills
- `DocumentUnderstanding` - Intelligent OCR
- `FormExtractor` - Form recognition
- `ClassifierScope` - Document classification

### 2. Potential Updates to SKIP_ELEMENTS

```python
# Additional metadata elements to consider:
SKIP_ELEMENTS_ADDITIONS = {
    # C# expression support
    'CSharpValue', 'CSharpReference',
    'VisualBasicValue', 'VisualBasicReference',

    # Framework elements
    'GlobalConstant', 'GlobalVariable',

    # Transaction handling
    'TransactionData', 'TransactionInfo',

    # Orchestrator integration
    'OrchestratorConnection', 'RobotInfo',
}
```

### 3. Potential Updates to CORE_VISUAL_ACTIVITIES

```python
# Additional visual activities to consider:
CORE_VISUAL_ACTIVITIES_ADDITIONS = {
    # Process control
    'InvokeProcess', 'ShouldStop', 'TerminateWorkflow',

    # Exception handling
    'Rethrow', 'Throw', 'GlobalHandler',

    # Transaction handling (REFramework)
    'TransactionItem', 'SetTransactionStatus',

    # Data activities
    'AddDataRow', 'RemoveDataRow', 'FilterDataTable',
    'OutputDataTable', 'BuildDataTable',

    # Queue activities
    'AddQueueItem', 'GetQueueItem', 'BulkAddQueueItems',
    'SetTransactionProgress', 'SetTransactionStatus',

    # HTTP activities
    'HttpClient', 'DownloadFile',

    # Comment (visual but not logic)
    'Comment',
}
```

### 4. Classification Improvements

```python
# File: python/xaml_parser/visibility.py

def classify_activity(tag: str) -> str:
    """Classify an activity element.

    Returns:
        "visual": User-visible workflow activity
        "metadata": Technical metadata (skip in tree)
        "container": Contains other activities
        "unknown": Needs classification
    """
    local_name = tag.split('}')[-1] if '}' in tag else tag

    if local_name in SKIP_ELEMENTS:
        return "metadata"
    if local_name in CORE_VISUAL_ACTIVITIES:
        return "visual"
    if local_name.endswith('.Variables') or local_name.endswith('.Catches'):
        return "container"
    if 'Activity' in local_name or local_name.startswith('ui'):
        return "visual"

    return "unknown"
```

---

## Test Plan

### Unit Tests

```python
# File: python/tests/unit/test_visibility.py

class TestActivityClassification:
    @pytest.mark.parametrize("tag,expected", [
        ("Sequence", "visual"),
        ("Members", "metadata"),
        ("Sequence.Variables", "container"),
        ("CustomActivity", "unknown"),
    ])
    def test_classify_activity(self, tag, expected):
        """Test activity classification."""
        assert classify_activity(tag) == expected

    def test_skip_elements_completeness(self):
        """Verify SKIP_ELEMENTS covers known metadata."""
        metadata_elements = [
            "Members", "Variables", "ViewState",
            "NamespacesForImplementation", "ReferencesForImplementation",
        ]
        for elem in metadata_elements:
            assert elem in SKIP_ELEMENTS

    def test_core_visual_activities_completeness(self):
        """Verify CORE_VISUAL_ACTIVITIES covers common activities."""
        common_activities = [
            "Sequence", "If", "While", "Assign",
            "InvokeWorkflowFile", "LogMessage",
        ]
        for activity in common_activities:
            assert activity in CORE_VISUAL_ACTIVITIES
```

### Corpus Validation

```bash
# Run on test corpus to find unclassified activities
uv run python developer-tests/test_corpus_output.py

# Check for "unknown" classifications
cat developer-tests/output/CORE_00000001/nested_view.json | \
  jq '.workflows[].activities[].type_short' | sort | uniq -c
```

---

## Process for Future Updates

1. **Monitor rpax usage**: Track unclassified activities in production
2. **Review UiPath releases**: Check release notes for new activities
3. **Community feedback**: Accept pattern contributions via issues
4. **Quarterly review**: Sync patterns between rpax and standalone

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/constants.py` | Update pattern sets |
| `python/xaml_parser/visibility.py` | Add classification function |
| `python/tests/unit/test_visibility.py` | Add classification tests |

---

## Validation Criteria

- [ ] All common activities correctly classified
- [ ] No false positives (visual activities marked as metadata)
- [ ] No false negatives (metadata shown as activities)
- [ ] Corpus projects parse without unclassified activities
- [ ] All existing tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Research new UiPath activities | 1 hour |
| Update constant sets | 30 minutes |
| Add classification function | 1 hour |
| Write unit tests | 1 hour |
| Test corpus | 30 minutes |
| **Total** | **~4 hours** |

---

## References

- UiPath Activity Packages: https://docs.uipath.com/activities/
- UiPath Release Notes: https://docs.uipath.com/release-notes/
- WF4 Activity Types: https://docs.microsoft.com/en-us/dotnet/framework/windows-workflow-foundation/
