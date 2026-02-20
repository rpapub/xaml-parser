Got it. Here’s a compact requirements draft + focused questions.

# XAML Parser — Requirements v0.1

## Goals

* Deterministically parse UiPath XAML workflows.
* Emit stable, schema-versioned DTOs for reuse.
* Support downstream consumption: docs + diagrams.

## Scope (MoSCoW)

* **Must**

  * Parse single file / folder (recursive).
  * Normalize activities, variables, arguments, dependencies, annotations, invoked workflows, transitions.
  * Produce JSON (canonical), optionally YAML.
  * Stable IDs per entity (path + index + hash of XML span).
  * CLI + importable API.
  * JSON Schema for all DTOs; self-describe (`$schema`, `$id`, `schemaVersion`).
  * Deterministic ordering (locale-independent).
* **Should**

  * Emit diagram source (Mermaid, Graphviz DOT, PlantUML).
  * Emit doc artifacts (Markdown via templates).
  * Validation subcommand (schema + referential).
  * Pluggable emitters (Python entry points).
* **Could**

  * SQLite/Parquet sink.
  * Rich HTML docs (md→site).
  * Cross-file call graph.
* **Won’t (v0.1)**

  * Edit/round-trip XAML.
  * Execute workflows.

## Inputs

* `.xaml` files (UiPath), UTF-8.
* Optional config file: `xamlparser.toml|yaml|json`.

## Outputs

* **Canonical JSON** (default): one file per workflow, or combined.
* **YAML** (flag).
* **Diagrams**: `.mmd` (Mermaid), `.dot`, `.puml`.
* **Docs**: `.md` from templates.

## CLI

* `xamlp parse --in <file|dir> --out <dir|-> --format json|yaml --combine --schema-version <semver> --relpaths`
* `xamlp validate --in <file|dir> --strict`
* `xamlp diagram --in <file|dir> --out <dir> --type mermaid|dot|plantuml`
* `xamlp doc --in <file|dir> --out <dir> --template <name|path>`
* `xamlp schema --print` (emit JSON Schema)
* Common flags: `--glob`, `--ignore`, `--workers <n>`, `--quiet`, `--pretty`, `--no-color`, `--fail-on-warn`.
* Exit codes: `0 ok`, `1 errors`, `2 validation failed`.

## API (Python)

```py
parse(path: PathLike, *, config: Config) -> List[WorkflowDto]
validate(objs: Iterable[WorkflowDto]) -> List[Issue]
emit_diagram(objs, kind="mermaid") -> List[Rendered]
render_docs(objs, template="default") -> List[Doc]
```

## Data Model (DTOs, sketch)

```json
{
  "schemaId": "https://example.org/schemas/xaml-workflow.json",
  "schemaVersion": "1.0.0",
  "collectedAt": "2025-10-11T07:15:00Z",
  "workflows": [
    {
      "id": "wf:relative/path/Main.xaml#sha256:...",
      "name": "Main",
      "source": {"path": "relative/path/Main.xaml", "hash": "sha256:..."},
      "metadata": {"projectName": "...", "namespace": "...", "annotations": ["..."]},
      "variables": [{"id":"var:...","name":"customerId","type":"String","scope":"Workflow","default":null}],
      "arguments": [{"id":"arg:...","name":"in_Config","direction":"In","type":"Dictionary`2"}],
      "dependencies": [{"package":"UiPath.Excel.Activities","version":"2.20.0"}],
      "activities": [
        {
          "id":"act:.../Sequence[0]",
          "type":"System.Activities.Statements.Sequence",
          "displayName":"Init",
          "location":{"line":42,"col":9},
          "children":["act:.../Assign[0]","act:.../If[0]"],
          "properties":{"Condition":"..."},
          "inArgs":{"Input": "arg:..."},
          "outArgs":{"Result": "var:..."}
        }
      ],
      "edges": [
        {"from":"act:.../If[0]","to":"act:.../Then[0]","kind":"Then"},
        {"from":"act:.../If[0]","to":"act:.../Else[0]","kind":"Else"}
      ],
      "invocations":[{"callee":"wf:./Sub.xaml#sha256:...","viaActivityId":"act:.../InvokeWorkflowFile[0]"}]
    }
  ],
  "issues": []
}
```

### ID/Determinism

* `id = prefix : normalized-path # sha256(xml-span)` for workflow; activities get path-like suffixes (type[index]).
* Sort lists by `id`.

