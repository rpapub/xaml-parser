# PLAN v0.2.11: Performance Profiling & Optimization

## Todo List

- [x] **Implement profiling framework**: Profiler class with context managers
- [x] **Add timing to parser**: Integrate profiling in parse_file()
- [x] **Add timing to extractors**: Profile activity extraction, expressions
- [x] **Implement memory profiling**: tracemalloc and psutil integration
- [x] **CLI performance report**: Format and display profiling data
- [ ] **Pre-compile regex patterns**: Optimize pattern matching
- [ ] **Create benchmarks**: Performance benchmark suite
- [ ] **Run benchmarks**: Identify bottlenecks on corpus
- [ ] **Document findings**: Performance characteristics and recommendations
- [ ] **Update CHANGELOG**: Document optimization work

---

## Status
**Planned** - Ready for Implementation

## Priority
**MEDIUM** - Quick win for scalability

## Version
0.2.11

---

## Problem Statement

### Current State

- Basic timing: `parse_time_ms` in ParseResult
- Performance metrics dict exists but sparsely populated
- No per-phase timing breakdowns
- No memory profiling
- Unknown bottlenecks for large files

### Why This Matters

- **Large Projects**: 100+ workflow projects need to parse quickly
- **CI/CD Integration**: Parser must be fast enough for build pipelines
- **User Experience**: Slow parsing frustrates users
- **Resource Planning**: Need to understand memory requirements

---

## Profiling Strategy

### 1. Detailed Timing Breakdowns

Add timing for each parse phase:
- File I/O: `file_read_ms`
- XML parsing: `xml_parse_ms`
- Namespace extraction: `namespace_extract_ms`
- Activity extraction: `activity_extract_ms`
- Expression parsing: `expression_parse_ms` (if enabled)
- Variable flow analysis: `variable_flow_ms` (if enabled)
- Normalization: `normalization_ms`

### 2. Memory Profiling

Track memory usage:
- Peak memory during parse
- Memory per activity
- Memory per expression
- Total allocated objects

### 3. Bottleneck Identification

Identify slow operations:
- Which extractor is slowest?
- Are regex patterns slow?
- Is XML traversal the bottleneck?
- Is defusedxml adding overhead?

---

## Implementation Approach

### Phase 1: Enhanced Timing

**File**: `python/xaml_parser/profiling.py` (NEW)

```python
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

@dataclass
class ProfileData:
    """Profiling data for parser operations."""

    timings: dict[str, float] = field(default_factory=dict)
    memory_peak: int = 0
    memory_start: int = 0
    memory_end: int = 0
    call_counts: dict[str, int] = field(default_factory=dict)

    def add_timing(self, operation: str, duration_ms: float):
        """Add timing measurement."""
        if operation in self.timings:
            self.timings[operation] += duration_ms
        else:
            self.timings[operation] = duration_ms

    def get_summary(self) -> dict[str, float]:
        """Get timing summary sorted by duration."""
        return dict(sorted(self.timings.items(), key=lambda x: x[1], reverse=True))

class Profiler:
    """Context manager for profiling parser operations."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.data = ProfileData()

    @contextmanager
    def profile(self, operation: str):
        """Profile a code block."""
        if not self.enabled:
            yield
            return

        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.data.add_timing(operation, duration_ms)
```

**Integration in parser.py**:
```python
class XamlParser:
    def __init__(self, config: dict | None = None):
        # ... existing init ...
        self.profiler = Profiler(enabled=self.config.get("enable_profiling", False))

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse XAML file with profiling."""

        with self.profiler.profile("total_parse"):
            with self.profiler.profile("file_read"):
                content, encoding = self._read_file_with_encoding(file_path)

            with self.profiler.profile("xml_parse"):
                root = self._parse_xml_content(content)

            with self.profiler.profile("content_extract"):
                workflow_content = self._parse_workflow_content(root)

        # Add profiling data to result
        result.diagnostics.performance_metrics = self.profiler.data.get_summary()

        return result
```

### Phase 2: Memory Profiling

**File**: `python/xaml_parser/profiling.py` (UPDATE)

Add memory tracking:
```python
import tracemalloc
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class Profiler:
    def start_memory_tracking(self):
        """Start memory profiling."""
        if self.enabled:
            tracemalloc.start()
            if PSUTIL_AVAILABLE:
                import os
                process = psutil.Process(os.getpid())
                self.data.memory_start = process.memory_info().rss

    def stop_memory_tracking(self):
        """Stop memory profiling."""
        if self.enabled:
            current, peak = tracemalloc.get_traced_memory()
            self.data.memory_peak = peak
            tracemalloc.stop()

            if PSUTIL_AVAILABLE:
                import os
                process = psutil.Process(os.getpid())
                self.data.memory_end = process.memory_info().rss

    def get_memory_summary(self) -> dict[str, int]:
        """Get memory usage summary."""
        return {
            "peak_bytes": self.data.memory_peak,
            "start_bytes": self.data.memory_start,
            "end_bytes": self.data.memory_end,
            "delta_bytes": self.data.memory_end - self.data.memory_start,
        }
```

