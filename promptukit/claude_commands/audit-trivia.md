Audit a promptukit question bank for correctness and quality. Default target: `promptukit/data/question_banks/jrb_industries_trivia.json`. If the user names a different bank, audit that instead. This is a human/AI pipeline — LLM judgment as a linter for prose content, the same way you'd use ESLint for JavaScript.

## Question types in scope

Banks may contain mixed types. Check the `question_type` field on each question. Supported types and their fields (see `promptukit/questions/question_models.py`):

- `MultipleChoice` — `choices` (list), `answer` (int index / letter / text)
- `TrueFalse` — `answer` (bool)
- `ShortAnswer` — `answer` (string)
- `FillInTheBlank` — `prompt` with `___`, `answers` (list)
- `Matching` — `pairs` (list of `[left, right]`)
- `Calculation` — `answer` (number), optional `tolerance`, `unit`

Questions without a `question_type` field can be inferred (see `promptukit/utils/json_tools.py:infer_question_type`). If many are missing the tag, recommend running migration before auditing:

```bash
.venv/Scripts/python -m promptukit.questions.question_bank migrate \
  --src <path>
```

## Steps

### 1. Run the automated validator

```bash
.venv/Scripts/python -m promptukit.questions.validate_question \
  promptukit/data/question_banks/jrb_industries_trivia.json
```

Report errors and warnings it surfaces before continuing.

Caveat: the validator currently hardcodes MCQ rules (4 choices, answer 0–3). For mixed-type banks it will produce spurious errors on non-MCQ questions. Note which reported errors are real vs. expected-for-type.

### 2. Read the full question list

Read the bank file. Group findings by check below. Apply type-specific checks only to questions of that type.

---

### Check A — Category correctness

The category list grows over time. Don't flag new categories, but verify the file's `"categories"` array stays in sync with what's actually used. For each question, ask: does the subject matter fit the stated category? Flag miscategorizations and suggest the better category (e.g. a question filed under `music` whose subject is really film soundtracks).

---

### Check B — Content quality (all types)

**Lauren's Time-Sensitive Rule.** Any question whose answer could change over time — words like "last", "latest", "current", "most recent", "first active", "reigning", "current holder", "current record" — **must** begin with `"As of [year],"`. Flag missing qualifiers and propose the corrected prompt.

**Education Rule.** Quips should teach something — a fun fact, correction, or context. Some purely comedic quips are fine, but the educational aspect should dominate. Flag pure throwaway quips with no informational value.

**Prompt clarity.** Reject prompts where the answer is embedded in the prompt text. Reject ambiguous phrasing where more than one choice is defensible.

---

### Check C — Type-specific structural checks

**MultipleChoice**
- Exactly 4 `choices` (flag fewer / more).
- `answer` resolves to a valid choice (int in `[0, len-1]`, letter within range, or exact choice text).
- No two choices functionally synonymous.
- No absurd distractors (e.g. 'Which planet is closest to the sun? A) Saturn B) The Moon C) Mercury D) A Toaster').
- Distractors from the same domain as the correct answer.
- Track answer index distribution across the bank; flag if any letter is overrepresented (>1.6× expected).

**TrueFalse**
- `answer` is a real boolean, not the string `"true"`/`"false"`.
- Avoid double negatives in the prompt.
- Balance true vs. false across the bank — flag heavy skew.

**ShortAnswer**
- `answer` is a non-empty string.
- Answer is unambiguous — if multiple spellings / phrasings are equally valid, note in `quip_correct` or flag for a metadata-level alt-answers field.

**FillInTheBlank**
- Count of `___` tokens in `prompt` equals `len(answers)` exactly.
- Each blank has a defensible single answer (not open-ended).
- Answers are reasonably short (single word / short phrase).

**Matching**
- `pairs` is a list of 2-element lists, all non-empty strings.
- 3–6 pairs typical; flag outside that range.
- Left items are distinct; right items are distinct.
- No right-column item trivially matches multiple left-column items.

**Calculation**
- `answer` parses as a number.
- `tolerance` (if present) is a non-negative number.
- If the prompt involves units, the expected unit is stated in the prompt (and ideally in a `unit` field).
- Numeric precision of `answer` matches the tolerance (e.g. answer `28.274` with tolerance `0.05` is fine; answer `28.274334...` with tolerance `1` is over-precise).

---

### Check D — Answer correctness (all types)

Verify each stated answer is actually correct. Cross-check your own knowledge.
- **MCQ:** flag if `answer` points to the wrong choice; state the correct index and choice text.
- **TrueFalse:** flag if the bool is inverted.
- **ShortAnswer:** flag if the expected string is factually wrong.
- **FillInTheBlank:** flag any blank where the expected answer is wrong.
- **Matching:** flag any pair whose right-side mapping is wrong.
- **Calculation:** recompute and flag if the stated numeric answer is off by more than its `tolerance`.

If genuinely uncertain about a fact, flag as `NEEDS VERIFICATION` rather than guessing.

---

### 3. Report findings

```
AUTOMATED VALIDATOR
  <pass / list real errors; note any expected-for-non-MCQ>

TYPE BREAKDOWN
  MultipleChoice: <n>
  TrueFalse:      <n>
  ShortAnswer:    <n>
  FillInTheBlank: <n>
  Matching:       <n>
  Calculation:    <n>
  (untagged):     <n>

CATEGORY ISSUES  (or "None found")
  - <id> [<type>]: currently '<category>', suggest '<better>' — reason

TIME-SENSITIVE ISSUES  (or "None found")
  - <id> [<type>]: missing "As of [year]," — suggested fix: "<corrected prompt>"

CONTENT QUALITY ISSUES  (or "None found")
  - <id> [<type>]: <description>

STRUCTURAL ISSUES  (or "None found")
  - <id> [<type>]: <what's wrong with the type-specific shape>

ANSWER CORRECTNESS ISSUES  (or "None found")
  - <id> [<type>]: stated answer <x> appears wrong — correct answer is <y>
  - <id> [<type>]: NEEDS VERIFICATION — <what you're unsure about>
```

---

### 4. Apply fixes

After showing the report, ask the user which fixes to apply. Then:

- Apply approved fixes to the bank file.
- Re-run the validator to confirm clean (noting remaining expected-for-non-MCQ errors).
- Report final stats: total count, per-category breakdown, per-`question_type` breakdown.

## Important

- `promptukit/data/question_banks/jrb_industries_trivia.json` is the canonical source of truth — git-tracked, served via jsDelivr CDN. Do not move, rename, or gitignore it.
- When adding `"As of [year],"` use the year the answer was last verifiably correct — not necessarily the current year.
- Don't change answer positions or reformat choices unnecessarily — only fix what's actually wrong.
- Don't strip existing `question_type` tags, and don't add them speculatively; if untagged, prefer running the migrate command over guessing.
