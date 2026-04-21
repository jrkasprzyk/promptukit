## New Question Types
## 🥷 New Question Types
- Expand the question types available within promptukit to include options beyond 4-answer multiple choice questions and provide a migration path for banks, validation, authoring, grading, and exports.

## Author / Date
## Author / Date
- Author: josephRobertBob and Copilot (GPT 5-mini)
- Date: 2026-04-18

## Status
## Status
- Draft

## Related issues / PRs
## Related issues / PRs
- Link to issue(s) or PR(s).
- See also: [dev/requirements/multiple_exam_versions.md](dev/requirements/multiple_exam_versions.md)

## Priority
## Priority
- Medium

## Owner / Stakeholders
## Owner / Stakeholders
- Owner: @username
- Stakeholders: instructors, exam authors, graders, platform admins, UX designers, QA

## Problem statement
## Problem statement
- Currently the framework and authoring tooling assume 4-answer multiple-choice questions. This limits the kinds of assessments authors can create (e.g., short-answer, essay, numeric parameterised problems, matching, and variable-choice questions). To support full exam authoring, grading workflows, and exports to LMS/PDF, promptukit must support a small set of additional canonical question types and a clear schema and validation path for them.

## Goals: Initial Expanded Problem Types as a Development Path
## Goals: Initial Expanded Problem Types as a Development Path
- Add first-class support for these question types: fill-in-the-blank, essay (manual grading), numeric/parameterised problems, matching, true/false, and variable-length MCQs.
- Provide a clear JSON schema extension and migration path so existing banks remain valid and authors can opt-in to new fields.
- Ensure authoring (CLI and API), validation, exporting, and grading pipelines support new types.
- Provide deterministic parameter sampling and answer calculation compatible with the existing randomization/seeding model used by `create_exam.py`.
- Support automated grading where reasonable (MCQ, TF, numeric, matching partial scoring) and manual grading workflows for essays.
- Maintain backward compatibility with current 4-choice MCQs and avoid data loss during migration.

## Non-goals
## Non-goals
- Build an automated essay-grading ML system. Essays will be surfaced to manual graders and optional rubric fields will be provided.
- Replace the entire export or LMS integration system in one change; initial work will target JSON/LTI-friendly exports and printable PDF/HTML previews.
- Redesign the UI/UX for large-scale authoring tools — this work focuses on data model, validation, CLI/API, and backend grading hooks; UX improvements will be a follow-up.

## Background / Context
## Background / Context
- promptukit currently models questions as fixed multiple-choice items (typically four choices). Many question banks include other formats or require numeric parameterisation (used elsewhere in the tool for randomized values). There is already randomization and seeding logic in `promptukit/exams/create_exam.py` and related modules; new question types should integrate with that deterministic model.
- Existing files to consider: [promptukit/questions/add_question.py](promptukit/questions/add_question.py), [promptukit/questions/validate_question.py](promptukit/questions/validate_question.py), [promptukit/questions/question_bank.py](promptukit/questions/question_bank.py), and the canonical question schema at [promptukit/data/question_banks/question_schema.json](promptukit/data/question_banks/question_schema.json).

## Assumptions
## Assumptions
- Question banks will continue to use unique stable `id` values per question.
- Existing MCQ items should remain valid; new `type` and `metadata` fields will be optional and backward compatible.
- Authors and graders prefer explicit, auditable data for auto-graded items (no opaque LLM scoring baked into artifacts by default).
- Numeric parameterisation uses deterministic seeding (exam id + seed) for reproducibility.
- The runtime environment will restrict evaluation of any expressions used to compute numeric answers (safe evaluator or sandboxed environment).

## User stories
## User stories
- As an instructor, I want to author numeric questions with parameter ranges, so that I can generate many unique exam instances without hand-editing values.
- As an exam author, I want to include short-answer (fill-in-the-blank) and matching questions, so that assessments can test recall and association beyond MCQs.
- As a grader, I want automatic grading for MCQs, TF, numeric questions, and partial scoring for matching, so that grading time is reduced while essays remain manual.
- As a content maintainer, I want the schema changes to be backward compatible, so that old banks still import and export correctly.
- As a platform admin, I want audit metadata (seed, computed values, and derivation) saved with generated exams, so regrading and troubleshooting are reproducible.

## Acceptance criteria (testable)
## Acceptance criteria (testable)
- Fill-in-the-blank (single token or short phrase):
	- Given a `fill_blank` question with one or more accepted answers (strings or regex), when the student submits an answer, then the grader returns `correct|incorrect` after normalising whitespace and case; regex matches succeed when provided.

- Essay:
	- Given an `essay` question, when a student submits text, then the submission is flagged as `manual_grade_required` and appears in the grader queue with any provided rubric.

- Numeric (parameterised):
	- Given a `numeric` question with parameter ranges and an expression, when an exam is materialised with seed S, then the question instance contains computed numeric values and an auto-generated numeric answer with tolerance metadata (abs/rel) in the answer key.

