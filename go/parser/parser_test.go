package parser

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestParserCreation(t *testing.T) {
	// Test creating parser with default config
	p := New(nil)
	if p == nil {
		t.Fatal("expected non-nil parser")
	}

	config := p.GetConfig()
	if !config.ExtractArguments {
		t.Error("expected ExtractArguments to be true by default")
	}
}

func TestParserWithCustomConfig(t *testing.T) {
	customConfig := DefaultConfig()
	customConfig.StrictMode = true
	customConfig.MaxDepth = 100

	p := New(&customConfig)
	config := p.GetConfig()

	if !config.StrictMode {
		t.Error("expected StrictMode to be true")
	}
	if config.MaxDepth != 100 {
		t.Errorf("expected MaxDepth to be 100, got %d", config.MaxDepth)
	}
}

// TestGoldenFreeze tests parsing against golden freeze test data.
// This test will be skipped until the parser implementation is complete.
func TestGoldenFreeze(t *testing.T) {
	t.Skip("Parser implementation not yet complete")

	testdataDir := filepath.Join("..", "..", "testdata", "golden")

	testCases := []struct {
		name       string
		xamlFile   string
		goldenFile string
	}{
		{
			name:       "SimpleSequence",
			xamlFile:   "simple_sequence.xaml",
			goldenFile: "simple_sequence.json",
		},
		{
			name:       "ComplexWorkflow",
			xamlFile:   "complex_workflow.xaml",
			goldenFile: "complex_workflow.json",
		},
		{
			name:       "InvokeWorkflows",
			xamlFile:   "invoke_workflows.xaml",
			goldenFile: "invoke_workflows.json",
		},
		{
			name:       "UIAutomation",
			xamlFile:   "ui_automation.xaml",
			goldenFile: "ui_automation.json",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Parse XAML file
			xamlPath := filepath.Join(testdataDir, tc.xamlFile)
			parser := New(nil)
			result, err := parser.ParseFile(xamlPath)

			if err != nil {
				t.Fatalf("parsing failed: %v", err)
			}

			if !result.Success {
				t.Fatalf("parsing failed: %v", result.Errors)
			}

			// Load golden JSON
			goldenPath := filepath.Join(testdataDir, tc.goldenFile)
			goldenData, err := os.ReadFile(goldenPath)
			if err != nil {
				t.Fatalf("failed to read golden file: %v", err)
			}

			var expected ParseResult
			if err := json.Unmarshal(goldenData, &expected); err != nil {
				t.Fatalf("failed to unmarshal golden JSON: %v", err)
			}

			// Compare results
			// TODO: Implement deep comparison logic
			_ = expected // Use expected when comparison is implemented
		})
	}
}

// TestCorpus tests parsing corpus test projects.
func TestCorpus(t *testing.T) {
	t.Skip("Parser implementation not yet complete")

	corpusDir := filepath.Join("..", "..", "testdata", "corpus")

	t.Run("SimpleProject", func(t *testing.T) {
		mainXaml := filepath.Join(corpusDir, "simple_project", "Main.xaml")

		parser := New(nil)
		result, err := parser.ParseFile(mainXaml)

		if err != nil {
			t.Fatalf("parsing failed: %v", err)
		}

		if !result.Success {
			t.Fatalf("parsing failed: %v", result.Errors)
		}

		// Validate parsed content
		if result.Content == nil {
			t.Fatal("expected non-nil content")
		}
	})
}
