"""Tests for profiling module (v0.2.11)."""

import time

import pytest

from cpmf_uips_xaml.profiling import ProfileData, Profiler


class TestProfileData:
    """Test ProfileData class."""

    def setup_method(self):
        """Setup test data."""
        self.data = ProfileData()

    def test_initial_state(self):
        """Test initial state of ProfileData."""
        assert self.data.timings == {}
        assert self.data.memory_start == 0
        assert self.data.memory_peak == 0
        assert self.data.memory_end == 0
        assert self.data.psutil_start == 0
        assert self.data.psutil_end == 0

    def test_add_timing(self):
        """Test adding timing measurements."""
        self.data.add_timing("operation1", 10.5)
        self.data.add_timing("operation1", 15.2)
        self.data.add_timing("operation2", 20.0)

        assert "operation1" in self.data.timings
        assert "operation2" in self.data.timings
        assert len(self.data.timings["operation1"]) == 2
        assert len(self.data.timings["operation2"]) == 1

    def test_get_total_time(self):
        """Test total time calculation."""
        self.data.add_timing("op1", 10.0)
        self.data.add_timing("op1", 20.0)
        self.data.add_timing("op2", 30.0)

        assert self.data.get_total_time() == 60.0

    def test_get_total_time_empty(self):
        """Test total time for empty data."""
        assert self.data.get_total_time() == 0.0

    def test_get_operation_total(self):
        """Test operation total time."""
        self.data.add_timing("op1", 10.0)
        self.data.add_timing("op1", 20.0)

        assert self.data.get_operation_total("op1") == 30.0
        assert self.data.get_operation_total("nonexistent") == 0.0

    def test_get_operation_count(self):
        """Test operation call count."""
        self.data.add_timing("op1", 10.0)
        self.data.add_timing("op1", 20.0)
        self.data.add_timing("op2", 30.0)

        assert self.data.get_operation_count("op1") == 2
        assert self.data.get_operation_count("op2") == 1
        assert self.data.get_operation_count("nonexistent") == 0

    def test_get_operation_average(self):
        """Test operation average time."""
        self.data.add_timing("op1", 10.0)
        self.data.add_timing("op1", 20.0)

        assert self.data.get_operation_average("op1") == 15.0
        assert self.data.get_operation_average("nonexistent") == 0.0

    def test_get_operation_percentage(self):
        """Test operation percentage calculation."""
        self.data.add_timing("op1", 60.0)  # 60% of total
        self.data.add_timing("op2", 40.0)  # 40% of total

        assert self.data.get_operation_percentage("op1") == pytest.approx(60.0, abs=0.1)
        assert self.data.get_operation_percentage("op2") == pytest.approx(40.0, abs=0.1)

    def test_get_operation_percentage_empty(self):
        """Test percentage when no data."""
        assert self.data.get_operation_percentage("op1") == 0.0

    def test_get_memory_delta_bytes(self):
        """Test memory delta calculation."""
        self.data.memory_start = 1000
        self.data.memory_end = 5000

        assert self.data.get_memory_delta_bytes() == 4000

    def test_get_memory_delta_mb(self):
        """Test memory delta in MB."""
        self.data.memory_start = 0
        self.data.memory_end = 2 * 1024 * 1024  # 2 MB

        assert self.data.get_memory_delta_mb() == pytest.approx(2.0, abs=0.01)

    def test_get_memory_peak_mb(self):
        """Test peak memory in MB."""
        self.data.memory_peak = 10 * 1024 * 1024  # 10 MB

        assert self.data.get_memory_peak_mb() == pytest.approx(10.0, abs=0.01)

    def test_psutil_metrics_when_unavailable(self):
        """Test psutil metrics when psutil not available."""
        self.data.has_psutil = False
        self.data.psutil_start = 1000
        self.data.psutil_end = 5000

        assert self.data.get_psutil_delta_mb() == 0.0
        assert self.data.get_psutil_peak_mb() == 0.0

    def test_psutil_metrics_when_available(self):
        """Test psutil metrics when available."""
        self.data.has_psutil = True
        self.data.psutil_start = 0
        self.data.psutil_end = 5 * 1024 * 1024  # 5 MB
        self.data.psutil_peak = 8 * 1024 * 1024  # 8 MB

        assert self.data.get_psutil_delta_mb() == pytest.approx(5.0, abs=0.01)
        assert self.data.get_psutil_peak_mb() == pytest.approx(8.0, abs=0.01)


