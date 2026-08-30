# RFC — The cell ledger: one "what happened", and incidents that become tests

Status: **draft for review** (2026-08-30). Branch: `claude/agentic-cell-setup-monitor-c5ubfs`.
Detailed design for step 1 of `agentic-cell-rfc.md`, and the substrate the steward
loop runs on. Supersedes the one-line sketch of `{realm}/events` in
`automation-framework-design-v5.md` §4.6.

The question this answers: **what does a robot cell have to write down so that a
physical bug becomes reproducible, then testable, then fixed, then proven fixed —
without storing terabytes?**

---

## 1. The shape of the answer

Three claims, in order of importance.

**1. The ledger is an index, not a database.** One append-only, low-rate,
semantically-typed stream of *events*. It is always on, small enough to keep
forever, and complete enough to answer "what happened, when, in what order,
because of what" without opening a single recording. Bulk data (frames, joint
traces, images) is **content-addressed evidence** that ledger entries point at,
and it has a retention policy. The ledger does not.

> The invariant: **every ledger entry either explains itself, or names the blobs
> that do.** If triage requires opening a 4 GB MCAP to find out whether an
> incident matters, the design has failed.

**2. The bus is the transport; the file is the truth.** Events are published on
`{realm}/events` so the UI, the recorder and a remote agent see them live — but
the durable copy is a file on the cell that outlives every recording, because
recordings rotate and get deleted. Nothing is invented here: the ledger writer is
just another subscriber.

**3. Reproducibility has levels, and the loop's first job is to say which one it
is facing.** You cannot re-run physics. You *can* re-run a decision. Being honest
about the difference is what stops the agent from writing tests that were always
green.

| Level | The bug is | Reproduce by | Test artefact | Runs in |
|---|---|---|---|---|
| **L0 — Decision** | a pure function of recorded observations got the wrong answer (vision mis-locate, a guard, IK/planning, a parse) | re-running that function on the recorded input, byte for byte | a fixture + expected output | CI, milliseconds, deterministic |
| **L1 — Interaction** | the logic is wrong (bad order, missing wait, race, unhandled fault path) | re-running the program against **sim devices seeded from the recording**, driven by the recorded external stimuli | a *scenario*: seed state + stimulus timeline + assertion | CI, seconds |
| **L2 — Physical** | the world varies (the part slipped, the fixture drifted, the lighting changed) | not reproducible in software | a **population** assertion over N cycles: a rate, a mean, a residual | on the cell |

The discipline that makes this real: **the generated test must fail on the
pre-fix code.** Red, then green. If the agent cannot make it go red at L0 or L1,
the bug is L2 and must be handled statistically — never by writing an L1 test
that passes both before and after and calling it fixed.

---

## 2. The event record

Design v5 §4.6 proposed `{t, severity, source, kind, message, data}`. That is
enough for a timeline and not enough for reproduction. Three groups are missing:
**causality**, **world version**, and **evidence**.

