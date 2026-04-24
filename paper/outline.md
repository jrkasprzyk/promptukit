# Handoff

After editing on 4/23, here are some open questions or points to edit next time:

**Decide the role of cven5393 (and use it consistently)**
Is it just an example, or your proof that this already works in practice? This decision affects Abstract, State of the Field, and Availability.

**Sharpen the “authoring layer vs LMS/autograder” sentence**
This is your core intellectual contribution. If this is fuzzy, the whole paper feels fuzzy.

**Add a 1–2 sentence framing at the start of “State of the Field”**
Just say what you’re comparing and why. Without this, the sections feel like a list instead of an argument.

# Abstract

`promptukit` is a Python package for authoring, validating, managing, and rendering structured assessment and instructional materials from plain-text source files. It supports question banks, worked examples, exams, and quiz documents through a local workflow that combines command-line tools, Python/Jupyter helpers, a browser-based authoring interface, validation utilities, and PDF generation.

- [ ] Clarify what “structured” specifically means (schema? JSON-based? typed objects?)

- [ ] Consider briefly distinguishing assessment vs instructional materials with an example (e.g., exams vs worked examples)

- [ ] Add one concrete example artifact (e.g., “a parameterized exam question with auto-validated solution) -- this could be a place to reference the `cven5393` repo, and a benefit of that is that it has years of commit history at this point

## Intended Audience
The package provides reusable, version-controlled educational artifacts that are open source and controlled by the course's instructors, course assistants, and students. The tool can be used outside of, or as a complement to, a full learning-management or assessment platform. Unlike static word-processor or spreadsheet workflows, `promptukit` represents questions and related instructional materials as structured data that can be inspected, diffed, validated, transformed, and rendered into final documents. When appropriate, these source files can call reusable domain libraries, such as engineering analysis packages, for parameter generation, solution computation, visualization, or answer-key validation.

This design is especially useful for AI-assisted authoring workflows, where generated or revised questions must be reviewed, normalized, checked, and incorporated into durable course materials. `promptukit` provides a lightweight open-source layer between informal local authoring and larger online assessment systems: it does not replace learning-management platforms or autograders, but instead helps instructors build auditable, reusable source materials that can be rendered, reviewed, and maintained over time.

- [ ] Tighten or clarify the distinction between “authoring layer” vs LMS/autograder (maybe one sharper contrast sentence)

- [ ] Consider adding a brief example of calling a domain library (e.g., parasolpy generating parameters)



# State of the Field

- [ ] Add framing paragraph to explicitly state comparison criteria

- [ ] Check balance of tone

Many instructional assessment workflows begin as word-processor documents, spreadsheets, or ad hoc scripts. These formats are familiar, but they make it difficult to reuse questions across courses, validate item structure, generate multiple document formats, or track revisions with version control. The following sections will briefly review tool-assisted workflows with the goal of making education management easier. Specifically we discuss online assessment platforms; domain-specific engineering software; and ad-hoc professor-authored notebooks.

## Online assessment platforms

Examples: PrairieLearn, WeBWorK, Moodle, etc.

They are good at: delivery, grading, randomization, course management

But they are not primarily designed as: a **local authoring layer** around reusable engineering domain packages.

- [ ] Clarify whether 'local authoring layer' is the key differentiator

## Domain-specific engineering software

Examples: general use domain-specific software for simulation model analysis, optimization, and scientific inquiry. parasolpy is a Python package developed by the author and his students, included as a dependency here for demonstration purposes.

They are good at: computation, domain modeling, reusable code

But they do not directly provide: assessment item structure, answer-key rendering, learning-objective metadata

- [ ] Clarify whether `parasolpy` is required or just an example dependency -- we could put it in its own category of dependency if we want. Perhaps break out the repo structure into more domain examples and keep the `promptukit` material clean, kind of like the integration with the `cven5393` repo -- should that be mentioned somewhere too? I'll add a comment at the beginning too.

## Ad-hoc notebooks and scripts

These are good at fast local experimentation, but they do not share a consistent source format, a reproducible build process, and artifact packaging. This is especially problematic if students lose access to the learning management system after graduation. 

## Emerging AI-assisted workflows

When using AI-assisted workflows, generated or revised questions need to be reviewed, audited, normalized, and incorporated into durable course materials. `promptukit` addresses this need by representing question banks as structured data and providing tools for authoring, validation, extraction, and document generation. We envision a flexible educational workflow that blends legacy textbook and published resources with both human- and AI-authored content where both humans and AI agents can collaborate on validation.

- [ ] Think of how this could be framed in a similar structure

# Contribution

promptukit is a source-based authoring layer that turns reusable engineering code into checked assessment items and worked lecture examples. We implement features from paid ecosystems but in a local, open source format that allows future collaborators to add functionality and use within their own codebases.

The package is intended for instructors, teaching assistants, and educational developers who want lightweight, local control over assessment materials without adopting a full learning-management or assessment platform.

# Functionality

Describe:
- structured JSON question banks
- CLI tools
- validation
- GUI
- notebook/Python API
- PDF exam and pub quiz generation
- AI-compatible Claude Code slash-command support

# Example workflow

1. Draft or import questions
2. Store them in structured JSON
3. Validate the bank
4. Review or edit through GUI/CLI
5. Extract subsets
6. Generate printable assessment documents
7. Version-control changes

# Availability

PyPI, GitHub, MIT license, Python version support, docs/examples.

promptukit at pypi: https://pypi.org/project/promptukit/

promptukit GitHub repo: https://github.com/jrkasprzyk/promptukit

documentation: within the GitHub repo (currently)

# AI use and verification

See `ai-use-log.md` in this repo for more information.

- [ ] consider summaries of that md document in 1-2 sentences

- [ ] clarify what verification entails