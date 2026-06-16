# Automation Framework — Architecture Design (v5)
*(first cell: Aubo i10 cobot + eye-in-hand GigE camera)*

**Target stack:** Python services · Zenoh bus · React + react-three-fiber (Three.js) UI
**Hardware:** Aubo i10 (existing Python CLI), GigE eye-in-hand camera via Harvester (GenICam), future additional GigE cameras (robot-mounted or fixed)

---

## 1. Goals & non-goals

### Goals
1. One **command channel** to the Aubo (paths, DIO writes) and one **high-rate state channel** (pose + IO, read as fast as the controller allows).
2. **Camera service** built on Harvester, calibrated intrinsics + extrinsics; the hand-eye result is stored as a robot **TCP** so the camera optical frame is a first-class tool frame. Multi-camera ready (eye-in-hand and fixed).
3. **Zenoh** as the single message fabric: pub/sub for streams, queryables for synchronous actions, storages for configuration.
4. **Interchangeable backends**: real robot ↔ simulated digital twin, real camera ↔ rendered camera — identical key space, so nothing upstream changes.
5. **Record everything** flowing on the bus into a scrubbable log (MCAP), enabling: timeline scrubbing on the digital twin, replaying recordings through updated vision pipelines, and offline regression testing.
6. Prepared seams for a **behavior tree / state machine** task layer.
7. A **teach-pendant-grade web UI** (jog, program, IO, safety) plus camera feeds and vision overlays, with rerun-style 3D/2D visualization and a replay timeline.

### Non-goals — permanent, not "for now"
- **This framework coordinates automation; it is not the safety controller.** Safety-rated functions (e-stop circuits, protective stops, enabling devices/deadman, safeguarded space) live in the robot controller and safety PLC/hardware, never in Zenoh, Python, or React. The web UI may *request* motion; the driver enforces lease, watchdog, speed clamp and mode checks; the safety chain remains physical and certified. The bus *reports* safety state, it never implements it.
- Hard real-time servo control from the PC (we command the Aubo controller; the controller closes the servo loop).
- Multi-robot coordination logic (but the key space is namespaced per resource so it costs nothing to prepare).

---

## 2. Core architectural principles

1. **The bus is the API.** Every capability (move, set DIO, grab frame, calibrate, replay-seek) is expressed as Zenoh keys. Services and the UI never talk to each other directly — only via the bus. This is what makes live / sim / twin / replay swappable.
2. **One key space, many realms.** All keys share one schema; the first segment is a *realm* (`live`, `sim`, `replay/<session>`). A digital twin mirroring a live robot is just a second realm running simultaneously.
3. **Streams are pub/sub, actions are queryables, config is storage.**
   - High-rate telemetry → publishers (best-effort, latest-wins for UI).
   - Synchronous requests (set DIO, get calibration, start move) → Zenoh queryables (request/reply).
   - Long-running operations (execute path, run calibration) → *action pattern*: a queryable accepts the goal and returns a `goal_id`; progress streams on a feedback key; result lands on a result key. (Same shape as ROS 2 actions, but plain Zenoh.)
   - Persistent data (TCPs, calibrations, programs, scene config) → Zenoh storage-backed keys or a small config service with queryables; either way addressed by key.
