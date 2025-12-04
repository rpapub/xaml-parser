"""Interprocedural variable ancestry analysis.

This module provides the main analyzer that builds ancestry graphs from workflows,
tracking variable flow across InvokeWorkflowFile boundaries and through transformations.
"""

import hashlib
from typing import cast

from .ancestry_graph import (
    AncestryEdge,
    AncestryGraph,
    AncestryNode,
    AncestryPath,
    ImpactAnalysisResult,
    TransformationInfo,
    ValueFlowTrace,
)
from .dto import ActivityDto, ArgumentDto, VariableDto, WorkflowDto
from .expression_parser import ExpressionParser
from .type_system import TypeInfo


class InterproceduralAliasAnalyzer:
    """Main analyzer for interprocedural variable ancestry tracking.

    This class orchestrates the complete ancestry analysis pipeline:
    1. Build graph nodes from variables and arguments
    2. Add interprocedural edges from InvokeWorkflowFile bindings
    3. Add intraprocedural edges from Assign/MultiAssign activities
    4. Provide query APIs for ancestry, descendants, impact analysis
    """

    def __init__(self, workflows: list[WorkflowDto]) -> None:
        """Initialize analyzer with workflows.

        Args:
            workflows: List of WorkflowDto objects to analyze
        """
        self.workflows = {wf.id: wf for wf in workflows}
        self.graph = AncestryGraph()
        self.expression_parser = ExpressionParser()

    def build_graph(self) -> AncestryGraph:
        """Build complete ancestry graph.

        Returns:
            AncestryGraph with all nodes and edges
        """
        self._add_nodes()
        self._add_interprocedural_edges()
        self._add_intraprocedural_edges()
        return self.graph

    def _add_nodes(self) -> None:
        """Phase 1: Add all variables and arguments as nodes."""
        for wf in self.workflows.values():
            # Add variable nodes
            for var in wf.variables:
                node = AncestryNode(
                    id=var.id,
                    entity_type="variable",
                    name=var.name,
                    type=TypeInfo.parse(var.type),
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    scope=var.scope,
                )
                self.graph.add_node(node)

            # Add argument nodes
            for arg in wf.arguments:
                node = AncestryNode(
                    id=arg.id,
                    entity_type="argument",
                    name=arg.name,
                    type=TypeInfo.parse(arg.type),
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    scope="workflow",
                )
                self.graph.add_node(node)

    def _add_interprocedural_edges(self) -> None:
        """Phase 2: Add edges for InvokeWorkflowFile argument bindings."""
        for wf in self.workflows.values():
            for invocation in wf.invocations:
                callee = self.workflows.get(invocation.callee_id)
                if not callee:
                    continue  # Unresolved workflow

                for arg_name, caller_expr in invocation.arguments_passed.items():
                    # Skip non-argument properties
                    if arg_name in [
                        "ArgumentsVariable",
                        "ContinueOnError",
                        "DisplayName",
                        "UnSafe",
                        "WorkflowFileName",
                    ]:
                        continue

                    # Parse caller expression
                    analysis = self.expression_parser.analyze(caller_expr)

                    # Find callee argument
                    callee_arg = next((a for a in callee.arguments if a.name == arg_name), None)
                    if not callee_arg:
                        continue

                    # Find caller variable(s)
                    for caller_var_name in analysis.source_variables:
                        caller_var = next(
                            (v for v in wf.variables if v.name == caller_var_name), None
                        )
                        if not caller_var:
                            # Might be an argument in caller
                            caller_var = cast(
                                VariableDto | None,
                                next(
                                    (a for a in wf.arguments if a.name == caller_var_name),
                                    None,
                                ),
                            )
                        if not caller_var:
                            continue

                        # Create edges based on argument direction
                        if callee_arg.direction in ["In", "InOut"]:
                            # Data flows: caller_var → callee_arg
                            edge = AncestryEdge(
                                id=self._generate_edge_id(
                                    caller_var.id, callee_arg.id, "arg_binding_in"
                                ),
                                from_id=caller_var.id,
                                to_id=callee_arg.id,
                                kind="arg_binding_in",
                                via_activity_id=invocation.via_activity_id,
                                transformation=None,
                                confidence="definite",
                            )
                            self.graph.add_edge(edge)

                        if callee_arg.direction in ["Out", "InOut"]:
                            # Data flows: callee_arg → caller_var
                            edge = AncestryEdge(
                                id=self._generate_edge_id(
                                    callee_arg.id, caller_var.id, "arg_binding_out"
                                ),
                                from_id=callee_arg.id,
                                to_id=caller_var.id,
                                kind="arg_binding_out",
                                via_activity_id=invocation.via_activity_id,
                                transformation=None,
                                confidence="definite",
                            )
                            self.graph.add_edge(edge)

    def _add_intraprocedural_edges(self) -> None:
        """Phase 3: Add edges for assignments and transformations within workflows."""
        for wf in self.workflows.values():
            for activity in wf.activities:
                if "Assign" in activity.type_short:
                    self._process_assign(wf, activity)
                elif "MultiAssign" in activity.type_short:
                    self._process_multiassign(wf, activity)

    def _process_assign(self, wf: WorkflowDto, activity: ActivityDto) -> None:
        """Process Assign activity to extract variable relationships."""
        # Extract To and Value
        to_expr = activity.in_args.get("To") or activity.properties.get("To")
        value_expr = activity.in_args.get("Value") or activity.properties.get("Value")

        if not to_expr or not value_expr:
            return

        # Parse target variable
        target_var_name = self._parse_simple_var_ref(to_expr)
        if not target_var_name:
            return

        target_var = next((v for v in wf.variables if v.name == target_var_name), None)
        if not target_var:
            return

        # Analyze value expression
        analysis = self.expression_parser.analyze(value_expr)

        # Create edges for each source variable
        for source_var_name in analysis.source_variables:
            source_var = next((v for v in wf.variables if v.name == source_var_name), None)
            if not source_var:
                # Check if it's an argument
                source_arg = next((a for a in wf.arguments if a.name == source_var_name), None)
                if source_arg:
                    # Argument to variable edge
                    edge_kind, transformation = self._classify_relationship(
                        source_arg, target_var, analysis.transformations
                    )

                    edge = AncestryEdge(
                        id=self._generate_edge_id(source_arg.id, target_var.id, edge_kind),
                        from_id=source_arg.id,
                        to_id=target_var.id,
                        kind=edge_kind,
                        via_activity_id=activity.id,
                        transformation=transformation,
                        confidence=analysis.confidence,
                    )
                    self.graph.add_edge(edge)
                continue

            # Variable to variable edge
            edge_kind, transformation = self._classify_relationship(
                source_var, target_var, analysis.transformations
            )

            edge = AncestryEdge(
                id=self._generate_edge_id(source_var.id, target_var.id, edge_kind),
                from_id=source_var.id,
                to_id=target_var.id,
                kind=edge_kind,
                via_activity_id=activity.id,
                transformation=transformation,
                confidence=analysis.confidence,
            )
            self.graph.add_edge(edge)

    def _process_multiassign(self, wf: WorkflowDto, activity: ActivityDto) -> None:
        """Process MultiAssign activity to extract multiple variable relationships."""
        # MultiAssign typically stores assignments in properties
        # Look for AssignOperationInfoes or similar structure
        # For now, skip as this requires deeper XAML structure analysis
        pass

    def _classify_relationship(
        self,
        source: VariableDto | ArgumentDto,
        target: VariableDto,
        transformations: list,
    ) -> tuple[str, TransformationInfo | None]:
        """Classify relationship and build transformation info.

        Args:
            source: Source variable or argument
            target: Target variable
            transformations: List of Transformation objects from expression analysis

        Returns:
            Tuple of (edge_kind, transformation_info)
        """
        if not transformations:
            # Direct assignment
            return ("assign", None)

        # Build transformation chain with type flow
        source_type = TypeInfo.parse(source.type)
        current_type = source_type

        # Process transformations to infer types
        for trans in transformations:
            if trans.operation == "dictionary_access":
                # Dict access: get element type
                element_type = current_type.get_element_type()

                return (
                    "extract",
                    TransformationInfo(
                        operation="dictionary_access",
                        details={
                            "key": trans.details.get("key", ""),
                            "key_is_static": trans.details.get("key_is_static", False),
                        },
                        from_type=current_type,
                        to_type=element_type,
                    ),
                )

            elif trans.operation == "method_call":
                # Method call: infer return type
                method_name = str(trans.details.get("method", ""))
                return_type = current_type.infer_method_return_type(method_name)

                return (
                    "cast",
                    TransformationInfo(
                        operation="method_call",
                        details={"method": method_name},
                        from_type=current_type,
                        to_type=return_type,
                    ),
                )

            elif trans.operation == "property_access":
                # Property access: infer property type
                property_name = str(trans.details.get("property", ""))
                property_type = current_type.infer_property_type(property_name)

                return (
                    "extract",
                    TransformationInfo(
                        operation="property_access",
                        details={"property": property_name},
                        from_type=current_type,
                        to_type=property_type,
                    ),
                )

            elif trans.operation == "cast":
                # Explicit cast
                cast_func = str(trans.details.get("cast_function", ""))
                # Infer target type from cast function
                target_type = self._infer_cast_target_type(cast_func)

                return (
                    "cast",
                    TransformationInfo(
                        operation="cast",
                        details={"cast_function": cast_func},
                        from_type=current_type,
                        to_type=target_type,
                    ),
                )

            elif trans.operation == "aggregate":
                # Multiple sources
                return (
                    "aggregate",
                    TransformationInfo(
                        operation="aggregate",
                        details={"expression": trans.details.get("expression", "")},
                        from_type=current_type,
                        to_type=TypeInfo.parse(target.type),
                    ),
                )

        # Default: generic transformation
        return (
            "transform",
            TransformationInfo(
                operation="complex",
                details={"transformations": [t.operation for t in transformations]},
                from_type=source_type,
                to_type=TypeInfo.parse(target.type),
            ),
        )

    def _infer_cast_target_type(self, cast_func: str) -> TypeInfo | None:
        """Infer target type from VB cast function name.

        Args:
            cast_func: Cast function name (CInt, CStr, etc.)

        Returns:
            TypeInfo for target type
        """
        cast_map = {
            "CInt": "System.Int32",
            "CStr": "System.String",
            "CDbl": "System.Double",
            "CBool": "System.Boolean",
            "CDate": "System.DateTime",
            "CLng": "System.Int64",
            "CShort": "System.Int16",
            "CByte": "System.Byte",
        }

        type_str = cast_map.get(cast_func)
        if type_str:
            return TypeInfo.parse(type_str)
        return None

    def _parse_simple_var_ref(self, expr: str) -> str | None:
        """Parse simple variable reference from expression.

        Args:
            expr: Expression like "[varName]" or "varName"

        Returns:
            Variable name or None
        """
        expr = expr.strip()
        if expr.startswith("[") and expr.endswith("]"):
            expr = expr[1:-1].strip()

        # Must be simple identifier
        if expr and expr[0].isalpha() or expr[0] == "_":
            return expr

        return None

    def _generate_edge_id(self, from_id: str, to_id: str, kind: str) -> str:
        """Generate stable edge ID.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            kind: Edge kind

        Returns:
            Stable edge ID (edge:sha256:...)
        """
        content = f"{from_id}→{to_id}:{kind}"
        hash_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"edge:sha256:{hash_digest[:16]}"

    # Query API

    def get_ancestry(self, var_id: str, max_depth: int = 10) -> list[AncestryPath]:
        """Get all ancestor paths for a variable.

        Args:
            var_id: Variable ID to trace
            max_depth: Maximum path depth to prevent infinite recursion

        Returns:
            List of AncestryPath objects from origins to target
        """
        paths: list[AncestryPath] = []
        visited: set[str] = set()

        def dfs(node_id: str, edge_path: list[AncestryEdge], depth: int) -> None:
            if depth > max_depth or node_id in visited:
                return

            visited.add(node_id)
            predecessors = self.graph.get_predecessors(node_id)

            if not predecessors:
                # Found origin variable
                origin_node = self.graph.nodes.get(node_id)
                target_node = self.graph.nodes.get(var_id)

                if origin_node and target_node:
                    transformations = [e.transformation for e in edge_path if e.transformation]
                    confidence = self._compute_path_confidence(edge_path)

                    paths.append(
                        AncestryPath(
                            origin_node=origin_node,
                            target_node=target_node,
                            edges=list(reversed(edge_path)),
                            transformations=transformations,
                            confidence=confidence,
                        )
                    )
            else:
                for pred_id in predecessors:
                    edge = self.graph.find_edge(pred_id, node_id)
                    if edge:
                        dfs(pred_id, edge_path + [edge], depth + 1)

        dfs(var_id, [], 0)
        return paths

    def _compute_path_confidence(self, edges: list[AncestryEdge]) -> str:
        """Compute overall confidence for a path.

        Args:
            edges: List of edges in path

        Returns:
            Confidence level ('definite', 'possible', 'unknown')
        """
        if any(e.confidence == "unknown" for e in edges):
            return "unknown"
        if any(e.confidence == "possible" for e in edges):
            return "possible"
        return "definite"

    def trace_value_flow(self, var_id: str) -> ValueFlowTrace:
        """Trace complete value flow with confidence levels.

        Args:
            var_id: Variable ID to trace

        Returns:
            ValueFlowTrace with paths grouped by confidence
        """
        variable = self.graph.nodes.get(var_id)
        if not variable:
            return ValueFlowTrace(
                variable=AncestryNode(
                    id=var_id,
                    entity_type="unknown",
                    name="unknown",
                    type=TypeInfo.parse("Object"),
                    workflow_id="",
                    workflow_name="",
                )
            )

        ancestry = self.get_ancestry(var_id)

        definite = [p for p in ancestry if p.confidence == "definite"]
        possible = [p for p in ancestry if p.confidence == "possible"]
        unknown = [p for p in ancestry if p.confidence == "unknown"]

        return ValueFlowTrace(
            variable=variable,
            definite_sources=definite,
            possible_sources=possible,
            unknown_sources=unknown,
        )

    def get_descendants(self, var_id: str) -> list[AncestryNode]:
        """Get all variables that depend on this variable (forward slice).

        Args:
            var_id: Variable ID

        Returns:
            List of descendant variable nodes
        """
        descendant_ids = self.graph.get_descendants(var_id)
        return [
            self.graph.nodes[nid]
            for nid in descendant_ids
            if nid in self.graph.nodes and self.graph.nodes[nid].entity_type == "variable"
        ]

    def impact_analysis(self, var_id: str) -> ImpactAnalysisResult:
        """Analyze impact of changing a variable.

        Args:
            var_id: Variable ID to analyze

        Returns:
            ImpactAnalysisResult with affected variables grouped by workflow
        """
        source_variable = self.graph.nodes.get(var_id)
        if not source_variable:
            return ImpactAnalysisResult(
                source_variable=AncestryNode(
                    id=var_id,
                    entity_type="unknown",
                    name="unknown",
                    type=TypeInfo.parse("Object"),
                    workflow_id="",
                    workflow_name="",
                )
            )

        descendants = self.get_descendants(var_id)

        # Group by workflow
        by_workflow: dict[str, list[AncestryNode]] = {}
        for node in descendants:
            if node.workflow_id not in by_workflow:
                by_workflow[node.workflow_id] = []
            by_workflow[node.workflow_id].append(node)

        return ImpactAnalysisResult(
            source_variable=source_variable,
            affected_variables=descendants,
            affected_workflows=list(by_workflow.keys()),
            by_workflow=by_workflow,
        )