**Note**: Make psutil optional dependency for memory profiling.

### Phase 3: Performance Reporting

**File**: `python/xaml_parser/cli.py` (UPDATE)

Add performance report:
```python
def format_performance_report(diagnostics: ParseDiagnostics) -> str:
    """Format performance profiling data."""
    if not diagnostics.performance_metrics:
        return "[INFO] Profiling not enabled"

    output = "Performance Report:\n"
    output += "=" * 50 + "\n"

    # Timing breakdown
    output += "\nTiming Breakdown:\n"
    for operation, duration_ms in diagnostics.performance_metrics.items():
        percentage = (duration_ms / diagnostics.performance_metrics['total_parse']) * 100
        output += f"  {operation:30s}: {duration_ms:8.2f}ms ({percentage:5.1f}%)\n"

    # Memory usage (if available)
    if hasattr(diagnostics, 'memory_metrics'):
        output += "\nMemory Usage:\n"
        mem = diagnostics.memory_metrics
        output += f"  Peak: {mem['peak_bytes'] / 1024 / 1024:.2f} MB\n"
        output += f"  Delta: {mem['delta_bytes'] / 1024 / 1024:.2f} MB\n"

    return output
```

Add CLI flag:
```python
parser.add_argument('--profile', action='store_true',
                   help='Enable performance profiling')
```

### Phase 4: Optimization Targets

Based on profiling, optimize:

**1. Regex Patterns**:
- Pre-compile all regex patterns in constants.py
- Use atomic groups for better performance

**2. Activity Extraction**:
- Optimize tree traversal
- Cache element lookups by tag

**3. Expression Parsing** (if v0.2.9 implemented):
- LRU cache for repeated expressions
- Lazy evaluation

### Phase 5: Benchmarking

**File**: `python/benchmarks/benchmark_parser.py` (NEW)

```python
"""Performance benchmarks for parser."""

import time
from pathlib import Path
from xaml_parser import XamlParser

def benchmark_parse_file(file_path: Path, iterations: int = 10):
    """Benchmark parse_file performance."""
    parser = XamlParser()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = parser.parse_file(file_path)
        duration = time.perf_counter() - start
        times.append(duration)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"File: {file_path.name}")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")
    print(f"  Activities: {result.content.total_activities}")

if __name__ == "__main__":
    # Benchmark on corpus files
    corpus_path = Path("test-corpus/c25v001_CORE_00000001")
    for xaml_file in corpus_path.glob("*.xaml"):
        benchmark_parse_file(xaml_file)
```

Run benchmarks:
```bash
uv run python benchmarks/benchmark_parser.py
```

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/profiling.py` | NEW - Profiling utilities |
| `python/xaml_parser/parser.py` | UPDATE - Add profiling integration |
| `python/xaml_parser/extractors.py` | UPDATE - Add profiling to extractors |
| `python/xaml_parser/cli.py` | UPDATE - Add --profile flag, performance report |
| `python/xaml_parser/constants.py` | UPDATE - Pre-compile regex patterns |
| `python/benchmarks/benchmark_parser.py` | NEW - Performance benchmarks |
| `python/pyproject.toml` | UPDATE - Add psutil as optional dependency |

---

## Validation Criteria

- [x] Detailed timing for all parse phases
- [x] Memory profiling available (required dependency: psutil)
- [x] Performance report shows breakdown
- [ ] Benchmarks run on corpus projects
- [ ] Regex patterns pre-compiled
- [x] Performance overhead of profiling < 5%
- [ ] Documentation of bottlenecks

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement profiling framework | 3 hours |
| Add timing to all phases | 2 hours |
| Add memory profiling | 2 hours |
| CLI performance report | 1 hour |
| Pre-compile regex patterns | 1 hour |
| Create benchmarks | 2 hours |
| Run benchmarks, identify bottlenecks | 2 hours |
| Documentation | 1 hour |
| **Total** | **~14 hours** |

---

## References

- Python profiling: https://docs.python.org/3/library/profile.html
- tracemalloc: https://docs.python.org/3/library/tracemalloc.html
- psutil: https://psutil.readthedocs.io/
