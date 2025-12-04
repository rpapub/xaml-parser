"""Tests for quality metrics calculator (v0.2.10)."""

from cpmf_xaml_parser.models import Activity, WorkflowVariable
from cpmf_xaml_parser.quality_metrics import QualityMetricsCalculator


class TestQualityMetricsCalculator:
    """Test quality metrics calculator."""

    def setup_method(self):
        """Setup calculator for each test."""
        self.calculator = QualityMetricsCalculator()

    def test_empty_workflow(self):
        """Test metrics for empty workflow."""
        metrics = self.calculator.calculate([], [], [])

        assert metrics.cyclomatic_complexity == 0
        assert metrics.cognitive_complexity == 0
        assert metrics.max_nesting_depth == 0
        assert metrics.total_activities == 0
        assert metrics.quality_score == 100.0  # Perfect score for empty workflow

    def test_cyclomatic_complexity_simple(self):
        """Test cyclomatic complexity for simple workflow."""
        activities = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="Assign", workflow_id="wf1", depth=1),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # No decision points, so complexity = 1
        assert metrics.cyclomatic_complexity == 1

    def test_cyclomatic_complexity_with_if(self):
        """Test cyclomatic complexity with If activity."""
        activities = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="Assign", workflow_id="wf1", depth=2),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # 1 decision point (If) + 1 = 2
        assert metrics.cyclomatic_complexity == 2

    def test_cyclomatic_complexity_multiple_decisions(self):
        """Test cyclomatic complexity with multiple decision points."""
        activities = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="Switch", workflow_id="wf1", depth=0),
            Activity(activity_id="act3", activity_type="While", workflow_id="wf1", depth=0),
            Activity(activity_id="act4", activity_type="ForEach", workflow_id="wf1", depth=0),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # 4 decision points + 1 = 5
        assert metrics.cyclomatic_complexity == 5

    def test_cognitive_complexity_flat(self):
        """Test cognitive complexity for flat workflow."""
        activities = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=0),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # 2 decision points at depth 0: 2 * (1 + 0) = 2
        assert metrics.cognitive_complexity == 2

    def test_cognitive_complexity_nested(self):
        """Test cognitive complexity with nesting."""
        activities = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="If", workflow_id="wf1", depth=2),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # Depth 0: 1 + 0 = 1
        # Depth 1: 1 + 1 = 2
        # Depth 2: 1 + 2 = 3
        # Total: 1 + 2 + 3 = 6
        assert metrics.cognitive_complexity == 6

    def test_max_nesting_depth(self):
        """Test maximum nesting depth calculation."""
        activities = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="While", workflow_id="wf1", depth=2),
            Activity(activity_id="act4", activity_type="Assign", workflow_id="wf1", depth=3),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        assert metrics.max_nesting_depth == 3

    def test_activity_count_by_type(self):
        """Test activity counting by type."""
        activities = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="While", workflow_id="wf1", depth=0),
            Activity(activity_id="act3", activity_type="Click", workflow_id="wf1", depth=0),
            Activity(activity_id="act4", activity_type="TypeInto", workflow_id="wf1", depth=0),
            Activity(activity_id="act5", activity_type="Assign", workflow_id="wf1", depth=0),
            Activity(activity_id="act6", activity_type="InvokeMethod", workflow_id="wf1", depth=0),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        assert metrics.total_activities == 6
        assert metrics.control_flow_activities == 2  # If, While
        assert metrics.ui_automation_activities == 2  # Click, TypeInto
        assert metrics.data_activities == 2  # Assign, InvokeMethod

    def test_variable_count(self):
        """Test variable counting."""
        variables = [
            WorkflowVariable(name="var1", type="String"),
            WorkflowVariable(name="var2", type="Int32"),
            WorkflowVariable(name="var3", type="Boolean"),
        ]

        metrics = self.calculator.calculate([], variables, [])

        assert metrics.total_variables == 3

    def test_expression_metrics(self):
        """Test expression metrics."""
        short_expr = "counter + 1"
        long_expr = "x" * 150  # 150 characters

        expressions = [short_expr, long_expr, short_expr]

        metrics = self.calculator.calculate([], [], expressions)

        assert metrics.total_expressions == 3
        assert metrics.complex_expressions == 1  # One expression > 100 chars

    def test_error_handling_detection(self):
        """Test error handling detection."""
        activities_with_try = [
            Activity(activity_id="act1", activity_type="TryCatch", workflow_id="wf1", depth=0)
        ]

        activities_without_try = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0)
        ]

        metrics_with = self.calculator.calculate(activities_with_try, [], [])
        metrics_without = self.calculator.calculate(activities_without_try, [], [])

        assert metrics_with.has_error_handling is True
        assert metrics_without.has_error_handling is False

    def test_quality_score_perfect(self):
        """Test quality score for perfect workflow."""
        activities = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="TryCatch", workflow_id="wf1", depth=0),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # Low complexity, has error handling
        assert metrics.quality_score > 95

    def test_quality_score_high_complexity(self):
        """Test quality score penalized for high complexity."""
        # Create workflow with high cyclomatic complexity
        activities = [
            Activity(activity_id=f"act{i}", activity_type="If", workflow_id="wf1", depth=0)
            for i in range(25)
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # High cyclomatic complexity (26) should reduce score
        assert metrics.cyclomatic_complexity > 20
        assert metrics.quality_score < 90

    def test_quality_score_high_nesting(self):
        """Test quality score penalized for deep nesting."""
        activities = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="If", workflow_id="wf1", depth=2),
            Activity(activity_id="act4", activity_type="If", workflow_id="wf1", depth=3),
            Activity(activity_id="act5", activity_type="If", workflow_id="wf1", depth=4),
            Activity(activity_id="act6", activity_type="If", workflow_id="wf1", depth=5),
        ]

        metrics = self.calculator.calculate(activities, [], [])

        # Deep nesting (6) should reduce score
        assert metrics.max_nesting_depth == 5
        assert metrics.quality_score < 90

    def test_quality_score_with_error_handling_bonus(self):
        """Test quality score bonus for error handling."""
        # Add nesting depth > 3 to trigger -5 penalty
        # Then error handling bonus (+10) should make a difference
        activities_with_try = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="If", workflow_id="wf1", depth=2),
            Activity(activity_id="act4", activity_type="If", workflow_id="wf1", depth=3),
            Activity(activity_id="act5", activity_type="Assign", workflow_id="wf1", depth=4),
            Activity(activity_id="act6", activity_type="TryCatch", workflow_id="wf1", depth=0),
        ]

        activities_without_try = [
            Activity(activity_id="act1", activity_type="If", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="If", workflow_id="wf1", depth=1),
            Activity(activity_id="act3", activity_type="If", workflow_id="wf1", depth=2),
            Activity(activity_id="act4", activity_type="If", workflow_id="wf1", depth=3),
            Activity(activity_id="act5", activity_type="Assign", workflow_id="wf1", depth=4),
            Activity(activity_id="act6", activity_type="Sequence", workflow_id="wf1", depth=0),
        ]

        metrics_with = self.calculator.calculate(activities_with_try, [], [])
        metrics_without = self.calculator.calculate(activities_without_try, [], [])

        # With error handling: 100 - 5 (nesting > 3) + 10 (error handling) = 105 -> capped at 100
        # Without error handling: 100 - 5 (nesting > 3) = 95
        # Since with error handling gets capped, we should instead verify the score difference exists
        # Actually: with TryCatch should have higher score due to +10 bonus
        assert metrics_with.quality_score > metrics_without.quality_score

    def test_quality_score_bounds(self):
        """Test quality score stays within 0-100 bounds."""
        # Create workflow with many issues
        activities = [
            Activity(activity_id=f"act{i}", activity_type="If", workflow_id="wf1", depth=i)
            for i in range(50)
        ]

        metrics = self.calculator.calculate(activities, [], [])
        metrics.empty_catch_blocks = 10
        metrics.hardcoded_strings = 20
        metrics.unreachable_activities = 5
        metrics.unused_variables = 30

        # Recalculate score with penalties
        score = self.calculator._calculate_quality_score(metrics)

        assert 0.0 <= score <= 100.0
