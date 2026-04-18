🥷 Feature / Requirement Template

Use this template for filing new feature requests or requirements. Create a new markdown file under `dev/requirements/` named after the feature (for example `multiple_exam_versions.md`) and fill the sections below.

---

## Short title
- One-line summary of the feature or requirement.

## Author / Date
- Author: 
- Date: YYYY-MM-DD

## Status
- Draft / Proposed / Accepted / Rejected / Implemented

## Related issues / PRs
- Link to issue(s) or PR(s).

## Priority
- Low / Medium / High / Critical

## Owner / Stakeholders
- Owner: @username
- Stakeholders: list of teams or roles

## Problem statement
- What is the problem we are solving? Keep this short and factual.

## Goals
- What success looks like — the measurable outcomes.

## Non-goals
- What we will explicitly NOT do as part of this work.

## Background / Context
- Any relevant background, constraints, or history.

## Assumptions
- What assumptions are being made about data, users, or systems.

## User stories
- As a [persona], I want [capability], so that [benefit].

## Acceptance criteria (testable)
- Use clear, verifiable criteria. Prefer Gherkin-style examples:

- Given <context>
- When <action>
- Then <expected outcome>

## Functional requirements
- FR1: ... (clear, numbered list)
- FR2: ...

## Non-functional requirements
- Performance
- Security
- Accessibility
- Scalability

## Data & content considerations
- Impact on existing data, schemas, and exports/imports.

## APIs / CLI / UX
- Proposed CLI flags, API endpoints, and UI flows.

## Implementation notes
- Suggested code locations, modules to touch, and migration steps.

## Testing & QA
- Unit tests, integration tests, property tests, and manual checks.

## Rollout / Migration plan
- Steps for gradual rollout, feature flags, and fallback.

## Monitoring & Metrics
- What to monitor and how to measure success.

## Security & Privacy
- Any sensitive data handling or access-control requirements.

## Risks & Mitigations
- Identify risks and proposed mitigations.

## Alternatives considered
- Short list of alternatives and why they were rejected.

## Open questions
- List any unresolved questions and owners.

## References
- Links to relevant docs, schemas, and examples.

---

Tips:
- Keep acceptance criteria small and testable.
- Prefer concrete examples and small reproducible steps.
- When in doubt, add a minimal spike PR to validate feasibility.
