Add questions to a promptukit question bank. The default target is the JRB Industries trivia bank, but these workflows apply to any bank in `promptukit/data/question_banks/`.

## Canonical file

```
promptukit/data/question_banks/jrb_industries_trivia.json
```

Git-tracked, served via jsDelivr CDN — treat as production content. Other banks (e.g. `general-water-management-sample.json`, `dev-unaware-challenge.json`) follow the same shape; pass the target path when invoking the CLI tools.

## Question types

The repo now supports multiple question types. Each question carries a `question_type` tag and type-specific fields. Supported types (see `promptukit/questions/question_models.py`):

| `question_type`   | Required fields                          | Notes |
|-------------------|------------------------------------------|-------|
| `MultipleChoice`  | `prompt`, `choices` (list), `answer`     | `answer` is 0-based index, or letter `"A"..`, or choice text. |
| `TrueFalse`       | `prompt`, `answer` (bool)                | `true` / `false`. |
| `ShortAnswer`     | `prompt`, `answer` (string)              | Free-text expected answer. |
| `FillInTheBlank`  | `prompt` (uses `[blank]`), `answers` (list)  | One answer per blank, in order. |
| `Matching`        | `prompt`, `pairs` (list of `[l, r]`)     | Pair order is the canonical match. |
| `Calculation`     | `prompt`, `answer` (number)              | Optional `tolerance` (number), `unit` (string). |

The `jrb_industries_trivia.json` bank is currently all `MultipleChoice`; other banks may mix types. If the target file has no `question_type` tags, run migration first:

```bash
.venv/Scripts/python -m promptukit.questions.question_bank migrate \
  --src promptukit/data/question_banks/<file>.json
```

## Workflow

### 1. Choose a question type

Ask the user which type(s) to add. For the JRB trivia bank, default to `MultipleChoice` unless the user says otherwise.

### 2. Choose a mode

- **Topic mode** — user names a topic (e.g. "90s hip-hop") and you draft 3–5 questions across difficulties.
- **Bulk mode** — user names a category and a count; you generate that many questions.
- **Dictation mode** — user provides a fully-formed question; you format it into the JSON schema.
- **Source material mode** — user provides a PDF / markdown / plain text; extract testable factual claims and write questions from them.

Source material mode: read the source carefully, identify numbers, named concepts, definitions, relationships, dates. Prefer testable facts over vague claims.

### 3. Draft questions

Read the bank file first. Check existing categories and (for MCQ) current answer index distribution before picking positions.

Common fields on every question:

```json
{
  "question_type": "<one of the types above>",
  "category":      "<must match the bank's declared categories>",
  "difficulty":    "easy|medium|hard",
  "prompt":        "The question text?",
  "quip_correct":  "Short, punchy — ideally teaches something.",
  "quip_wrong":    "Short corrective hint."
}
```

Do **not** include an `"id"` field — it's auto-assigned by the CLI. `quip_correct` / `quip_wrong` are shown in the game UI after answering; keep them punchy and educational where possible.

Type-specific shapes:

**MultipleChoice**

```json
{
  "question_type": "MultipleChoice",
  "choices": ["A", "B", "C", "D"],
  "answer":  0
}
```

- `choices` commonly 4 strings.
- `answer` is the 0-based index.
- Distribute correct answers across A/B/C/D roughly evenly.
- Mix difficulties: ~40–50% easy, ~30% medium, ~20–30% hard.
- Distractors must be plausible, same-domain, not absurd.
- Avoid embedding the answer in the prompt. Avoid synonymous choices.

**TrueFalse**

```json
{
  "question_type": "TrueFalse",
  "answer": true
}
```

- Balance true vs. false across a set. Avoid double negatives.

**ShortAnswer**

```json
{
  "question_type": "ShortAnswer",
  "answer": "Pharos of Alexandria"
}
```

- Answer should be unambiguous. If multiple spellings/phrasings are valid, note in `quip_correct` or a metadata field.

**FillInTheBlank**

