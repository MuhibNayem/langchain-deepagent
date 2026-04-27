---
phase: 11
plan: 13
subsystem: luminamind/api
tags: [bugfix, events, router, fastapi]
dependency_graph:
  requires: []
  provides:
    - luminamind/api/app.py (events router included)
  affects:
    - luminamind/api/routes/events.py
tech_stack:
  added: []
  patterns:
    - FastAPI include_router pattern for events endpoints
key_files:
  created: []
  modified:
    - luminamind/api/app.py
decisions: []
metrics:
  duration: "<1 minute"
  completed: "2026-04-28T00:00:00Z"
---

# Phase 11 Plan 13: Include Events Router in FastAPI App

## One-liner
Fix missing API events router - events router was not included in FastAPI app, making /events and /events/replay endpoints inaccessible.

## Task Summary

### Task 1: Include events router in FastAPI app
**Status:** ✅ COMPLETE  
**Commit:** 7a38e39

**Changes made:**
1. Added import: `from .routes import events as events_router` (line 7)
2. Added `app.include_router(events_router.router)` after existing router includes (line 61)

**Verification:**
```bash
python3 -c "from luminamind.api import create_app; app = create_app(); print('Routes:', [r.path for r in app.routes if hasattr(r, 'path')])"
```
Output confirmed `/events` and `/events/replay/{session_id}` routes are now registered.

## Deviations from Plan
None - plan executed exactly as written.

## Files Modified
| File | Change |
|------|--------|
| luminamind/api/app.py | Added events router import and include_router call |

## Verification Against Must-Haves

| Must Have | Status |
|-----------|--------|
| /events and /events/replay endpoints are registered | ✅ Verified |
| Events router is included in FastAPI app | ✅ Verified |
| Key link: app.py → events.py via include_router | ✅ Verified |

## Self-Check: PASSED
- Commit 7a38e39 exists in git history
- luminamind/api/app.py shows events_router import on line 7
- luminamind/api/app.py shows include_router on line 61
- Route verification confirms /events and /events/replay/{session_id} are accessible
