# PLAN v0.2.9: Expression Parser & Variable Flow Analysis

## Todo List

- [x] **Implement tokenizer**: Regex-based lexical analysis for VB.NET and C#
- [x] **Implement parser**: Lightweight recursive descent parser
- [x] **Add data models**: VariableAccess, MethodCall, ParsedExpression
- [x] **Integrate with extractors**: Update _extract_expressions() method
- [x] **Implement variable flow analyzer**: Build variable flow graph
- [x] **Add DTO models**: VariableFlowDto and integrate with WorkflowDto
- [x] **Write unit tests**: Expression parser, variable flow analyzer
- [x] **Write corpus tests**: Test on real XAML from corpus
- [x] **Performance tuning**: LRU cache, optimize for < 10% overhead
- [x] **Update CHANGELOG**: Document new feature

---

## Status
**Planned** - Ready for Implementation

## Priority
**MEDIUM** - Enhances LLM/MCP use cases

## Version
0.2.9

---

## Problem Statement

### Current Limitations

- Expressions extracted as raw strings only (`Activity.expressions: list[str]`)
- `Expression.contains_variables` and `contains_methods` fields exist but are never populated
- No variable flow analysis (which activities read/write which variables)
- No method call detection beyond pattern matching
- Limited value for LLM context ("What does this workflow do with the customer_email variable?")

### Why This Matters

- **LLM Context**: Enable queries like "trace data flow of customer_id through workflow"
- **Impact Analysis**: Determine what breaks if variable X changes
- **Data Lineage**: Track where data comes from and goes to
- **Code Quality**: Detect unused variables, detect variables used before assignment

---

## Implementation Approach

**Architecture: Hybrid Tokenizer + Lightweight Parser**

1. **Tokenization Layer**: Regex-based lexical analysis
2. **Lightweight Recursive Descent Parser**: Simple parser for token streams
3. **Graceful Degradation**: Falls back to regex extraction on errors
4. **Zero External Dependencies**: Python stdlib only (re module)

**Rationale:**
- VB.NET/C# expressions in XAML are typically simple
- Regex tokenization is fast and sufficient
- Lightweight parser avoids complexity of full language parsers
- Graceful degradation ensures robustness

---

## Data Models

### New Internal Models (models.py)

```python
@dataclass
class VariableAccess:
    """Records a variable access in an expression."""
    name: str                    # Variable name
    access_type: str             # 'read' | 'write' | 'readwrite'
    context: str                 # Where in expression (LHS, RHS, argument)
    member_chain: list[str]      # Property/method chain: ['ToString', 'ToUpper']

@dataclass
class MethodCall:
    """Records a method call in an expression."""
    method_name: str             # Method name
    qualifier: str | None        # Qualifier (String, DateTime, variable name)
    is_static: bool = False      # True for String.Format, False for var.ToString()
    arguments: list[str] = field(default_factory=list)

@dataclass
class ParsedExpression:
    """Result of expression parsing."""
    raw: str                     # Original expression
    language: str                # 'VisualBasic' | 'CSharp'
    is_valid: bool               # Parsing succeeded
    variables: list[VariableAccess] = field(default_factory=list)
    methods: list[MethodCall] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
```

### New DTO Model (dto.py)

```python
@dataclass
class VariableFlowDto:
    """Variable data flow between activity and variable."""
    activity_id: str             # Activity that accesses variable
    variable_name: str           # Variable being accessed
    flow_type: str               # 'read' | 'write' | 'readwrite'
    property_context: str | None # Which property (Value, Condition)
    expression_snippet: str | None  # Abbreviated expression (first 50 chars)

# Add to WorkflowDto
@dataclass
class WorkflowDto:
    # ... existing fields ...
    variable_flows: list[VariableFlowDto] | None = None
```

---

## Implementation Steps

### Phase 1: Core Expression Parser

**File**: `python/xaml_parser/expression_parser.py` (NEW)

**Components:**
1. `ExpressionTokenizer` class:
   - `tokenize(expression, language) -> list[Token]`
   - VB.NET patterns: `[var]`, `AndAlso`, `OrElse`, `<>`, keywords
   - C# patterns: `&&`, `||`, `==`, `=>`, keywords

2. `ExpressionParser` class:
   - `parse(expression) -> ParsedExpression`
   - `_extract_variables(tokens, raw_expr) -> list[VariableAccess]`
   - `_extract_methods(tokens) -> list[MethodCall]`
   - `_extract_operators(tokens) -> list[str]`

**Key Algorithms:**
- **Variable read/write detection**: Check if variable on LHS of `=` operator
- **Method call extraction**: Find IDENTIFIER followed by LPAREN, look back for DOT to find qualifier
- **Member chain tracking**: Follow DOT sequences to build property/method chains

**Error Handling:**
- Try-catch wrapper around parsing
- Return `ParsedExpression` with `is_valid=False` on errors
- Populate `parse_errors` list with error messages