## JSON Schema

* Publish at `/schemas/xaml-workflow-1.0.0.json`.
* `$defs`: `Workflow`, `Activity`, `Edge`, `Variable`, `Argument`, `Dependency`, `Invocation`, `Issue`.

## Normalization Rules

* Strip BOM; collapse whitespace in text nodes where UiPath is non-semantic.
* Preserve original casing for names; normalize types (fully-qualified) in `typeFqn`.
* Paths relative to `--in` root unless `--abs-paths`.

## Doc Generation

* Templating: Jinja2.
* Bundled templates:

  * `workflow.md.j2` (per workflow: header, variables/args table, activity list, invocation list).
  * `index.md.j2` (summary + call graph).
* Artifacts organized:

  * `/docs/index.md`
  * `/docs/workflows/<name>.md`
  * `/diagrams/<name>.mmd|dot|puml`

## Diagram Generation

* **Mermaid (default)**: `flowchart TD` or `graph TD`; nodes=activities, edges=control flow; subgraphs=Sequences/Flowcharts.
* **Graphviz DOT**: clusters by container activities.
* **PlantUML Activity**: optional, map `If/FlowDecision/Switch/ForEach/TryCatch`.
* Node labels: `displayName\n(type)`.
* Node IDs use DTO `id` (sanitized).

### Mermaid example (sketch)

```
flowchart TD
  A["Init\n(Sequence)"] --> B["Check\n(If)"]
  B -->|Then| C["Do X\n(Sequence)"]
  B -->|Else| D["Skip\n(Sequence)"]
```

## Config

* `xamlparser.yaml`

  * `exclude: ["**/Tests/**"]`
  * `emit: { diagrams: ["mermaid"], docs: true }`
  * `schemaVersion: "1.0.0"`

## Quality

* Unit tests: XML fixtures in `testdata/` (small, curated).
* Golden tests: JSON outputs under `testdata/golden/` with update flag.
* Schema validation tests (draft 2020-12).
* Determinism tests (hash stable across runs).
* Large-repo smoke test (parallel parse).

## Performance

* Streaming XML (iterparse).
* Optional `--workers N` (process pool).
* Memory cap via chunked emission.

## Packaging

* Python package `xamlparser`:

  * `xamlparser/__main__.py` → `python -m xamlparser`.
  * `xamlp` console script.
* SemVer for tool; schema version tracked separately.
* Repro builds: lockfile; pinned deps.

## Extensibility

* Emitter plugin interface:

  * `xamlparser.emitters.<name>: Emitter` discovered via entry points.
* Custom Jinja templates via `--template-dir`.

---

## Questions (please confirm/choose)

1. **Language**: stick with Python first, or target Go now (or both with shared schema)?
2. **Diagram default**: Mermaid only, or also DOT/PlantUML in v0.1?
3. **Doc templates**: minimal tables only, or include embedded diagrams?
4. **Output mode**: one combined JSON vs. one-file-per-workflow (default)?
5. **IDs**: ok with `sha256(xml-span)` + path, or prefer incremental stable IDs?
6. **Validation**: strict fail on unknown activity types, or warn and include `typeRaw`?
7. **Performance target**: expected repo size (# XAML files) to guide parallelism?
8. **Licensing**: keep CC-BY for docs + MIT/Apache-2.0 for code?
9. **Downstream**: which consumers first—rpax diagnostics, site docs, call-graph reviews?
10. **YAML**: needed in v0.1 or can wait?
