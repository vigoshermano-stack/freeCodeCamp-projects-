# Pull request workflow

**Method A: GitHub Flow.** `main` is the only long-lived branch, it is always
deployable, and every change lands as one squashed pull request. The branch is
the unit of review; the merge is the deployment.

```
main ──●────────●────────●────────●──►   one commit per PR, always deployable
        \      /        /        /
         ●─●─●  feat/…  ●─●─●  fix/…
           PR  (checks)   PR  (squash + delete)
```

Three documents make this real, in order of authority:

| File | Role |
|---|---|
| `docs/branch-protection.md` | the `gh api` commands that enforce it; required checks |
| this file | the day-to-day: naming, commits, review, merge, release |
| `CONTRIBUTING.md` | the same rules for someone who just cloned |

Branch lifetime is measured in hours, not days. A branch that lives a week has
drifted from `main` far enough that a squash hides the conflict instead of
resolving it.

## 1. Branch

```bash
git switch -c fix/queue-reclaim-lock
```

Prefixes: `feat/`, `fix/`, `docs/`, `test/`, `refactor/`, `chore/`.
Kebab-case, five words maximum. The prefix is what makes `git branch` readable
after twenty PRs.

## 2. Commit

```
fix(queue): do not re-claim a locked row

claim() filtered on status only. A worker that died mid-delivery left the row
in 'sending', so the next poll picked it up and delivered twice.
```

Subject: `type(scope): imperative`, 72 characters, no full stop.
Types: `feat` `fix` `docs` `test` `refactor` `chore` `perf`.
Body: the why, plus what breaks without the change. One logical change per
commit — but do not polish WIP commits, they get squashed at merge anyway.

## 3. Open the PR early

Open it as a draft as soon as the shape is clear. A reviewer catching a wrong
approach in 40 lines is cheap; the same review after 400 lines is a rewrite.

## 4. Gates

All three must be green before review is requested.

| Gate | Where | Command | Fails when |
|---|---|---|---|
| Title | Actions `pr-title` | `sh scripts/check-pr-title.sh` | the squashed subject would be unreadable in `git log` |
| Structure / secret guard | both providers, `structure-guard` | `sh scripts/structure-guard.sh` | a test sits in `src/`, or `.env` / `reports/` is tracked |
| Suite | both providers, `test` | `python -m pytest tests/ -q` | any of the 17 cases fails |

Run the first two locally in about a second:

```bash
sh scripts/structure-guard.sh
sh scripts/check-pr-title.sh "fix(queue): do not re-claim a locked row"
```

Both providers call the same two scripts out of `scripts/`, so they cannot
disagree about what passing means — only about which machine said so. The
required checks and how to set them are in
[`branch-protection.md`](branch-protection.md).

## 5. Review

- The reviewer reads `src/` first and `tests/` second. If the tests are hard to
  follow, the design is not finished — that is a legitimate review comment.
- Answer every comment, even with one word. An unresolved thread blocks merge.
- Push ordinary commits during review; squash at merge. Do not force-push after
  an approval without saying so in the thread — it silently invalidates the review.

## 6. Merge

**Squash and merge.** Title becomes the commit subject. Delete the branch.

Squash because `main` then reads as one line per PR: `git log --oneline` stays
scannable, `git bisect` stays useful, and `git revert <sha>` undoes exactly one
PR instead of a dozen fixup commits.

Merge with the button, or skip the second click:

```bash
gh pr merge --squash --auto
```

`--auto` waits for the required checks and merges without you watching the tab.
If the base moved on, GitHub asks for the branch to be updated first; that is
`strict` doing its job, not an error.

### Tag the release, not the branch

`main` has no version of its own, so a tag is the only thing that says "this
exact tree shipped":

```bash
git switch main && git pull --ff-only
git tag -a v0.1.0 -m "relay: 17 cases, worker drains dead letters"
git push origin v0.1.0
```

Tags are cheap and they answer the only question that matters three months
later: which commit is on the device?

## 7. After merge

```bash
git switch main && git pull --ff-only && git branch -d fix/queue-reclaim-lock
```

## Sizing

| Changed lines | Verdict |
|---|---|
| under 200 | ideal — reviews in one sitting |
| 200 to 400 | acceptable if it is one concern |
| over 400 | split by concern, not by file |

## What goes straight to `main`

A typo in a doc, a comment fix, a version bump: commit directly if you work
alone. Anything touching `src/` gets a PR even when you are the only reviewer —
the pipeline is the reviewer, and a squash commit with a green tick is what you
want in the history when a webhook goes missing at 2 a.m.

## Worked example

```
fix(queue): release rows stuck in 'sending' after a worker crash

A worker killed between claim() and ack() left the row in 'sending' forever.
claim() now also takes rows whose lease is older than 60s, which is longer than
the slowest delivery timeout, so a live worker is never pre-empted.

Closes #14

Verified:
- python -m pytest tests/ -q -> 19 passed (2 new: crash recovery, lease not stolen)
- manual: SIGKILL the worker mid-delivery, restart, row delivered once

Risk: delivery worker only. A wrong lease window means duplicate delivery, not
lost webhooks — the intake path is untouched. Revert is a single commit.
```
