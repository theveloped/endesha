# Phase 2a spike evidence — browser as bus citizen (design §9 / §10.3)

Measured 2026-06-12 on the live cell (Aubo i10 @ 192.168.188.20, servo on,
`speed_scale=0.3`). Stack: docker router `eclipse/zenoh:1.8.0` (tcp/7447) ←
`wf.hal.aubo_i10` driver ← `zenoh-bridge-remote-api` (built from zenoh-ts tag
1.8.0, peer mode, `--ws-port 127.0.0.1:10000`) ← this app via
`@eclipse-zenoh/zenoh-ts@1.8.0` in headless Chromium.

## Checklist results

| # | Item | Result |
|---|------|--------|
| 1 | State @ full UI rate | **PASS** — joints UI receive rate **199–203 Hz** sustained (wire rate 200 Hz, `state_rate_hz=200.0`); RingChannel(1) latest-wins; twin renders at display rate decoupled from bus rate |
| 2 | Live digital twin | **PASS** — URDF + DAE meshes track reality; terminal-driven `wfctl movej` reflected in twin pose, flange xyz `(-0.1044,-0.6401,0.3564) → (0.5134,-0.2013,0.1188)`, joints read back the commanded target exactly |
| 3 | State panels | **PASS** — `mode=Running, servo_on=true, state_rate_hz=200.0`; DI/DO lamps match wire sample `di=8200` (bits 3,13), `do=1032` (bits 3,10) |
| 4 | Queryable from browser: `cmd/set_do` | **PASS** — DO pin 1 toggled on→off from the browser; lamp follows the next `state/io` sample (no optimistic update), `Ack.ok=true` both ways |
| 5 | Action lifecycle from browser | **PASS** — `execute_path` goal accepted (UUIDv7 goal id), feedback drove progress bar (sampled 0.19–0.70 mid-motion), terminal `succeeded`; Cancel → `canceled` **with physical stop** (halted at −35° en route to +40°); STOP → `aborted — cmd_stop` **with physical stop** (halted at +11° en route to +40°); concurrent second goal (second tab) rejected with verbatim `busy`. Requires the stop fix below. |
| 6 | Liveliness visibility | **PASS** — driver kill → DELETE token → badge DOWN + motion controls disabled within ~1 s; driver restart → PUT token → badge ALIVE + 200 Hz resumed, **no page reload** |

## Driver defect found by this validation — FIXED (sdk.py / __main__.py)

As found: cancel/stop transitioned goal state correctly (`canceled` /
`aborted`) but did **not physically interrupt** path-buffer motion — the
robot always completed the full trajectory (reproduced identically with the
python `ActionClient`; not a browser-slice issue). Exhaustive live probe
(`scripts/probe_stop.py`, owning RPC session, controller SERVER 0.24):

| call | rc | physically stops? |
|------|----|--------------------|
| `stopMove(True, True)` | 0 | no (resumable task-pause, ignored for path buffer) |
| `stopJoint(3.0)` | 0 | **yes — standstill in 0.42 s** (+ trips ProtectiveStop) |
| `stopLine(3.0, 3.0)` | 0 | **yes — 0.52 s** (+ trips ProtectiveStop) |
| `setServoMode` toggle | 0 | no |
| `moveJoint` preempt | 2 (busy) | no |
| `pathBufferFree` / `RuntimeMachine.abort/pause/stop` / `setSpeedFraction(0)` | 0 | no |

Version skew ruled out: the exact-match `pyaubo-sdk==0.24.1` binding behaves
identically — this controller simply ignores `stopMove` for path-buffer
motion; `moveStop()` does not exist on either binding.

**Fix** (firmware not updatable — SDK/HAL side only):
`AuboSession._stop_call` now fires `stopJoint(3.0)` (or `moveStop()` when a
future binding exposes it); `_recover_after_stop` verifies standstill
(raises `stop ineffective` if the arm keeps moving — surfaced in the goal
result instead of a false clean cancel). `_on_stop` raises
`_external_stop` *before* the blocking stop so the halt is attributed to
`cmd_stop` (→ `aborted`), and `_run_path_job` only reports `succeeded` when
the final pose matches the trajectory end (`motion_incomplete` otherwise —
kills the false-`succeeded`-mid-path failure mode observed during probing).

**Protective-stop semantics** (operator decision): `cmd/stop` deliberately
LEAVES the stop-induced ProtectiveStop in place — re-arming is an explicit
operator action via the new `cmd/clear_protective_stop` queryable
(`wfctl clear-pstop`; UI "Clear protective stop" button in the status
panel, shown only while `protective_stop=true`). The same command clears
an externally/manually triggered protective stop. Cancel auto-clears
(routine operation, back-to-back goals stay ergonomic).

