# Invariants — the rules every plan and PR is validated against

These are the load-bearing decisions of the platform, stated as checkable
rules. Each links to the decision record that carries the context. Breaking
one is sometimes right — but it requires an RFC that explicitly supersedes
the ADR, never a silent exception.

How to use this file:
- **Planning / RFC review**: walk the list; for each rule, state "complies /
  n.a. / needs supersession". The interesting design work usually lives
  where a plan strains against a rule.
- **Code review**: the questions are phrased to be answerable from a diff.

## Transport & topology

1. **The bus is the API.** No service↔service or UI↔service path other than
   Zenoh keys. The only standing exception is the host API's process
   lifecycle role.
   [ADR-0001](decisions/0001-zenoh-bus-is-the-api.md),
   [ADR-0010](decisions/0010-host-api-scope.md)
2. **Five shapes, one envelope.** A new interaction picks one of: stream,
   retained value, query/reply, action, config. Every command/request
   queryable speaks the reply envelope with closed error codes and
   registered reasons; retained reads answer with the identical published
   payload; streams carry no wrapper.
   [ADR-0013](decisions/0013-reply-envelope.md)
3. **The backend is never in the key.** The namespace is the fixed cell
   token (or `replay/<id>`); no key or consumer encodes or branches on
   whether a device is live, sim, or replayed.
   [ADR-0002](decisions/0002-realms.md)
4. **Realm-scoped = recorded.** Runtime state lives under the realm prefix
   (and thus replays); persistent state is realm-less config with
   provenance. Every new piece of state chooses one, explicitly.
   [ADR-0002](decisions/0002-realms.md),
   [ADR-0012](decisions/0012-config-service-provenance.md)
5. **The plan works when the prefix is `replay/<id>`.** If a feature is
   meaningless under replay, it must degrade visibly, not crash or lie.
   [ADR-0002](decisions/0002-realms.md)

## Layering

6. **Dependency direction:** core → contracts → hal → services/program.
   Never an import against the arrow. HALs never import other HALs; shared
   behaviour hoists to a `*_core` package or the contract.
   [ADR-0003](decisions/0003-package-tiers.md)
7. **Contracts contain no implementation** — keys, messages, semantics,
   conformance tests only.
   [ADR-0003](decisions/0003-package-tiers.md),
   [ADR-0004](decisions/0004-contracts-first-class-devices.md)

## Devices

8. **Every external interaction is a logical device with a contract, named
   channels, and a sim provider.** No one-off clients buried in programs or
   services. The sim provider ships with the feature, not after it.
   [ADR-0004](decisions/0004-contracts-first-class-devices.md),
   [ADR-0005](decisions/0005-simulators-are-hals.md)
9. **The arm is a peer.** A cell with no arm must work; nothing may assume
   "the" arm exists. Arm onboard IO appears as a `dio` device.
   [ADR-0004](decisions/0004-contracts-first-class-devices.md)
10. **Per-device source selection** (live/sim/replay/off) is the model; no
    whole-cell mode switches in logic.
    [ADR-0006](decisions/0006-selectable-sources.md)

## Programs

11. **Code is the only source of truth for behaviour.** Graphs/visuals are
    derived, read-only projections. No editable flow-as-data that generates
    behaviour. [ADR-0007](decisions/0007-code-first-programs.md)
12. **PackML lifecycle lives in the runner.** User programs never implement
    or bypass Start/Hold/Stop/Abort/Reset semantics.
    [ADR-0008](decisions/0008-packml-in-runner.md)

## Authority & safety

13. **One cell-level control lease, one holder.** Every mutating surface is
    lease-gated; input forcing is the deliberate, visibly-flagged
    exception. [ADR-0009](decisions/0009-cell-level-lease.md)
14. **Never the safety controller.** No software on the bus is responsible
    for preventing harm; it reports and visualizes safety state only. No
    hard real-time claims from the PC.
    [ADR-0011](decisions/0011-safety-out-of-scope.md) — permanent, not
    supersedable by RFC.

## Wire & state

17. **Retention has two classes.** Session-retained state dies with its
    producer's liveliness token; durable-retained state exists only behind
    the config service's validated write path. Every retained key names
    its class; consumers use the shared seed-then-subscribe helper.
    [ADR-0014](decisions/0014-retention-classes.md)
18. **No anonymous payloads.** Every wire payload is a named message type
    in its contract, following the [wire vocabulary](wire-vocabulary.md)
    (ns timestamps, `seq` on streams, unit suffixes, null-vs-absent,
    tolerant reader, additive-only evolution).
    [ADR-0013](decisions/0013-reply-envelope.md)

## Fit & finish

15. **Conformance over trust.** A new contract implementation (including
    sims) passes the contract's conformance suite over the bus before it is
    considered done.
    [ADR-0004](decisions/0004-contracts-first-class-devices.md),
    [ADR-0005](decisions/0005-simulators-are-hals.md)
16. **Descriptors over hardcoding.** The UI renders what inventory and
    descriptors declare; it never hardcodes a specific cell's devices.
    [ADR-0004](decisions/0004-contracts-first-class-devices.md),
    [ADR-0006](decisions/0006-selectable-sources.md)