```json
{
  "question_type": "FillInTheBlank",
  "prompt":  "The [blank] is the largest [blank] of the Solar System.",
  "answers": ["Sun", "star"]
}
```

- Each `[blank]` in `prompt` corresponds to one entry in `answers`, in order. Counts must match.

**Matching**

```json
{
  "question_type": "Matching",
  "prompt": "Match each country to its capital.",
  "pairs":  [["France", "Paris"], ["Japan", "Tokyo"], ["Egypt", "Cairo"]]
}
```

- Pair order is the canonical correct matching; the game UI shuffles the right column.
- Keep 3–6 pairs. More than 6 gets clumsy.

**Calculation**

```json
{
  "question_type": "Calculation",
  "prompt":    "What is the area of a circle with radius 3? (in m²)",
  "answer":    28.27,
  "tolerance": 0.05,
  "unit":      "m^2"
}
```

- `tolerance` accepts an absolute margin of error. Default 0 if omitted.
- Put the expected unit in the prompt as well; `unit` is metadata.

### 4. Show and get approval

Present drafts in a readable format. Get approval before writing anything.

### 5. Add to the bank

**MultipleChoice — batch mode (supported):**

```bash
.venv/Scripts/python -m promptukit.questions.add_question --batch questions_draft.json \
  promptukit/data/question_banks/jrb_industries_trivia.json
```

Or pipe:

```bash
cat questions_draft.json | .venv/Scripts/python -m promptukit.questions.add_question --batch - \
  promptukit/data/question_banks/jrb_industries_trivia.json
```

The batch tool auto-assigns IDs, inserts after the last question of the same category, and auto-adds new categories. It requires: `category`, `difficulty`, `prompt`, `choices`, `answer`. Optional: `quip_correct`, `quip_wrong`. Any `"id"` in input is ignored.

**Non-MCQ types (manual edit):**

`add_question.py` currently handles MCQ only. For `TrueFalse`, `ShortAnswer`, `FillInTheBlank`, `Matching`, `Calculation`:

1. Edit the bank JSON directly — append the new question object(s) to the `questions` array (or the appropriate `sections[].questions` for section-shaped banks).
2. Assign IDs following the existing convention in that bank (e.g. `category_014`).
3. Insert after the last question sharing the same category.
4. If introducing a new category, add it to the top-level `"categories"` list.
5. Ensure every new entry has `"question_type": "<Type>"`.

### 6. Validate

```bash
.venv/Scripts/python -m promptukit.questions.validate_question \
  promptukit/data/question_banks/jrb_industries_trivia.json
```

Caveat: the validator currently hardcodes MCQ rules (4 choices, 0–3 answer index). It will flag non-MCQ questions as errors. For mixed-type banks, read the reported errors with that in mind and treat non-MCQ "errors" as expected until the validator is updated.

Fix real issues: missing fields, wrong category name, bad answer index, overrepresented answer letter (MCQ), placeholder text.

### 7. Spot-check with extract

```bash
.venv/Scripts/python -m promptukit.questions.extract_question \
  --file promptukit/data/question_banks/jrb_industries_trivia.json \
  --list-categories

.venv/Scripts/python -m promptukit.questions.extract_question \
  --file promptukit/data/question_banks/jrb_industries_trivia.json \
  --category "<cat>" --fields prompt,answer
```

### 8. Report stats

Report: total count, per-category breakdown, per-`question_type` breakdown, answer distribution (MCQ only).

## Creating a new bank from scratch

```bash
.venv/Scripts/python -m promptukit.questions.question_bank create \
  --dest promptukit/data/question_banks/my-new-bank.json \
  --categories "category-one,category-two"
```

Then follow steps 1–8 above.

## Question-writing guidelines

- **Easy**: recall of a single named fact.
- **Medium**: application or comparison.
- **Hard**: precise technical detail, edge case, or multi-step reasoning.
- Quips should teach something — a fun fact, correction, or context. Purely comedic quips are fine occasionally but shouldn't dominate.
- If unsure about a fact, say so and let the user confirm — don't guess.
