
🥷 Multiple exam versions (A–E) — requirements brainstorm

## Short title
- Multiple exam versions (A–E) with shuffled question order, shuffled choices, and optional per-version sampling.

## Author / Date
- Author: Copilot (GPT 5-mini) and josephRobertBob
- Date: 2026-04-18

## Status
- Draft

## Related issues / PRs
- (add issue links)

## Priority
- High — reduces cheating and simplifies grading for mixed-version exams.

## Owner / Stakeholders
- Owner: TBD
- Stakeholders: instructors, exam authors, proctors, graders, platform admins

## Problem statement
- We need to produce multiple labeled versions of the same exam (e.g., A,B,C,D,E) to reduce collusion.
- We want to enable flexibility when using the tool. Multiple options for creating multiple exams should be available. Initial ideas include: present the same questions in a different order; for multiple-choice items, shuffle the answer choices while preserving the correct answer mapping; or create different test versions that each have N questions from a particular category, where each version has a different set of questions (sampling mode).

## Goals
- Generate N labeled versions (default 5: A–E), or support per-version sampled exams with configurable question counts and category distributions.
- Ensure fairness: no change to question content or difficulty; maintain balanced coverage across versions when sampling is enabled.
- Produce machine-readable answer keys and human-friendly keys; include per-version question lists when sampling.
- Allow deterministic reproduction (seeded generation) for auditing and regrading.
- Expose options to customize the process (shuffling, sampling, category constraints, output formats).

## Non-goals
- Changing question text or distractor content to alter difficulty.
- Randomly removing or adding questions unless per-version sampling is explicitly enabled (sampling must be configured and auditable).

## Background / Context
- Current exam creation workflow produces a single canonical exam. Instructors request multiple labeled variants for in-person and remote proctored environments.

## Assumptions
- Question bank contains stable question IDs.
- Multiple-choice questions include a list of choices with an indicator of the correct choice (id or index).
- Questions may include metadata flags: `shuffle_choices: true|false`, `group_id` for multi-part grouping, and `categories` or `tags` for sampling.

## User stories
- As an instructor, I want to generate 5 labeled versions so students get different orderings and choices, reducing cheating.
- As an instructor, I want versions where each version has N questions sampled from specific categories so cohorts receive different but balanced subsets.
- As a grader, I want machine-readable answer keys per version to bulk grade submissions.
- As an admin, I want generation logs so we can audit which seed/user produced which versions.

## Acceptance criteria (testable)
- Given a canonical exam and seed S, generating versions A–E produces output files that satisfy the configured mode:
  - Default (shuffle-only): each version contains the same set of question IDs; only question order and choice order vary per version.
  - Sampling-enabled: each version contains the configured number of questions and satisfies the requested category distribution; versions may contain different sets of question IDs.
- For all modes:
  - Question ordering differs between at least 90% of positions across versions (configurable threshold), unless sampling produces different counts.
  - For MCQs with `shuffle_choices=true`, the choice order is shuffled and the correct answer is updated in the generated answer key.
  - Generation is deterministic given the same seed and inputs (ordering and selection reproducible).
  - Output includes: per-version exam JSON (annotated with `original_position`, `version_position`, `included_questions`), per-version human-readable PDF/HTML, per-version answer key (JSON/CSV), and a sampling report when sampling is used.
  - When sampling with uniqueness enforced, no question appears in more than one version; if duplicates are allowed, document and surface that in the sampling report.

## Functional requirements
- FR1: Version count and labels: support `--versions N` and `--labels` override; default labels A,B,C,D,E when N=5.
- FR2: Question order shuffling per version: random permutation of question list respecting `group_id` constraints.
- FR3: Choice shuffling: for each question where `shuffle_choices` is true, randomize the order of choices and update correct mapping in answer key.
- FR4: Deterministic generation: accept a `--seed` parameter; default derivation uses exam id + label to generate consistent results per label — applies to both ordering and sampling/selection.
- FR5: Output formats: JSON (internal), PDF (printable), HTML (preview), and CSV/JSON answer key.
- FR6: Answer keys: include mapping from original `question_id` -> `new_choice_id` and `new_choice_index`, and include the per-version `included_questions` list and seed/metadata.
- FR7: Preserve non-shuffle flags: questions with `shuffle_choices=false` or explicit fixed positions remain unchanged.
- FR8: Group preservation: questions sharing a `group_id` must remain contiguous and preserve internal order unless overridden; groups act as atomic units for sampling when configured.
- FR9: CLI/API: expose options `--versions`, `--labels`, `--seed`, `--preserve-groups`, `--output-dir`, `--formats`, `--force`, plus sampling options (see FR12).
- FR10: Preview mode and QA report: produce a sample student view and a report of collisions/duplicate versions and sampling statistics.
- FR11: Logging & audit: record parameters, user, timestamp, seed, and checksums of outputs and sampling reports.
- FR12: Per-version sampling: support `--sample-mode {none,per-version}`, `--questions-per-version <N>`, `--category-distribution <cat:count,...>`, `--sample-strategy {random,stratified,round-robin}`, and `--allow-duplicates`.
- FR13: Sampling balance & validation: provide options to ensure per-version category balance and fail-fast with clear messages if constraints cannot be satisfied given the bank size.
- FR14: Uniqueness and coverage controls: allow `--ensure-unique-questions-across-versions` to avoid overlap, plus `--max-duplicate-allowed` as a tolerance parameter.