```yaml
# {realm}/events  — and one NDJSON line in the ledger
id:        01JAV3K8Q0X7Z9MNPQ4R5S6T7V     # ULID: time-sortable, unique, no coordination
t:         1781328076708408400            # ns, wall clock
t_mono:    884213771229                   # ns, monotonic — survives NTP steps

# ── causality ────────────────────────────────────────────────────────────
trace:     01JAV3K8..                     # the CYCLE this belongs to
span:      goal:7f3a / infer:22 / null    # the unit of work inside the cycle
cause:     01JAV3K7..                     # the event that led to this one

# ── origin ───────────────────────────────────────────────────────────────
cell:      venlo-line2
node:      main
service:   arm:r1                         # who emitted
device:    r1                             # what it is about (nullable)
program:   demo_pick
state:     picking                        # the program state at the time

# ── classification ───────────────────────────────────────────────────────
kind:      motion.rejected                # closed vocabulary, dotted
category:  motion                         # safety|motion|device|program|vision|config|platform|operator
severity:  error                          # debug|info|warning|error|critical
code:      MOTION_COLLISION               # closed, countable, alertable
fingerprint: 9f2c1e7a                     # stable hash: dedupes 400 recurrences into 1 case

# ── payload ──────────────────────────────────────────────────────────────
message:   "goal 7f3a rejected: collision link6|fixture_a"
data:      {pair: [link6, fixture_a], waypoint: 2, goal_id: "7f3a"}   # bounded, 2 KB

# ── provenance: the inputs needed to re-run this ─────────────────────────
versions:  {platform: "0.1.0+8c293f9", driver: "aubo_i10/0.26.0", program_rev: "a41c", pipeline_rev: null}
world_rev: "sha256:41ab…"                 # see §2.2

# ── evidence ─────────────────────────────────────────────────────────────
refs:
  - {kind: mcap_slice, uri: "blob:sha256:8c1d…", bytes: 41200311, span_ns: [.., ..]}
  - {kind: image,      uri: "blob:sha256:aa07…", bytes: 214003, topic: "camera2d/cam0/image"}
  - {kind: snapshot,   uri: "blob:sha256:5b93…", bytes: 4102, note: "execution snapshot"}
```

Three fields carry most of the weight, and none exist today.

### 2.1 `trace` — a cell runs forever; incidents are per-cycle

Without a trace id you cannot slice one cycle out of a continuous stream, and
"what happened" is only meaningful per cycle. The program runner mints a ULID at
each cycle boundary and emits `cycle.begin` / `cycle.end`.

Propagation is deliberately asymmetric, to avoid touching every contract:

- **Command path — explicit.** Every command payload is already a dict; it gains
  one optional `trace` field. `QueryAudit` and the `ActionServer` copy it into
  their echo. That covers arm goals, dio/tags writes, washer actions, lease
  acquisition, vision runs — the whole causal spine.
- **Telemetry — by time window.** Joint states, images and channel snapshots are
  continuous and need no trace field: `[cycle.begin.t, cycle.end.t]` selects them.

`cause` links an event to the one that produced it (`motion.rejected` ← the
`goal.submitted` that was rejected), which is what turns a flat log into a story.

### 2.2 `world_rev` — the version of physical reality

The most under-served field, and the one that makes L1 tests possible. A large
share of physical bugs are "the pose was retaught last Tuesday" or "somebody
changed the TCP". The config store already keeps per-key revisions and an
append-only `history.jsonl`; `world_rev` is a hash over the current revision of
every entry that describes the cell's geometry — frames, poses, TCPs, scene,
intrinsics, collision exceptions.

That gives a complete, restorable input set:

> **reproduce = (platform version) + (program revision) + (`world_rev`) + (recorded stimuli)**

All four are in every ledger row, so an agent can reconstruct the exact world the
cell was in without asking anyone. This generalises what the arm's execution
snapshot already does for one goal (resolved waypoints, active TCP, driver
version) to the whole cell.

### 2.3 `fingerprint` — recurrence is one case, not N incidents

A stable hash over `(code, service, program, state, normalised data)`. The same
failure at the same place collapses to one **case** with a count and a
first/last-seen, instead of 400 issues. It is also the identity of the generated
regression test, and the key under which the "golden" evidence bundle is kept
forever (§4).

### 2.4 The vocabulary

`kind` is closed and dotted, so it can be subscribed to by prefix and counted. The
starting set, all of which the platform already knows internally and currently
throws away:

| Prefix | Events |
|---|---|
| `cell.` | `activated`, `stopped`, `source_switched`, `config_written`, `snapshot_taken` |
| `service.` | `started`, `exited` (with code), `spawn_failed`, `unreachable`, `recovered` |
| `control.` | `acquired`, `released`, `lost`, `denied` |
| `program.` | `loaded`, `started`, `state_entered`, `transition`, `held`, `completed`, `aborted` |
| `cycle.` | `begin`, `end` (with outcome + duration) |
| `motion.` | `goal_submitted`, `goal_succeeded`, `goal_failed`, `rejected`, `cancelled` |
| `device.` | `fault`, `cleared`, `stale`, `forced` |
| `safety.` | `estop`, `protective_stop`, `cleared`, `speed_clamped` |
| `vision.` | `inference`, `low_confidence`, `no_detection`, `frame_published` |
| `operator.` | `command`, `confirmation`, `override` |
| `experiment.` | `started`, `promoted`, `reverted` |

