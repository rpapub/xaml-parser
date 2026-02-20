# PLAN v0.2.10: Quality Metrics & Static Analysis

## Todo List

- [x] **Implement quality metrics calculator**: Cyclomatic complexity, cognitive complexity, nesting depth
- [x] **Implement size metrics**: Activity counts by type, expression complexity
- [x] **Implement anti-pattern detector**: Empty catch, hardcoded values, unreachable code
- [x] **Add data models**: QualityMetrics, AntiPattern dataclasses
- [x] **Integrate with normalization**: Add quality_metrics and anti_patterns to WorkflowDto
- [x] **CLI integration**: Add --metrics and --anti-patterns flags
- [x] **Write unit tests**: Metrics calculator, anti-pattern detector
- [x] **Run on corpus**: Verify metrics on real workflows
- [x] **Update CHANGELOG**: Document new feature

---

## Status
**Planned** - Ready for Implementation

## Priority
**MEDIUM** - Enables data lake analytics

## Version
0.2.10

---

## Problem Statement

### Current State

- Basic counting metrics exist (total_activities, total_variables, etc.)
- No complexity measurements (cyclomatic complexity, nesting depth)
- No anti-pattern detection (empty try-catch, hardcoded credentials)
- No quality scoring for workflows

### Why This Matters

- **Data Lake Analytics**: Answer "which workflows are most complex?"
- **Quality Dashboards**: Track code quality trends across projects
- **Automated Review**: Flag problematic patterns before code review
- **Technical Debt**: Identify workflows needing refactoring

---

## Metrics to Implement

### 1. Complexity Metrics

**Cyclomatic Complexity**:
- Count decision points: If, Switch, While, DoWhile, TryCatch branches
- Formula: Count decision points + 1
- TryCatch adds complexity per Catch block

**Cognitive Complexity**:
- Nesting penalty: +1 per nesting level for each decision point
- Recursion penalty: +1 for InvokeWorkflowFile to self

**Nesting Depth**:
- Maximum nesting level of activities
- Already tracked in `Activity.depth`, aggregate max

### 2. Size Metrics

- **Activity Count by Type**: Control flow, UI automation, data activities
- **Variable Count**: Total and per-scope breakdown
- **Expression Count**: Total and complex expressions (length >100 chars)

### 3. Anti-Pattern Detection

**Empty Exception Handlers**:
- TryCatch with empty Catch block
- TryCatch with only LogMessage in Catch

