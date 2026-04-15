# Skill: write-questions

Generate trivia/exam questions from source material and add them to a question bank using the promptukit CLI.

## Workflow

### 1. Understand the source material
Read the source (PDF, markdown, slides, plain text). Extract factual, testable claims — specific numbers, named concepts, definitions, relationships, and dates.

### 2. Know the target bank
- Read the destination JSON file to understand its `"categories"` list and existing questions.
- Check which categories already have questions so you can target under-represented ones.

### 3. Draft questions as a JSON array
Each object needs:
```json
{
  "category":   "<must match one of the bank's categories>",
  "difficulty": "easy|medium|hard",
  "prompt":     "The question text?",
  "choices":    ["Option A", "Option B", "Option C", "Option D"],
  "answer":     0,
  "quip_correct": "Short celebratory or fun fact (optional)",
  "quip_wrong":   "Short corrective hint (optional)"
}
```
- `answer` is the **0-based index** into `choices` of the correct answer.
- Do **not** include an `"id"` field — it is auto-assigned by the tool.
- Distribute correct answers across indices 0–3 to avoid skew (aim for roughly equal A/B/C/D split).
- Mix difficulty levels: roughly 40–50% easy, 30% medium, 20–30% hard.

### 4. Add questions via batch mode
Save the draft array to a temp file (or pipe it) and run:
```bash
python -m promptukit.add_trivia --batch questions_draft.json question_banks/your-bank.json
# or pipe directly:
cat questions_draft.json | python -m promptukit.add_trivia --batch - question_banks/your-bank.json
```

### 5. Validate
```bash
python -m promptukit.validate_trivia question_banks/your-bank.json
```
Fix any reported errors (missing fields, wrong category name, bad answer index, overrepresented answer letter).

### 6. Spot-check with extract
```bash
python -m promptukit.extract_trivia --file question_banks/your-bank.json --list-categories
python -m promptukit.extract_trivia --file question_banks/your-bank.json --category "<cat>" --fields prompt,answer
```

## Creating a new bank from scratch
```bash
python -m promptukit.trivia_tool create \
  --dest question_banks/my-new-bank.json \
  --categories "category-one,category-two"
```
Then follow steps 3–6 above.

## Question-writing guidelines
- **Easy**: recall of a single named fact (a number, a name, a definition).
- **Medium**: application or comparison (which tool does X, what does acronym Y mean).
- **Hard**: precise technical detail, edge case, or multi-step reasoning.
- Distractors should be plausible — wrong answers from the same domain, not nonsense.
- Keep prompts unambiguous; avoid "which of the following" when a direct question works.
- `quip_correct` / `quip_wrong` are shown in the game UI after answering — make them punchy and informative (one sentence each).
- Try to keep a balance of A, B, C, and D in your answer set.

## Key file locations (this repo)
- Question banks: `question_banks/`
- Schema reference: `question_banks/question_schema.json`
- Tools: `python -m promptukit.trivia_tool`, `promptukit.add_trivia`, `promptukit.extract_trivia`, `promptukit.validate_trivia`
- Default bank (block-doku game): `question_banks/block-doku-questions.json`

## Validator behavior
`validate_trivia` reads the `"categories"` array declared at the top of the bank file and uses that as the allowed set. If no `"categories"` key is present it falls back to the block-doku hardcoded set. Always declare categories in `trivia_tool create --categories` so the validator stays bank-specific.
