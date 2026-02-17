# Documentation Archive

This directory contains historical documentation from completed implementation sessions, outdated instructions, and superseded architecture documents.

## Purpose

These documents are archived (not deleted) because they:
- Provide historical context for design decisions
- Show the evolution of the codebase
- May contain useful reference information
- Document completed implementation work

## Archive Structure

### `implementation-sessions/`
Session summaries and post-implementation analyses:
- `IMPLEMENTATION_DAY1.md` - Day 1 implementation session
- `SESSION_SUMMARY.md` - Earlier session summary
- `POST_REWRITE_ANALYSIS.md` - Analysis after major rewrite
- `IMPLEMENTATION-SUMMARY-ancestry.md` - Ancestry feature implementation summary

### `instructions/`
Completed implementation instruction documents (no longer actively used):
- `INSTRUCTIONS-ancestry.md` (45K) - Ancestry graph implementation guide
- `INSTRUCTIONS-nesting.md` (104K) - Nested view implementation guide
- `INSTRUCTIONS-cli-py.md` - CLI implementation instructions
- `INSTRUCTIONS-assembly-refs.md` - Assembly reference handling
- `INSTRUCTIONS-packaging.md` - Packaging setup instructions

### `analysis/`
Completed analysis documents:
- `ANALYSIS-expression-language-field.md` - Expression language field analysis
- `ANALYSIS-xaml-metadata.md` - XAML metadata analysis

### Root Archive Files
- `PLAN.md` (63K) - Original implementation plan
- `architecture.md` - Early architecture doc (superseded by ADRs)
- `MIGRATION.md` - Migration guide from earlier versions
- `zweitmeinung.md` - Second opinion / review document
- `EVALUATION.md` - Schema evaluation (from schemas/)

## Active Documentation (Not Archived)

For current, active documentation, see:
- `/README.md` - Main project readme
- `/CLAUDE.md` - Claude Code instructions
- `/CONTRIBUTING.md` - Contribution guidelines
- `/TESTING_STATUS.md` - Current test status
- `/docs/ADR-*.md` - Architecture Decision Records (current)
- `/python/README.md` - Python package documentation
- `/python/CHANGELOG.md` - Version history

## When to Archive Documents

Archive a document when:
1. The implementation it describes is complete
2. It's an instruction document no longer needed for development
3. It's been superseded by newer documentation (e.g., ADRs)
4. It's a session summary or temporal analysis

## When NOT to Archive

Keep documents active if they:
1. Describe current architecture (ADRs)
2. Are user-facing (README, CONTRIBUTING)
3. Track ongoing status (TESTING_STATUS)
4. Contain operational procedures still in use

---

*Last Updated: 2025-10-12*