## Non-functional requirements
- NFR1: Performance: generating 5 versions for a 100-question exam should complete within X (configurable) seconds on standard dev hardware.
- NFR2: Reproducibility: given same inputs and seed, outputs must be identical (bit-for-bit JSON when stable export is chosen).
- NFR3: Security: answer keys stored separately; restrict key access to graders/admins.
- NFR4: Scalability: support large banks and batch-generation (e.g., generate 50 labeled versions for many cohorts).

## Data & content considerations
- Input schema expectations: each question must include unique `id`, `choices` (each choice with `id` and `text`), and a `correct_choice_id` or `correct_choice_index`.
- For sampling mode, each question should include `categories` (list of category tags), optional `difficulty` or `weight`, and an `available` flag.
- Output should annotate each question with `original_position`, `version_position`, `choice_order` mapping, and for sampling mode include `included_in_versions` metadata.

## APIs / CLI / UX
- CLI example (shuffle-only):

```
python -m promptukit.exams.create_exam \
  --bank promptukit/data/question_banks/crb-water-management-sample.json \
  --versions 5 --labels A,B,C,D,E --seed 12345 \
  --output-dir output/exams/multi --formats json,pdf,csv
```

- CLI example (sampling-enabled):

```
python -m promptukit.exams.create_exam \
  --bank promptukit/data/question_banks/crb-water-management-sample.json \
  --versions 5 --sample-mode per-version --questions-per-version 50 \
  --category-distribution math:20,verbal:30 --sample-strategy stratified \
  --ensure-unique-questions-across-versions --seed 12345 \
  --output-dir output/exams/multi --formats json,pdf,csv
```

- Programmatic API example:

```
generate_versions(
  bank,
  versions=5,
  labels=["A","B","C","D","E"],
  seed=12345,
  sample_mode='per-version',
  questions_per_version=50,
  category_distribution={'math':20,'verbal':30},
  sample_strategy='stratified',
)
```

## Implementation notes
- Use a deterministic PRNG seeded per exam+label (e.g., HMAC(exam_id + label, global_secret) => seed). Apply the same deterministic seed for both ordering and selection to allow reproducible debugging.
- Shuffle algorithm: Fisher–Yates on question index array for order shuffling; for grouped questions use group-level units.
- Sampling algorithms:
  - `random`: pseudo-random sampling without stratification.
  - `stratified`: sample per category counts (preferred to maintain balance).
  - `round-robin`: rotate windows across the bank to maximize coverage across versions.
- When sampling, track and output explicit `included_questions` per version and a sampling report that records why a question was selected/omitted.
- Validation: pre-check bank size vs requested sampling constraints and fail with clear diagnostic messages when constraints cannot be met.
- For choices: shuffle list of choice objects and update `correct_choice_id` by tracking choice `id`.
- Logging & audit: persist seed, parameters, user id, and checksums. Include sampling report in artifacts.

## Testing & QA
- Unit tests: shuffle preserves set of choices; correct choice remains present and marked.
- Sampling tests: validate per-version counts, category distributions, uniqueness constraints, and deterministic reproduction given a seed.
- Integration tests: full end-to-end generation with sample banks, check uniqueness and key integrity across modes.
- Property tests: varying seeds produce different permutations/selection; same seed reproduces identical output.
- QA preview: produce human-readable previews and a sampling statistics report for manual inspection before release.

## Rollout / Migration plan
- Start with a CLI flag behind a feature flag and small pilot with instructors.
- Collect feedback and iterate before enabling for all users.

## Monitoring & Metrics
- Metrics: versions generated, generation time, number of collisions detected, sampling distribution statistics, keys accessed.

## Security & Privacy
- Store answer keys in restricted storage; avoid embedding keys in student-facing PDFs.

## Risks & Mitigations
- Risk: shuffled or sampled order may accidentally place dependency questions apart — mitigate with `group_id` and QA preview; default to shuffle-only until sampling is validated.

## Alternatives considered
- Per-student randomization at delivery time (more complexity for grading) vs fixed labeled versions (simpler grading) vs sampled labeled versions (hybrid).

## Open questions
- What is the target max versions per exam? (5 vs per-student)
- Should numbering (question numbers) be global or per-version (i.e., should references in explanations match across versions)?
- What is the default `sample_strategy` and should `ensure-unique-questions-across-versions` be on by default?

## Example data snippets

Input (excerpt):

```
{
  "id": "Q1",
  "text": "What is 2+2?",
  "choices": [
    {"id":"c1","text":"3"},
    {"id":"c2","text":"4"},
    {"id":"c3","text":"5"}
  ],
  "correct_choice_id": "c2",
  "shuffle_choices": true,
  "categories": ["arithmetic","easy"],
  "available": true
}
```

Generated answer key (version A, excerpt):

```
{
  "version_label": "A",
  "seed": 12345,
  "included_questions": ["Q1","Q3","Q5"],
  "answers": [
    {"question_id":"Q1","correct_choice_id":"c2","correct_index":1}
  ]
}
```

## Next steps
- Agree on constraints (grouping rules, default labels, sampling defaults, and output formats).
- Implement CLI flags, deterministic seeding strategy, and sampling algorithms.
- Add unit/integration/sampling tests and run a small pilot with sample exams.