- Matching:
	- Given a `matching` item with N pairs, when grading in auto mode, then each correctly matched pair contributes configured partial credit and the answer key maps the canonical pairings.

- True/False and variable MCQs:
	- Given a `tf` or MCQ with variable choices, when the bank is validated, then the `choices` array may be any length ≥2 and the correct choice is unambiguously recorded with `correct_choice_id`.

- Integration & exports:
	- Given an exam containing new types, when exported to JSON/PDF/LMS formats, then the exported artifacts include the computed instance data, seed, and answer key (machine-readable) and preserve information needed for grading.

- Backwards compatibility:
	- Given an existing bank with MCQs only, when loaded by the updated code, then no data loss occurs and existing items validate under the extended schema.
- Then <expected outcome>

## Functional requirements
-- FR1: Data model: add `type` field to question schema with allowed values: `mcq`, `tf`, `fill_blank`, `essay`, `numeric`, `matching`. Extend schema files in [promptukit/data/question_banks/question_schema.json](promptukit/data/question_banks/question_schema.json).
- FR2: Authoring API/CLI: extend `promptukit/questions/add_question.py` to accept `--type`, `--choices`, `--answers`, `--rubric`, `--expression`, `--params`, and other type-specific fields; support JSON import and interactive prompts.
- FR3: Validation: extend `promptukit/questions/validate_question.py` to validate type-specific constraints (e.g., numeric expressions compile in safe mode, matching pairs are balanced, fill_blank has at least one accepted answer).
- FR4: Serialization: maintain backward compatible JSON export for MCQs; new fields are optional and ignored by older clients.
- FR5: Grading primitives: implement auto-graders for `mcq`, `tf`, `numeric` (with tolerances), and `matching` (partial scores). Provide a `manual_grade_required` flag for `essay` and optionally `fill_blank` when fuzzy matching is enabled.
- FR6: Randomization & parameterisation: integrate numeric parameter generation with existing seeding model in `exams/create_exam.py` so parameter values and resulting answers are deterministic given seed.
- FR7: Partial scoring: support per-pair scoring for `matching` and multi-select partial-credit rules for multi-answer MCQs.
- FR8: CLI flags & API: add `--question-type`, `--expression`, `--params`, `--tolerance`, and `--max-score` where applicable. Ensure programmatic API mirrors CLI.
- FR9: Exports: ensure answer keys (JSON/CSV) include explicit fields for `computed_values`, `correct_answer`, `tolerance`/`rubric`, and `manual_grade_required`.
- FR10: Backwards compatibility check: provide a migration linter and a CLI `validate-bank` command that reports deprecated/unknown fields and suggested fixes.
- FR2: ...

## Non-functional requirements
- Performance: authoring and validation operations should remain sub-second for individual questions; batch validation for a 10k question bank should complete in a reasonable timeframe (configurable). Numeric generation should add negligible overhead to exam materialisation.
- Security: expression evaluation must be sandboxed and disallow arbitrary code execution. All user-supplied rubric/answer text must be treated as untrusted input in export paths.
- Accessibility: exported PDFs/HTML should include alt-text and clear keyboard navigation markers for non-MCQ interactions.
- Scalability: support large banks (10k+ items) and bulk grading operations via batch APIs and streaming graders.
- Scalability

## Data & content considerations
-- Schema change: add optional `type`, `answers`, `rubric`, `expression`, `params`, `tolerance`, and `pairs` fields. Update [promptukit/data/question_banks/question_schema.json](promptukit/data/question_banks/question_schema.json) and provide a migration guide.
- Migration: provide a `bank:migrate` command that annotates legacy MCQs with explicit `type: mcq` and validates missing fields. Do not mutate authors' content by default — only offer a `--apply` option.
- Exports/Imports: ensure imports that do not understand new fields ignore them gracefully. Provide sample bank snippets and update README and `DATASETS.md`.
- Impact on existing data, schemas, and exports/imports.

## APIs / CLI / UX
- CLI examples:

```
python -m promptukit.questions.add_question --type numeric --id N1 \
	--text "Compute area for radius {r}" --expression "pi*r*r" \
	--params "r=rand(1,10)" --tolerance "0.01" --max-score 1
```

```
python -m promptukit.questions.add_question --type fill_blank --id F1 \
	--text "The capital of France is ____" --answers "Paris|paris|PARIS"
```

- Programmatic API: `Question(type='numeric', expression='...', params={...})` with `validate()` and `to_json()` helpers.
- UX: keep authoring CLI/JSON first; plan lightweight web UI additions later. Show `manual_grade_required` flags prominently when listing submissions.
- Proposed CLI flags, API endpoints, and UI flows.

