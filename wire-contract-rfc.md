# RFC — Wire contract: five shapes, one reply envelope, generated TypeScript

Status: **reviewed — accepted** (2026-09-01; decisions from review in §11).
Branch: `observability`. Implementation: core envelope/retained helpers, dio+tags, control, and washer commands landed (with conformance); program/camera2d/arm/config + codegen pending.
Builds on ADR-0001…0012 ([platform/docs/decisions/](platform/docs/decisions/)),
the query/reply audit (`wf.core.audit`), the conformance mechanism
(arm/camera2d/dio), and the as-built picture in
[platform/docs/architecture.md](platform/docs/architecture.md).
First RFC written under the documentation lifecycle
([platform/docs/README.md](platform/docs/README.md)) — it includes the
invariants walk (§8) that lifecycle prescribes.

## 0. Decisions already taken (not up for discussion here)

- **The bus is the API**; streams are pub/sub, requests are queryables,
  long operations are actions, persistent data goes through the config
  service ([ADR-0001](platform/docs/decisions/0001-zenoh-bus-is-the-api.md)).
  This RFC renames and sharpens that taxonomy; it does not change the
  transport. No request/response topic pairs; no merging queries into
  actions — both were examined and rejected (a query is atomic from the
  caller's view; an action has identity mid-flight: cancellable,
  progress-reporting, Hold-aware).
- **The backend is never in the key**; realm-scoped = recorded
  ([ADR-0002](platform/docs/decisions/0002-realms.md)).
- **Contracts are dataclasses + conformance, not pydantic, not a schema
  registry** ([ADR-0004](platform/docs/decisions/0004-contracts-first-class-devices.md)).
  This RFC keeps that: rigor by enforcement, not by runtime validation.
  A full external IDL (protobuf/CDDL) remains declined; §7 is *not* that.
- **Reads and state polls are not audited**; the audit policy stands.

## 1. Goals / non-goals

Goals

1. Name the interaction shapes that actually exist — five, not four — so
   each new feature picks one instead of re-deciding conventions.
2. **One reply envelope** for every queryable on the bus: a caller sends
   one request shape and handles exactly three reply branches. Generic
   tooling (audit, proxies, UI, conformance, retries) gets one code path.
3. A **closed error grammar** so errors are enumerable, retryable-aware,
   and machine-checkable instead of free text.
4. **Self-describing goals**: the reply carries the follow keys, so
   clients need no key-building convention for the goal lifecycle.
5. Make all of the above **enforceable by conformance suites** from the
   start — uniformity you can fail in CI, not review into existence.