**Rule: if it isn't in the ledger, it didn't happen.** A service that does
something consequential and emits no event is a review finding, not a style
preference.

---

## 3. Storage

```
fleet/deployments/<site>/journal/
├─ events.ndjson              # THE LEDGER. append-only, one JSON per line, forever
├─ index.sqlite               # DERIVED. rebuildable from events.ndjson. never authoritative
├─ blobs/8c/8c1d…             # content-addressed evidence, sha256-named
├─ ring/                      # the flight recorder (§4.1), fixed size, rotating
└─ cases/<fingerprint>/       # promoted incidents = regression fixtures (§5)
```

Why these choices:

- **NDJSON for the ledger.** Crash-safe (a torn last line is discardable),
  appendable without rewriting, greppable by a human at 3 a.m., diffable, and
  needs no daemon. `fsync` on `severity >= error`, buffered otherwise.
- **SQLite as a derived index, never the truth.** An agent needs
  `WHERE code=… AND t BETWEEN …` without scanning a year of lines. It is a cache:
  delete it and it rebuilds. This distinction matters — the moment the index is
  authoritative, a corrupt index is a lost history.
- **Content-addressed blobs.** Free dedup: 400 aborts at the same pose reference
  one scene snapshot, not 400. Free integrity: the ref carries the hash. Free
  transport: an incident bundle is a manifest plus the blobs the receiver lacks.
- **Not a TSDB, not Loki, not a cloud sink.** A cell must work with no network,
  restore from a checkout, and be diffable in a PR. A file-based ledger plus a
  derived index is operationally free and survives the machine being offline for
  a week.
- **The ledger is not in git.** It is append-only operational data. What goes to
  git is `cases/` — the promoted fixtures — and the fixes.

Sizing: 400 B/event × even 5 000 events/day = **2 MB/day, 700 MB/year**. Keeping
the ledger forever is not a decision that needs revisiting.

---

## 4. Not storing terabytes

### 4.1 What actually costs

Order-of-magnitude, from this repo's configured defaults (`cell.yaml`
`stream_defaults`, `servo_cycle_s: 0.005`):

| Stream | Rate | Per sample | Per day | Share |
|---|---|---|---|---|
| `camera2d/*/image` (stream, scale 0.25, q75) | 15 Hz | ~12 KB | **~15 GB** | dominates when streaming |
| `camera2d/*/image` (grabs, full res, q90) | ~10/min | ~200 KB | ~3 GB | the frames that *matter* |
| `arm/*/state/{joints,flange,tcp}` | 200 Hz live | ~440 KB/s total | **~8 GB** | dominates when not streaming |
| `program/*`, `audit/*`, `supervisor/*/log/*`, `events` | event-driven | ~300 B | **< 0.5 GB** | negligible |
| `dio|tags/*/state/*` | on change + 1 Hz | ~200 B | negligible | |

Two conclusions. First, **the entire retention problem is images plus joint
telemetry**; the semantic streams are free and should simply be kept. Second, the
*preview stream* is the expensive thing and is also the least useful for
reproduction — nobody debugs from a 320×200 preview when the pipeline consumed a
full-res grab.

That motivates a schema change: **split the camera topic.** Today
`camera2d/{cid}/image` carries both the stream and grabs (its own docstring says
so). Design v5 §4.3 already anticipated `image/preview`. Separating them lets the
recorder keep every decision frame forever and drop the preview entirely — the
single largest volume win available, for a small contract change.

### 4.2 Three tiers

**Tier 1 — the ledger. Always on, kept forever.** §3. Megabytes per year.