## Implementation notes
- Code locations to touch:
	- [promptukit/questions/add_question.py](promptukit/questions/add_question.py) — extend CLI/import
	- [promptukit/questions/validate_question.py](promptukit/questions/validate_question.py) — validation rules
	- [promptukit/questions/question_bank.py](promptukit/questions/question_bank.py) — serialization, migration helpers
	- [promptukit/exams/create_exam.py](promptukit/exams/create_exam.py) — parameter sampling & deterministic generation
	- `promptukit/exams/graders.py` (new) — implement grading primitives and manual grading hooks

- Numeric evaluation: implement a small, safe evaluator that supports arithmetic, `min/max`, and deterministic `rand()` with seed. Prefer an existing audited library (e.g., `asteval` with restricted symbols) or a custom AST interpreter that only allows whitelisted nodes.
- Matching representation: store `pairs: [{left_id, right_id, left_text, right_text}]` and canonical `correct_pairs` for grading.
- Fill-blank answers: allow `answers` as a list of exact strings and optional `regex` entries. Provide normalization rules (unicode, case, punctuation) and document them.
- Rubrics: `rubric: [{criteria: 'clarity', max_score: 2}, ...]` for essays to assist manual graders.
- Testing: add example bank files under `dev/fixtures/` and unit tests under `dev/checks/`.
- Suggested code locations, modules to touch, and migration steps.

## Testing & QA
- Unit tests:
	- Validation tests for each type (missing fields, invalid expressions, malformed pairs).
	- Grader tests for MCQ/TF/numeric/matching, including edge cases and tolerances.
- Integration tests:
	- Materialise an exam with parameterised numeric questions with a fixed seed and assert computed values and answer keys.
	- Export-roundtrip tests (bank → exam → export → re-import where applicable).
- Property tests: randomised parameter ranges to ensure numeric generator respects bounds and seeds.
- Manual checks: spot-check essay submission flow and grader UI hooks.
- Unit tests, integration tests, property tests, and manual checks.

## Rollout / Migration plan
- Phase 1 (internal): add schema extensions and validators; implement CLI support and unit tests; land behind feature flag `new_question_types`.
- Phase 2 (pilot): enable for a small set of instructors; collect feedback and fix migration issues.
- Phase 3 (wider rollout): enable by default, provide `bank:migrate --apply` and update docs and dataset samples.
- Fallback: if migration issues occur, provide `bank:validate` and a restore path to previous bank snapshots.
- Steps for gradual rollout, feature flags, and fallback.

## Monitoring & Metrics
- Adoption metrics: percentage of new questions created with non-MCQ types.
- Error metrics: validation failures per bank import, expression-evaluation errors, grader failures.
- Grading metrics: time-to-grade per essay, auto-grade success rate for numeric/matching items.
- What to monitor and how to measure success.

## Security & Privacy
- Essay content and student-submitted text should be stored with the same protections as existing submission data (access controls, encryption at rest where configured).
- Expression evaluation must be sandboxed to prevent code execution; disallow network/file I/O in evaluator.
- Answer keys and computed values should be protected and exported only to authorized roles (graders/admins).
- Any sensitive data handling or access-control requirements.

## Risks & Mitigations
- Risk: insecure expression evaluation. Mitigation: use a whitelist AST evaluator or audited library and CI checks for known exploit patterns.
- Risk: increased grading burden from more essay/short-answer items. Mitigation: provide clear `manual_grade_required` flags, rubrics, and batching tools for graders.
- Risk: schema drift and broken imports. Mitigation: provide `validate-bank` linting, migration tool, and non-destructive `--apply` behavior.
- Identify risks and proposed mitigations.

## Alternatives considered
- Plugin architecture for custom question types: rejected for initial iteration because it increases complexity; revisit after core types stabilise.
- Delegate all non-MCQ types to external services (e.g., third-party graders): rejected for offline/paper exam workflows and auditability concerns.
- Short list of alternatives and why they were rejected.

## Open questions
- Which numeric expression language is acceptable (subset of Python, a DSL, or an existing expression library)? — Owner: @username
- Should `fill_blank` support multi-token cloze fields vs single-token blanks? — Owner: content team
- What is the default tolerance policy for numeric grading (absolute vs relative)? — Owner: assessment team
- Do we need an explicit `order` or numbering system that stays consistent across versions for references? — Owner: product
- List any unresolved questions and owners.

## References
- Question schema: [promptukit/data/question_banks/question_schema.json](promptukit/data/question_banks/question_schema.json)
- Example: [dev/requirements/multiple_exam_versions.md](dev/requirements/multiple_exam_versions.md)
- Code locations: [promptukit/questions/add_question.py](promptukit/questions/add_question.py), [promptukit/questions/validate_question.py](promptukit/questions/validate_question.py), [promptukit/exams/create_exam.py](promptukit/exams/create_exam.py)
- Links to relevant docs, schemas, and examples.
---
- Prefer concrete examples and small reproducible steps.
- When in doubt, add a minimal spike PR to validate feasibility.
