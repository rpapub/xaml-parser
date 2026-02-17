# Schema Directory

## Overview

**v2/**: PRIMARY external record contracts (stable, versioned)
**v1/**: Internal DTO schemas (diagnostic, may change)

## Record Envelope (v2)

Every exported record has this structure:

```json
{
  "schema_id": "cpmf-uips-xaml://v2/workflow-record",
  "schema_version": "2.0.0",
  "kind": "workflow",
  "payload": { /* curated fields */ }
}
```

Kinds: `workflow`, `activity`, `argument`, `invocation`, `issue`, `dependency`

## Usage

```python
from cpmf_uips_xaml import load

session = load(project_path)
records_jsonl = session.emit("jsonl", kinds=["workflow", "activity"])
```

## Go Compatibility

v2 schemas are designed for code generation:
- Semantic versioning (breaking changes → v3)
- Curated payloads (not raw DTO dumps)
- Stable field names and types
