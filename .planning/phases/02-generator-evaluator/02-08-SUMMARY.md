---
phase: "02"
plan: "08"
subsystem: "evaluator"
tags: ["criteria", "grading", "engine", "GE-04"]
dependency_graph:
  requires: ["02-01", "02-02", "02-03", "02-04"]
  provides: ["CriteriaEngine"]
  affects: ["luminamind/evaluator/criteria.py", "luminamind/evaluator/code.py", "luminamind/evaluator/frontend.py"]
tech_stack:
  added: ["CriteriaEngine", "CriteriaNotFoundError"]
  patterns: ["criteria registry", "weighted composite scoring", "domain-based selection"]
key_files:
  created:
    - path: "luminamind/evaluator/criteria_engine.py"
      lines: 161
    - path: "tests/unit/test_criteria_engine.py"
      lines: 135
  modified: []
decisions:
  - "CriteriaEngine uses registry pattern for domain criteria management"
  - "Default weights: design=0.30, code=0.35, craft=0.15, originality=0.20"
  - "Composite score normalized by total weight for consistent 0-100 range"
  - "Artifact type inference mapping: frontend→design, code→code+craft, spec→originality, full→all"
---

# Phase 02 Plan 08: CriteriaEngine for Domain-Specific Criteria Management

## One-liner

CriteriaEngine with criteria registry, weighted composite scoring, and domain-based artifact selection.

## Summary

Implemented CriteriaEngine per GE-04 requirements for managing domain-specific grading criteria sets. The engine provides criteria selection based on artifact type and supports composite evaluation across multiple domains with configurable weights.

## Implementation Details

### CriteriaEngine Class

**Location:** `luminamind/evaluator/criteria_engine.py`

**Core functionality:**
- `__init__()`: Initializes registry with default criteria instances and weights
- `get_criteria(domain)`: Returns GradingCriteria for a specific domain
- `get_criteria_for_artifact(artifact_type, domains?)`: Selects appropriate criteria based on artifact type
- `register_criteria(domain, criteria)`: Registers custom criteria
- `set_domain_weight(domain, weight)`: Configures weights for composite scoring
- `evaluate_composite(artifact, domains?)`: Produces weighted composite score

**Default domains:**
| Domain | Criteria Class | Weight |
|--------|---------------|--------|
| design | DesignCriteria | 0.30 |
| code | CodeCriteria | 0.35 |
| craft | CraftCriteria | 0.15 |
| originality | OriginalityCriteria | 0.20 |

**Artifact type mapping:**
| Artifact Type | Selected Domains |
|---------------|------------------|
| frontend | design |
| code | code, craft |
| spec | originality |
| full | design, code, craft, originality |

### CriteriaNotFoundError

Custom exception inheriting from ValueError for missing domain handling.

### Composite Scoring

```
composite_score = sum(domain_score * weight) / total_weight
```

Normalized to 0-100 range for consistent interpretation.

## Unit Tests

**Location:** `tests/unit/test_criteria_engine.py` (14 tests)

| Test | Description |
|------|-------------|
| test_initialization | Engine starts with 4 default domains |
| test_get_criteria | Returns correct GradingCriteria for domain |
| test_get_criteria_not_found | Returns None for unknown domain |
| test_criteria_selection_by_artifact_type | Correct criteria list by type |
| test_criteria_selection_with_explicit_domains | Respects explicit domains parameter |
| test_composite_criteria | Produces weighted composite score |
| test_composite_evaluation_with_multiple_domains | Combines multiple domain scores |
| test_custom_criteria_registration | Custom criteria can be registered |
| test_domain_weight_configuration | Weights are configurable |
| test_clear_criteria | Registry can be cleared |
| test_evaluate_composite_normalizes_weight | Normalization works correctly |
| test_criteria_registry_persists | Registry maintains identity |

## Verification

```bash
pytest tests/unit/test_criteria_engine.py -x -v
# 14 passed in 0.02s
```

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface

| Flag | File | Description |
|------|------|-------------|
| N/A | criteria_engine.py | No new security surface - uses established GradingCriteria base class |

## Completion

**Status:** ✅ Complete
**Duration:** ~2 minutes
**Commits:** 2