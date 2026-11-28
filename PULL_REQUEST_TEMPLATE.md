<!--
Method A - GitHub Flow: branch off main, one concern, squash-merged.
The PR title becomes the permanent commit subject, so it must read
as `type(scope): subject` - scripts/check-pr-title.sh enforces that in CI.
-->

<!--
Title: type(scope): summary     e.g. fix(queue): do not re-claim a locked row
Keep the diff under ~400 lines. One concern per PR.
Leave the tables; delete the HTML comments.
-->

## What this changes

<!-- Present tense, one paragraph, no adjectives. What the diff does. -->

## Why

<!-- The failure this prevents. If nothing fails without it, say "refactor" and name who benefits. -->

Closes #

## How it was verified

<!-- Paste real output. "Tests pass" is not evidence. -->

| Check | Command | Result |
|---|---|---|
| Suite | `python -m pytest tests/ -q` | 17 passed |
| Structure guard | CircleCI job `structure-guard` | green |
| Manual replay | same `idempotency_key` posted twice | 202 then 200, one delivery |

## Checklist

- [ ] New module has a matching `tests/test_<module>.py` in this PR
- [ ] No `time.sleep` in `backoff.py` — delays stay a pure function of `attempt`
- [ ] New queue state is in the schema block with `CREATE TABLE IF NOT EXISTS`
- [ ] Replaying an `idempotency_key` still returns the original result
- [ ] Dead-letter path either unchanged or explicitly covered by a test
- [ ] `.env.example` got placeholders, never a real token
- [ ] No `print` in `src/` — the worker logs through the handler

## Risk and rollback

| Question | Answer |
|---|---|
| Blast radius | <!-- e.g. delivery worker only; intake unaffected --> |
| Failure mode if wrong | <!-- e.g. webhooks retry forever instead of dead-lettering --> |
| Rollback | `git revert <sha>` — no migration to unwind |
| Deploy order | <!-- worker first, then intake? say so --> |

## Where to look first

<!-- Point the reviewer at the 20 risky lines and say what you are unsure about.
     "queue.py claim() is the whole change; the rest is tests" beats "PTAL". -->