4. **Sources of truth are explicit.** The robot controller owns kinematic truth in `live`; the simulator owns it in `sim`; the MCAP file owns it in `replay`. Consumers never care which.
5. **Time is recorded, not assumed.** Every message carries a capture timestamp (and Zenoh's HLC timestamp comes for free). Replay republishes with original timestamps in the payload plus a replay-clock topic, so consumers can run in "data time".

### 2.1 Layered resource model — contracts and HALs

To make this a general automation framework rather than a one-cell app, the stack is split into three layers with strict dependency direction (lower layers know nothing about upper ones):

**L0 — `core` (transport & patterns; the package formerly known as `cobotlib`).** Zenoh session bootstrap, CBOR codecs, the action pattern (server/client), frames helper, registry/liveliness helpers, structured logging. Knows nothing about robots or cameras.

**L1 — `contracts/*` (resource-class definitions).** One package per *device class*, each defining:
- the key-space template `{realm}/{class}/{instance}/...`,
- the message schemas (Python dataclasses + generated TypeScript),
- action semantics (goal/feedback/result payloads, cancel behavior),
- required config keys (e.g. an arm must expose `config/arm/{id}/urdf` and a TCP store),
- a **conformance test suite**: a pytest package that exercises any implementation purely over the bus.

Initial contracts:

| Contract | Covers | Core surface |
|---|---|---|
| `arm` | 6-axis+ manipulators | joints/flange/tcp/io/status streams; set_do/set_tcp/jog; execute_path action |
| `camera2d` | area-scan cameras | image + preview streams; configure; grab; intrinsics/mount config |
| `dio` | standalone IO devices (bus couplers, PLC blocks) | io state stream; set_do/set_ao |
| later: `gripper`, `conveyor`, `camera3d`, … | | |

The arm's onboard IO **embeds the `dio` message shapes** (`arm/{id}/state/io` uses the same payloads as `dio/{id}/state/io`), so IO panels, recording analysis and BT leaves work identically on robot IO and standalone IO hardware.

**L2 — `hal/*` (implementations).** A HAL binds a contract to concrete hardware: a process entrypoint wrapping the vendor SDK, plus assets (URDF + meshes, joint/velocity limits, motion-profile parameters) and quirk configuration.
- `hal/aubo_i10` implements `arm` (your existing CLI code becomes its SDK layer).
- For cameras, GenICam is *already* a hardware abstraction — so a single `hal/genicam` (Harvester) implements `camera2d` for most GigE/USB3 cameras, with small per-model feature-name maps. A new camera model is usually a YAML entry, not a new HAL.
- **Simulators are HALs too:** `hal/arm_sim` implements `arm` for any URDF + motion profile; `hal/camera2d_sim` implements `camera2d` by rendering. The conformance suite runs in CI against the sim HALs and on demand against real hardware — swappability is *tested*, not hoped for.

**Resource instances, supervision & discovery.** A deployment is one `cell.yaml`: a list of resources `{id, contract, hal, params}` (your cell: one `arm` via `aubo_i10`, one `camera2d` via `genicam`, mount=flange). A `supervisor` service launches/restarts HAL processes from it. Each running resource asserts a liveliness token and answers `{realm}/registry/{id}` with a **resource descriptor** — a formal schema in `core`, versioned like any contract message:

```yaml
id: r1
contract: arm            # + contract_version
hal: aubo_i10            # + hal_version
realm: live
capabilities: {motion: {movej: true, movel: true, jog_joint: true, jog_cartesian: true},
               io: {digital_in: 16, digital_out: 16}}
limits: {joints: [...], velocity: [...], acceleration: [...]}
assets: {urdf: config/arm/r1/urdf}
```

The UI builds itself from descriptors — panels render the capabilities and limits they find, never hardcoded assumptions about what an "arm" can do. The UI subscribes to the registry and instantiates **panel plugins keyed by contract type** — an `arm` gets jog/teach/IO panels, a `camera2d` gets an image pane. Adding a device class to the framework = new contract + HAL + panel plugin; `core`, recorder, replayer and registry are untouched.

**Key-space note:** keys use *contract* names from day one — `{realm}/{contract}/{instance}/...`, i.e. `arm/r1`, `camera2d/cam0`, `dio/io1` — never `robot/` or `camera/`. This costs nothing now and avoids a fleet-wide key migration later; panel plugins key off the same names.

---

## 3. System topology

```
                                ┌────────────────────────────────────────────┐
                                │                 Zenoh router                │
                                │   (+ storage plugin, + remote-api plugin)  │
                                └───────┬──────────┬──────────┬──────────────┘
            pub/sub + queryables        │          │          │   WebSocket (zenoh-ts)
        ┌───────────────┬───────────────┤          │          └───────────────┐
        │               │               │          │                          │
┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼─────┐ ┌──▼─────────┐        ┌───────▼────────┐
│ aubo_driver  │ │ camera_driver│ │ vision    │ │ task_runner│        │  React + R3F   │
│  (live)      │ │  ×N (live)   │ │ pipelines │ │ (BT, later)│        │  pendant UI    │
│ cmd socket ──┼─► Aubo i10     │ │           │ └────────────┘        │  3D, cameras,  │
│ state socket◄┼── controller   │ │           │                       │  timeline      │
└──────────────┘ └──────────────┘ └───────────┘                       └────────────────┘
        ▲               ▲
        │ same keys     │ same keys                ┌──────────────┐   ┌──────────────┐
┌───────┴──────┐ ┌──────┴───────┐                  │   recorder   │   │   replayer   │
│  sim_robot   │ │  sim_camera  │                  │ realm/** →   │   │ MCAP → realm │
│ (digital twin│ │ (offscreen   │                  │ MCAP file    │   │ + clock ctrl │
│  kinematics) │ │  render)     │                  └──────────────┘   └──────────────┘
└──────────────┘ └──────────────┘
```

Every box is an independent Python process (the UI excepted), connected only to the Zenoh router. Any subset can run on any machine; the GigE camera driver typically runs on the host with the NIC tuned for jumbo frames.

---

## 4. Zenoh key space

`{realm}` ∈ `live` | `sim` | `replay/{session_id}`. `{rid}` = robot id (`r1`), `{cid}` = camera id (`cam0`, `cam1`).

### 4.1 Arm telemetry (pub/sub, high rate)

| Key | Rate | Payload (CBOR) |
|---|---|---|
| `{realm}/arm/{rid}/state/joints` | max (≈100–200 Hz from Aubo SDK) | `{t, q[6], qd[6], tau[6]}` |
| `{realm}/arm/{rid}/state/tcp` | same | `{t, tcp_name, pose: {xyz, quat}, frame: "base"}` |
| `{realm}/arm/{rid}/state/flange` | same | flange pose in base (so TCP math is checkable) |
| `{realm}/arm/{rid}/state/io` | on change + 10 Hz keepalive | `{t, di: bits, do: bits, ai[], ao[]}` |
| `{realm}/arm/{rid}/state/status` | on change + 1 Hz | `{mode, servo_on, estop, protective_stop, speed_scale, active_tcp, error}` |

The state-socket reader thread in `aubo_driver` does nothing but read → decode → publish; no logic, no locks shared with the command side.

### 4.2 Arm commands

Short synchronous ops — queryables (reply = ack/result):

- `{realm}/arm/{rid}/cmd/set_do` `{pin, value}`
- `{realm}/arm/{rid}/cmd/set_tcp` `{name}` (selects from TCP store)
- `{realm}/arm/{rid}/cmd/set_speed_scale` `{scale}`
- `{realm}/arm/{rid}/cmd/stop` (category 2 stop / abort current goal)
- `{realm}/arm/{rid}/cmd/jog` — see safety note below

Long-running ops — action pattern:

- `{realm}/arm/{rid}/action/execute_path` — goal: list of waypoints `{type: movej|movel|movec, target: {frame, pose}|{q[6]}, speed, accel, blend_radius, tracking?: false}` → reply `{goal_id}`; frame-referenced targets are resolved to base at goal acceptance (§4.5)
  - feedback: `{realm}/arm/{rid}/action/{goal_id}/feedback` `{progress, current_wp, state}`
  - result: `{realm}/arm/{rid}/action/{goal_id}/result` `{ok, error?}` (also queryable for late joiners)
- `{realm}/arm/{rid}/action/cancel` `{goal_id}`

**Jogging & the watchdog:** jog is the one place a web UI can hurt someone. The UI publishes `cmd/jog` setpoints at 10–20 Hz *only while the button is held*; the driver applies a 250 ms watchdog and issues a stop if the stream dies (tab closed, Wi-Fi drop). Additionally a single **control lease** queryable (`{realm}/arm/{rid}/cmd/acquire_control`) ensures only one client commands motion at a time. The lease carries an **identity** (`{client_id, user, granted_at, expires_at}`) from day one — full role-based permissions (view / jog / edit frames / run programs / calibrate / admin) come later (§8.4 fleet phase), but retrofitting identity into a lease that never had it is the expensive version. Lease state is published (`state/control_owner`) so every UI shows who is in control.

### 4.3 Cameras & vision

| Key | Kind | Payload |
|---|---|---|
| `{realm}/camera2d/{cid}/image` | pub | header in Zenoh attachment `{t_capture, frame_id, w, h, encoding, exposure, gain, seq}`, payload = raw or JPEG bytes |
| `{realm}/camera2d/{cid}/image/preview` | pub | downscaled JPEG ~15 Hz for the UI (saves the browser from 25 MB/s raw Bayer) |
| `{realm}/camera2d/{cid}/cmd/configure` | queryable | exposure, gain, trigger mode, ROI (GenICam node writes via Harvester) |
| `{realm}/camera2d/{cid}/cmd/grab` | queryable | software-triggered single frame, replies with the frame (for calibration & vision-on-demand) |
| `{realm}/vision/{pipeline}/result` | pub | detections/poses `{t_capture, frame_id, items[], debug_overlays[]}` |
| `{realm}/frames/{name}` | pub | dynamically located frames `{t, parent, pose, source, confidence}` — see §4.5 |
| `{realm}/vision/{pipeline}/overlay` | pub | rerun-style primitives (2D boxes/points on image, 3D points/meshes in a named frame) the UI renders generically |

Overlays as *data, not pixels* is the rerun trick worth copying: a vision node publishes `{space: "camera/cam0/image", primitives: [{type:"rect",...},{type:"text",...}]}` or `{space:"3d", frame:"base", primitives:[{type:"points3d",...}]}` and the UI has one generic renderer for both panes. New pipelines get visualization for free, and overlays replay perfectly.

### 4.4 Configuration store (persistent, realm-less)

Config is shared by all realms — the sim robot uses the same TCPs and camera calibrations as the live one. Backed by the Zenoh storage plugin (filesystem/RocksDB backend) so plain `get`/`put` works:

- `config/frames/{name}` → `{parent, pose, source, meta}` — static frames (CAD import, touch-off, calibration); see §4.5
- `config/arm/{rid}/tcp/{name}` → `{xyz, quat, role: tool|sensor|virtual, selectable_as_tcp, mass?, cog?}` — TCPs; each is also a frame parented to the flange (§4.5). **The hand-eye result is written here**, e.g. `config/arm/r1/tcp/cam0_optical`
- `config/arm/{rid}/urdf` → URDF + mesh references (UI and sim both load this)
- `config/camera2d/{cid}/intrinsics` → `{model: "opencv_pinhole", K, dist, w, h, rms}`
- `config/camera2d/{cid}/mount` → `{type: "flange"|"world", parent_frame, pose}` (for fixed cameras, `world` + pose from base-eye calibration)
- `config/programs/{name}` → saved waypoint programs (what the pendant edits)
- `config/scene/{name}` → collision/visual objects `{frame, pose, geometry}` for sim & 3D view — parented to `world` or any frame (§4.5); the collision spine (§5.10) consumes the same geometry

### 4.5 Frames as first-class citizens

Frames get the same treatment as devices: named, addressable, recorded, with provenance. There is one **frame tree** rooted at `world`; every frame has `{parent, pose, source}`. Three kinds, distinguished only by where their pose comes from:

| Kind | Lives at | Updated by | Examples |
|---|---|---|---|
| **Static** | `config/frames/{name}` → `{parent, pose, source: cad\|manual\|calib, meta}` | CAD import, touch-off teach, calibration | fixture corners, pallet origin from CAD, fixed-camera mount |
| **Dynamic** | `{realm}/frames/{name}` (pub, latest-wins) → `{t, parent, pose, source: "vision/{pipeline}", confidence}` | vision pipelines, trackers | located pallet, part pose on a table, conveyor-tracked object (later) |
| **Kinematic** | derived, already streaming | arm HAL + URDF + TCP store | `arm/r1/base`, `arm/r1/flange`, `arm/r1/tcp/{name}`, `camera2d/cam0/optical` |

**TCPs are unified into this model — with roles.** A TCP is a frame parented to `arm/{rid}/flange` that additionally carries tool payload data (mass, CoG). But not every flange-mounted frame should be an operator-selectable motion TCP: every such frame carries `role: tool | sensor | virtual` and `selectable_as_tcp: bool`. The camera optical frame is `role: sensor, selectable_as_tcp: true` — fully resolvable in the frame tree, selectable as TCP *deliberately* (calibration, debug), but filtered out of the default TCP picker so an operator can't accidentally run production paths with `cam0_optical` active. Storage stays unified; the UI and command layer filter by role.

**The resolver is a core subsystem, not a helper.** Nearly everything consumes it — UI, moves, camera projection, vision, sim camera, replay, calibration, collision objects — so it gets industrial semantics from the start: `resolve(target, source, t) → pose` with **no cycles** (parent writes validated against the tree), **explicit parent ownership** (one writer per frame; a vision pipeline owns the frames it publishes), **TTL on dynamic frames** (a stale `pallet_1` raises `FrameStale`, never silently returns the old pose — staleness threshold and minimum confidence are per-consumer parameters), and **structured errors** (`FrameUnknown | FrameStale | FrameLowConfidence | NoPathToRoot`, each naming the offending frame). It is **time-aware**: kinematic and dynamic frames keep a short ring buffer (a few seconds) so lookups at a *past* timestamp interpolate correctly — exactly what eye-in-hand vision needs: an image captured at `t_capture` must be combined with the flange pose *at `t_capture`*, not "now". The replayer fills the same buffers, so resolution is deterministic when scrubbing. The same logic is implemented once in TypeScript for the UI, against the same conformance vectors.

**Naming rules (cheap now, painful later):** static and taught frames use flat reserved names (`pallet_1`, `fixture_a`); vision-published frames live under `frames/detections/{pipeline}/{object_id}` unless they *update* a declared logical frame, which is an explicit pipeline output binding ("this detection updates `pallet_1`"). Cross-cell collisions are a non-issue by deployment choice: **one Zenoh router per cell**; fleets don't share a bus.

**Everything references frames.** Any pose payload on the bus is `{frame, xyz, quat}` — already the convention, now load-bearing:

- **Scene/collision objects:** `config/scene/{name}` gains a `frame` field. An object parented to `world` is fixed; parented to a dynamic frame (`frames/pallet_1`) it moves when vision relocates the pallet — automatically, in the 3D view, the sim, the rendered sim-camera, and collision checking (§5.10), because all of them go through the resolver.
- **Robot moves:** `execute_path` waypoint targets are `{frame, pose}`. Default binding is **at goal acceptance**: the driver resolves every target into base coordinates once, when the goal is accepted, and emits a formal **execution snapshot** (published + recorded, returned in the result): program name/revision, operator identity from the control lease, input frames *with revisions/timestamps*, resolved waypoints in base, active TCP, speed scale, software versions. "Why did the robot move there?" is then a lookup, not an investigation. A `tracking: true` flag is reserved in the schema for genuinely moving frames (conveyor following) but is explicitly out of scope until needed.
- **Vision results:** a pipeline output is a pose in `camera2d/{cid}/optical` at `t_capture`; the pipeline (via the resolver) can *publish a frame* from it — e.g. detect a fiducial → `{realm}/frames/pallet_1` parented to `world`. Locating a reference frame dynamically is thus an ordinary pipeline output, and "move relative to what the camera just found" is an ordinary `{frame: "pallet_1"}` waypoint.

**Provenance & trust.** Every frame write records `source`, timestamp, and quality (calibration residual, detection confidence). Dynamic frames are recorded like all bus traffic, so a replay shows *why* the robot went where it went — the frame tree state at every instant is part of the log. Static frames in config keep a revision history (the storage keeps prior values; a `calib` or touch-off overwrite never silently destroys the old value).

**Getting frames in:**
- **CAD import:** a small importer maps a CAD export (frame names + transforms, e.g. from a STEP-derived JSON/CSV convention agreed with the CAD side) into `config/frames/**` and meshes into `config/scene/**` referenced to those frames.
- **Touch-off teach:** classic pendant 3-point method (origin, +X, +XY point) using the active TCP — implemented as a calibration-service action, surfaced in the UI frame manager.
- **Calibration & vision:** as above.

### 4.6 Cell event log

Telemetry tells you *what the numbers were*; events tell you *what happened*. A first-class, human-readable stream:

`{realm}/events` → `{t, severity, source, kind, message, data}` — kinds include: control acquired/released (with identity), program started/finished/aborted (with execution-snapshot id), frame updated (by whom: vision/touch-off/calibration, old→new delta), calibration written, protective stop / e-stop, driver reconnect, speed-scale change, recording marker, version change.

Events are ordinary bus traffic — recorded into MCAP like everything else — but the UI timeline renders them as markers, the incident-review workflow starts from them, and they are what a future fleet dashboard aggregates. Every service gets an `emit_event()` one-liner in `core` so emitting them is never friction.

---

## 5. Services

All Python services build on `core` (L0) and the relevant `contracts/*` packages (L1). The two hardware services below are L2 HALs: `aubo_driver` ⇒ `hal/aubo_i10` implementing `arm`, `camera_driver` ⇒ `hal/genicam` implementing `camera2d`. Everything else (calibration, recorder, replayer, vision, task_runner, supervisor) is contract-generic.

### 5.1 `aubo_driver` (live realm)

- **Connection A — command socket:** wraps your existing CLI logic as a library. Single worker thread consumes an internal queue fed by the queryables/actions, so commands to the controller are strictly serialized. Path execution streams waypoints to the controller (Aubo SDK `movej`/`movel`/trajectory interface) and emits action feedback by watching motion state.
- **Connection B — state socket:** dedicated thread, tight loop: read → decode → `publish()`. Target the SDK's max report rate; measure and publish the achieved rate in `state/status` so degradation is visible.
- Owns the jog watchdog and the control lease.
- Crash-only design: on reconnect it re-declares everything; subscribers notice via `status` liveliness (Zenoh liveliness tokens on `{realm}/arm/{rid}/alive`).

### 5.2 `camera_driver` (one process per camera)

- Harvester → `ImageAcquirer`, free-run or triggered per config.
- Publishes full-res frames (raw or lossless) + the downscaled preview stream.
- `cmd/grab` switches to software trigger, grabs, replies — used by the calibration wizard so robot pose and frame capture are synchronized deliberately rather than by luck.
- Stamps frames with the camera's hardware timestamp when available, mapped to host time (record the offset; GigE timestamps drift).
- Config-file driven (`cameras.yaml`: serial → `cid`, mount type, pixel format), so adding camera #2 is a config entry, not code.

### 5.3 `sim_robot` (sim realm — the digital twin core)

- Loads the same URDF; integrates joint-space trajectories with the same motion profile semantics (trapezoidal/scurve approximations of movej/movel, blend radii) so timing is representative, not just poses.
- Serves the **identical** queryables/actions; publishes identical state keys at the same rates. The test for done: point the UI at `sim/**` and the pendant is fully functional.
- Two clocks: real-time mode (twin), and as-fast-as-possible / stepped mode (headless CI tests of the task layer).
- Optional *mirror mode*: subscribes to `live/robot/r1/state/joints` and shadows it — this is the "digital twin next to the real robot" view, and it is also exactly what replay drives.

### 5.4 `sim_camera`

- Offscreen renderer (**pyrender**) of the scene graph (URDF pose from `sim_robot` + `config/scene/**` — the same glTF asset the browser viewer loads, §5.10), using the **calibrated intrinsics** from config and the camera TCP for the eye-in-hand pose. `pyrender`'s `IntrinsicsCamera` takes `fx, fy, cx, cy` directly, so the calibrated **K** drops in unchanged, and one `render()` returns **color + depth + segmentation** in a single call — covering the 2D camera, a depth/3D camera, and ground-truth masks for vision testing. Headless via **EGL** (GPU) or **OSMesa** (pure CPU). Lens distortion (the one gap) is a post-process warp using the calibrated `dist` coefficients. Publishes the same image keys.
- This closes the loop for testing vision: rendered ChArUco/objects → real pipeline code → overlays in the UI.

### 5.5 `calibration` service

- **Intrinsics action** `{realm}/calib/action/intrinsics`: wizard captures N `cmd/grab` frames of a ChArUco board, runs `cv2.calibrateCamera`, writes `config/camera2d/{cid}/intrinsics`, returns RMS + per-view errors (UI shows coverage heatmap).
- **Hand-eye action** `{realm}/calib/action/hand_eye`: drives (or guides the user to jog) the robot through 15–30 diverse poses; per pose stores flange pose (from `state/flange`, settled) + board detection; runs `cv2.calibrateHandEye` (Park/Daniilidis) → `X_flange_camera`; writes **both** `config/camera2d/{cid}/mount` and `config/arm/{rid}/tcp/{cid}_optical`; reports translation/rotation residuals.
- Fixed-camera variant uses `cv2.calibrateRobotWorldHandEye` → writes a `world` mount instead of a TCP.
- Because grabs and poses go through the bus, a calibration run is itself recorded and re-runnable from MCAP — improve the detector later, recompute the calibration from the same recording.

### 5.6 `recorder`

- **It is a Zenoh sink.** It subscribes `{realm}/**` (configurable realm + filters) and persists; its counterpart, the replayer, is a Zenoh source. Both are plain bus citizens — nothing else in the system knows or cares that they exist. The only design choice is the on-disk format *behind* the sink, hidden behind a `LogSink`/`LogSource` interface so it stays swappable.
- **Default backend: MCAP** — one channel per Zenoh key, schemas registered from the `contracts/*` types, Zenoh attachments preserved, HLC + capture timestamps stored. MCAP is chosen because scrubbing and reprocessing need an *indexed, seekable, self-describing* log: chunk index for random seek, embedded schemas, native handling of multi-MB image blobs, and ready-made tooling (Python reader, `mcap` CLI, Foxglove for ad-hoc inspection).
- The alternative "pure Zenoh" sink — the storage-manager plugin with a time-series backend (e.g. InfluxDB) — is the right tool for *latest-value config* (we use it there), but time-series databases handle large binary frames poorly and offer no media-style seek index; we would end up reimplementing MCAP's features on top. If aligned-state queries over history ever become valuable, such a storage can run *in addition* to the recorder; the bus-centric design doesn't preclude it.
- Chunked + indexed → random seek is cheap; rotation by size/time; a `recording/cmd/start|stop|mark` queryable lets the UI and the task layer drop markers ("pick #42 failed") into the log.

### 5.7 `replayer`

- Opens an MCAP (via `LogSource`), republishes onto `replay/{session}/**` (key rewritten from the recorded realm), honoring inter-message timing — i.e. the bus sees it "as if it is happening in real time".
- **Realm caution:** republishing onto the *original* `live/**` keys would make recorded data indistinguishable from reality (provenance loss, and recorded *commands* could reach real drivers). Default is always the rewritten replay realm; an explicit `--impersonate` flag may republish onto original keys for hardware-in-the-loop tricks, and is refused whenever a live driver holds the liveliness token for that resource.
- Control queryables: `replay/{session}/cmd/{play,pause,seek,rate}`; publishes `replay/{session}/clock` `{t_data, rate, playing}`.
- Scrubbing = seek to nearest chunk + fast-forward decode to t, republishing only *latest state per key* (joints, IO, last image) so the twin and UI snap to that instant.
- Vision regression mode: replay only `camera/**` keys into a realm where the *current* vision pipeline is live-subscribed → new results computed from old pixels, compared against recorded `vision/**` channels.

### 5.8 `task_runner` (later, but the seams exist now)

- **Recommendation: behavior tree first** (`py_trees`), with leaves that are thin wrappers over bus actions (`ExecutePath`, `SetDO`, `Grab`, `RunPipeline`, `WaitForInput`). Reusable subtrees are packaged as **skills** (§8.2): role-parameterized, contract-typed, hardware-blind. BTs compose retries/fallbacks/timeouts naturally for pick-and-place style flows; a state machine (`python-statecharts`/`transitions`) remains a fine alternative for strictly modal processes — because leaves only touch the bus, the choice is swappable.
- Publishes `{realm}/task/state` (tree snapshot: node states) → UI renders the live tree; recorded like everything else, so a failure can be scrubbed with the BT state visible at each timestep.
- Runs unchanged against `sim/**` for CI.

### 5.9 Web bridge

- Zenoh's **remote-api plugin** on the router + **zenoh-ts** in the browser (WebSocket). The UI is then a real bus citizen: subscribes to state, declares the jog publisher, calls queryables. No bespoke REST layer to keep in sync.
- Fallback if zenoh-ts is ever limiting: a thin FastAPI/WebSocket gateway process — but try the native route first.

### 5.10 `world_model` (geometry & collision spine)

**One scene graph, many solvers.** Wanting "one unified engine" is right at the level of the *scene description* and wrong at the level of the *solver*: forcing collision, planning and rendering through a single heavyweight simulator inherits its hardware demands and its opinions everywhere. Every mature stack (Drake, MoveIt, Isaac) instead keeps one authoritative scene graph consumed by separate, purpose-built engines for geometry, rendering and physics. We already have that scene graph — the frame tree (§4.5) plus the config store (`config/arm/{rid}/urdf`, `config/scene/**`, §4.4). So `world_model` is a small `core`-adjacent package that owns **kinematics + geometry + frames** and hands thin slices to each solver — never a monolith the rest of the system routes through.

**One definition of "are we in collision."** `world_model` exposes exactly four primitives, shared identically across `live`, `sim` and `replay`:
- `fk(q)` → link poses
- `check_collision(q, scene)` → `{hit, pairs}` (self + world)
- `min_distance(q, scene)` → `{d, witness_points, pair}` — *how close did we get*, with configurable safety margins, not just yes/no
- `preflight(trajectory, scene)` → `{ok, first_violation}` — dense collision-check of a path

These are called by `sim_robot`, the `execute_path` **acceptance preflight** (a path that self-collides or hits a scene object is `rejected` with a machine-readable reason, alongside *unresolvable frame* — §4.2 / Appendix A), the planner (§5.11), and the UI clearance readout (§7.1). The system gets a single collision authority, not one re-derived per consumer.

**Collision engine: Pinocchio + Coal** (Coal is the 2024 renamed/rewritten HPP-FCL). Self-collision, world-collision, preflight and planning all reduce to one primitive — distance/penetration between posed geometries — and Coal returns it with witness points and safety margins. It is **CPU, pip/conda, no GPU**, so it runs identically on the robot PC, in CI and on a laptop (which the roadmap requires), and it loads the same URDF the HAL and UI already use. Scene objects come from `config/scene/**` posed through the resolver, so collision geometry tracks dynamic frames (a vision-relocated pallet) for free.

**Share the asset, not the renderer.** The browser twin viewer (r3f + `urdf-loader`, §7.1) is the right tool for *visualization* and nothing else: browser WebGL geometry drifts from the real collision meshes and must never be the collision source of truth or the sim camera. "Same scene at both ends" means authoring geometry once and exporting **glTF/GLB**, which `pyrender` (Python, §5.4) and Three.js (browser) load from opposite ends of the bus — one scene graph, two consumers, no second renderer in the safety-adjacent path.

**Escalation behind the contracts — opt-in, never a rewrite.** Depth cameras and basic LiDAR are raycasts against the same Coal geometry — no new engine. Photoreal rendering becomes an Isaac Sim or Genesis `camera2d` HAL swap. Rigid-body contact physics (the one thing CPU libraries do poorly) becomes a MuJoCo or Newton HAL when bin-picking contact actually demands it. Each is an additional HAL behind an existing contract, chosen per cell — not a change to `world_model` or the spine.

### 5.11 `planner` (later; the seam exists now)

Path planning is a bus action whose output is an ordinary `execute_path` goal, so the planner is swappable like every other engine. **Now: OMPL / a Coal-gradient optimizer on CPU** — for known-scene pick-and-place, sampling/optimization is plenty, and preflighting a generated path is just dense `world_model` collision-checking through the same Coal queries. **Later: cuRobo** (NVIDIA, Apache-2.0, ~60× faster, GPU) slots in behind the same planner action when CPU planning is outgrown — it carries CUDA/PyTorch/GPU weight and a separate commercial licensing path for the cuMotion plugin, so it stays an opt-in cell choice, not a baseline dependency.

---

## 6. Data model & encoding

- **Encoding:** CBOR for everything structured (fast, schemaless-friendly, binary-safe); images as raw payload + CBOR attachment header. Schemas defined once per device class in `contracts/*` as Python dataclasses with generated TypeScript types (e.g. via a small JSON-schema export) so UI and services cannot drift.
- **Poses:** position meters, orientation **unit quaternion (x,y,z,w)** everywhere on the bus; convert to/from Aubo's axis-angle/rpy only inside `aubo_driver`. Every pose carries `frame`.
- **Time:** a contract-level timestamp policy, future-proofed now, filled simply at first. Every message carries `t_capture` (best estimate of physical acquisition — for images the *exposure midpoint*, not receive time), and where relevant `t_observed` (host receive/decode) and `t_published`, plus `clock_domain: host | camera_hw | robot_controller | replay` and an optional sync-quality estimate. Phase 1 sets them all from host time — fine, because calibration and vision grabs happen with the robot *settled*. The fields exist so that moving-capture or conveyor work later is a clock-sync project, not a schema migration. (Robot pose changes meaningfully over the 20–50 ms a naive timestamp can be off by.) Nanoseconds; Zenoh HLC additionally orders the bus; replay consumers prefer payload time.
- **IDs:** `goal_id` = UUIDv7 (time-ordered, nice in logs).

## 7. UI design (React + react-three-fiber)

Single-page app, panel layout (dockable, e.g. `react-mosaic`/`dockview`):

1. **3D viewport (R3F):** URDF via `urdf-loader`, driven by `state/joints`; TCP triads; camera frustums from intrinsics + mount; trajectory preview (ghost path before `execute_path` is sent — preview computed by `sim_robot` via a `plan_preview` queryable); twin mode renders live robot solid + replay/sim robot ghosted; generic 3D overlay renderer for `vision/*/overlay`. A **clearance readout** from `world_model.min_distance` (§5.10) flags near-collisions live; viewport geometry loads from the shared **glTF** asset (same as the sim camera), never the viewer's own collision truth.
2. **Jog panel:** joint ± and cartesian XYZ/RPY jog in base/tool frame, speed scale, hold-to-jog publishing the watchdogged setpoint stream; keyboard bindings.
3. **Program editor (teach):** waypoint list with movej/movel/movec, blend radius, per-move speed; "touch up" button captures current pose; save/load via `config/programs/**`; run/step/stop through `execute_path` with live feedback highlighting the active waypoint.
4. **IO panel:** DI as lamps, DO as toggles (→ `cmd/set_do`), analog gauges.
5. **Status/safety strip:** mode, e-stop, protective stop, speed scale, control-lease owner, driver liveliness.
6. **Camera panes:** preview streams, exposure/gain controls, 2D overlay renderer, click-to-grab full-res.
7. **Frame manager:** tree view of the frame hierarchy with provenance badges (CAD / taught / calibrated / vision-live) and confidence; triad visibility toggles for the 3D view; create/edit static frames numerically, by 3-point touch-off, or import from CAD; attach scene objects to frames; waypoint and program editors pick target frames from here.
8. **Calibration wizard:** guided intrinsics (coverage heatmap) and hand-eye (pose checklist, residuals) flows driving the calibration actions.
9. **Timeline (replay):** scrubber bound to `replay/.../clock` + seek/rate controls, markers from the recorder, channel toggles; identical panels work because replay uses the same keys — including the frame tree state at the scrubbed instant.
10. **Realm switcher:** top-level selector `live / sim / replay`, which simply changes the key prefix the whole app subscribes under — this single design decision is what makes the rest cheap.
11. **Task view (later):** live behavior-tree graph from `task/state`.

## 8. Code topology — universal vs. specific, scaling to 20+ deployments

### 8.1 Four tiers, one dependency direction

| Tier | Contains | Changes when… | Lives in |
|---|---|---|---|
| **Platform** (L0–L2 + services + UI shell) | `core`, `contracts/*`, `hal/*`, generic services (supervisor, calibration, recorder, replayer, vision runtime), web shell + contract panel plugins | engineering improves the product | `platform` repo; semver releases (wheels + Docker images) |
| **Skills** (L3 — part of the platform) | reusable, role-parameterized flow building blocks: BT subtrees like `locate_with_camera`, `vision_guided_pick`, `palletize_pattern`, `touch_off_frame` | a new *generic* capability matures | `platform/packages/skills/*` |
| **Cell types** (solutions) | the blueprint of a deployable cell archetype: required roles, scene template, composed flows, calibration procedure, UI layout preset | a new kind of cell is productized, or a blueprint improves | `fleet/cell-types/*` |
| **Deployments** (instances) | `cell.yaml` role bindings (serials, IPs, mounts), site frames from CAD, flow parameter values, platform version pin, state snapshots | a site is installed, tuned, or upgraded | `fleet/deployments/{site}/` |

**Dependency rule — down only:** a deployment references one cell type + a pinned platform version; cell types depend on skills + contracts; skills depend on **contracts only** — never on HALs, never on instance ids. Anything that violates this rule is, by definition, in the wrong tier.

### 8.2 Role binding — the mechanism that makes flows reusable

Flows and skills never name hardware; they declare **roles** typed by contract:

```yaml
# skills/vision_guided_pick/skill.yaml
requires:
  arm:     {contract: arm}
  cam:     {contract: camera2d, mount: flange}
  gripper: {contract: dio, signals: [grip, part_present]}
frames:    [pick_area]                  # logical frame names, bound per deployment
params:    {approach_height: 0.08, retreat_height: 0.12, max_locate_residual: 0.5}
```

The cell type composes skills into flows and forwards the role declarations; the deployment's `cell.yaml` binds roles → resource instances and logical frames → site frames:

```yaml
# fleet/deployments/venlo-line2/cell.yaml
cell_type: vision-pick-cell@1.4
platform: 2.7.1
resources:
  r1:   {contract: arm,      hal: aubo_i10,  params: {ip: 10.0.0.2}}
  cam0: {contract: camera2d, hal: genicam,   params: {serial: "GV12345", mount: flange}}
  io1:  {contract: dio,      hal: modbus_io, params: {ip: 10.0.0.5}}
bindings:
  vision_guided_pick: {arm: r1, cam: cam0, gripper: io1, frames: {pick_area: pallet_1}}
```

This is dependency injection over the bus: contracts are the interfaces, roles are the constructor arguments, `cell.yaml` is the container configuration. The same skill runs on a different cell type with different HALs, untouched — which is exactly the reuse-across-cell-types requirement.

### 8.3 Declarative config vs. operational state

"Cell-specific" splits into two things with different lifecycles:

- **Declarative config (in git, in the deployment dir):** `cell.yaml`, CAD-derived frames, scene, flow selection + parameters, version pins. Reviewed, diffed, reproducible.
- **Operational state (born on the cell):** calibrations, touched-off frames, programs taught at the pendant, tuned camera exposure. Source of truth is the cell's config storage — but a `snapshot` command exports it as a commit back into the deployment dir.

**The fleet invariant:** any cell must be rebuildable from *(platform images @ pin) + (deployment dir) + (latest state snapshot)*. If a cell dies, restoring it is a checkout, not an archaeology project.

### 8.4 Versioning & fleet upgrades

- **Contracts are semver'd.** Additive schema fields = minor; breaking changes = major, and the conformance suites double as compatibility tests. Old MCAP recordings remain readable because schemas are embedded in the files (§5.6).
- **Upgrading a site = bumping a pin**, gated by: (1) CI boots that cell type in the sim realm and runs its flow tests; (2) **replay regression** — the site's recorded MCAPs are run through the new vision pipelines / resolver / flows and results diffed against the recorded ones — the recording infrastructure *is* the fleet upgrade harness; (3) staged rollout: digital twin first, then live, with the recorder dropping a version marker.
- **CI scales by cell type, not by site:** 20 deployments of 3 cell types = 3 sim matrices, not 20.

### 8.5 The promotion path (how the tiers stay healthy)

One-off needs are allowed to land in a deployment dir as a custom flow — that escape hatch keeps installs unblocked. The discipline is in the graduation: needed by a second site → promote into the cell type; needed by a second cell type → generalize into the skills library. Code moves *up*; deployment dirs stay thin. Review heuristic: **a deployment dir that contains substantial Python a month after install is a smell** — it means a skill or cell-type feature is hiding in the wrong tier.

### 8.6 Repository layout

Start with **two repos** — splitting further later is cheap precisely because the tier boundaries already exist in the directory structure:

```
platform/                            # the product — semver released
├─ packages/
│  ├─ core/                          # L0 (ex-cobotlib)
│  ├─ contracts/{arm,camera2d,dio}/  # L1: schemas + keyspace + conformance tests
│  ├─ hal/{aubo_i10,genicam,modbus_io,arm_sim,camera2d_sim}/   # L2
│  ├─ services/{supervisor,calibration,recorder,replayer,vision,task_runner}/
│  └─ skills/{locate_with_camera,vision_guided_pick,...}/      # L3
├─ web/                              # shell + panel plugins keyed by contract
├─ schemas/                          # py + ts codegen from contracts
└─ deploy/                           # base compose profiles: live / sim / replay

fleet/                               # everything deployment-shaped
├─ cell-types/
│  └─ vision-pick-cell/              # roles, scene template, flows, UI preset, calib procedure
└─ deployments/
   └─ venlo-line2/
      ├─ cell.yaml                   # bindings (above)
      ├─ frames/                     # CAD-imported site frames
      ├─ params/                     # flow parameter values
      └─ snapshots/                  # exported operational state (§8.3)
```

Split per-customer deployment repos out of `fleet` only when IP or access isolation demands it. Cell types move to their own repo when a separate solutions team owns them — the dependency rule doesn't change either way.

`docker compose --profile sim up` against any deployment dir gives that exact cell, virtually, on a laptop — including its frames, scene and flows. That is also the support story at 20+ sites: reproduce a customer's cell in sim from their deployment dir plus a recording of the incident.

## 9. Risks & decisions to validate early

| Risk | Mitigation / spike |
|---|---|
| Aubo state rate & jitter over the SDK socket | Week-1 spike: measure achievable Hz and latency, publish metrics in `status` |
| Raw GigE bandwidth through Zenoh + browser | Preview stream pattern (above); keep raw frames on the wired segment; test 1 camera @ full rate through recorder |
| **Browser-as-bus-citizen (zenoh-ts)** — the biggest early unknown. Not pub/sub, but the full set: queryables from the browser, binary image payloads, attachments, reconnect behavior, backpressure, liveliness/lease visibility, debugging ergonomics | **Dedicated spike with a pass/fail checklist** (subscribe state @ full UI rate, call set_do, hold-to-jog with watchdog, camera preview stream, grab, show liveliness + control owner). Hard decision gate in week 4 (roadmap): if painful, insert a thin typed gateway *then*, while the UI is small. The gateway, if needed, only translates WS↔Zenoh — business logic in a gateway is forbidden |
| Hand-eye accuracy | Validate with a touch-point test (camera-located target → TCP touch) before trusting vision-guided motion |
| Sim/real motion-timing mismatch | Acceptable early; record both realms and diff joint traces to tune sim profiles |
| Jog safety from a browser | Watchdog + control lease + speed-scale clamp from day one, never "later" |
| Framework-heaviness before the first automation problem is solved | **Two-implementations rule:** every abstraction must be proven by two implementations, or one implementation + sim/replay (arm: Aubo + arm_sim; camera2d: GenICam + replay; frames: live calibration + replay). An abstraction with one real user stays simple |
| Monolithic-sim-engine creep — routing collision + planning + rendering through one heavyweight simulator | **Scene-graph spine + purpose-built solvers:** `world_model` owns frames + geometry + kinematics; Coal (collision), pyrender (render) and OMPL/cuRobo (planning) are thin adapters behind it, all CPU/pip by default. Heavyweight engines (Isaac, MuJoCo, Genesis) enter only as opt-in HALs behind existing contracts (§5.10) |

## 10. Phased roadmap

**First six weeks — one vertical slice, not the platform.** The spine to prove with live hardware before investing in the full structure is: *Aubo state → Zenoh → recorder → UI, and the same UI fed from replay.* Contract schemas are written by hand (no codegen yet); the conformance suite exists from week 1 but only as a skeleton that grows with the driver — generic machinery waits until the slice works.

1. **Weeks 1–2 — bus + Aubo:** router config, `core` session bootstrap, hand-written `arm` messages, state publisher, `set_do` queryable, minimal `execute_path` (movej) action with lifecycle per Appendix A, CLI test client. *Exit: pose stream in `z_sub`; a move runs and produces a correct goal lifecycle.*
2. **Week 3 — recorder/replayer:** record `live/arm/r1/**` to MCAP; replay into `replay/test/**`; script verifies replayed state matches recorded byte-for-byte. *Exit: the realm idea is proven.*
3. **Week 4 — UI skeleton + the zenoh-ts decision gate:** R3F viewport from joint state, status strip, DO toggle, realm switcher (live/replay). Run the browser spike checklist (§9); **decide native zenoh-ts vs. thin gateway now**, while the UI is one panel.
4. **Week 5 — camera:** `hal/genicam`, preview stream, grab queryable, UI camera pane; camera keys join the recording.
5. **Week 6 — frames v0:** static frames + TCP frames + basic resolver; execute one frame-referenced waypoint resolved at goal acceptance; store the execution snapshot; replay it. *Exit: the architecture's spine is proven end-to-end.*

**Then the platform phases:**

6. **Sim realm:** `arm_sim` + mirror mode → full pendant against the twin; conformance suite now runs against two `arm` implementations (the two-implementations rule paying out).
7. **Calibration:** intrinsics + hand-eye wizards; camera sensor-frame/TCP in store; frustum correct in 3D view.
8. **Jog + teach + frames v1:** watchdogged jog, identity-bearing lease surfaced in UI, program editor with frame-referenced waypoints, frame manager panel (roles, provenance), 3-point touch-off, CAD frame import, time-aware resolver buffers, dynamic-frame TTL; `world_model` (Pinocchio + Coal) with collision preflight gating `execute_path` acceptance and a UI clearance readout.
9. **Vision + sim_camera:** overlay protocol, first pipeline, pipelines publishing dynamic frames, replay-regression workflow.
10. **Task layer:** py_trees runner, leaves over bus actions, first skill (`vision_guided_pick`) with role binding, BT view in UI.
11. **Fleet-readiness pass (before deployment #2):** split `fleet` repo, first cell-type package, state-snapshot command, replay-regression job in CI, platform release pipeline (wheels + images, semver'd contracts), role-based permissions on the lease.

---

### Appendix A — Action pattern over Zenoh (concrete)

**Goal lifecycle (normative, identical for every contract):**
`accepted | rejected → running → canceling → canceled | succeeded | failed | aborted`

Rules every action server in `core` enforces (so HALs cannot diverge):
- **Acceptance is a gate:** a goal is `rejected` (with a machine-readable reason) if the caller doesn't hold the control lease (for motion), if a mutually exclusive goal is active, or if preconditions fail (e-stop, unresolvable frame). **At most one active motion goal per arm** — no implicit queueing; a queue, if ever wanted, is an explicit higher-level service.
- **Idempotency:** resubmitting an identical `goal_id` returns the existing goal's state/result, never starts a second execution.
- **Result retention:** results are cached and queryable for 60 s (configurable) after terminal state; after that, `unknown_goal`.
- **Cancel semantics map to physics:** for `arm`, cancel = controller category-2 stop, then `canceled`; `cmd/stop` and protective stops abort the goal → `aborted` with cause. The mapping is part of the contract, not driver discretion.
- **Driver restart:** on startup a driver publishes `aborted {cause: driver_restart}` for any goal it cannot account for. No goal ever ends in limbo.
- **QoS:** feedback is best-effort (a missed progress tick is harmless); *state transitions* are reliable — the result queryable is the source of truth, late joiners and flaky links reconcile through it.

The conformance suite tests this lifecycle against every implementation — it's the part of the contract most likely to drift otherwise.

**Wire flow:**

```
client                          server (driver)
  │ get  {realm}/.../action/execute_path  payload=goal
  │ ◄── reply {goal_id, accepted: true}
  │ subscribe .../action/{goal_id}/feedback
  │ ◄── {progress: 0.4, current_wp: 3, state: "moving"}   (pub)
  │ ◄── {progress: 1.0, state: "succeeded"}
  │ get  .../action/{goal_id}/result      (idempotent, cached 60 s)
  │ ◄── {ok: true}
cancel: get .../action/cancel {goal_id}
```

### Appendix B — Realms cheat-sheet

| Scenario | Robot keys | Camera keys | Notes |
|---|---|---|---|
| Production | `live/**` | `live/**` | recorder on |
| Pure simulation | `sim/**` | `sim/**` (rendered) | CI / development |
| Live + twin | `live/**` + `sim/**` (mirror) | `live/**` | side-by-side 3D compare |
| Replay scrub | `replay/{id}/**` | from MCAP | twin driven by recorded joints |
| Vision regression | — | `replay/{id}/camera/**` | live pipeline, recorded pixels |
