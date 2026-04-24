# MATLAB Interoperability Plan for PromptuKit

## Purpose

This document outlines a lightweight plan for adding MATLAB interoperability examples to PromptuKit. The goal is not to make MATLAB a dependency, nor to create a full MATLAB binding layer. Instead, the goal is to demonstrate that MATLAB users can keep existing scripts, teaching workflows, and numerical analyses in MATLAB while delegating prompt construction, templating, and AI-facing workflow logic to PromptuKit in Python.

This is especially useful for instructors, researchers, and engineers who already use MATLAB for modeling or visualization but want a reusable and inspectable Python layer for AI-assisted educational or analytical materials.

## Recommended Scope

Add a small, optional example under the repository's `examples/` directory:

```text
examples/
  matlab/
    README.md
    call_promptukit_from_matlab.m
    promptukit_api_example.py
```

The example should be documentation-focused and should not be included in core automated tests unless a MATLAB environment is available.

## Core Design Principle

The recommended direction is:

> MATLAB orchestrates the workflow; Python and PromptuKit handle reusable prompt logic.

This keeps the example simple and credible. MATLAB users do not need to rewrite their existing workflows, and PromptuKit remains a Python package with a clear, reusable API.

## Interoperability Options

### Option A: MATLAB Calls Python

This is the preferred path for the initial example.

MATLAB can call Python code using `py.`, `pyrun`, or `pyrunfile`. The MATLAB script can pass values or strings to a Python script, and the Python script can use PromptuKit to build or execute an AI-facing workflow.

This approach is best when:

- A MATLAB user already has data, simulations, or teaching scripts in MATLAB.
- Prompt construction and AI workflow logic should live in reusable Python code.
- The example should remain small and easy to understand.

### Option B: Python Calls MATLAB

Python can also call MATLAB through the MATLAB Engine API for Python. This is useful when a Python workflow needs to call legacy `.m` code or MATLAB-specific routines.

This is not recommended for the first example because it requires more setup and makes the example feel heavier. It may be worth documenting later as an advanced pattern.

## Proposed Example Narrative

A MATLAB user has generated numerical results from a model or teaching example. They want to generate a short student-facing explanation of those results using a reusable PromptuKit prompt template.

For example, a water resources instructor might compute design performance metrics in MATLAB, then call a Python PromptuKit script to produce an explanation suitable for students.

The example should show:

1. MATLAB defines or computes input values.
2. MATLAB calls a Python script using `pyrunfile`.
3. The Python script uses PromptuKit to format or run a prompt workflow.
4. MATLAB receives and displays the result.

## Example MATLAB Script

File: `examples/matlab/call_promptukit_from_matlab.m`

```matlab
% call_promptukit_from_matlab.m
%
% Demonstrates how a MATLAB workflow can call a small Python script that uses
% PromptuKit for reusable prompt construction or AI-facing workflow logic.
%
% Requirements:
%   1. MATLAB configured with a Python environment.
%   2. PromptuKit installed in that Python environment.
%   3. The Python example file available in the same directory.

% Optional: explicitly select the Python environment.
% Uncomment and edit this line if MATLAB is not already using the desired Python.
% pyenv("Version", "path/to/python");

% Example values from a MATLAB-side analysis or teaching workflow.
flow_mgd = 125.4;
cost_usd = 8.91e6;
reliability = 0.93;

% Construct a compact task description for the Python prompt workflow.
task = sprintf([ ...
    "Explain this water-system design for undergraduate students. " + ...
    "The design has flow %.1f MGD, cost $%.2g, and reliability %.2f."], ...
    flow_mgd, cost_usd, reliability);

% Call the Python script and retrieve the variable named "response".
response = pyrunfile("promptukit_api_example.py", "response", task=task);

% Display the response in MATLAB.
disp(string(response));
```

## Example Python Script

File: `examples/matlab/promptukit_api_example.py`