**Hardcoded Values**:
- File paths (C:\, /home/, /usr/)
- URLs (http://, https://)
- Potential credentials (password=, key=, secret=)

**Missing Error Handling**:
- Workflows without TryCatch
- High-risk activities without error handling

**Unreachable Code**:
- Activities after Throw/TerminateWorkflow
- Dead branches in If/Switch

**Excessive Variables**:
- More than 20 variables in single scope
- Unused variables (declared but never referenced)

---

## Data Models

### New Models (models.py)

```python
@dataclass
class QualityMetrics:
    """Quality and complexity metrics for a workflow."""

    # Complexity metrics
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    max_nesting_depth: int = 0

    # Size metrics
    total_activities: int = 0
    control_flow_activities: int = 0
    ui_automation_activities: int = 0
    data_activities: int = 0
    total_variables: int = 0
    total_expressions: int = 0
    complex_expressions: int = 0

    # Quality indicators
    has_error_handling: bool = False
    empty_catch_blocks: int = 0
    hardcoded_strings: int = 0
    unreachable_activities: int = 0
    unused_variables: int = 0

    # Overall score (0-100)
    quality_score: float = 0.0

@dataclass
class AntiPattern:
    """Detected anti-pattern in workflow."""

    pattern_type: str            # 'empty_catch' | 'hardcoded_value' | 'unreachable_code'
    severity: str                # 'error' | 'warning' | 'info'
    activity_id: str | None      # Activity where detected
    message: str                 # Human-readable description
    suggestion: str | None       # How to fix
    location: str | None         # Context (e.g., 'TryCatch.Catch')
```

### DTO Integration (dto.py)

```python
@dataclass
class WorkflowDto:
    # ... existing fields ...

    # NEW: Quality metrics (optional, enabled by config)
    quality_metrics: QualityMetrics | None = None
    anti_patterns: list[AntiPattern] | None = None
```

---

## Implementation Steps

### Phase 1: Metrics Calculator

**File**: `python/xaml_parser/quality_metrics.py` (NEW)

Implement `QualityMetricsCalculator` class:

```python
class QualityMetricsCalculator:
    """Calculates quality and complexity metrics for workflows."""

    def calculate(
        self,
        activities: list[Activity],
        variables: list[WorkflowVariable],
        expressions: list[str]
    ) -> QualityMetrics:
        """Calculate all quality metrics."""

        metrics = QualityMetrics()

        # Complexity metrics
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(activities)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(activities)
        metrics.max_nesting_depth = self._calculate_max_nesting_depth(activities)

        # Size metrics
        metrics.total_activities = len(activities)
        metrics.control_flow_activities = self._count_control_flow(activities)
        metrics.ui_automation_activities = self._count_ui_automation(activities)
        metrics.data_activities = self._count_data_activities(activities)

        # Quality indicators
        metrics.has_error_handling = self._has_error_handling(activities)
        metrics.empty_catch_blocks = self._count_empty_catch_blocks(activities)

        # Overall score
        metrics.quality_score = self._calculate_quality_score(metrics)

        return metrics
```

**Key Methods:**
- `_calculate_cyclomatic_complexity()`: Count decision points
- `_calculate_cognitive_complexity()`: Include nesting penalties
- `_count_control_flow()`, `_count_ui_automation()`, `_count_data_activities()`: Classify by type

### Phase 2: Anti-Pattern Detector

**File**: `python/xaml_parser/anti_patterns.py` (NEW)

Implement `AntiPatternDetector` class:

```python
class AntiPatternDetector:
    """Detects anti-patterns and code smells in workflows."""

    def detect(
        self,
        activities: list[Activity],
        variables: list[WorkflowVariable]
    ) -> list[AntiPattern]:
        """Detect all anti-patterns."""

        patterns = []

        # Empty catch blocks
        patterns.extend(self._detect_empty_catch_blocks(activities))

        # Hardcoded credentials/paths
        patterns.extend(self._detect_hardcoded_values(activities))

        # Unreachable code
        patterns.extend(self._detect_unreachable_code(activities))

        # Missing error handling
        patterns.extend(self._detect_missing_error_handling(activities))

        # Unused variables
        patterns.extend(self._detect_unused_variables(variables, activities))

        return patterns
```

**Hardcoded Value Patterns:**
```python
hardcoded_patterns = [
    (r'[A-Z]:\\', 'Windows file path'),
    (r'/(?:home|usr|var)/', 'Unix file path'),
    (r'https?://', 'URL'),
    (r'(?:password|pwd|pass|secret|key)\s*[=:]\s*["\'][^"\']+["\']', 'Potential credential'),
]
```

### Phase 3: Integration

**File**: `python/xaml_parser/normalization.py` (UPDATE)

Add parameters:
```python
def normalize(
    self,
    parse_result: ParseResult,
    # ... existing parameters ...
    include_quality_metrics: bool = False,  # NEW
    detect_anti_patterns: bool = False,     # NEW
) -> WorkflowDto:
```

Calculate metrics and patterns:
```python
# Quality metrics
quality_metrics = None
if include_quality_metrics and content.activities:
    from .quality_metrics import QualityMetricsCalculator
    calculator = QualityMetricsCalculator()
    quality_metrics = calculator.calculate(
        content.activities,
        content.variables,
        [expr for act in content.activities for expr in act.expressions]
    )

# Anti-pattern detection
anti_patterns = None
if detect_anti_patterns and content.activities:
    from .anti_patterns import AntiPatternDetector
    detector = AntiPatternDetector()
    anti_patterns = detector.detect(content.activities, content.variables)
```

**Config Changes** (constants.py):
```python
DEFAULT_CONFIG = {
    # ... existing ...
    "extract_quality_metrics": False,  # NEW
    "detect_anti_patterns": False,      # NEW
}
```

### Phase 4: CLI Integration

**File**: `python/xaml_parser/cli.py` (UPDATE)

Add output formatters:
```python
def format_quality_metrics(metrics: QualityMetrics) -> str:
    """Format quality metrics for console output."""
    return f"""
Quality Metrics:
  Cyclomatic Complexity: {metrics.cyclomatic_complexity}
  Cognitive Complexity: {metrics.cognitive_complexity}
  Max Nesting Depth: {metrics.max_nesting_depth}

  Size:
    Total Activities: {metrics.total_activities}
    Control Flow: {metrics.control_flow_activities}
    UI Automation: {metrics.ui_automation_activities}

  Quality Score: {metrics.quality_score:.1f}/100
"""

def format_anti_patterns(patterns: list[AntiPattern]) -> str:
    """Format anti-patterns for console output."""
    if not patterns:
        return "[OK] No anti-patterns detected"

    output = f"Anti-Patterns Detected: {len(patterns)}\n"
    for pattern in patterns:
        severity_marker = {
            'error': '[ERROR]',
            'warning': '[WARN]',
            'info': '[INFO]'
        }.get(pattern.severity, '[?]')

        output += f"\n{severity_marker} {pattern.message}\n"
        if pattern.location:
            output += f"  Location: {pattern.location}\n"
        if pattern.suggestion:
            output += f"  Suggestion: {pattern.suggestion}\n"

    return output
```

Add CLI flags:
```python
parser.add_argument('--metrics', action='store_true',
                   help='Show quality metrics')
parser.add_argument('--anti-patterns', action='store_true',
                   help='Detect and show anti-patterns')
```

### Phase 5: Testing

**File**: `python/tests/unit/test_quality_metrics.py` (NEW)

Test coverage:
- Cyclomatic complexity calculation
- Cognitive complexity with nesting
- Max nesting depth
- Activity count by type
- Quality score calculation

**File**: `python/tests/unit/test_anti_patterns.py` (NEW)

Test coverage:
- Empty catch block detection
- Hardcoded value detection
- Unreachable code detection
- Unused variable detection

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/quality_metrics.py` | NEW - Quality metrics calculator |
| `python/xaml_parser/anti_patterns.py` | NEW - Anti-pattern detector |
| `python/xaml_parser/models.py` | UPDATE - Add QualityMetrics, AntiPattern |
| `python/xaml_parser/dto.py` | UPDATE - Add quality_metrics, anti_patterns |
| `python/xaml_parser/normalization.py` | UPDATE - Integrate calculators |
| `python/xaml_parser/cli.py` | UPDATE - Add --metrics, --anti-patterns flags |
| `python/xaml_parser/constants.py` | UPDATE - Add config flags |
| `python/tests/unit/test_quality_metrics.py` | NEW - Unit tests |
| `python/tests/unit/test_anti_patterns.py` | NEW - Unit tests |

---

## Validation Criteria

- [ ] Cyclomatic complexity calculated correctly
- [ ] Cognitive complexity includes nesting penalties
- [ ] Empty catch blocks detected
- [ ] Hardcoded credentials flagged as warnings
- [ ] Unreachable code detected
- [ ] Quality score ranges 0-100
- [ ] CLI displays metrics correctly
- [ ] All unit tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement quality metrics calculator | 4 hours |
| Implement anti-pattern detector | 4 hours |
| Integrate with normalization | 2 hours |
| CLI integration | 2 hours |
| Write unit tests | 4 hours |
| Documentation | 1 hour |
| **Total** | **~17 hours** |

---

## References

- Cyclomatic Complexity: https://en.wikipedia.org/wiki/Cyclomatic_complexity
- Cognitive Complexity: https://www.sonarsource.com/docs/CognitiveComplexity.pdf
- Code Smells: https://refactoring.guru/refactoring/smells
