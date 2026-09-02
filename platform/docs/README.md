# Documentation map

This file is the **single entry point** for every piece of documentation
and agent guidance in this repository. The rule that keeps it honest:
**every markdown document in the repo must be reachable from this page**
(directly or through a linked page), and every relative link must resolve —
checked mechanically by [`scripts/check_docs.py`](../scripts/check_docs.py)
(`pixi run docs-check`). A doc the checker reports as orphaned is either
linked here or deleted; there is no third state where a file quietly
steers the agent without being visible from this map.

Each document answers one kind of question. If you cannot name which
document a piece of writing belongs in, it probably mixes two kinds and
should be split.

| Question | Document | Nature |
|---|---|---|
| How is the system built *today*? | [architecture.md](architecture.md) | As-built, verified against source. Wins over RFCs and design v5. Updated in the same PR that changes the architecture. Includes the [seams list](architecture.md#12-seams--known-gaps) — read it when looking for what no longer should hold. |
| What rules must a plan not break? | [invariants.md](invariants.md) | Checklist distilled from ADRs; walked rule-by-rule for every plan/RFC. |
| Why is it this way? | [decisions/](decisions/) — index below | Append-only ADRs. Superseded, never rewritten. |
| What are we about to build? | In-flight RFCs, repo root: [wire-contract-rfc.md](../../wire-contract-rfc.md), [vision-pipeline-rfc.md](../../vision-pipeline-rfc.md) | Proposal. Historical once landed. |
| What did we build from? | [program-layer-rfc.md](../../program-layer-rfc.md) (landed), [automation-framework-design-v5.md](../../automation-framework-design-v5.md) (founding design), [gui-design-spec.md](../../gui-design-spec.md) (early UI spec), [web/SPIKE.md](../web/SPIKE.md) (bus-citizen gate evidence) | Historical. Where they disagree with architecture.md, architecture.md wins. |
| How do I run it locally? | [DEVELOPMENT.md](../DEVELOPMENT.md) | Operational how-to. |
| How do I write a program? | [PROGRAMS.md](../PROGRAMS.md) | Authoring guide for `wf.program`. |
| What are the wire conventions? | [wire-vocabulary.md](wire-vocabulary.md) | Field/encoding/evolution rules every payload follows. |
| Web app dev notes | [web/README.md](../web/README.md) | Vite/React housekeeping. |
| External datasheets/manuals | [references/reference-inventory.md](../../references/reference-inventory.md) | Pointer inventory for vendor material. |
| Robot asset provenance | [aubo_description/README.md](../packages/hal/aubo_i10/src/wf/hal/aubo_i10/assets/aubo_description/README.md) | Where the URDF/meshes came from. |

## Decision records (ADRs)

| | Decision |
|---|---|
| [0001](decisions/0001-zenoh-bus-is-the-api.md) | Zenoh is the single fabric; the bus is the API |
| [0002](decisions/0002-realms.md) | One key space; the backend is never in the key; replay is a realm |
| [0003](decisions/0003-package-tiers.md) | Package tiers with one dependency direction |
| [0004](decisions/0004-contracts-first-class-devices.md) | Every device class is a first-class contract; the arm is a peer |
| [0005](decisions/0005-simulators-are-hals.md) | Simulators are HALs; swappability is tested |
| [0006](decisions/0006-selectable-sources.md) | Logical devices with selectable sources (live/sim/replay/off) |
| [0007](decisions/0007-code-first-programs.md) | Code-first statechart programs; graphs are derived |
| [0008](decisions/0008-packml-in-runner.md) | PackML unit states live in the runner |
| [0009](decisions/0009-cell-level-lease.md) | One cell-level control lease; input forcing ungated |
| [0010](decisions/0010-host-api-scope.md) | Host API = cell registry + supervisor lifecycle only |
| [0011](decisions/0011-safety-out-of-scope.md) | Never the safety controller (permanent) |
| [0012](decisions/0012-config-service-provenance.md) | Config is realm-less, via the config service, with provenance |
| [0013](decisions/0013-reply-envelope.md) | Five interaction shapes; one reply envelope |
| [0014](decisions/0014-retention-classes.md) | Two retention classes: session vs durable |
| [0015](decisions/0015-generated-typescript.md) | The TS wire mirror is generated from the Python contracts |

## Agent context — everything that steers Claude, and where it lives

So that no guidance is invisible to a human reader, this is the complete
inventory of what an agent session loads or consults:

| Context | Location | Visible how |
|---|---|---|
| Repo instructions | [CLAUDE.md](../CLAUDE.md) | In-repo, versioned. Points into this map; contains the doc-lifecycle rules and pre-commit checks. |
| This documentation tree | `platform/docs/` + the linked files above | In-repo, versioned. |
| User-global instructions | `~/.claude/CLAUDE.md` | **Out-of-repo**, user-owned. Policy: personal tooling only (currently: the graphify skill trigger) — never project guidance. |
| Persistent agent memory | `~/.claude/projects/<this-project>/memory/` | **Out-of-repo.** Policy: memory holds *pointers* to repo docs and personal/user facts, never standing project guidance of its own. Anything durable about the project belongs in this docs tree, where you can read it. |
| Tool permissions | `.claude/settings.local.json` (repo root) | In-repo config; permissions only, no guidance. |

If an agent session learns something durable about the project, the correct
write target is this docs tree (usually architecture.md, a new ADR, or a
seam row) — *not* its private memory. That policy is what the inventory
above enforces socially; `docs-check` enforces the in-repo half
mechanically.

## The lifecycle (how these stay honest)

1. **A feature starts as an RFC** (repo root) — including a "Decisions
   already taken" section and a walk of the plan against
   [invariants.md](invariants.md): each rule marked *complies / n.a. /
   needs supersession*.
2. **Review resolves the open questions**; decisions from review are
   written into the RFC (as both existing RFCs already do).
3. **When the work lands**, the same PR adds one short ADR per durable
   decision, updates [architecture.md](architecture.md) (including seam
   rows it closes or opens), and — rarely — adds a rule to
   [invariants.md](invariants.md).
4. **RFCs are then historical.** Nobody maintains them; nobody should need
   one to learn the current system.

## ADR format

Small and boring on purpose (~30 lines): title stating the decision, date +
source, **Decision**, **Consequences**, and — the point of this repo's
ADRs — **Validate new plans against**: the concrete question a reviewer
asks of a future plan. Status is `accepted` until another ADR supersedes
it; add `superseded by ADR-NNNN` at the top, never rewrite history.

## Reading this as HTML

Every file here is plain Markdown with relative links, so it renders as a
browsable, clickable site anywhere Markdown renders: GitHub (browse
`platform/docs/` on the repo), VS Code (`Ctrl+Shift+V`), or any static
renderer. No generator, no build step, no second copy to drift.