```python
"""Minimal Python-side PromptuKit example called from MATLAB.

This file is intentionally small. It demonstrates the boundary between a
MATLAB-side workflow and a reusable Python prompt workflow.
"""

# Replace these imports and calls with the actual PromptuKit API.
# The structure below is illustrative.

try:
    from promptukit import PromptTemplate
except ImportError as exc:
    raise ImportError(
        "PromptuKit must be installed in the Python environment used by MATLAB."
    ) from exc


# MATLAB passes `task` into this script through pyrunfile.
# If the script is run directly from Python, provide a fallback task.
try:
    task
except NameError:
    task = "Explain Pareto optimality for an undergraduate engineering class."


template = PromptTemplate(
    system="You are a concise engineering educator.",
    user="{task}",
)

# Depending on PromptuKit's API, this may be render(), run(), format(), etc.
# The initial example can demonstrate prompt construction only, even without
# making a live model call.
response = template.render(task=task)
```

## Example README Outline

File: `examples/matlab/README.md`

```markdown
# MATLAB Interoperability Example

This example demonstrates how a MATLAB workflow can call Python code that uses
PromptuKit for reusable prompt construction or AI-facing workflow logic.

## Why this example exists

Many instructors and researchers already use MATLAB for simulation, analysis,
and classroom demonstrations. PromptuKit does not replace those workflows.
Instead, it can provide a reusable Python layer for prompt templates,
structured AI interactions, and educational content generation.

## Requirements

- MATLAB with Python interoperability enabled.
- A Python environment visible to MATLAB.
- PromptuKit installed in that Python environment.

## Files

- `call_promptukit_from_matlab.m`: MATLAB-side driver script.
- `promptukit_api_example.py`: Python-side PromptuKit workflow.

## Running the example

From MATLAB, navigate to this directory and run:

```matlab
call_promptukit_from_matlab
```

If MATLAB is using the wrong Python environment, edit the `pyenv` line in the
MATLAB script.

## Notes

This is an optional interoperability example. MATLAB is not required to install
or use PromptuKit.
```

## Packaging Guidance

Do not add MATLAB to the package dependencies. The interoperability example should be optional and should not affect normal installation.

Recommended packaging treatment:

- Include the example files in the source repository.
- Mention the example in the documentation.
- Avoid importing MATLAB-related code from PromptuKit itself.
- Do not run this example in standard CI unless MATLAB is available.

## Testing Strategy

For the first version, testing can be documentation-based:

- Ensure the Python script can run directly with a fallback task.
- Ensure the example imports the real PromptuKit API correctly.
- Optionally add a lightweight Python-only test for the Python script.
- Do not require MATLAB in CI.

If MATLAB access is available later, an optional integration test could verify that MATLAB can call `pyrunfile` successfully.

## Documentation Notes

The documentation should emphasize that this example demonstrates interoperability, not a full MATLAB interface.

Suggested phrasing:

> This example shows how MATLAB users can call PromptuKit-based Python workflows from existing MATLAB scripts. This can be useful in teaching and research contexts where numerical analysis remains in MATLAB, while reusable prompt construction and AI-facing workflow logic are handled in Python.

## Potential JOSS Relevance

This example supports a broader software story:

- PromptuKit can work alongside existing domain tools.
- Users are not forced into a platform or a new end-to-end environment.
- Instructors can preserve familiar workflows while adopting reusable AI-assisted authoring patterns.
- The package can serve as a bridge between domain computation and structured educational content generation.

This helps frame PromptuKit as an interoperability-oriented tool rather than a closed instructional platform.

## Future Extensions

Possible later examples could include:

- MATLAB-generated plots or result summaries passed into a PromptuKit workflow.
- A Python workflow that calls MATLAB through the MATLAB Engine API.
- A classroom example where MATLAB simulation outputs are converted into quiz prompts or concept explanations.
- A comparison between direct ad hoc prompting and reusable PromptuKit templates.

## Initial Implementation Checklist

- [ ] Create `examples/matlab/`.
- [ ] Add `README.md` explaining the goal and setup.
- [ ] Add `call_promptukit_from_matlab.m`.
- [ ] Add `promptukit_api_example.py` using the actual PromptuKit API.
- [ ] Confirm the Python script runs without MATLAB using a fallback task.
- [ ] Optionally test the full MATLAB call manually.
- [ ] Link the example from the main documentation or examples index.