6. **Generate the TypeScript side from the Python dataclasses** — the
   promise design v5 §2.1 already made ("Python dataclasses + generated
   TypeScript") and that was never built. Kill the hand-maintained mirror
   and the second hand-rolled CBOR encoder at the root.

Non-goals

- No transport change. Queryables stay queryables (absence detection,
  reply routing, glob completion are load-bearing; see §10 prior art).
- No envelope on streams. The 200 Hz joints payload stays lean; streams
  get a shared *header convention* only (§6).
- No runtime schema registry, no protobuf/CDDL, no build-time coupling of
  consumers to a codegen pipeline beyond one in-repo script (§7).
- No change to safety semantics, lease semantics, or the audit policy.
- Not in scope: making callers ignorant of semantics. The envelope makes
  the wire self-describing for *tools*; a program author must still know
  that `open_door` is cancellable mid-travel. The contract fixes the
  shape per key at design time; the envelope makes it discoverable at
  runtime.

## 2. Motivation — the drift is measurable, in-repo, today

- **Six reply dialects.** `Ack`, `{ok, revision}`, `GrabReply`,
  `ControlAck`, the action-accept shape, supervisor's inline dicts.
  `wf.core.audit.QueryAudit` derives `ok` by sniffing replies for *either*
  an `ok` *or* an `accepted` field — that heuristic exists precisely
  because there is no uniform envelope.
- **Key-building knowledge is duplicated by hand.** `web/src/lib/config.ts`
  mirrors every Python `keys.py` by hand; the action client in
  `actions.ts` constructs feedback/result keys by convention. The web
  exploration flagged the mirror as an explicit, comment-maintained drift
  surface.
- **Two CBOR write paths.** `cbor-x` for reads, a hand-rolled float-marking
  encoder for camera2d because `cbor-x` encodes `1.0` as an int. The
  cross-language gate (`web/scripts/_cbor_gate_*`) is run manually.
- **An unnamed fifth shape.** Publish latest-wins *and* answer the same
  key as a queryable is used consistently in at least six places
  (`program/state`, `programs/catalog`, `control/state/owner`, supervisor
  log/event rings, action results, config republish) with no shared
  helper and no rule; each consumer re-implements seed-vs-delta ordering.
- **Retry safety is partial.** Actions have client-minted UUIDv7 goal ids
  (idempotent resubmission); plain commands have nothing — a dropped
  reply on `cmd/set` cannot be retried safely.

## 3. The five shapes

The taxonomy becomes: **two primitives, three codified patterns.**

| # | Shape | Primitive(s) | Rule |
|---|---|---|---|
| 1 | **Stream** | pub/sub | High-rate telemetry, best-effort, latest-wins. No envelope; shared header `{t, seq}` (§6). |
| 2 | **Retained value** | pub/sub + queryable | Latest-wins publish; the *same key* answers queries with the *same payload* (§3.1). |
| 3 | **Query/reply** | queryable | One request shape, one reply envelope (§4). |
| 4 | **Action** | 3 + 1 + 2 | A query whose reply is the envelope's `goal` branch; feedback is a stream; the result is a retained value whose payload is itself the envelope (§4.3). |
| 5 | **Config** | 3 + 2, durable | An ordinary shape-3 write behind the config service's validating gate; an ordinary shape-2 read — with durability and provenance as its extra property. |

Shapes 4 and 5 are *compositions* of 1–3. Naming them stays valuable (the
protocol conventions are the feature — ROS 2's actions are likewise built
from services + topics, and naming the composition was the whole point),
but the layering is now stated honestly.

### 3.1 Retained value, made a rule

- Querying a retained key returns exactly the payload last published on
  it — the *identical* payload both ways; retained reads are not
  enveloped. (Implementation note 2026-09-01: this simplifies the earlier
  value-branch gloss — byte-equal is stronger and keeps state readers
  untouched.) **Query/subscribe equivalence is a conformance assertion.**
- Consumer discipline, provided once as a core helper per language
  (Python + TS) instead of re-implemented per consumer: **subscribe
  first, seed with a query second, deltas win over the seed.** The web's
  `subscribeConfigList` already encodes this; the helper generalizes it.
- **Two retention classes** — this distinction is the invariant candidate:
  - **Session-retained** (shape 2): lives and dies with its producer's
    liveliness token. Inventory, program state, owner, rings. A consumer
    that sees the token drop treats the value as gone — "authority not
    alive ⇒ nobody holds the lease" generalized.
  - **Durable-retained** (shape 5): survives restarts, exists *only*
    behind the config service's validated, provenance-keeping write path.
  Blurring the classes is how retained-state systems serve stale truth
  after a crash (MQTT retained messages being the cautionary tale). A
  crashed supervisor must not keep asserting a device list.

## 4. The reply envelope

### 4.1 Request

Every queryable request is:

```json
{ "req_id": "0198f3c9-…",          // client-minted UUIDv7, always
  "client_id": "ui:7f3a…",         // who is asking (as today)
  "args": { … } }                   // named message type from the contract
```

`req_id` on *every* request extends the actions' idempotent-resubmission
property to all commands: a provider that has seen this `req_id` replies
with the original outcome instead of re-executing.

### 4.2 Reply — one tagged union, three branches

```json
{ "ok": true,  "value": { … } }                       // answered now
{ "ok": true,  "goal":  { … } }                       // accepted; follow the keys
{ "ok": false, "error": { … } }                       // refused (§5)
```

The `goal` branch is fully closed — it contains zero domain content:

```json
{ "goal_id":      "0198f3c2-…",     // the adopted req_id → retries stay idempotent
  "state":        "running",         // accepted-queued vs running
  "feedback_key": "cell/arm/r1/action/0198f3c2-…/feedback",
  "result_key":   "cell/arm/r1/action/0198f3c2-…/result",
  "cancel_key":   "cell/arm/r1/action/cancel",
  "result_ttl_s": 60 }
```

Returning the keys (rather than clients building them by convention)
makes the goal lifecycle self-describing and shrinks the TS key mirror.
`result_ttl_s` surfaces server behavior that today is undocumented.

Feedback gets a fixed header with domain content quarantined:

```json
{ "t": …, "seq": 3, "goal_id": "0198f3c2-…", "progress": 0.4, "detail": { … } }
```

(`progress` optional 0–1 — a wash cycle knows it, a wait-for-part
doesn't; `detail` is the only domain-shaped hole.)

### 4.3 The result is recursively the envelope

The result key is a retained value (shape 2) whose payload is the
envelope's value/error branch:

```json
{ "ok": true,  "value": { "final_q": [ … ] } }
{ "ok": false, "error": { "code": "cancelled", "reason": "hold" } }
```

So result standardization comes for free, and shape 4 is visibly shapes
3 + 2 composed.

### 4.4 The SDK surface

One `call(key, args)` helper in `wf.core` and in the TS client: returns a
future that resolves immediately on `value`, transparently follows
`result_key` on `goal`, raises/rejects a typed error on `error`. Generic
consumers become branch-agnostic; an operation that starts synchronous
(`set_tcp`) can later become a goal **without breaking a single caller**.
`QueryAudit` reads the envelope directly; the ok/accepted sniffing is
deleted.

### 4.5 Concrete before/after (dio set, control acquire, execute_path)

```json
→ cell/dio/io0/cmd/set      { "req_id": "…", "client_id": "ui:7f3a…",
                              "args": { "channel": "clamp", "value": true } }
← { "ok": true, "value": {} }

→ cell/control/cmd/acquire  { "req_id": "…", "client_id": "ui:7f3a…",
                              "args": { "user": "tobias" } }
← { "ok": false, "error": { "code": "conflict", "reason": "held_by",
                            "detail": "program:demo_pick", "retryable": false } }

→ cell/arm/r1/action/execute_path
                            { "req_id": "0198f3c2-…", "client_id": "program:demo_pick:a1b2",
                              "args": { "waypoints": [ … ], "tcp": "camera_tcp" } }
← { "ok": true, "goal": { "goal_id": "0198f3c2-…", "state": "running", … } }
```

The demo of the whole idea in one line: the `execute_path` request and
the `set` request are **the same message shape**; the caller that gets
`value` back is done, the one that gets `goal` back follows the keys it
was handed.

## 5. The error grammar

The existing error strings are already half a grammar
(`held_by:…`, `busy`, `invalid_key:…`, `bind:role:ambiguous:…`,
`provided_by:…`, `lease_lost:…`, `safety:estop`). What is missing is a
closed top level. Following gRPC's canonical-codes precedent:

```json
{ "code": "conflict", "reason": "held_by", "detail": "program:demo_pick",
  "retryable": false }
```

| `code` | Meaning | Existing strings that map onto it |
|---|---|---|
| `invalid` | request malformed / fails validation | `invalid_key:`, `bad_frame:`, `bind:…`, `bad_cell:` |
| `conflict` | valid but conflicts with current holder/state | `held_by:`, `provided_by:`, `reserved_name:` |
| `busy` | one-active-goal / try later | action `busy` |
| `unavailable` | serving party absent | no authority alive, `no_source:` |
| `not_found` | referent unknown | `unknown_goal`, `unknown_device:` |
| `cancelled` | terminated by cancel/Hold/Stop | `cancelled:hold` |
| `safety` | terminated by the safety chain (reported, never implemented — ADR-0011) | `safety:estop`, `safety:protective_stop` |
| `internal` | provider fault | `spawn_failed:`, `action_hang:` |

Rules that make it a standard rather than a style: `code` comes from this
one shared enum in `wf.core` (**adding a code is an ADR-level event**);
`reason` comes from a per-contract list registered in the contract
package; `retryable` lets a generic SDK retry without domain knowledge;
`detail` is human-oriented and **never parsed**. Conformance asserts every
emitted error uses a registered code+reason.

## 6. Value rules and the wire vocabulary

The content of `value` is the domain; no standard flattens it. Three
frame rules around it:

1. **No anonymous payloads.** Every `value`, stream sample, and retained
   payload is a named message type in the contract's `messages.py`. The
   supervisor contract's inline dicts (architecture seam #3) become a
   conformance failure, not a style complaint.
2. **One wire-vocabulary page** (`platform/docs/wire-vocabulary.md`, new)
   fixing conventions that today exist as habits: integer-nanosecond `t`
   (capture time); monotonic per-publisher `seq` on every stream sample
   (streams only — review decision §11.4; retained values carry `t`
   without a mandated `seq` for now); SI units bare, non-SI suffixed
   (`_deg`, `_s`, `_ms`); absent
   means "no statement", `null` means "explicitly none"; id naming
   (`req_id`/`client_id`/`goal_id`, UUIDv7 where minted). The camera2d
   CBOR gate already tests null-vs-absent and float-vs-int for one
   contract — the vocabulary extends that to all.
3. **Evolution.** Tolerant reader everywhere (unknown fields ignored,
   never an error); changes additive-only; a breaking change means a new
   key, not a mutated message. This is what keeps recorded MCAP files
   replayable against next year's code — for a record-everything platform
   that is a requirement, not hygiene.

## 7. Generated TypeScript (the reconsidered IDL question)

Reconsidered, and landed in the middle: **no external IDL — the Python
dataclasses become the formal source of truth, and the TS side is
generated from them.** This is design v5 §2.1's original wording
("message schemas: Python dataclasses + generated TypeScript"); the
hand-written mirror is where that promise was dropped.

One in-repo generator (a `wf.tools` script, stdlib + introspection of the
contract packages; no third-party codegen framework) emits, per contract:

- TS interfaces for every message type (from the dataclass fields),
- TS key-builder functions (from `keys.py`),
- TS CBOR encode/decode with correct float/int handling (the generator
  knows which fields are floats — the hand-rolled float-marker encoder
  and its class of bugs disappear),
- the envelope/error/goal types once, from `wf.core`.

Generated output is committed (reviewable diffs, no build-time coupling);
`docs-check`'s sibling `pixi run wire-check` regenerates and fails on
drift, and the existing CBOR gate becomes the generator's cross-language
regression test, run in the same check. What this deliberately does not
add: runtime validation, a schema registry, or any consumer-side codegen
step. The escalation path to a formal IDL stays open if contracts ever
cross an organizational boundary.

## 8. Invariants walk ([platform/docs/invariants.md](platform/docs/invariants.md))

| Rule | Verdict |
|---|---|
| 1 bus is the API | complies — transport untouched |
| 2 four interaction shapes | **needs supersession** — this RFC's core: five named shapes + envelope. ADR-0013 supersedes ADR-0001; rule 2 rewritten |
| 3 backend never in the key | complies |
| 4 realm-scoped = recorded | complies — audit/feedback/results stay realm topics |
| 5 works under replay | complies — streams unchanged, so recordings replay; envelope applies to request/reply, which replay does not re-execute |
| 6 dependency direction | complies — envelope + error enum live in `wf.core`; generator in `wf.tools` reads contracts (tools may depend on contracts; contracts stay implementation-free) |
| 7 contracts contain no implementation | complies — registered reason lists are data |
| 8 device = contract + channels + sim provider | n.a. |
| 9 arm is a peer | n.a. |
| 10 per-device sources | n.a. |
| 11 code is the only source of truth | complies — generated TS is derived artifact, Python is the truth; committed output is a projection, like the program graph |
| 12 PackML in the runner | n.a. |
| 13 one cell lease | complies — `client_id` unchanged |
| 14 never the safety controller | complies — `safety` error code *reports* chain state, per ADR-0011 |
| 15 conformance over trust | strengthened — envelope, equivalence, and error grammar become conformance assertions |
| 16 descriptors over hardcoding | strengthened — self-describing goal keys remove client key conventions |

New invariant candidates on landing: (a) every queryable replies in the
envelope; every retained key is query/subscribe equivalent; (b)
session-retained state dies with its producer's liveliness token;
durable-retained state exists only behind the config service; (c) no
anonymous payloads — every wire payload is a named contract message type.

## 9. Delivery order

Contract-by-contract, each step behind conformance, docs landing with
each PR per the lifecycle. Wire-breaking for request/reply — and this is
the cheapest it will ever be: every consumer ships from this repo, no
fleet is deployed, and streams (hence existing MCAP recordings) are
untouched.

1. **Core**: envelope + error enum + `call()` in `wf.core` and the TS
   client; `QueryAudit` reads the envelope (sniffing deleted). Retained
   seed-then-subscribe helper both sides.
2. **Pilot: `dio`** (smallest contract with a conformance suite; `tags`
   rides along automatically — both are served by the shared
   `ChannelsCore`, so the pilot covers the table contracts).
   Envelope + query/subscribe-equivalence + registered-error assertions
   added to its conformance tests; provider + Python proxy + web client
   migrate in one PR.
3. **Sweep**: `control`, `tags`, `washer`, `program`, `camera2d`, `arm`
   (actions last), `config`; write `supervisor/messages.py` (closes
   architecture seam #3). Conformance suites added where missing as each
   contract is touched.
4. **Codegen**: the generator, swap `config.ts`/`messages.ts`/hand codec
   for generated modules, `wire-check` task wired into the pre-commit
   checks next to `docs-check`.
5. **Docs on each landing**: ADR-0013 (five shapes + envelope, supersedes
   ADR-0001), ADR-0014 (retention classes), ADR-0015 (generated TS),
   `wire-vocabulary.md`, invariants rules updated, architecture §3
   rewritten, seams #3/#11/#12 updated or closed.

## 10. Prior art (why this shape and not another)

- **ROS 2** maps near 1:1 onto the five shapes (topic / TRANSIENT_LOCAL
  latched topic / service / action / parameters+YAML) — validating the
  taxonomy — but names only three of them, never standardized service
  replies (`bool success, string message` is unenforced folklore: the
  same multi-dialect disease §2 documents here), has **no
  durable-retained class** (the YAML-file gap this platform's config
  service already fills), and took until Iron (2023) to add service
  introspection — its QueryAudit. Its *action* envelope, however,
  independently confirms this design: client-generated goal UUIDs, a
  closed status enum. One divergence in our favor: ROS builds goal topic
  names by convention in the client library; we return them in the reply.
- **gRPC**: the closed canonical error codes (§5).
- **HTTP 202 + Location / cloud long-running-operations**: the
  sync-or-goal tagged reply (§4).
- **Rejected**: request/response topic pairs (loses absence detection,
  reply routing, glob completion — and the recorder-visibility argument
  is already paid by `QueryAudit`); merging queries and actions (the
  distinction is identity mid-flight, not duration); full external IDL
  (§7).

## 11. Decisions from review (2026-09-01)

1. **Envelope for the host API: no.** The host API's three HTTP endpoints
   keep their plain JSON replies; the envelope is a bus convention. (The
   symmetry argument was considered and declined — the host API is
   already the deliberate exception to bus uniformity, ADR-0010.)
2. **`client_id` is top-level beside `req_id`** — it is protocol (the
   lease check needs it), not domain args.
3. **Error codes: the §5 eight-code set stands** for now. Additions
   remain ADR-level events. (`unauthenticated`/`permission` style codes
   deliberately absent — the lease *is* the authorization model and maps
   onto `conflict`.)
4. **`seq` is mandatory on streams only.** Retained values carry `t`;
   no mandated `seq` for now (§6 adjusted accordingly).
5. **Empty `value` is `{}`** — the branch is always present on `ok`.
6. **No migration of recorded audit shapes, and no backwards
   compatibility required.** Old recordings carry the old reply dialects
   in their audit records as-is; viewers are not required to render them
   under the new grammar.
