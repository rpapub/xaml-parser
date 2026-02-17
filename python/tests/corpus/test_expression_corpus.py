"""Corpus tests for expression parser.

These tests validate the expression parser on real-world UiPath workflows
to ensure >80% success rate on production code.
"""

import pytest

from cpmf_uips_xaml.stages.parsing.expression_parser import ExpressionParser
from cpmf_uips_xaml.stages.assemble.project import ProjectParser


@pytest.mark.corpus
def test_expression_parser_corpus_success_rate(core_projects):
    """Expression parser should successfully parse >80% of real-world expressions."""
    vb_parser = ExpressionParser("VisualBasic")
    cs_parser = ExpressionParser("CSharp")

    total_expressions = 0
    successful_parses = 0
    failed_expressions = []

    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path, recursive=True)

        for wf in result.workflows:
            if not wf.parse_result.success:
                continue

            # Detect expression language
            language = wf.parse_result.content.expression_language or "VisualBasic"
            expr_parser = vb_parser if language == "VisualBasic" else cs_parser

            # Extract expressions from activities
            for activity in wf.parse_result.content.activities:
                # Check visible attributes for expressions
                for _key, value in activity.visible_attributes.items():
                    if isinstance(value, str) and _is_expression(value):
                        total_expressions += 1
                        parsed = expr_parser.parse(value)

                        if parsed.is_valid and len(parsed.variables) > 0:
                            successful_parses += 1
                        elif parsed.is_valid:
                            # Valid parse but no variables found (e.g., literals)
                            successful_parses += 1
                        else:
                            failed_expressions.append(
                                {
                                    "workflow": wf.relative_path,
                                    "activity": activity.activity_type,
                                    "expression": value[:100],  # Truncate for readability
                                    "error": parsed.parse_errors,
                                }
                            )

    # Calculate success rate
    success_rate = (successful_parses / total_expressions * 100) if total_expressions > 0 else 0

    # Report statistics
    print("\n[INFO] Expression Parser Corpus Test Results:")
    print(f"  Total expressions: {total_expressions}")
    print(f"  Successful parses: {successful_parses}")
    print(f"  Failed parses: {len(failed_expressions)}")
    print(f"  Success rate: {success_rate:.2f}%")

    if failed_expressions and len(failed_expressions) <= 10:
        print("\n[INFO] Failed expressions sample:")
        for i, fail in enumerate(failed_expressions[:10], 1):
            print(f"  {i}. {fail['workflow']} - {fail['activity']}")
            print(f"     Expression: {fail['expression']}")

    # Verify success rate meets threshold
    assert success_rate >= 80.0, (
        f"Expression parser success rate {success_rate:.2f}% is below 80% threshold. "
        f"Failed {len(failed_expressions)} out of {total_expressions} expressions."
    )


@pytest.mark.corpus
def test_expression_parser_variable_extraction_accuracy(core_projects):
    """Verify variable extraction accuracy on corpus expressions."""
    vb_parser = ExpressionParser("VisualBasic")

    extracted_vars = []
    activities_checked = 0

    for project_path in core_projects[:2]:  # Check first 2 CORE projects
        parser = ProjectParser()
        result = parser.parse_project(project_path, recursive=True)

        for wf in result.workflows[:5]:  # Check first 5 workflows per project
            if not wf.parse_result.success:
                continue

            for activity in wf.parse_result.content.activities[:10]:  # First 10 activities
                activities_checked += 1

                # Check all visible attributes for expressions
                for _key, value in activity.visible_attributes.items():
                    if value and isinstance(value, str) and _is_expression(value):
                        parsed = vb_parser.parse(value)

                        if parsed.is_valid:
                            for var in parsed.variables:
                                extracted_vars.append(
                                    {
                                        "name": var.name,
                                        "access_type": var.access_type,
                                        "expression": value[:50],
                                    }
                                )

    print("\n[INFO] Variable Extraction Results:")
    print(f"  Activities checked: {activities_checked}")
    print(f"  Variables extracted: {len(extracted_vars)}")

    if extracted_vars:
        # Sample output
        print("\n[INFO] Sample extracted variables:")
        for var in extracted_vars[:10]:
            print(f"  - {var['name']} ({var['access_type']}) from: {var['expression']}")

    # Should extract at least some variables if we checked enough activities
    # This is a best-effort test - corpus may not have many Assign activities
    if activities_checked > 50:
        assert (
            len(extracted_vars) > 0
        ), f"No variables extracted after checking {activities_checked} activities"
    else:
        print(f"[SKIP] Not enough activities found ({activities_checked}) to validate extraction")