**Tier 2 — the flight recorder. Always on, fixed size, mostly discarded.** You
cannot know in advance which cycle will fail, so a rolling on-disk ring of the
full `{realm}/**` stream is always running. Two rings at different depths, because
the cost profiles differ by three orders of magnitude:

| Ring | Contents | Depth | Cost |
|---|---|---|---|
| A | everything except images | 60 min | ~0.5 GB |
| B | images (decision frames always; preview only if streaming) | 5 min | ~1–4 GB |

On an incident, **freeze and promote**: the ring window around the event
(`[t-60 s, t+15 s]` by default, widened to the enclosing `cycle.begin/end`) is
written out as a permanent bundle and referenced from the ledger row. Bounded
disk, complete evidence for anything that fires.

**Tier 3 — the durable keeps.** Deliberately *value-based*, not age-based:

- **Every incident bundle** — until its case is closed, plus 90 days.
- **One golden bundle per `fingerprint`** — forever. This is the regression
  fixture; deleting it deletes the test.
- **A daily sample of N successful cycles** — forever, and small. This is what
  makes "is this a regression?" answerable at all, and it doubles as the labelled
  set for vision replay-evaluation. Without a baseline of *good* runs you can only
  ever compare a failure against nothing.
- **Every experiment window** (§ tuning envelope) — until the experiment is
  promoted or reverted, plus 30 days.
- Everything else: lives in the ring, then is gone. That is the point.

### 4.3 Decimation by class, not by age

Age-based retention throws away the wrong things first. Retain per topic class:

- **Semantic streams** (events, audit, logs, program state/transitions, goal
  results and execution snapshots) — full fidelity, forever. They are the spine
  and they are cheap.
- **Joint telemetry** — full rate inside kept windows; outside them, either a
  decimated 10 Hz track (20× smaller, still enough for most triage) or just the
  per-goal summary the driver can compute anyway: start/end `q`, duration,
  peak velocity, max tracking error, and whether it matched the planned
  trajectory.
- **Images** — keep *decision frames* only: every image a vision pipeline actually
  consumed, with its result and overlay. Never the preview. Content addressing
  means a static scene costs one blob.

### 4.4 Escalate on precursors

Run decimated by default; when something looks marginal, record everything for a
while. Precursors are cheap because they are rare: a retry, a confidence within
10 % of threshold, a near-collision in preflight, a cycle time beyond 2σ, a device
reconnect. Any of them arms full fidelity for the next M cycles. Most real
failures announce themselves at least once before they bite, and this is how you
get a full-fidelity recording of the *second* occurrence instead of the fortieth.

---

## 5. Incident → case → test → proof

An incident bundle is promoted into a **case**, which is a directory in git and is
simultaneously the bug report, the fixture and the test:

```
fleet/deployments/<site>/cases/9f2c1e7a/
├─ case.yaml       # fingerprint, code, first/last seen, count, status, world_rev, versions
├─ bundle.mcap     # the frozen ring window
├─ world/          # the config entries AT world_rev (poses, frames, TCPs, scene, intrinsics)
├─ scenario.yaml   # L1: seed state + stimulus timeline + assertion   (generated)
├─ fixtures/       # L0: the recorded inputs to the offending function (generated)
└─ expect.yaml     # what should have happened
```

The loop, with the gate that makes it honest:

1. **Classify.** L0, L1 or L2 (§1). This is a decision the agent must record, not
   skip.
2. **Reproduce.** L0: re-run the function on `fixtures/`. L1: boot the cell in sim
   seeded from `world/`, replay `scenario.yaml`'s stimuli. L2: no reproduction —
   go to 6.
3. **Gate — prove it fails.** Run the generated test against the **pre-fix**
   revision. If it passes, the reproduction is invalid: either the classification
   is wrong (it is really L2) or the fixture is missing an input. **No fix
   proceeds past a test that was never red.**