Measured after fix (live): cancel → standstill + `canceled` in **0.88 s**,
follow-up goal accepted with no manual step; `cmd/stop` ack **0.81 s**,
result `aborted/cmd_stop`, `protective_stop=true` until cleared — Move
rejected `safety_stop_active` while locked, accepted immediately after the
clear button. A manually raised protective stop was cleared from the
browser with the same button. Stop is initiated within one 50 ms tick; the
~0.85 s figure is decel physics (~0.4 s) + result pathway. §9 "cancel
honored < 250 ms" should be read as initiation latency (met);
time-to-standstill is physics on this firmware.

## Environment findings (recorded for the week-4 gate)

- zenoh-ts GitHub release zips for Windows (1.8.0 **and** 1.9.0) ship only
  `zenoh_plugin_remote_api.dll` — no standalone exe. Bridge is built from
  source instead (`deploy/get_bridge.ps1`, cargo, tag 1.8.0).
- The bridge's `--ws-port <port>` binds `[::]` v6-only on Windows and refuses
  `ws://127.0.0.1`; bind explicitly: `--ws-port 127.0.0.1:10000`.
- Vite: zenoh-ts's wasm-bindgen ESM wasm import needs `vite-plugin-wasm`;
  zenoh-ts must be excluded from prebundling, and its CJS transitive deps
  (`channel-ts`, `typed-duration`, `base64-arraybuffer`, `uuid`) explicitly
  included (named-export interop in dev).
- cbor-x decodes the ns timestamps (uint64 > 2^53) as **BigInt** (verified
  against wire-identical bytes); `t` is typed `number | bigint` and is
  display-only — no UI code does arithmetic on it.
- A dropped WebSocket and a dead driver are indistinguishable at the UI today
  (both surface via the 3 s status-staleness rule + liveliness); acceptable
  for this phase, revisit with zenoh-ts close events in the UI week.

## Deferred to the week-4 gate

- ~~Hold-to-jog watchdog (requires the control lease — does not exist yet)~~
  **DONE** (phase-8 core): a generic `ControlLease` (`core/lease.py`, 30 s TTL,
  UI renews every 10 s) arbitrates motion to one client; frame-aligned
  hold-to-jog (joint + cartesian about the active TCP, in any reference frame)
  with a 250 ms **in-driver** watchdog (`speedJoint` held → `halt_speed` on
  stream stop); `execute_path` is lease-gated (`no_control`/`jog_active`). Sim
  + Aubo share the contract — full arm conformance (incl. `test_control_lease`,
  `test_execute_path_requires_lease`, `test_jog_moves_and_watchdog`) passes
  live against the sim realm. Operate page drives it; STOP stays ungated.
- ~~Camera preview @ 30 FPS in the browser~~ **DONE** (week 5, camera
  vertical): 15 Hz stream → 14.8 Hz browser-side; 30 Hz request → **22.3 fps
  browser-side == 22.3 Hz driver-side** (seq delta over 10 s, 612×512 jpeg
  q75). The FLIR BFS-PGE-50S4C sensor tops out at ~23.5 fps full-res
  (GigE-saturated), so 22 fps IS the full sensor rate — remote-api/zenoh-ts
  added **zero** frame loss. The zcam-rest webserver-plugin fallback was not
  needed.
- ~~`cmd/grab` round-trip~~ **DONE**: full-res 2448×2048 jpeg grab
  (~400 KB CBOR reply) round-trips from browser and wfctl in ~1–2 s
  (SingleFrame trigger ≈ 1 s of that); the published image-topic copy is
  byte-equal to the reply (conformance-verified) and renders in the pane
  through the one stream subscription.
- ~~Native-vs-gateway gate decision~~ **CLOSED: native zenoh-ts retained,
  no gateway.** Camera preview and grab numbers above are the evidence.
  Quirk on record: the bridge process can die during ws-session churn
  (observed once while realm-switching); restart
  `zenoh-bridge-remote-api.exe` + manual re-Connect recovers — acceptable,
  revisit only if it recurs in normal operation.

Bandwidth note (week-5 §9 measurement, recorder running): full-res jpeg q90
@ 24 Hz request → ~22 fps achieved, ~169 KB/frame ≈ 4.5 MB/s; full-res raw
BayerRG8 → ~22 fps, 5 MB/frame ≈ **132 MB/s** on the bus — the recorder kept
up with no drop warnings (1.6 GB mcap for a 27 s double run). Raw full-rate
streaming is recordable but storage-expensive; keep raw runs short.
