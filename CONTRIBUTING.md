# Contributing

This repository uses **GitHub Flow** (method A): `main` is the only long-lived
branch, it is always deployable, and every change arrives as one squashed pull
request. Full rules: [`docs/pr-workflow.md`](docs/pr-workflow.md) and
[`docs/branch-protection.md`](docs/branch-protection.md).

## The five commands

```bash
git switch main && git pull --ff-only
git switch -c feat/retry-budget
# ... edit ...
python -m pytest tests/ -q
git commit -m "fix(queue): do not re-claim a locked row"
git push -u origin HEAD
```

`gh pr create --fill` then `gh pr merge --squash --auto` once CI is green.

## Branch in this repository, not a fork

Method A assumes contributors with push access: branch here, so the CI run,
the review and the merge all happen against the same repository. Fork if you
must - the checks are written to pass without secrets - but say so in the PR,
because a fork's run is a copy of the truth, not the truth.

## Branch names

`type/short-description`, kebab-case, five words maximum:
`feat/retry-budget`, `fix/locked-row-reclaim`, `docs/retry-table`.
One concern per branch. If you cannot name it in five words, it is two PRs.

## Commit and PR title format

```
fix(queue): do not re-claim a locked row
```

`type(scope): imperative subject`, 72 characters, no full stop. The type is one
of `feat fix docs test refactor perf chore ci build revert`.

The PR title matters more than the commits, because squash merging makes it the
permanent subject line on `main`. `scripts/check-pr-title.sh` enforces the shape;
you can run it yourself before pushing:

```bash
sh scripts/check-pr-title.sh "fix(queue): do not re-claim a locked row"
```

## What CI runs, and how to run it first

```bash
sh scripts/structure-guard.sh    # seconds - do this first
python -m pytest tests/ -q          # 17 cases
```

Both run with nothing but Python: no broker, no database, no network.
If a test needs a queue to talk to, it is testing the wrong layer.

## What gets a PR sent back

- a new module in `src/` with no `tests/test_<module>.py` in the same PR
- `time.sleep` inside `backoff.py` (delays stay a pure function of `attempt`)
- a new queue state that is not in the schema block with `CREATE TABLE IF NOT EXISTS`
- a real token in `.env.example`, or any `print` in `src/`


## Reviews

The `.github/PULL_REQUEST_TEMPLATE.md` questions are not decoration. Say which 20 lines are risky. "`queue.py claim()` is the whole change"
is a review that takes four minutes; "PTAL" is one that takes forty.

Answer review threads rather than resolving them yourself; an open thread blocks
the merge by design.

## License

By contributing you agree your work is released under the MIT licence in
[`LICENSE`](LICENSE).