### Phase 2: Integration with Parser

**File**: `python/xaml_parser/utils.py` (UPDATE)

Add new method:
```python
@staticmethod
def parse_expression(text: str, language: str = "VisualBasic") -> ParsedExpression:
    """Parse expression using new expression parser."""
    from .expression_parser import ExpressionParser
    parser = ExpressionParser(language)
    return parser.parse(text)
```

Keep existing `extract_variable_references()` for backward compatibility.

**File**: `python/xaml_parser/extractors.py` (UPDATE)

Update `_extract_expressions()` method to use parser.

**Config Changes** (constants.py):
```python
DEFAULT_CONFIG = {
    # ... existing ...
    "parse_expressions": False,      # NEW - opt-in for performance
    "extract_variable_flow": False,  # NEW - opt-in
}
```

### Phase 3: Variable Flow Analysis

**File**: `python/xaml_parser/variable_flow.py` (NEW)

Implement `VariableFlowAnalyzer` class with `analyze_workflow()` method.

**File**: `python/xaml_parser/normalization.py` (UPDATE)

Add `include_variable_flow: bool = False` parameter to `normalize()`.

### Phase 4: Testing

**File**: `python/tests/unit/test_expression_parser.py` (NEW)

Test coverage:
- VB.NET tokenization and parsing
- C# tokenization and parsing
- Graceful degradation
- Edge cases

**File**: `python/tests/unit/test_variable_flow.py` (NEW)

Test coverage:
- Variable flow graph construction
- Read vs write classification

**File**: `python/tests/corpus/test_expression_corpus.py` (NEW)

Test coverage:
- Real-world XAML expressions
- Success rate >80%

---

## Edge Cases to Handle

1. **Malformed Expressions**: Return `is_valid=False`, populate `parse_errors`
2. **String Literals with Brackets**: Tokenizer recognizes STRING_LITERAL, skip variable extraction
3. **VB.NET vs C# Operator Ambiguity**: Language-aware tokenizer
4. **Complex Member Chains**: Track full `member_chain` in VariableAccess
5. **New Object Expressions**: Keyword tokenization, skip `New`
6. **Generic Type Arguments**: Handle `List(Of String)` and `List<String>`
7. **Lambda Expressions**: Recognize `=>` operator

---

## Performance Considerations

1. **Lazy Parsing**: Expression parsing is opt-in (default: False)
2. **Caching**: Use `@lru_cache(maxsize=256)` on `parse()` method
3. **Memory**: Don't keep ParsedExpression objects, convert immediately
4. **Performance Target**: < 10% overhead
5. **Measurement**: Add timing metrics, benchmark on corpus

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/expression_parser.py` | NEW - Core parser with tokenizer |
| `python/xaml_parser/variable_flow.py` | NEW - Variable flow analyzer |
| `python/xaml_parser/models.py` | UPDATE - Add VariableAccess, MethodCall, ParsedExpression |
| `python/xaml_parser/dto.py` | UPDATE - Add VariableFlowDto |
| `python/xaml_parser/utils.py` | UPDATE - Add parse_expression() method |
| `python/xaml_parser/extractors.py` | UPDATE - Integrate parser in _extract_expressions() |
| `python/xaml_parser/normalization.py` | UPDATE - Add variable flow analysis |
| `python/xaml_parser/constants.py` | UPDATE - Add parse_expressions, extract_variable_flow config |
| `python/tests/unit/test_expression_parser.py` | NEW - Unit tests for parser |
| `python/tests/unit/test_variable_flow.py` | NEW - Unit tests for flow analysis |
| `python/tests/corpus/test_expression_corpus.py` | NEW - Corpus tests |

---

## Validation Criteria

- [ ] VB.NET expressions parse correctly (>80% success on corpus)
- [ ] C# expressions parse correctly (>80% success on corpus)
- [ ] Variable reads vs writes correctly classified
- [ ] Method calls extracted with qualifiers
- [ ] Variable flow graph builds correctly
- [ ] Malformed expressions handled gracefully (no crashes)
- [ ] Performance overhead < 10%
- [ ] All unit tests pass
- [ ] Corpus tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement tokenizer | 3 hours |
| Implement parser logic | 4 hours |
| Integrate with extractors | 2 hours |
| Implement variable flow analyzer | 2 hours |
| Write unit tests | 4 hours |
| Write corpus tests | 1 hour |
| Performance tuning | 2 hours |
| **Total** | **~18 hours** |

---

## References

- VB.NET expression syntax: https://docs.microsoft.com/en-us/dotnet/visual-basic/programming-guide/language-features/
- C# expression syntax: https://docs.microsoft.com/en-us/dotnet/csharp/language-reference/
- UiPath expressions: https://docs.uipath.com/activities/docs/about-expressions