4. **Fix.** Cell-level → the deployment dir. Platform-level → a GitHub issue
   carrying the case directory, which is already a runnable reproduction rather
   than a prose description.
5. **Prove.** The same test goes green; the whole `cases/**` suite still passes,
   so the fix did not resurrect an older case.
6. **L2 path.** No unit test exists. The artefact is a population assertion —
   a rate or a residual over `sample.cycles` — plus a permanent metric in the
   scoreboard. "Fixed" means the metric moved beyond run-to-run noise, and it is
   the tuning-envelope machinery, not the test suite, that proves it.

`cases/**` is then the cell's regression suite: every bug that ever happened,
runnable in CI, red before its fix and green after.

### What this needs from the platform

Reproduction at L1 requires **seedable sim providers** — `arm_sim`, `sim_dio`,
`sim_tags`, `ecoclean_sim` must start from a recorded state (initial joints,
channel and tag values) and consume a scripted stimulus timeline rather than only
their defaults. This is the highest-leverage missing piece for turning physical
bugs into tests, and it is a modest addition: the `replay` sources already prove
the pattern.

**Risk, stated plainly: L1 tests are timing-sensitive.** Program actions run on
threads; `ctx.sleep` is wall-clock; a sim run is not deterministic today, so a
scenario can flake. Three mitigations, cheapest first: assert on the *sequence* of
states and events rather than on durations; run sim at a fixed `time_scale` (the
Ecoclean sim already has one); make the action clock injectable so `ctx.sleep`
can be virtual. The first two are enough for most cases; the third is what makes
L1 genuinely deterministic and is worth doing before the case suite grows large.

---

## 6. Delta against what exists

| Piece | Status |
|---|---|
| `{realm}/events` + `wf.core.events.emit_event()` | **new** — nothing exists |
| Event schema with `trace` / `world_rev` / `fingerprint` / `refs` | **new** |
| `trace` on command payloads; echoed by `QueryAudit` and `ActionServer` | small change to `core/audit.py`, `core/action.py`, one field per contract message |
| `world_rev` from the config store's revisions | small — `history.jsonl` and per-key revisions already exist |
| Ledger writer (bus → NDJSON + SQLite index + blob store) | **new** service, small |
| Rolling ring recorder + freeze-and-promote | extends `services/recording/recorder.py` (today: start/stop only, unbounded) |
| Decimation and per-class retention policy | **new** — the recorder has no notion of topic classes |
| `camera2d` topic split: `image` (decisions) vs `image/preview` | contract change, anticipated by design v5 §4.3 |
| Per-goal motion summary (so joints can be decimated outside incidents) | small addition to `arm_core`; the execution snapshot is the precedent |
| Seedable sim providers + scenario runner | **new**, and the gating piece for L1 |
| `cases/` layout, generators, and the red-then-green gate | **new**, agent-side |

Sequencing: the event schema and the ledger writer come first and are useful
alone (they make the cell legible headlessly, step 1 of the parent RFC). The ring
and retention policy come next and are what make it affordable to run forever.
Seedable sim and the case suite come last and are what make the fix loop real.

---

## Open questions

1. **Is `trace` worth threading through every contract message, or is
   time-window correlation enough?** The proposal above is a hybrid: explicit on
   the command path (cheap, one field, and where causality actually lives),
   implicit for telemetry. The alternative — pure time-window — costs nothing but
   loses causality whenever two cycles overlap or a goal outlives its state.
2. **Ring depth and incident window** are guesses (60 min / 5 min / ±60 s). They
   should be measured on the first real cell, and they are per-deployment config,
   not platform constants.
3. **Does the ledger belong per-cell or per-fleet?** Per-cell is proposed: it
   works offline, and a fleet view is an aggregation of ledgers rather than a
   dependency of them.
4. **Who assigns `fingerprint`?** A platform-side hash of a declared tuple is
   predictable and dedupes reliably; letting the agent judge similarity dedupes
   better but is not reproducible. Proposal: platform-side hash, with the agent
   allowed to *merge* cases explicitly and record that it did.