class TestProfiler:
    """Test Profiler class."""

    def test_profiler_disabled_by_default(self):
        """Test profiler is disabled by default."""
        profiler = Profiler()
        assert profiler.enabled is False

    def test_profiler_can_be_enabled(self):
        """Test profiler can be enabled via constructor."""
        profiler = Profiler(enabled=True)
        assert profiler.enabled is True

    def test_profile_context_manager_disabled(self):
        """Test context manager has zero overhead when disabled."""
        profiler = Profiler(enabled=False)

        # Should execute quickly with no tracking
        with profiler.profile("test_op"):
            time.sleep(0.01)  # 10ms sleep

        # No data should be collected
        assert profiler.data.timings == {}

    def test_profile_context_manager_enabled(self):
        """Test context manager tracks timing when enabled."""
        profiler = Profiler(enabled=True)

        with profiler.profile("test_op"):
            time.sleep(0.01)  # 10ms sleep

        # Data should be collected
        assert "test_op" in profiler.data.timings
        assert len(profiler.data.timings["test_op"]) == 1
        # Should be approximately 10ms (allow ±5ms for system variance)
        assert 5.0 <= profiler.data.timings["test_op"][0] <= 20.0

    def test_profile_multiple_operations(self):
        """Test profiling multiple operations."""
        profiler = Profiler(enabled=True)

        with profiler.profile("op1"):
            time.sleep(0.01)

        with profiler.profile("op2"):
            time.sleep(0.02)

        with profiler.profile("op1"):  # Same operation again
            time.sleep(0.01)

        assert len(profiler.data.timings) == 2  # Two distinct operations
        assert len(profiler.data.timings["op1"]) == 2  # Called twice
        assert len(profiler.data.timings["op2"]) == 1  # Called once

    def test_profile_exception_handling(self):
        """Test profiler records time even when exception occurs."""
        profiler = Profiler(enabled=True)

        with pytest.raises(ValueError):
            with profiler.profile("failing_op"):
                time.sleep(0.01)
                raise ValueError("Test error")

        # Should still have recorded the timing
        assert "failing_op" in profiler.data.timings
        assert len(profiler.data.timings["failing_op"]) == 1

    def test_memory_tracking_disabled(self):
        """Test memory tracking when profiler disabled."""
        profiler = Profiler(enabled=False)

        profiler.start_memory_tracking()
        # Do some work
        _ = [i for i in range(1000)]
        profiler.stop_memory_tracking()

        # No tracking should occur
        assert profiler.data.memory_start == 0
        assert profiler.data.memory_peak == 0
        assert profiler.data.memory_end == 0

    def test_memory_tracking_enabled(self):
        """Test memory tracking when profiler enabled."""
        profiler = Profiler(enabled=True)

        profiler.start_memory_tracking()

        # Allocate some memory
        data = [i for i in range(10000)]  # noqa: F841

        profiler.stop_memory_tracking()

        # Should have tracked memory
        assert profiler.data.memory_start >= 0
        assert profiler.data.memory_peak > 0
        assert profiler.data.memory_end > 0
        # Peak should be >= end (monotonic)
        assert profiler.data.memory_peak >= profiler.data.memory_end

    def test_get_summary_structure(self):
        """Test summary dictionary structure."""
        profiler = Profiler(enabled=True)

        with profiler.profile("op1"):
            time.sleep(0.01)

        with profiler.profile("op2"):
            time.sleep(0.01)

        summary = profiler.get_summary()

        # Should have timing metrics for each operation
        assert "op1_total_ms" in summary
        assert "op1_count" in summary
        assert "op1_avg_ms" in summary
        assert "op2_total_ms" in summary
        assert "op2_count" in summary
        assert "op2_avg_ms" in summary

        # Should have overall metrics
        assert "total_profiled_ms" in summary
        assert "memory_peak_mb" in summary
        assert "memory_delta_mb" in summary

        # All values should be non-negative
        for key, value in summary.items():
            assert value >= 0, f"{key} should be non-negative"

    def test_get_summary_values(self):
        """Test summary values are correct."""
        profiler = Profiler(enabled=True)

        profiler.data.add_timing("op1", 10.0)
        profiler.data.add_timing("op1", 20.0)
        profiler.data.add_timing("op2", 30.0)

        summary = profiler.get_summary()

        assert summary["op1_total_ms"] == 30.0
        assert summary["op1_count"] == 2
        assert summary["op1_avg_ms"] == 15.0
        assert summary["op2_total_ms"] == 30.0
        assert summary["op2_count"] == 1
        assert summary["op2_avg_ms"] == 30.0
        assert summary["total_profiled_ms"] == 60.0

    def test_get_bottlenecks(self):
        """Test bottleneck identification."""
        profiler = Profiler(enabled=True)

        profiler.data.add_timing("fast_op", 5.0)  # 5% of total
        profiler.data.add_timing("slow_op", 60.0)  # 60% of total
        profiler.data.add_timing("medium_op", 35.0)  # 35% of total

        # Get operations > 10% of total time
        bottlenecks = profiler.get_bottlenecks(threshold_percent=10.0)

        assert len(bottlenecks) == 2  # slow_op and medium_op
        # Should be sorted by percentage descending
        assert bottlenecks[0][0] == "slow_op"
        assert bottlenecks[0][1] == pytest.approx(60.0, abs=0.1)
        assert bottlenecks[1][0] == "medium_op"
        assert bottlenecks[1][1] == pytest.approx(35.0, abs=0.1)

    def test_get_bottlenecks_custom_threshold(self):
        """Test bottleneck identification with custom threshold."""
        profiler = Profiler(enabled=True)

        profiler.data.add_timing("op1", 25.0)
        profiler.data.add_timing("op2", 75.0)

        # Higher threshold
        bottlenecks = profiler.get_bottlenecks(threshold_percent=50.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0][0] == "op2"

    def test_reset(self):
        """Test profiler reset."""
        profiler = Profiler(enabled=True)

        # Add some data
        profiler.data.add_timing("op1", 10.0)
        profiler.data.memory_start = 1000

        # Reset
        profiler.reset()

        # Should be clean
        assert profiler.data.timings == {}
        assert profiler.data.memory_start == 0

    def test_profiler_overhead_disabled(self):
        """Test overhead when profiler is disabled (should be ~0%)."""
        iterations = 1000

        # Time without profiler
        start = time.perf_counter()
        for _ in range(iterations):
            time.sleep(0.0001)  # 0.1ms per iteration
        baseline_time = time.perf_counter() - start

        # Time with disabled profiler
        profiler = Profiler(enabled=False)
        start = time.perf_counter()
        for _ in range(iterations):
            with profiler.profile("op"):
                time.sleep(0.0001)
        profiled_time = time.perf_counter() - start

        # Overhead should be < 1%
        overhead_pct = ((profiled_time - baseline_time) / baseline_time) * 100
        assert overhead_pct < 1.0, f"Overhead {overhead_pct:.2f}% exceeds 1%"

    def test_profiler_overhead_enabled(self):
        """Test overhead when profiler is enabled (should be < 5%)."""
        iterations = 1000

        # Time without profiler
        start = time.perf_counter()
        for _ in range(iterations):
            time.sleep(0.0001)  # 0.1ms per iteration
        baseline_time = time.perf_counter() - start

        # Time with enabled profiler
        profiler = Profiler(enabled=True)
        start = time.perf_counter()
        for _ in range(iterations):
            with profiler.profile("op"):
                time.sleep(0.0001)
        profiled_time = time.perf_counter() - start

        # Overhead should be < 5%
        overhead_pct = ((profiled_time - baseline_time) / baseline_time) * 100
        assert overhead_pct < 5.0, f"Overhead {overhead_pct:.2f}% exceeds 5%"

    def test_psutil_availability_check(self):
        """Test psutil availability is checked during initialization."""
        profiler = Profiler()

        # Should have checked for psutil (result depends on environment)
        assert isinstance(profiler.data.has_psutil, bool)

    def test_nested_profiling(self):
        """Test nested profiling operations."""
        profiler = Profiler(enabled=True)

        with profiler.profile("outer"):
            time.sleep(0.01)
            with profiler.profile("inner"):
                time.sleep(0.01)

        # Both should be tracked
        assert "outer" in profiler.data.timings
        assert "inner" in profiler.data.timings

        # Outer should take longer than inner
        outer_time = profiler.data.get_operation_total("outer")
        inner_time = profiler.data.get_operation_total("inner")
        assert outer_time > inner_time
