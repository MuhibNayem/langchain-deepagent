---
phase: "03-planner-sprint"
plan: "02"
subsystem: planning
tags: [spec, user-stories, acceptance-criteria, feature-decomposition]

# Dependency graph
requires:
  - phase: "03-01"
    provides: "PlannerAgent with generate_spec, parse_json_response, parse_alternatives"
provides:
  - "SpecBuilder class with decompose(), generate_criteria(), build_spec()"
  - "Rule-based fallback when LLM unavailable"
  - "User story format validation (As-a-[role]-I-want-[feature]-so-that-[benefit])"
affects: [03-03, 03-04, 03-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [feature-decomposition, user-story-generation, rule-based-fallback]

key-files:
  created:
    - "luminamind/planner/spec_builder.py"
    - "tests/unit/test_spec_builder.py"
  modified: []

key-decisions:
  - "Used UserStory.from_dict() and AcceptanceCriterion.from_dict() instead of direct constructor to properly handle nested dataclass deserialization"
  - "Rule-based fallback extracts roles via keyword matching and features via stopword filtering"

patterns-established:
  - "Feature decomposition pattern: extract roles, features, then pair into user stories"
  - "As-a-[role]-I-want-[feature]-so-that-[benefit] format enforced in all outputs"

requirements-completed: ["PLAN-02"]

# Metrics
duration: 12min
completed: 2026-04-27
---

# Phase 03-02: SpecBuilder for Structured Spec Generation Summary

**SpecBuilder decomposes feature requests into user stories with acceptance criteria and verify methods**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-27T09:24:00Z
- **Completed:** 2026-04-27T09:36:09Z
- **Tasks:** 1 (TDD - RED test, GREEN impl, implicit REFACTOR)
- **Files modified:** 2

## Accomplishments
- SpecBuilder class with LLM-based and rule-based decomposition
- User stories follow "As a [role] I want [feature] so that [benefit]" format
- Acceptance criteria include specific verify_method pointing to test/command
- Full test coverage with 13 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: SpecBuilder core decomposition logic** - `48df86f` (feat)
   - Created luminamind/planner/spec_builder.py
   - Created tests/unit/test_spec_builder.py
   - TDD: RED test (spec_builder tests) → GREEN impl (SpecBuilder class)
   - All 13 tests passing

**Plan metadata:** `a17ca78` (docs: complete plan)

## Files Created/Modified
- `luminamind/planner/spec_builder.py` - SpecBuilder class with decompose(), generate_criteria(), build_spec()
- `tests/unit/test_spec_builder.py` - 13 unit tests covering decomposition, criteria, fallback

## Decisions Made

- **Used from_dict() for nested dataclass deserialization:** LLM returns JSON dicts with nested criteria lists. Direct UserStory(**item) failed because criteria needed proper AcceptanceCriterion objects, not dicts. Using UserStory.from_dict() handles the nested deserialization correctly.

- **Rule-based fallback uses keyword extraction:** Extracts roles via keyword matching (user, admin, developer, system, customer, guest) and features via stopword filtering (the, a, to, for, and, or, with, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Rule 1 (Auto-fix bugs): UserStory constructor failed with nested criteria dicts**
  - Found during: GREEN phase implementation
  - Issue: UserStory(**item) failed when criteria was a list of dicts, not AcceptanceCriterion objects
  - Fix: Changed to UserStory.from_dict(item) which properly deserializes nested criteria
  - Files modified: luminamind/planner/spec_builder.py
  - Verification: Tests passed with from_dict() approach
  - Committed in: `48df86f` (part of task commit)

## Next Phase Readiness

- SpecBuilder ready for integration with PlannerAgent (phase 03-03)
- Rule-based fallback ensures functionality when LLM unavailable
- All acceptance criteria have verify_method for contract verification

---
*Phase: 03-planner-sprint*
*Completed: 2026-04-27*