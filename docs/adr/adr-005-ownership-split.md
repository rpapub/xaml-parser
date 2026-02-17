# ADR-005: Ownership Split Between cpmf-uips-xaml Library and rpax CLI

## Status

Accepted

## Context

We are building `cpmf-uips-xaml` as a reusable library and `rpax` as the
user-facing CLI. The current behavior mixes concerns (parsing, graph building,
view rendering, and output formatting). We need a clear ownership split so the
library stays reusable and the CLI stays focused on UX and artifact layout.

## Decision

### Library (`cpmf-uips-xaml`) owns:

- Project discovery: read `project.json`, resolve entry points.
- XAML parsing: parse all workflows.
- Extraction: arguments, variables, activities, invocations, expressions.
- Normalization: stable IDs, deterministic DTOs.
- Graph construction: call graph and control-flow graph.
- Views: nested/execution/slice renderings.
- Built-in filters: known field profiles and None filtering.
- Schema validation of DTOs.
- Progress event emission (UI-agnostic).
- Error aggregation into structured issues.

### CLI (`rpax`) owns:

- Output folder structure and file naming.
- Artifact layout (manifest, index, invocations, paths, etc.).
- Presentation and formatting of results.
- Custom filters beyond built-in library profiles.
- Logging/progress rendering and exit codes.

### Filtering model

- Library provides a fixed set of known filters (profiles, None filtering).
- Caller can apply additional custom filters to DTO/view JSON as needed.

## Consequences

- Library remains reusable and UI-agnostic.
- `rpax` focuses on UX and artifact composition without reimplementing parsing.
- The API surface must expose graph building, views, and filters explicitly.
- Customization remains possible without forking library internals.

## Notes

This ADR is aligned with the pipeline model:
parse → normalize → build → view/filter → emit/sink.
