"""Core XAML parser for workflow automation projects.

This module provides the main XamlParser class that extracts complete
workflow metadata from XAML files using only Python stdlib.

Platform-agnostic: Uses XamlDialect for platform-specific constants.
"""

import html
import logging
import time
from dataclasses import dataclass, field

# Use secure XML parsing
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

try:
    from defusedxml.ElementTree import fromstring as defused_fromstring
except ImportError:
    # Fallback to standard library if defusedxml not available
    from xml.etree.ElementTree import fromstring as defused_fromstring

from .extractors import MetadataExtractor
from ..normalize.id_generation import IdGenerator
from ...shared.model.models import (
    Activity,
    Expression,
    ParseDiagnostic,
    ParseDiagnostics,
    ParseResult,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)
from ...profiling import Profiler
from ...shared.model.validation import validate_output

logger = logging.getLogger(__name__)


@dataclass
class XamlDialect:
    """Platform-specific constants for XAML parsing.

    Generic parser accepts this config to support multiple automation platforms.
    """

    # Namespace configuration
    standard_namespaces: dict[str, str] = field(default_factory=dict)
    platform_namespace: str = ""

    # Platform-specific utilities (injected, not imported)
    activity_utils: Any = None

    # Activity classification
    core_visual_activities: set[str] = field(default_factory=set)
    skip_elements: set[str] = field(default_factory=set)

    # Argument parsing
    argument_directions: dict[str, str] = field(default_factory=dict)

    # Attribute categorization
    invisible_attribute_patterns: list[str] = field(default_factory=list)
    viewstate_properties: set[str] = field(default_factory=set)

    # Expression detection
    expression_patterns: list[str] = field(default_factory=list)

    # Parser defaults
    default_parser_config: dict[str, Any] = field(default_factory=dict)


