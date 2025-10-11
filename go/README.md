# XAML Parser - Go Implementation

Go implementation of the XAML workflow parser for automation projects.

## Status

🚧 **In Development** - This is a prepared structure for the Go implementation. The parser functionality is not yet implemented.

## Installation

```bash
go get github.com/rpapub/xaml-parser/go/parser
```

## Planned Usage

```go
package main

import (
	"fmt"
	"log"

	"github.com/rpapub/xaml-parser/go/parser"
)

func main() {
	// Create parser with default configuration
	p := parser.New(nil)

	// Parse a workflow file
	result, err := p.ParseFile("workflow.xaml")
	if err != nil {
		log.Fatal(err)
	}

	if result.Success {
		content := result.Content
		fmt.Printf("Workflow: %s\n", *content.RootAnnotation)
		fmt.Printf("Arguments: %d\n", len(content.Arguments))
		fmt.Printf("Activities: %d\n", len(content.Activities))

		// Access arguments
		for _, arg := range content.Arguments {
			fmt.Printf("  %s %s: %s\n", arg.Direction, arg.Name, arg.Type)
			if arg.Annotation != nil {
				fmt.Printf("    -> %s\n", *arg.Annotation)
			}
		}
	} else {
		fmt.Printf("Parsing failed: %v\n", result.Errors)
	}
}
```

## Custom Configuration

```go
config := parser.DefaultConfig()
config.StrictMode = true
config.MaxDepth = 100
config.ExtractViewstate = false

p := parser.New(&config)
result, err := p.ParseFile("workflow.xaml")
```

## API Compatibility

The Go implementation is designed to match the Python API and produce identical JSON output. This ensures:

- **Schema Compliance**: Both implementations validate against the same JSON schemas
- **Cross-Language Testing**: Shared test data in `../testdata/`
- **Consistent Behavior**: Same parsing rules and error handling

## Data Models

All data models are defined in `parser/models.go`:

- `WorkflowContent`: Complete workflow metadata
- `WorkflowArgument`: Argument definition
- `WorkflowVariable`: Variable definition
- `Activity`: Activity with full metadata
- `Expression`: Expression with language detection
- `ParseResult`: Top-level parse result with diagnostics

## Implementation Roadmap

### Phase 1: Core Parsing (Planned)
- [ ] XML parsing with namespace handling
- [ ] Argument extraction
- [ ] Variable extraction
- [ ] Basic activity extraction
- [ ] Annotation extraction

### Phase 2: Advanced Features (Planned)
- [ ] Expression parsing and analysis
- [ ] Variable/method reference detection
- [ ] ViewState handling
- [ ] Assembly reference extraction
- [ ] Nested activity tree construction

### Phase 3: Validation & Testing (Planned)
- [ ] Schema validation
- [ ] Golden freeze test suite
- [ ] Corpus test suite
- [ ] Error handling and diagnostics
- [ ] Performance benchmarks

### Phase 4: Polish (Planned)
- [ ] Documentation
- [ ] Examples
- [ ] CLI tool
- [ ] CI/CD integration

## Development

### Running Tests

```bash
# Run all tests
go test ./...

# Run with verbose output
go test -v ./...

# Run golden freeze tests (once implemented)
go test -v ./parser -run TestGoldenFreeze

# Run corpus tests (once implemented)
go test -v ./parser -run TestCorpus
```

### Code Quality

```bash
# Format code
go fmt ./...

# Lint
golangci-lint run

# Vet
go vet ./...
```

### Building

```bash
# Build the package
go build ./...

# Run tests with coverage
go test -cover ./...
```

## Project Structure

```
go/
├── parser/               # Main parser package
│   ├── models.go         # Data models
│   ├── parser.go         # Parser implementation
│   └── parser_test.go    # Tests
├── go.mod                # Go module definition
├── go.sum                # Dependency checksums (future)
└── README.md             # This file
```

## Test Data

Tests reference shared test data in `../testdata/`:

- `../testdata/golden/`: Golden freeze test pairs (XAML + JSON)
- `../testdata/corpus/`: Structured test projects

This ensures consistency with the Python implementation.

## Contributing

See the main repository [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

When contributing to the Go implementation:

1. Follow Go coding conventions
2. Add tests for new functionality
3. Ensure golden freeze tests pass (once implemented)
4. Update documentation

## License

Licensed under CC-BY 4.0. See [LICENSE](../LICENSE) for details.

## Links

- **Monorepo**: https://github.com/rpapub/xaml-parser
- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **Go Package**: https://pkg.go.dev/github.com/rpapub/xaml-parser/go/parser (once published)
