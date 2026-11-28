# Branch protection: GitHub Flow on `main`

Method **A** for this repository: `main` is the only long-lived branch, it is
always deployable, and every change lands through one squashed pull request.
This file is the configuration that makes that true instead of aspirational -
it is the difference between "we use GitHub Flow" and a repository where someone
can still push to `main` on a Friday.

```
   main ──●──────────●──────────●──────────●──►  (always deployable, one commit per PR)
           \        /          /          /
            ●──●──●  feat/…    ●──●──●  fix/…
              PR        squash    PR
```

## 1. Repository settings: squash only

Merge commits and rebase merges both reintroduce the history shape GitHub Flow
exists to avoid. Turn them off, keep squash, and let the PR title become the
commit subject - that is what `scripts/check-pr-title.sh` is guarding.

```bash
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -F allow_auto_merge=true \
  -F squash_merge_commit_title=PR_TITLE \
  -F squash_merge_commit_message=BLANK
```

| Setting | Value | Why |
|---|---|---|
| Squash merging | on | one PR = one revertable commit on `main` |
| Merge commits | off | they make `git log --oneline` a merge graph, not a changelog |
| Rebase merging | off | rewrites every commit into a history nobody reviewed as a unit |
| Auto-delete head branches | on | a merged branch is noise; GitHub deletes it |
| Auto-merge | on | `gh pr merge --squash --auto` merges the moment checks go green |
| Squash title | PR title | the title is the changelog line - hence the title check |
| Squash message | blank | the commit body belongs in the PR, not in `git log` |

## 2. Protect `main`

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "pr-title",
      "structure-guard",
      "test"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
```

| Field | Value | What it stops |
|---|---|---|
| `required_status_checks.contexts` | the checks below | merging with a red or missing gate |
| `strict` | `true` | merging a green PR whose base has moved on since |
| `enforce_admins` | `true` | "just this once" pushes straight to `main` |
| `required_approving_review_count` | `0` | nothing - see the note below |
| `required_linear_history` | `true` | a merge commit sneaking in through another path |
| `allow_force_pushes` | `false` | rewriting `main` |
| `allow_deletions` | `false` | deleting `main` |
| `required_conversation_resolution` | `true` | merging with an open review thread |

**On the review count.** `0` is the honest setting for a repository with one
maintainer: GitHub does not let you approve your own PR, so `1` would mean
nothing can ever merge. If a second maintainer joins, raise it to `1` and expect
to stop merging your own work - which is the entire point of the number.

**On `strict`.** It requires a branch to be up to date before merging, so a PR
that went green an hour ago needs one rebase and one re-run. That cost is real;
so is the alternative, which is merging into a `main` nobody has tested the
combination against. With the suite running in well under a minute, keep it on.

## 3. The required checks

These are job names from `.github/workflows/ci.yml`. They must match exactly:
a required check that never reports leaves every PR "Expected - waiting for
status to be reported" forever.

| Check | Proves |
|---|---|
| `pr-title` | the squashed commit subject is `type(scope): subject`, under 72 chars |
| `structure-guard` | no test file under `src/`, no `.env` or `reports/` tracked |
| `test` | the 17 cases in `tests/` |

`pr-title` only runs on pull requests, which is correct: it guards the merge,
not the commit that lands.

## 4. Verify it, don't assume it

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  | jq '{strict: .required_status_checks.strict,
         checks: .required_status_checks.contexts,
         linear: .required_linear_history.enabled,
         force_push: .allow_force_pushes.enabled}'
```

Then prove the door is shut, deliberately:

```bash
git switch main && git commit --allow-empty -m "chore: should be rejected"
git push            # expect: protected branch hook declined
git reset --hard HEAD~1
```

If that push succeeds, the protection is not on `main` - check for a typo in the
branch name, or a repository ruleset that overrides this configuration.

## 5. Day to day

| Situation | What you do |
|---|---|
| New work | `git switch -c feat/thing main`, commit, push, open the PR |
| Ready to merge | `gh pr merge --squash --auto`; walk away |
| Base moved on | `git pull --rebase origin main`, push; the concurrency group cancels the stale run |
| Hotfix | same flow, `fix/` prefix - no bypass, that is the whole promise |
| Release | tag `main` after the merge: `git tag -a v0.1.0 -m "..." && git push origin v0.1.0` |

## 6. What is deliberately not here

- No `develop` branch, no `release/*`: two long-lived branches means two things
  to keep green and a merge that nobody tested.
- No required external reviewer, no CODEOWNERS round-robin: an empty review slot
  that nobody fills is worse than an honest `0`.
- No required deployment approval: this repository builds an artifact; approving
  the artifact is the merge.
