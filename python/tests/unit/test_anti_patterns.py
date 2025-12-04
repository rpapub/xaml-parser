"""Tests for anti-pattern detector (v0.2.10)."""

from cpmf_xaml_parser.anti_patterns import AntiPatternDetector
from cpmf_xaml_parser.models import Activity, WorkflowVariable


class TestAntiPatternDetector:
    """Test anti-pattern detector."""

    def setup_method(self):
        """Setup detector for each test."""
        self.detector = AntiPatternDetector()

    def test_empty_workflow(self):
        """Test detector with empty workflow."""
        patterns = self.detector.detect([], [])

        assert len(patterns) == 0

    def test_missing_error_handling(self):
        """Test detection of missing error handling."""
        activities = [
            Activity(activity_id="act1", activity_type="Sequence", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="Assign", workflow_id="wf1", depth=1),
        ]

        patterns = self.detector.detect(activities, [])

        # Should detect missing error handling
        missing_eh = [p for p in patterns if p.pattern_type == "missing_error_handling"]
        assert len(missing_eh) == 1
        assert missing_eh[0].severity == "warning"
        assert "no error handling" in missing_eh[0].message.lower()

    def test_has_error_handling(self):
        """Test workflow with error handling doesn't trigger warning."""
        activities = [
            Activity(activity_id="act1", activity_type="TryCatch", workflow_id="wf1", depth=0),
            Activity(activity_id="act2", activity_type="Assign", workflow_id="wf1", depth=1),
        ]

        patterns = self.detector.detect(activities, [])

        # Should not detect missing error handling
        missing_eh = [p for p in patterns if p.pattern_type == "missing_error_handling"]
        assert len(missing_eh) == 0

    def test_empty_catch_block(self):
        """Test detection of empty catch blocks."""
        activity = Activity(
            activity_id="act1",
            activity_type="TryCatch",
            workflow_id="wf1",
            depth=0,
        )
        # Empty catch block
        activity.properties = {"Catches": [None]}

        patterns = self.detector.detect([activity], [])

        empty_catch = [p for p in patterns if p.pattern_type == "empty_catch"]
        assert len(empty_catch) == 1
        assert empty_catch[0].severity == "error"
        assert "empty catch block" in empty_catch[0].message.lower()

    def test_catch_with_only_logging(self):
        """Test detection of catch block with only logging."""
        activity = Activity(
            activity_id="act1",
            activity_type="TryCatch",
            workflow_id="wf1",
            depth=0,
        )
        # Catch block with only LogMessage
        activity.properties = {"Catches": [{"activities": [{"type": "LogMessage", "id": "log1"}]}]}

        patterns = self.detector.detect([activity], [])

        empty_catch = [p for p in patterns if p.pattern_type == "empty_catch"]
        assert len(empty_catch) == 1
        assert "empty catch block" in empty_catch[0].message.lower()

    def test_hardcoded_windows_path(self):
        """Test detection of hardcoded Windows file path."""
        activity = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Value": "C:\\Users\\test\\file.txt"}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert hardcoded[0].severity == "warning"
        assert "windows file path" in hardcoded[0].message.lower()
        assert "Config" in hardcoded[0].suggestion

    def test_hardcoded_unix_path(self):
        """Test detection of hardcoded Unix file path."""
        activity = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Value": "/home/user/data.csv"}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert "unix file path" in hardcoded[0].message.lower()

    def test_hardcoded_url(self):
        """Test detection of hardcoded URL."""
        activity = Activity(
            activity_id="act1",
            activity_type="HttpRequest",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Url": "https://api.example.com/data"}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert hardcoded[0].severity == "info"
        assert "url" in hardcoded[0].message.lower()

    def test_hardcoded_credential(self):
        """Test detection of hardcoded credentials."""
        activity = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Value": 'password="secret123"'}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert hardcoded[0].severity == "error"
        assert "credential" in hardcoded[0].message.lower()

    def test_hardcoded_ip_address(self):
        """Test detection of hardcoded IP address."""
        activity = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Server": "192.168.1.100"}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert "ip address" in hardcoded[0].message.lower()

    def test_multiple_hardcoded_values(self):
        """Test detection of multiple hardcoded values."""
        act1 = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        act1.visible_attributes = {"Value": "C:\\data\\file.txt"}

        act2 = Activity(
            activity_id="act2",
            activity_type="HttpRequest",
            workflow_id="wf1",
            depth=0,
        )
        act2.visible_attributes = {"Url": "http://example.com"}

        patterns = self.detector.detect([act1, act2], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 2

    def test_unused_variable(self):
        """Test detection of unused variables."""
        variables = [
            WorkflowVariable(name="usedVar", type="String"),
            WorkflowVariable(name="unusedVar", type="String"),
        ]

        activities = [
            Activity(activity_id="act1", activity_type="Assign", workflow_id="wf1", depth=0)
        ]
        activities[0].variables_referenced = ["usedVar"]

        patterns = self.detector.detect(activities, variables)

        unused = [p for p in patterns if p.pattern_type == "unused_variable"]
        assert len(unused) == 1
        assert "unusedVar" in unused[0].message
        assert unused[0].severity == "info"

    def test_all_variables_used(self):
        """Test no unused variable detection when all are used."""
        variables = [
            WorkflowVariable(name="var1", type="String"),
            WorkflowVariable(name="var2", type="String"),
        ]

        activities = [
            Activity(activity_id="act1", activity_type="Assign", workflow_id="wf1", depth=0)
        ]
        activities[0].variables_referenced = ["var1", "var2"]

        patterns = self.detector.detect(activities, variables)

        unused = [p for p in patterns if p.pattern_type == "unused_variable"]
        assert len(unused) == 0

    def test_unreachable_code_after_throw(self):
        """Test detection of unreachable code after Throw."""
        activities = [
            Activity(
                activity_id="act1",
                activity_type="Sequence",
                workflow_id="wf1",
                depth=0,
            ),
            Activity(
                activity_id="act2",
                activity_type="Throw",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
            Activity(
                activity_id="act3",
                activity_type="Assign",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
        ]

        patterns = self.detector.detect(activities, [])

        unreachable = [p for p in patterns if p.pattern_type == "unreachable_code"]
        assert len(unreachable) == 1
        assert "unreachable" in unreachable[0].message.lower()
        assert unreachable[0].severity == "warning"

    def test_unreachable_code_after_terminate(self):
        """Test detection of unreachable code after TerminateWorkflow."""
        activities = [
            Activity(
                activity_id="act1",
                activity_type="Sequence",
                workflow_id="wf1",
                depth=0,
            ),
            Activity(
                activity_id="act2",
                activity_type="TerminateWorkflow",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
            Activity(
                activity_id="act3",
                activity_type="Assign",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
            Activity(
                activity_id="act4",
                activity_type="LogMessage",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
        ]

        patterns = self.detector.detect(activities, [])

        unreachable = [p for p in patterns if p.pattern_type == "unreachable_code"]
        assert len(unreachable) == 1
        assert "2 activities" in unreachable[0].message

    def test_no_unreachable_code_last_activity(self):
        """Test no unreachable code when Throw is last activity."""
        activities = [
            Activity(
                activity_id="act1",
                activity_type="Sequence",
                workflow_id="wf1",
                depth=0,
            ),
            Activity(
                activity_id="act2",
                activity_type="Assign",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
            Activity(
                activity_id="act3",
                activity_type="Throw",
                workflow_id="wf1",
                depth=1,
                parent_activity_id="act1",
            ),
        ]

        patterns = self.detector.detect(activities, [])

        unreachable = [p for p in patterns if p.pattern_type == "unreachable_code"]
        assert len(unreachable) == 0

    def test_complex_workflow_multiple_patterns(self):
        """Test detection of multiple anti-patterns in complex workflow."""
        # Create complex workflow with multiple issues
        activities = [
            Activity(
                activity_id="act1",
                activity_type="TryCatch",
                workflow_id="wf1",
                depth=0,
            ),
            Activity(
                activity_id="act2",
                activity_type="Assign",
                workflow_id="wf1",
                depth=1,
            ),
        ]
        activities[0].properties = {"Catches": [None]}  # Empty catch
        activities[1].visible_attributes = {"Value": "C:\\hardcoded\\path.txt"}  # Hardcoded path

        variables = [
            WorkflowVariable(name="unused", type="String"),
        ]

        patterns = self.detector.detect(activities, variables)

        # Should detect: empty_catch, hardcoded_value, unused_variable
        pattern_types = {p.pattern_type for p in patterns}
        assert "empty_catch" in pattern_types
        assert "hardcoded_value" in pattern_types
        assert "unused_variable" in pattern_types
        assert len(patterns) >= 3

    def test_pattern_suggestions_provided(self):
        """Test that patterns include helpful suggestions."""
        activity = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        activity.visible_attributes = {"Value": "C:\\test.txt"}

        patterns = self.detector.detect([activity], [])

        hardcoded = [p for p in patterns if p.pattern_type == "hardcoded_value"]
        assert len(hardcoded) == 1
        assert hardcoded[0].suggestion is not None
        assert len(hardcoded[0].suggestion) > 0

    def test_pattern_severity_levels(self):
        """Test that patterns have appropriate severity levels."""
        act1 = Activity(
            activity_id="act1",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        act1.visible_attributes = {"Value": 'password="secret"'}  # Error severity

        act2 = Activity(
            activity_id="act2",
            activity_type="Assign",
            workflow_id="wf1",
            depth=0,
        )
        act2.visible_attributes = {"Value": "C:\\test.txt"}  # Warning severity

        act3 = Activity(
            activity_id="act3",
            activity_type="HttpRequest",
            workflow_id="wf1",
            depth=0,
        )
        act3.visible_attributes = {"Url": "http://example.com"}  # Info severity

        patterns = self.detector.detect([act1, act2, act3], [])

        severities = {p.severity for p in patterns if p.pattern_type == "hardcoded_value"}
        assert "error" in severities
        assert "warning" in severities
        assert "info" in severities
