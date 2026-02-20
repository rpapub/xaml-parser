// Package parser provides XAML workflow parsing functionality.
package parser

// WorkflowContent represents the complete parsed workflow metadata.
type WorkflowContent struct {
	Arguments          []WorkflowArgument `json:"arguments"`
	Variables          []WorkflowVariable `json:"variables"`
	Activities         []Activity         `json:"activities"`
	RootAnnotation     *string            `json:"root_annotation"`
	DisplayName        *string            `json:"display_name"`
	Description        *string            `json:"description"`
	Namespaces         map[string]string  `json:"namespaces"`
	AssemblyReferences []string           `json:"assembly_references"`
	ExpressionLanguage string             `json:"expression_language"`
	Metadata           map[string]any     `json:"metadata"`
	TotalActivities    int                `json:"total_activities"`
	TotalArguments     int                `json:"total_arguments"`
	TotalVariables     int                `json:"total_variables"`
}

// WorkflowArgument represents a workflow argument definition.
type WorkflowArgument struct {
	Name         string  `json:"name"`
	Type         string  `json:"type"`
	Direction    string  `json:"direction"` // "in", "out", "inout"
	Annotation   *string `json:"annotation,omitempty"`
	DefaultValue *string `json:"default_value,omitempty"`
}

// WorkflowVariable represents a workflow variable definition.
type WorkflowVariable struct {
	Name         string  `json:"name"`
	Type         string  `json:"type"`
	Scope        string  `json:"scope"`
	DefaultValue *string `json:"default_value,omitempty"`
}

// Activity represents a complete activity with metadata.
type Activity struct {
	Tag                  string             `json:"tag"`
	ActivityID           string             `json:"activity_id"`
	DisplayName          *string            `json:"display_name,omitempty"`
	Annotation           *string            `json:"annotation,omitempty"`
	VisibleAttributes    map[string]string  `json:"visible_attributes"`
	InvisibleAttributes  map[string]string  `json:"invisible_attributes"`
	Configuration        map[string]any     `json:"configuration"`
	Variables            []WorkflowVariable `json:"variables"`
	Expressions          []Expression       `json:"expressions"`
	ParentActivityID     *string            `json:"parent_activity_id,omitempty"`
	ChildActivities      []string           `json:"child_activities"`
	DepthLevel           int                `json:"depth_level"`
	XPathLocation        *string            `json:"xpath_location,omitempty"`
	SourceLine           *int               `json:"source_line,omitempty"`
}

// Expression represents an expression found in XAML.
type Expression struct {
	Content           string   `json:"content"`
	ExpressionType    string   `json:"expression_type"` // "assignment", "condition", etc.
	Language          string   `json:"language"`        // "VisualBasic" or "CSharp"
	Context           *string  `json:"context,omitempty"`
	ContainsVariables []string `json:"contains_variables,omitempty"`
	ContainsMethods   []string `json:"contains_methods,omitempty"`
}

// ParseResult represents the complete parsing result with diagnostics.
type ParseResult struct {
	Content      *WorkflowContent  `json:"content"`
	Success      bool              `json:"success"`
	Errors       []string          `json:"errors"`
	Warnings     []string          `json:"warnings"`
	ParseTimeMs  float64           `json:"parse_time_ms"`
	FilePath     *string           `json:"file_path"`
	Diagnostics  *ParseDiagnostics `json:"diagnostics,omitempty"`
	ConfigUsed   Config            `json:"config_used"`
}

// ParseDiagnostics provides detailed diagnostic information.
type ParseDiagnostics struct {
	TotalElementsProcessed int                `json:"total_elements_processed"`
	ActivitiesFound        int                `json:"activities_found"`
	ArgumentsFound         int                `json:"arguments_found"`
	VariablesFound         int                `json:"variables_found"`
	AnnotationsFound       int                `json:"annotations_found"`
	ExpressionsFound       int                `json:"expressions_found"`
	NamespacesDetected     int                `json:"namespaces_detected"`
	SkippedElements        int                `json:"skipped_elements"`
	XMLDepth               int                `json:"xml_depth"`
	FileSizeBytes          int64              `json:"file_size_bytes"`
	EncodingDetected       *string            `json:"encoding_detected,omitempty"`
	RootElementTag         *string            `json:"root_element_tag,omitempty"`
	ProcessingSteps        []string           `json:"processing_steps"`
	PerformanceMetrics     map[string]float64 `json:"performance_metrics"`
}

// Config represents parser configuration.
type Config struct {
	ExtractArguments         bool   `json:"extract_arguments"`
	ExtractVariables         bool   `json:"extract_variables"`
	ExtractActivities        bool   `json:"extract_activities"`
	ExtractExpressions       bool   `json:"extract_expressions"`
	ExtractViewstate         bool   `json:"extract_viewstate"`
	ExtractNamespaces        bool   `json:"extract_namespaces"`
	ExtractAssemblyRefs      bool   `json:"extract_assembly_references"`
	PreserveRawMetadata      bool   `json:"preserve_raw_metadata"`
	StrictMode               bool   `json:"strict_mode"`
	MaxDepth                 int    `json:"max_depth"`
	ExpressionLanguage       string `json:"expression_language"` // "VisualBasic" or "CSharp"
}

// DefaultConfig returns the default parser configuration.
func DefaultConfig() Config {
	return Config{
		ExtractArguments:    true,
		ExtractVariables:    true,
		ExtractActivities:   true,
		ExtractExpressions:  true,
		ExtractViewstate:    false,
		ExtractNamespaces:   true,
		ExtractAssemblyRefs: true,
		PreserveRawMetadata: false,
		StrictMode:          false,
		MaxDepth:            50,
		ExpressionLanguage:  "VisualBasic",
	}
}