class XamlParser:
    """Complete XAML workflow parser for automation projects.

    Extracts all workflow metadata including arguments, variables, activities,
    annotations, and expressions from XAML workflow files.

    Platform-agnostic: Requires XamlDialect for platform-specific constants.
    """

    def __init__(
        self, platform_config: XamlDialect, config: dict[str, Any] | None = None
    ) -> None:
        """Initialize parser with platform and parser configuration.

        Args:
            platform_config: Platform-specific constants (namespaces, activities, etc.)
            config: Parser configuration dict, uses platform defaults if None
        """
        self.platform = platform_config
        default_config = platform_config.default_parser_config or {}
        self.config = {**default_config, **(config or {})}
        self._id_generator = IdGenerator()
        self._diagnostics: ParseDiagnostics = (
            ParseDiagnostics()
        )  # Re-initialized per parse operation
        self._workflow_xml_content = ""  # Store original XML for workflow ID generation

        # Initialize profiler (v0.2.11)
        self.profiler = Profiler(enabled=self.config.get("enable_profiling", False))

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse XAML workflow file.

        Args:
            file_path: Path to XAML file

        Returns:
            ParseResult with extracted content or error information
        """
        start_time = time.time()
        result = ParseResult(file_path=str(file_path), config_used=self.config.copy())

        # Initialize diagnostics
        self._diagnostics = ParseDiagnostics()
        self._diagnostics.processing_steps.append("parse_file_started")

        # Start memory tracking (v0.2.11)
        if self.profiler.enabled:
            self.profiler.start_memory_tracking()

        try:
            # Read file and collect diagnostics
            with self.profiler.profile("file_read"):
                file_size = file_path.stat().st_size
                logger.info("Parsing file: %s (size: %d bytes)", file_path.name, file_size)
                self._diagnostics.file_size_bytes = file_size
                self._diagnostics.processing_steps.append("file_read")

                # Read and parse XAML with encoding detection
                content, encoding_used = self._read_file_with_encoding(file_path)
                self._workflow_xml_content = content  # Store for workflow ID generation
                self._diagnostics.encoding_detected = encoding_used

            # Parse XML
            with self.profiler.profile("xml_parse"):
                parse_start = time.time()
                root = defused_fromstring(content)
                self._diagnostics.performance_metrics["xml_parse_ms"] = (
                    time.time() - parse_start
                ) * 1000
                self._diagnostics.root_element_tag = root.tag
                self._diagnostics.processing_steps.append("xml_parsed")

            # Extract all workflow content
            with self.profiler.profile("content_extract_total"):
                extract_start = time.time()
                workflow_content = self._extract_workflow_content(root, str(file_path))
                self._diagnostics.performance_metrics["content_extract_ms"] = (
                    time.time() - extract_start
                ) * 1000

            result.content = workflow_content
            self._diagnostics.processing_steps.append("content_extracted")

            # Store raw XML and content hash for stable ID generation
            result.raw_xml = content
            result.content_hash = self._id_generator.compute_full_hash(content)

            logger.info(
                "Successfully parsed %s: %d activities, %d arguments, %d variables",
                file_path.name,
                len(workflow_content.activities),
                len(workflow_content.arguments),
                len(workflow_content.variables),
            )

        except ET.ParseError as e:
            result.success = False
            # Extract line/column info from parse error
            line = getattr(e, "lineno", None)
            column = getattr(e, "offset", None)

            # Create structured diagnostic
            diagnostic = ParseDiagnostic(
                level="error",
                message=f"XML parse error: {str(e)}",
                line=line,
                column=column,
                suggestion="Check for unclosed tags, mismatched brackets, or invalid XML syntax",
            )
            self._diagnostics.messages.append(diagnostic)
            result.errors.append(str(diagnostic))
            logger.error("XML parse error in %s: %s", file_path, e)
            self._diagnostics.processing_steps.append("xml_parse_failed")
        except UnicodeDecodeError as e:
            result.success = False
            diagnostic = ParseDiagnostic(
                level="error",
                message=f"Encoding error: {str(e)}",
                suggestion="File may be in a different encoding. Common encodings: UTF-8, UTF-16, ISO-8859-1",
            )
            self._diagnostics.messages.append(diagnostic)
            result.errors.append(str(diagnostic))
            logger.error("Encoding error in %s: %s", file_path, e)
            self._diagnostics.processing_steps.append("encoding_error")
        except (FileNotFoundError, PermissionError, OSError) as e:
            result.success = False
            diagnostic = ParseDiagnostic(
                level="error",
                message=f"File access error: {str(e)}",
                suggestion="Check file path exists and you have read permissions",
            )
            self._diagnostics.messages.append(diagnostic)
            result.errors.append(str(diagnostic))
            logger.error("File access error in %s: %s", file_path, e)
            self._diagnostics.processing_steps.append("file_access_error")
        except Exception as e:
            # Broad catch for any other errors (AttributeError, ValueError, etc.)
            # This is intentionally broad as a last-resort handler for parse_file()
            # Note: KeyboardInterrupt and SystemExit inherit from BaseException, not Exception,
            # so they will NOT be caught here and will propagate correctly
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            logger.exception("Unexpected error parsing %s", file_path)
            self._diagnostics.processing_steps.append("unexpected_error")
        finally:
            # Stop memory tracking and merge profiler data (v0.2.11)
            if self.profiler.enabled:
                self.profiler.stop_memory_tracking()
                self._diagnostics.performance_metrics.update(self.profiler.get_summary())

        result.parse_time_ms = (time.time() - start_time) * 1000
        result.diagnostics = self._diagnostics

        logger.debug("Parse completed for %s in %.2fms", file_path.name, result.parse_time_ms)

        # Validate output if in strict mode
        if self.config.get("strict_mode", False):
            try:
                validation_errors = validate_output(result, strict=False)
                if validation_errors:
                    result.warnings.extend([f"Validation: {err}" for err in validation_errors])
                    self._diagnostics.processing_steps.append("validation_warnings_added")
            except Exception as e:
                result.warnings.append(f"Validation failed: {str(e)}")

        return result

    def parse_content(self, xml_content: str, file_path: str = "<string>") -> ParseResult:
        """Parse XAML content from string.

        Args:
            xml_content: Raw XAML content
            file_path: Virtual file path for error reporting

        Returns:
            ParseResult with extracted content or error information
        """
        start_time = time.time()
        result = ParseResult(file_path=file_path, config_used=self.config.copy())

        # Initialize diagnostics
        self._diagnostics = ParseDiagnostics()
        self._diagnostics.processing_steps.append("parse_content_started")

        logger.debug("Parsing content from string (length: %d chars)", len(xml_content))

        try:
            # Store XML content for workflow ID generation
            self._workflow_xml_content = xml_content

            # Parse XAML securely with defusedxml
            parse_start = time.time()
            root = defused_fromstring(xml_content)
            self._diagnostics.performance_metrics["xml_parse_ms"] = (
                time.time() - parse_start
            ) * 1000
            self._diagnostics.root_element_tag = root.tag
            self._diagnostics.processing_steps.append("xml_parsed")

            # Extract workflow content
            extract_start = time.time()
            workflow_content = self._extract_workflow_content(root, file_path)
            self._diagnostics.performance_metrics["content_extract_ms"] = (
                time.time() - extract_start
            ) * 1000

            result.content = workflow_content
            self._diagnostics.processing_steps.append("content_extracted")

            # Store raw XML and content hash for stable ID generation
            result.raw_xml = xml_content
            result.content_hash = self._id_generator.compute_full_hash(xml_content)

        except ET.ParseError as e:
            result.success = False
            result.errors.append(f"XML parse error: {e}")
            self._diagnostics.processing_steps.append("xml_parse_failed")
        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            self._diagnostics.processing_steps.append("unexpected_error")

        result.parse_time_ms = (time.time() - start_time) * 1000
        result.diagnostics = self._diagnostics

        # Validate output if in strict mode
        if self.config.get("strict_mode", False):
            try:
                validation_errors = validate_output(result, strict=False)
                if validation_errors:
                    result.warnings.extend([f"Validation: {err}" for err in validation_errors])
                    self._diagnostics.processing_steps.append("validation_warnings_added")
            except Exception as e:
                result.warnings.append(f"Validation failed: {str(e)}")

        return result

    def _extract_workflow_content(self, root: ET.Element, file_path: str) -> WorkflowContent:
        """Extract complete workflow content from XML root.

        Args:
            root: XML root element
            file_path: Source file path

        Returns:
            WorkflowContent with all extracted metadata
        """
        content = WorkflowContent()

        # Generate stable workflow ID from complete XML content
        workflow_id = self._id_generator.generate_workflow_id(self._workflow_xml_content)

        # Count total elements for diagnostics
        total_elements = sum(1 for _ in root.iter())
        self._diagnostics.total_elements_processed = total_elements

        # Calculate XML depth
        max_depth = 0

        def get_depth(elem: ET.Element, depth: int = 0) -> None:
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in elem:
                get_depth(child, depth + 1)

        get_depth(root)
        self._diagnostics.xml_depth = max_depth

        # Extract namespaces (xmlns declarations)
        with self.profiler.profile("namespace_extract"):
            content.namespaces = self._extract_namespaces(root)
            content.xmlns_declarations = content.namespaces.copy()  # Alias
            self._diagnostics.namespaces_detected = len(content.namespaces)
            self._diagnostics.processing_steps.append("namespaces_extracted")

        # Extract XAML class name (x:Class attribute)
        with self.profiler.profile("xaml_class_extract"):
            content.xaml_class = self._extract_xaml_class(root, content.namespaces)
            self._diagnostics.processing_steps.append("xaml_class_extracted")

        # Extract imported .NET namespaces (TextExpression.NamespacesForImplementation)
        with self.profiler.profile("imported_ns_extract"):
            content.imported_namespaces = self._extract_imported_namespaces(root)
            self._diagnostics.processing_steps.append("imported_namespaces_extracted")

        # Extract assembly references (TextExpression.ReferencesForImplementation)
        if self.config["extract_assembly_references"]:
            with self.profiler.profile("assembly_refs_extract"):
                content.assembly_references = self._extract_assembly_references(root)
                self._diagnostics.processing_steps.append("assembly_references_extracted")

        # Extract expression language (VisualBasic or CSharp)
        with self.profiler.profile("expr_lang_detect"):
            content.expression_language = self._extract_expression_language(root)
            self._diagnostics.processing_steps.append("expression_language_extracted")

        # Extract arguments from x:Members
        if self.config["extract_arguments"]:
            with self.profiler.profile("arguments_extract"):
                content.arguments = self._extract_arguments(root, content.namespaces)
                self._diagnostics.arguments_found = len(content.arguments)
                self._diagnostics.processing_steps.append("arguments_extracted")

        # Extract variables from all scopes
        if self.config["extract_variables"]:
            with self.profiler.profile("variables_extract"):
                content.variables = self._extract_variables(root, content.namespaces)
                self._diagnostics.variables_found = len(content.variables)
                self._diagnostics.processing_steps.append("variables_extracted")

        # Extract activities with complete metadata
        if self.config["extract_activities"]:
            with self.profiler.profile("activities_extract"):
                content.activities = self._extract_activities(root, content.namespaces, workflow_id)
                self._diagnostics.activities_found = len(content.activities)
                # Count activities with annotations
                self._diagnostics.annotations_found = sum(
                    1 for a in content.activities if a.annotation
                )
                # Count expressions
                self._diagnostics.expressions_found = sum(
                    len(a.expressions) for a in content.activities
                )
                self._diagnostics.processing_steps.append("activities_extracted")

        # Extract root annotation
        with self.profiler.profile("root_annotation_extract"):
            content.root_annotation = self._extract_root_annotation(root, content.namespaces)
            if content.root_annotation:
                self._diagnostics.annotations_found += 1
            self._diagnostics.processing_steps.append("root_annotation_extracted")

        # Calculate statistics
        content.total_activities = len(content.activities)
        content.total_arguments = len(content.arguments)
        content.total_variables = len(content.variables)

        return content

    def _extract_namespaces(self, root: ET.Element) -> dict[str, str]:
        """Extract all XML namespaces from root element."""
        namespaces = {}

        # Get namespaces from root attributes
        for key, value in root.attrib.items():
            if key.startswith("xmlns:"):
                prefix = key[6:]  # Remove 'xmlns:' prefix
                namespaces[prefix] = value
            elif key == "xmlns":
                namespaces[""] = value  # Default namespace

        # Merge with standard namespaces
        return {**self.platform.standard_namespaces, **namespaces}

    def _extract_arguments(
        self, root: ET.Element, namespaces: dict[str, str]
    ) -> list[WorkflowArgument]:
        """Extract workflow arguments from x:Members section."""
        arguments: list[WorkflowArgument] = []

        # Find x:Members element
        x_ns = namespaces.get("x", "")
        if not x_ns:
            return arguments

        members = root.find(f"{{{x_ns}}}Members")
        if members is None:
            return arguments

        # Extract each x:Property (argument definition)
        sap2010_ns = namespaces.get("sap2010", "")
        for prop in members.findall(f"{{{x_ns}}}Property"):
            name = prop.get("Name")
            type_attr = prop.get("Type", "")

            if not name:
                continue

            # Parse direction from type (InArgument, OutArgument, InOutArgument)
            direction = "in"  # Default
            for type_prefix, dir_value in self.platform.argument_directions.items():
                if type_prefix in type_attr:
                    direction = dir_value
                    break

            # Extract annotation
            annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText" if sap2010_ns else None
            annotation = None
            if annotation_attr:
                annotation = prop.get(annotation_attr)
                if annotation:
                    annotation = html.unescape(annotation)  # Decode HTML entities

            # Extract default value (check both lowercase and capitalized)
            default_value = prop.get("default") or prop.get("Default") or prop.text

            argument = WorkflowArgument(
                name=name,
                type=type_attr,
                direction=direction,
                annotation=annotation,
                default_value=default_value,
            )
            arguments.append(argument)

        return arguments

    def _extract_variables(
        self, root: ET.Element, namespaces: dict[str, str]
    ) -> list[WorkflowVariable]:
        """Extract all variables from workflow scopes."""
        variables = []

        # Find all Variable elements throughout the tree
        for elem in root.iter():
            if elem.tag.endswith("Variable") or "Variable" in elem.tag:
                name = elem.get("Name")
                type_attr = elem.get("Type", "Object")
                default_value = elem.get("Default") or elem.text

                if name:
                    # Determine scope from parent context
                    scope = self._determine_variable_scope(elem)

                    variable = WorkflowVariable(
                        name=name, type=type_attr, default_value=default_value, scope=scope
                    )
                    variables.append(variable)

        return variables

    def _extract_activities(
        self, root: ET.Element, namespaces: dict[str, str], workflow_id: str
    ) -> list[Activity]:
        """Extract all activities with complete metadata."""
        activities = []
        sap2010_ns = namespaces.get("sap2010", "")

        def process_element(elem: ET.Element, parent_id: str | None = None, depth: int = 0) -> None:
            """Recursively process elements to find activities."""
            tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Skip non-activity elements
            if tag_name in self.platform.skip_elements:
                # Still process children for nested activities
                for child in elem:
                    process_element(child, parent_id, depth)
                return

            # Check if this is an activity (either in whitelist or has activity-like attributes)
            is_activity = (
                tag_name in self.platform.core_visual_activities
                or elem.get("DisplayName") is not None
                or any(attr.endswith("Annotation.AnnotationText") for attr in elem.attrib)
                or self._looks_like_activity(elem, tag_name)
            )

            if is_activity:
                # Capture XML span for stable ID generation
                xml_span = ET.tostring(elem, encoding="unicode")

                # Generate stable activity ID from XML span
                activity_id = self._id_generator.generate_activity_id(xml_span)

                # Extract namespace information from tag
                activity_type_full, activity_type_short, activity_ns, activity_prefix = (
                    self._extract_type_info(elem, namespaces)
                )

                # Extract all attributes
                visible_attrs, invisible_attrs = self._categorize_attributes(elem.attrib)

                # Extract annotation
                annotation = None
                if sap2010_ns:
                    annotation_key = f"{{{sap2010_ns}}}Annotation.AnnotationText"
                    annotation = elem.get(annotation_key)
                    if annotation:
                        annotation = html.unescape(annotation)

                # Extract expressions from this activity
                expressions = []
                if self.config["extract_expressions"]:
                    expressions = self._extract_expressions_from_element(elem)

                # Extract activity-scoped variables
                activity_variables = []
                for child in elem:
                    if child.tag.endswith("Variable"):
                        var_name = child.get("Name")
                        if var_name:
                            activity_variables.append(
                                WorkflowVariable(
                                    name=var_name,
                                    type=child.get("Type", "Object"),
                                    default_value=child.get("Default"),
                                    scope=activity_id,
                                )
                            )

                # Create activity content
                activity = Activity(
                    activity_id=activity_id,
                    workflow_id=workflow_id,
                    activity_type=activity_type_full,  # Full type with namespace
                    activity_type_short=activity_type_short,  # Short local name
                    activity_namespace=activity_ns,  # Namespace URI
                    activity_prefix=activity_prefix,  # Namespace prefix
                    display_name=elem.get("DisplayName"),
                    node_id=activity_id,  # Use activity_id as node_id
                    parent_activity_id=parent_id,
                    depth=depth,
                    arguments=visible_attrs,  # Map visible attributes to arguments
                    configuration=self._extract_configuration(elem),
                    properties=visible_attrs,  # Map to properties
                    metadata=invisible_attrs,  # Map to metadata
                    expressions=[expr.content for expr in expressions] if expressions else [],
                    variables_referenced=[],  # Extract separately
                    selectors={},  # Extract separately
                    annotation=annotation,
                    is_visible=True,  # Default to visible
                    container_type=None,  # Will be determined by hierarchy
                    visible_attributes=visible_attrs,
                    invisible_attributes=invisible_attrs,
                    variables=activity_variables,
                    expression_objects=expressions,
                    xml_span=xml_span,  # Store XML span for stable ID generation
                )

                activities.append(activity)

                # Process children with this activity as parent
                for child in elem:
                    process_element(child, activity_id, depth + 1)

                # Update parent-child relationships
                if parent_id:
                    for parent_activity in activities:
                        if parent_activity.activity_id == parent_id:
                            parent_activity.child_activities.append(activity_id)
                            break
            else:
                # Not an activity, but process children
                for child in elem:
                    process_element(child, parent_id, depth)

        # Start processing from root
        process_element(root)
        return activities

    def _extract_root_annotation(self, root: ET.Element, namespaces: dict[str, str]) -> str | None:
        """Extract root workflow annotation."""
        sap2010_ns = namespaces.get("sap2010", "")
        if not sap2010_ns:
            return None

        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"

        # Try root element first
        annotation = root.get(annotation_attr)
        if annotation:
            return html.unescape(annotation)

        # Fallback: find first Sequence with annotation
        for elem in root.iter():
            if elem.tag.endswith("Sequence"):
                annotation = elem.get(annotation_attr)
                if annotation:
                    return html.unescape(annotation)

        return None

    def _read_file_with_encoding(self, file_path: Path) -> tuple[str, str]:
        """Read file content with encoding detection.

        Tries multiple encodings in order: UTF-8, UTF-8 with BOM, UTF-16,
        ISO-8859-1, Windows-1252. Falls back to UTF-8 with error replacement.

        Args:
            file_path: Path to file to read

        Returns:
            Tuple of (content, encoding_used)
        """
        encodings = ["utf-8", "utf-8-sig", "utf-16", "iso-8859-1", "cp1252"]

        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                logger.debug("Successfully read file with encoding: %s", encoding)
                return content, encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Last resort: read as binary, replace errors
        logger.warning(
            "Unable to decode %s with standard encodings, using UTF-8 with error replacement",
            file_path.name,
        )
        content = file_path.read_bytes().decode("utf-8", errors="replace")
        return content, "utf-8-fallback"

    def _extract_xaml_class(self, root: ET.Element, namespaces: dict[str, str]) -> str | None:
        """Extract x:Class attribute from root Activity element."""
        return MetadataExtractor.extract_xaml_class(root, namespaces)

    def _extract_imported_namespaces(self, root: ET.Element) -> list[str]:
        """Extract .NET namespaces from TextExpression.NamespacesForImplementation."""
        return MetadataExtractor.extract_imported_namespaces(root)

    def _extract_assembly_references(self, root: ET.Element) -> list[str]:
        """Extract assembly references from TextExpression.ReferencesForImplementation."""
        return MetadataExtractor.extract_assembly_references(root)

    def _extract_expression_language(self, root: ET.Element) -> str | None:
        """Extract expression language (VisualBasic or CSharp) from workflow XAML."""
        return MetadataExtractor.extract_expression_language(root)

    def _extract_type_info(
        self, element: ET.Element, namespaces: dict[str, str]
    ) -> tuple[str, str, str | None, str | None]:
        """Extract full type information with namespace for activity.

        Args:
            element: XML element
            namespaces: Namespace prefix → URI mappings

        Returns:
            Tuple of (full_type, short_type, namespace_uri, prefix)
            - full_type: Full XML tag ({http://...}LocalName)
            - short_type: Local name only (LocalName)
            - namespace_uri: Namespace URI or None
            - prefix: Namespace prefix (ui, s, etc.) or None
        """
        tag = element.tag

        if "}" in tag:
            # Has namespace: "{http://...}LocalName"
            namespace_uri, local_name = tag.split("}", 1)
            namespace_uri = namespace_uri[1:]  # Remove leading '{'

            # Find prefix for this namespace URI
            prefix = None
            for ns_prefix, ns_uri in namespaces.items():
                if ns_uri == namespace_uri and ns_prefix:  # Skip default namespace ("")
                    prefix = ns_prefix
                    break

            return tag, local_name, namespace_uri, prefix
        else:
            # No namespace - use default namespace if available
            default_ns = namespaces.get("")
            return tag, tag, default_ns, None

    def _determine_variable_scope(self, var_element: ET.Element) -> str:
        """Determine the scope context for a variable."""
        parent = var_element.getparent() if hasattr(var_element, "getparent") else None
        if parent is not None:
            parent_tag: str = parent.tag.split("}")[-1] if "}" in parent.tag else parent.tag
            if parent_tag in self.platform.core_visual_activities:
                return parent_tag
        return "workflow"

    def _categorize_attributes(
        self, attrib: dict[str, str]
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Categorize attributes into visible and invisible."""
        visible = {}
        invisible = {}

        for key, value in attrib.items():
            # Remove namespace prefixes for comparison
            clean_key = key.split("}")[-1] if "}" in key else key

            # Check if attribute matches invisible patterns
            is_invisible = (
                any(pattern in key for pattern in self.platform.invisible_attribute_patterns)
                or clean_key in self.platform.viewstate_properties
                or "ViewState" in key
                or "HintSize" in key
                or "IdRef" in key
            )

            if is_invisible:
                invisible[key] = value
            else:
                visible[key] = value

        return visible, invisible

    def _looks_like_activity(self, elem: ET.Element, tag_name: str) -> bool:
        """Heuristic to determine if element is an activity."""
        # Has typical activity attributes
        if any(attr in elem.attrib for attr in ["DisplayName", "Result", "Value", "Text"]):
            return True

        # Has child elements that suggest it's a container activity
        child_tags = {child.tag.split("}")[-1] for child in elem}
        if child_tags & self.platform.core_visual_activities:
            return True

        # Namespace suggests it's a platform activity
        if self.platform.platform_namespace and elem.tag.startswith(
            f"{{{self.platform.platform_namespace}}}"
        ):
            return True

        return False

    def _extract_configuration(self, elem: ET.Element) -> dict[str, Any]:
        """Extract nested configuration from activity element."""
        config = {}

        for child in elem:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            # Skip variable definitions (handled separately)
            if child_tag.endswith("Variable"):
                continue

            # Extract nested configuration
            if len(child) > 0:  # Has children
                config[child_tag] = self._extract_nested_config(child)
            else:
                # Simple value
                config[child_tag] = child.text or child.attrib

        return config

    def _extract_nested_config(self, elem: ET.Element) -> Any:
        """Recursively extract nested configuration."""
        if len(elem) == 0:
            return elem.text or elem.attrib

        if len(elem.attrib) > 0 and len(elem) > 0:
            # Has both attributes and children
            return {
                "attributes": elem.attrib,
                "children": {
                    child.tag.split("}")[-1]: self._extract_nested_config(child) for child in elem
                },
            }
        elif len(elem) > 0:
            # Only children
            return {child.tag.split("}")[-1]: self._extract_nested_config(child) for child in elem}
        else:
            # Only attributes
            return elem.attrib

    def _extract_expressions_from_element(self, elem: ET.Element) -> list[Expression]:
        """Extract all expressions from an activity element."""
        expressions = []

        # Check attributes for expressions
        for key, value in elem.attrib.items():
            if self._is_expression(value):
                expr = Expression(
                    content=value,
                    expression_type=self._classify_expression_type(key),
                    language=self.config["expression_language"],
                    context=key,
                )
                expressions.append(expr)

        # Check text content for expressions
        if elem.text and self._is_expression(elem.text):
            expr = Expression(
                content=elem.text.strip(),
                expression_type="text_content",
                language=self.config["expression_language"],
                context="text",
            )
            expressions.append(expr)

        return expressions

    def _is_expression(self, text: str) -> bool:
        """Check if text contains expression patterns."""
        if not text or len(text.strip()) < 2:
            return False

        # Look for expression patterns
        return any(pattern in text for pattern in self.platform.expression_patterns)

    def _classify_expression_type(self, context: str) -> str:
        """Classify expression type based on context."""
        context_lower = context.lower()

        if "condition" in context_lower:
            return "condition"
        elif "value" in context_lower or "result" in context_lower:
            return "assignment"
        elif "message" in context_lower or "text" in context_lower:
            return "message"
        else:
            return "general"
