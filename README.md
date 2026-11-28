# Local-First Webhook & API Relay Queue

[![CI](https://github.com/<your-username>/webhook-relay-queue/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/webhook-relay-queue/actions)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

> A durable, local-first relay that accepts webhooks at the edge, stores them in
> SQLite, and delivers them upstream with exponential backoff — so a slow or
> offline upstream never silently drops an event.

## The problem it solves

Cloud workers lose sync in high-latency or intermittent network zones. A
webhook arrives, the upstream API times out, and the event is **gone** — no
retry, no record, no alert. You find out days later when a customer's order is
missing.

This service guarantees **at-least-once delivery**: every accepted webhook is
persisted before it is acknowledged, retried on a schedule, and parked in a
**dead-letter table** when it finally fails — so nothing vanishes silently.

## Architecture

```
  sender ──POST──> [edge buffer]  ──forward──>  [relay: intake]
                   (Cloudflare)                     |
                                                    v
                                            [SQLite queue]
                                             pending | inflight
                                                    |
                                              [delivery worker]
                                              backoff + jitter
                                                    |
                                     delivered  <---+--->  dead-letter
                                                    |
                                                    v
                                             upstream API
```

Three properties that matter:

| Property | How |
|---|---|
| **Durable** | Row is written to SQLite *before* the HTTP 202 is returned |
| **Idempotent** | Every attempt carries a stable `Idempotency-Key` from the event ID |
| **Recoverable** | `inflight` rows are reclaimed on restart by a lease timeout |

## Quick start

```bash
git clone https://github.com/<your-username>/webhook-relay-queue.git
cd webhook-relay-queue
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# start intake (port 8080) and the worker together
python -m src.app
```

Send a test event:

```bash
curl -X POST http://localhost:8080/hooks/orders \
  -H "Content-Type: application/json" \
  -d '{"order_id": 1042, "status": "paid"}'
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `RELAY_DB` | `relay.db` | SQLite file path |
| `UPSTREAM_URL` | *(required)* | Where events are forwarded |
| `MAX_ATTEMPTS` | `8` | Attempts before dead-lettering |
| `BASE_DELAY_MS` | `500` | First retry delay |
| `MAX_DELAY_MS` | `300000` | Backoff ceiling (5 min) |
| `LEASE_SECONDS` | `60` | Inflight reclaim timeout |

Copy `.env.example` to `.env` and fill it in. `.env` is gitignored.

## Backoff behaviour

`delay = min(MAX_DELAY, BASE_DELAY * 2^(attempt-1))` plus up to 30 % jitter, so a
fleet of workers does not retry in lockstep after an outage.

| Attempt | Nominal delay |
|---:|---|
| 1 | 0.5 s |
| 2 | 1 s |
| 3 | 2 s |
| 4 | 4 s |
| 5 | 8 s |
| 6 | 16 s |
| 7 | 32 s |
| 8 | 64 s → dead-letter |

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/hooks/<source>` | Accept and enqueue an event (202) |
| `GET` | `/health` | Liveness plus queue depth |
| `GET` | `/stats` | Counts by state |
| `POST` | `/dead-letter/<id>/replay` | Requeue a dead-lettered event |

## Tests

```bash
python -m pytest tests/ -v
```

No network or database server needed — the queue uses a temporary SQLite file
and the delivery worker takes an injectable `post` function.

## Repository structure: `src/` and `tests/`

Two folders, one rule: **`src/` is what ships, `tests/` is what proves it.**
The dependency arrow only ever points one way — tests import `src`, and nothing
in `src/` knows that `tests/` exists.

```
webhook-relay-queue/
|- src/                      # importable package, ships to production
   |- __init__.py            # package marker + the public surface
   |- queue.py               # SQLite state machine: claim, retry, dead-letter
   |- backoff.py             # delay maths, pure functions, no sleeping
   |- relay.py               # orchestrates one delivery attempt
   |- app.py                 # I/O boundary: HTTP intake + worker loop
|- tests/                    # pytest suite, ships nowhere
   |- test_queue.py          # 11 cases: transitions, idempotency, DLQ
   |- test_backoff.py        # 6 cases: growth, cap, jitter bounds
|- services/edge-buffer/     # separate deployable (Cloudflare Worker)
|- docs/                     # architecture, PR workflow, branch protection
|- scripts/                  # the gates, one copy, called by both CIs
   |- structure-guard.sh
   |- check-pr-title.sh
|- CONTRIBUTING.md           # GitHub Flow in five commands
|- .circleci/config.yml      # CircleCI pipeline
|- .github/workflows/ci.yml  # same jobs, GitHub Actions
   |- PULL_REQUEST_TEMPLATE.md # PR checklist: gates, replay, blast radius
```

### What belongs where

| Path | Belongs there | Never there |
|---|---|---|
| `src/queue.py` | schema, transitions, `claim()`, dead-lettering | HTTP, sleeps, retry timing |
| `src/backoff.py` | arithmetic on attempt numbers | `time.sleep` calls, env parsing |
| `src/relay.py` | one attempt + outcome classification | its own `urllib` calls (the `post` function is injected) |
| `src/app.py` | sockets, threads, env vars | business rules |
| `tests/*.py` | arrange / act / assert, `tmp_path` files | imports from other test modules |

### Module to test map

| Module | Test file | What it pins down |
|---|---|---|
| `src/queue.py` | `tests/test_queue.py` | enqueue to claim to ack to dead-letter, duplicate keys |
| `src/backoff.py` | `tests/test_backoff.py` | exponential growth, cap, jitter range |
| `src/relay.py` | covered through `test_queue.py` | outcome classification on 2xx / 4xx / 5xx |
| `src/app.py` | not unit-tested | thin transport shell, exercised by hand |

`app.py` is untested on purpose: it is the only file holding a real socket, and
a test there would mock away the thing worth testing. Keep it thin enough to
read in one sitting and the risk stays at the edge.

### Adding a module

1. Name it after the job, not the layer: `backoff.py`, never `utils.py`.
2. Keep every decision a pure function; take `now`, `sleep` and `post` as
   arguments so a test can pin them.
3. Land `tests/test_<module>.py` in the same commit. CI does not gate on
   coverage, but a module with no test is a module nobody can safely change.
4. Needs a table? Add it inside `queue.py`'s schema block and keep it
   idempotent (`CREATE TABLE IF NOT EXISTS`).

### What CI enforces

| Check | Command | Fails when |
|---|---|---|
| Structure guard | `find src -name "test_*.py"` | a test file was dropped into `src/` |
| Secret guard | `git ls-files` matching `.env`, `*.pyc`, `__pycache__` | something generated or secret got committed |
| Suite | `python -m pytest tests/ -v` | any of the 17 cases fails |
| Coverage artifact | `pytest --cov=src --cov-report=xml` | never gates, it is there to spot dead code |

Both pipelines call the same entry point — `.circleci/config.yml` for CircleCI,
`.github/workflows/ci.yml` for GitHub Actions — so they cannot drift apart.

---

## Submission workflow — the 7 steps from the infographic

![Practice submission via GitHub.com](docs/images/github-submission-flow.png)

The infographic walks a change from code to contribution in seven cards. Every
card's elements map to a concrete action in **this** repository:

| # | Card title | Elements shown on the card | Function — what the element does | Your action in this repo |
|--:|---|---|---|---|
| 1 | **Create or Fork Repository** | `New repository`, `Import`, `Templates` buttons; **Repository name** field; `Public` / `Private` radios; `Create repository` button | Bootstraps the remote: name and visibility are set here, and public visibility is what makes the repo indexable | Create `webhook-relay-queue`, **Public**, no README (you already have one) |
| 2 | **Clone Repository** | Terminal card: `git clone https://github.com/username/my-practice-project.git` | Copies the remote, with history, to your machine so you can edit locally | `git clone https://github.com/<your-username>/webhook-relay-queue.git` |
| 3 | **Make Changes** | Editor card: `main.py`, `def greet(name):`, `print("Hello from GitHub!")` | The edit itself — code, docs, or a fix; this is the only step that creates value | Work in `src/queue.py` or `src/backoff.py`; add a matching test |
| 4 | **Commit Changes** | Commit list: `Add feature for user login`, `Update documentation`, `Fix typo in README.md`, `Initial commit` | Groups a coherent change with a message; small commits keep review cheap | `git commit -m "Add lease reclaim for inflight rows"` |
| 5 | **Push to GitHub** | `git add .`, `git commit -m "Add new feature"`, `git push origin main` | Publishes local commits to the remote so reviewers can see them | `git push -u origin main` |
| 6 | **Create Pull Request** | `New pull request` button; `base: main` / `compare: feature-branch` selectors | Opens the diff for review; base/compare define exactly what is being proposed | Only for later changes: branch first, then open the PR |
| 7 | **Review & Merge** | `All checks have passed`, `3 successful checks`, comment thread (`Nice work!`, `LGTM!`), `Approved`, `Merge pull request` | CI status plus human review decide merge; merge is what makes the change permanent | Wait for the CI badge to go green, then merge |

### The roles strip at the bottom

The infographic closes with three role cards — the same repo can be read by all
three audiences:

| Role on the card | Card copy | What it means for this repo |
|---|---|---|
| **Technical Writer** | *Clear Documentation Empowers People* | `README.md` + `docs/architecture.md` are the deliverable, not an afterthought |
| **System Administrator** | *Reliable Infrastructure Keeps Things Running* | The lease/reclaim logic in `queue.py` is the reliability story |
| **Cloud Engineer** | *Scalable Solutions Power Possibilities* | `services/edge-buffer/worker.js` is the edge tier |

### The full command sequence

```bash
git init
git branch -M main
git add .
git commit -m "Initial commit: durable webhook relay with backoff and dead-letter"
git remote add origin https://github.com/<your-username>/webhook-relay-queue.git
git push -u origin main
```

### The PR this repository expects

**GitHub Flow, method A:** `main` is the only long-lived branch, every change
arrives as one squashed PR, and branch protection enforces it rather than
asking politely.

`.github/PULL_REQUEST_TEMPLATE.md` pre-fills every pull request with the checks
that matter here: the suite count, the idempotency replay, the dead-letter path
and the blast radius of the delivery worker. `docs/pr-workflow.md` carries the
branch naming, commit format, squash-merge rule and a fully worked PR body.
`docs/branch-protection.md` holds the `gh api` commands that turn the rules into
settings, and `CONTRIBUTING.md` is the five-command version for a contributor
who just cloned.

## Where this fits as a portfolio piece

| Program | Angle |
|---|---|
| **DigitalOcean** | "Build a resilient local-first webhook relay with SQLite and exponential backoff" — concrete, testable, uses a Droplet |
| **Twilio Blog** | "Never drop a webhook: buffering at the edge and retrying upstream" |
| **dev.to** | Shorter version: the queue state machine in 60 lines |

## License

MIT. Copyright (c) 2026 techapplied.