@pytest.mark.corpus
def test_expression_parser_method_extraction_accuracy(core_projects):
    """Verify method call extraction accuracy on corpus expressions."""
    vb_parser = ExpressionParser("VisualBasic")

    extracted_methods = []
    activities_checked = 0

    for project_path in core_projects[:2]:  # Check first 2 CORE projects
        parser = ProjectParser()
        result = parser.parse_project(project_path, recursive=True)

        for wf in result.workflows[:5]:  # Check first 5 workflows per project
            if not wf.parse_result.success:
                continue

            for activity in wf.parse_result.content.activities[:10]:  # First 10 activities
                activities_checked += 1

                # Check all visible attributes for method calls
                for _key, value in activity.visible_attributes.items():
                    if value and isinstance(value, str) and _is_expression(value) and "(" in value:
                        parsed = vb_parser.parse(value)

                        if parsed.is_valid:
                            for method in parsed.methods:
                                extracted_methods.append(
                                    {
                                        "method": method.method_name,
                                        "qualifier": method.qualifier,
                                        "is_static": method.is_static,
                                        "expression": value[:50],
                                    }
                                )

    print("\n[INFO] Method Extraction Results:")
    print(f"  Activities checked: {activities_checked}")
    print(f"  Methods extracted: {len(extracted_methods)}")

    if extracted_methods:
        # Sample output
        print("\n[INFO] Sample extracted methods:")
        for method in extracted_methods[:10]:
            qualifier_str = f"{method['qualifier']}." if method["qualifier"] else ""
            static_str = " (static)" if method["is_static"] else ""
            print(f"  - {qualifier_str}{method['method']}{static_str} from: {method['expression']}")

    # Should extract at least some methods
    assert len(extracted_methods) > 0, "No methods extracted from corpus"


@pytest.mark.corpus
def test_expression_parser_handles_complex_expressions(core_projects):
    """Verify parser handles complex nested expressions without crashing."""
    vb_parser = ExpressionParser("VisualBasic")
    cs_parser = ExpressionParser("CSharp")

    crashed_expressions = []
    parsed_count = 0

    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path, recursive=True)

        for wf in result.workflows:
            if not wf.parse_result.success:
                continue

            language = wf.parse_result.content.expression_language or "VisualBasic"
            expr_parser = vb_parser if language == "VisualBasic" else cs_parser

            for activity in wf.parse_result.content.activities:
                for _key, value in activity.visible_attributes.items():
                    if isinstance(value, str) and _is_expression(value) and len(value) > 100:
                        # Test complex/long expressions
                        try:
                            parsed = expr_parser.parse(value)
                            parsed_count += 1

                            # Should not crash
                            assert parsed is not None
                        except Exception as e:
                            crashed_expressions.append(
                                {
                                    "workflow": wf.relative_path,
                                    "expression": value[:100],
                                    "error": str(e),
                                }
                            )

    print("\n[INFO] Complex Expression Handling:")
    print(f"  Complex expressions parsed: {parsed_count}")
    print(f"  Crashes: {len(crashed_expressions)}")

    # Should not crash on any expression
    assert (
        len(crashed_expressions) == 0
    ), f"Parser crashed on {len(crashed_expressions)} expressions"


@pytest.mark.corpus
def test_expression_parser_read_write_detection(core_projects):
    """Verify read/write detection works on real assignments."""
    vb_parser = ExpressionParser("VisualBasic")

    assignments_found = 0
    correct_detections = 0

    for project_path in core_projects[:2]:
        parser = ProjectParser()
        result = parser.parse_project(project_path, recursive=True)

        for wf in result.workflows[:5]:
            if not wf.parse_result.success:
                continue

            for activity in wf.parse_result.content.activities:
                # Look for Assign activities
                if activity.activity_type == "Assign":
                    value = activity.visible_attributes.get("Value")
                    if value and isinstance(value, str) and "=" in value:
                        parsed = vb_parser.parse(value)

                        if parsed.is_valid and len(parsed.variables) >= 2:
                            assignments_found += 1

                            # Check if we detected write on LHS and read on RHS
                            write_vars = [v for v in parsed.variables if v.access_type == "write"]
                            read_vars = [v for v in parsed.variables if v.access_type == "read"]

                            if len(write_vars) >= 1 and len(read_vars) >= 1:
                                correct_detections += 1

    print("\n[INFO] Read/Write Detection:")
    print(f"  Assignment expressions found: {assignments_found}")
    print(f"  Correct read/write detections: {correct_detections}")

    if assignments_found > 0:
        accuracy = correct_detections / assignments_found * 100
        print(f"  Detection accuracy: {accuracy:.2f}%")

        # Should have reasonable accuracy
        assert accuracy >= 50.0, f"Read/write detection accuracy too low: {accuracy:.2f}%"


def _is_expression(text: str) -> bool:
    """Check if text appears to be an expression (not just a literal)."""
    if not text or len(text.strip()) < 2:
        return False

    # Common expression patterns
    expression_indicators = [
        "[",  # VB.NET bracket variables
        ".",  # Member access
        "(",  # Method calls
        "+",  # Operators
        "=",  # Assignment/comparison
        "AndAlso",
        "OrElse",
    ]

    return any(indicator in text for indicator in expression_indicators)
