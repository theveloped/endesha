# RFC — Vision pipelines

Status: **draft for review** (2026-08-27). Branch: `program-graph`.
Builds on the program layer (`program-layer-rfc.md`: code-first statechart
programs, roles → devices, declarative triggers, cancel-on-exit actions), the
`camera2d` contract + `Camera2dCore` (one image topic, `FrameHeader`
attachment, stamped eye-in-hand pose), the action pattern (`wf.core.action`),
the recorder/replayer, and design v5 §4.3 / §4.5 / §5.5 (vision keys, dynamic
frames, calibration).

## 0. Decisions already taken (not up for discussion here)

- **The bus is the API.** A pipeline only speaks contract keys, so it runs
  unchanged against live, sim (browser/headless twin render) and replay
  cameras.
- **Code-first, graph derived.** Programs are Python; their graph is exported
  from the class and drawn read-only. Pipelines follow the same rule: a
  pipeline is a Python file, its node graph is data derived from the class,
  React Flow renders it, the code stays the only source of truth.
- **Frame convention** (`wf.contracts.camera2d.messages.FrameHeader`): image
  bytes as the zenoh payload, CBOR header as the attachment, on an
  `.../image` topic. *Derived frame producers preserve `t_capture`,
  `frame_id` and `pose`, assign their own `seq`, update `w`/`h`/`encoding`.*
  Origin is carried by the topic.
- **Design v5 §4.3 / §4.5**: `{realm}/vision/{pipeline}/result` and
  `/overlay` (overlays as *data, not pixels*; one generic renderer in the
  UI), dynamically located frames `{realm}/frames/{name}` with
  `source: vision/{pipeline}` and a TTL / confidence, detections under
  `frames/detections/{pipeline}/{object_id}` unless explicitly bound to a
  declared frame.
- **Realm-scoped = recorded.** Everything a pipeline publishes under the
  realm is captured by the recorder and comes back verbatim in
  `replay/{id}`. Config writes are realm-less and go through the config
  service with provenance.
- **Supervisor model**: one provider process per resource, `provides` for
  several contracts in one process, `launch: module | external`, crash-only
  restart, device inventory published for the UI and the program runner.

## 1. Goals / non-goals

Goals

1. One or more cameras per cell; each camera feeds any number of processing
   graphs; a graph's outputs are usable anywhere a program (or the UI, or
   another graph) needs them.
2. Cover the four shapes of vision work with **one** mechanism:
   (a) on-demand "find a pixel/pose, then move"; (b) continuous detection
   while a program state is active; (c) always-on watchers that fire program
   events (QR / barcode); (d) an algorithm over all frames between two
   instants that yields one result (measurement, calibration, reference
   frame).
3. **No computation without demand.** Expensive nodes only run while
   something — a program state, a goal, a viewer, another pipeline — asks
   for them, and camera bandwidth follows demand. Start/stop from the
   program is a special case of demand, not a separate mechanism.
4. Heavy work (OpenCV, later ML) is isolated from the program runner and
   from other pipelines: a slow or crashing detector never stalls the
   statechart or an always-on watcher.
5. Every result is time-correct: stamped with the capture instant, the frame
   sequence and the camera pose *at capture*; consumers can insist on
   freshness. Pipelines replay deterministically for regression.
6. Nodes are pure functions of frames + params → unit-testable with fixture
   images, runnable offline against an MCAP without a bus.

Non-goals (now)

- A drag-and-drop pipeline editor. The graph view is read-only (the same
  decision as for programs). A YAML "compose nodes from a library" mode is
  a possible later increment (§11).
- ML runtimes / GPU (the design leaves the seams: a node kind and
  `launch: external`; no code now).
- Zero-copy frame transport (zenoh SHM). Localhost JPEG / Mono8 at reduced
  scale is sufficient for the first cells (§5.4).
- 3D / depth cameras. `camera2d` only; the frame convention generalises.
- Conveyor tracking (`tracking: true` frames), multi-node distribution.

## 2. Concepts

### 2.1 Vocabulary

| term | meaning |
|---|---|
| **pipeline** | one Python class (`deploy/vision/<name>.py`), one process, one node graph, bound to camera roles at cell activation. Appears in the device inventory with contract `vision`. |
| **node** | a method `run_<node>` with declared inputs. Kinds by signature: `Frame -> Frame` (feed), `Frame -> Result`, `Result -> Result`, `Result -> FramePose` (frame binding), `list[Frame] -> Result` (window). |
| **source** | the root of a graph: a camera role plus the stream parameters this pipeline wants from it. |
| **demand** | a ref-counted, TTL'd request from a client (`client_id`) that a *node* be computed. Demand propagates upstream through inputs down to the source, and from the source to the camera stream. |
| **always** | a node flag: computed whenever the pipeline is up, without external demand (watchers). |
| **tap** | demand on a feed node from a viewer: the node additionally encodes + publishes its image on the bus. |
| **goal** | a one-shot or windowed computation run via the action pattern (`wf.core.action`): accept → (feedback) → result / cancel. |
| **lane** | implementation term: a worker thread with a 1-slot latest-wins mailbox. One per source by default; a node may ask for its own. |

### 2.2 In-process graph, bus at the edges

Nodes of one pipeline exchange decoded numpy arrays in memory. Only the graph's
edges touch the bus: sources subscribe to `{realm}/camera2d/{cid}/image` (or to
another pipeline's published feed); outputs are published only when declared
(`result=True`, `overlay=True`, `frame=...`) or demanded (a tap). Pushing every
intermediate feed through zenoh would cost a JPEG encode + CBOR + copy per node
per frame; tapping gives the "a feed at every layer" model without paying for
it continuously.

### 2.3 `Frame` (the SDK type)

A lazy view over one bus frame, shared by every node that reads it:

- `header: FrameHeader` — `t_capture`, `seq`, `frame_id`, `pose` (world←optical
  at capture, may be `None`), `w`, `h`, `encoding`, `clock_domain`; plus `cid`
  and the source topic.
- `.raw` (bytes as published), `.bgr`, `.gray` — decoded once, cached.
  `BayerRG8` is debayered with `cv2.COLOR_BayerRG2BGR` (the stack-wide
  convention in `camera2d_core.processing`).
- `.derive(array, encoding="Mono8"|"jpeg"|"BayerRG8")` → a new `Frame` that
  **keeps `t_capture`, `frame_id`, `pose`, `cid`** and gets its own `seq`
  from the pipeline's counter. The contract rule is enforced by the SDK, not
  by every author.
- `.intrinsics` — the `CameraInfo` for `cid` from `config/intrinsics/{cid}`
  (cached, refreshed on store change), scaled to this frame's `w`/`h` when
  the frame was resized. `.ray(u, v)` (pixel → unit ray in the optical
  frame, undistorted with `D`) and `.pose_at_capture()` are the two helpers
  eye-in-hand lifting needs.

### 2.4 Time and freshness

- Every `Result` carries `t_capture` and `frame_seq` of the frame it came
  from (a window carries the range and count). Results are latest-wins on the
  bus. A consumer that acts on a result must decide *how fresh* it must be:
  the program proxy takes `fresh_after=<ns>` (typically a timestamp taken
  after the arm settled); one-shot goals wait for a frame with
  `t_capture > t_accepted` before computing.
- Windows collect by `t_capture` range, never by wall clock, so they are
  identical under replay.
- Camera pose at capture comes from `FrameHeader.pose` (stamped by
  `Camera2dCore` from the flange stream) — pipelines never look the flange up
  "now".

## 3. The `vision` contract (`wf.contracts.vision`)

### 3.1 Keys

```
{realm}/vision/{pid}/state/status            pub 1 Hz + on change   PipelineStatus
{realm}/vision/{pid}/state/demand            pub latest-wins        DemandState
{realm}/vision/{pid}/{node}/image            pub DROP (only while tapped)   FrameHeader attachment + image bytes
{realm}/vision/{pid}/{node}/result           pub latest-wins + keepalive, queryable (last)   Result
{realm}/vision/{pid}/{node}/overlay          pub DROP               Overlay
{realm}/vision/{pid}/cmd/demand              queryable DemandRequest -> DemandAck
{realm}/vision/{pid}/cmd/release             queryable {client_id, nodes?} -> Ack
{realm}/vision/{pid}/cmd/params              queryable {params} -> Ack        (validated, live)
{realm}/vision/{pid}/cmd/close               queryable {goal_id} -> Ack       (end an open window, keep the result)
{realm}/vision/{pid}/action/{node}           goal submit (wf.core.action) — one ActionServer per goal node
{realm}/vision/{pid}/action/{goal_id}/feedback|result, {realm}/vision/{pid}/action/cancel
{realm}/vision/{pid}/alive                   liveliness token
{realm}/frames/{name}                        pub, when a node is bound to a frame (design §4.5)
```

`{pid}` is the pipeline id from `cell.yaml` (§6); `{node}` a node name. Keys
under `vision/{pid}/{node}/...` are recorded like every realm topic.

### 3.2 Messages

- `Result`: `{t, t_capture, t_capture_end?, frame_seq, frames?, seq, cid, frame_id,
  pose, ok, error, items: [Item], data: {}, compute_ms}`. `Item`:
  `{id?, label?, score?, bbox?: [x,y,w,h], points?: [[u,v],...], pose?:
  {frame, xyz, quat}, data: {}}`. `items` is the list-shaped part (detections,
  codes); `data` the scalar/structured part (a measured pose, a residual).
- `Overlay` (design §4.3): `{t_capture, seq, space: "camera2d/{cid}/image" |
  "vision/{pid}/{node}/image" | "3d", frame?: "world", primitives:
  [{type: rect|points|polyline|text|axes|mask_rle|points3d|frustum, ...}]}`.
  Rendered generically by the UI in the 2D and 3D panes.
- `PipelineStatus`: `{t, pipeline, ok, error, cameras: {role: cid}, params,
  nodes: {name: {active, always, demanded_by: [client_id], tapped, fps,
  dropped, latency_ms, error}}}`.
- `DemandRequest`: `{client_id, nodes: [name], ttl_s}` → `DemandAck`:
  `{ok, error, expires_at}`. `DemandState`: `{node: [{client_id, expires_at}]}`.
- Goal (`action/{node}`): `{mode: "once" | "n" | "duration" | "until_close",
  n?, duration_s?, fresh: true, params?: {}}` → result `Result`; feedback
  `{collected, of}`. `cancel` discards; `cmd/close` ends an `until_close`
  window and computes the result.
- `FramePose` (node → dynamic frame): `{name, parent, xyz, quat, confidence,
  ttl_s}`; published as `{realm}/frames/{name}` with `source: vision/{pid}/{node}`
  and `t = t_capture`.

### 3.3 Demand semantics

- Demand is per node and **ref-counted per `client_id`** with a TTL (default
  10 s; the runner and the UI renew at half the TTL — same shape as the
  control lease and the browser producer lease). An expired or released
  client drops out; a node runs while `always` or `demanded_by` is non-empty
  or any downstream node runs.
- Activation propagates upstream through a node's inputs to its source; a
  source with no active consumer asks the camera to stop. The pipeline
  computes the union of its active sources per `cid` (`max(rate_hz)`,
  `max(scale)`, raw if any needs raw, the union ROI) and issues one
  `stream_start` / `stream_stop` (see §5.3 for several pipelines on one
  camera).
- A **tap** is demand from a viewer on a feed node: the node additionally
  encodes (JPEG, preview scale by default) and publishes `.../{node}/image`.
  Result and overlay publishing is always on while the node is active — it
  is cheap.

### 3.4 Goals

- A node declared `action=True` gets an `ActionServer` (`wf.core.action`)
  under `action/{node}`; the server's "one active goal" rule applies per
  node, so two windows on different nodes do not block each other.
- `once`: enable the node's upstream, wait for the first frame with
  `t_capture > t_accepted` (`fresh: true`, the default), compute, reply,
  release. `n` / `duration` / `until_close`: collect frames by `t_capture`,
  feed the window function once, reply. Cancel releases upstream demand and
  discards; the program proxy registers cancel on the running action's
  `ActionContext`, so leaving the state cancels the goal exactly like an arm
  move.
- Results of goals are also published on `{node}/result` (so they are
  recorded and shown on the Vision page) and duplicated in the action result
  so the synchronous caller never races a subscription — the same shape as
  `GrabReply`.

### 3.5 Frames and config outputs

- A node with `frame="pallet_1"` (or `frame=True` for
  `frames/detections/{pid}/{item.id}`) publishes a dynamic frame per result.
  Ownership: one writer per frame name (design §4.5); the vision service
  rejects a pipeline whose frame name is claimed by another pipeline in the
  same cell at activation.
- Config writes (calibration results, taught reference frames) go through the
  config service from the node via `self.config.write_intrinsics(cid,
  CameraInfo)` / `self.config.write_frame(name, FrameDef)`; the store keeps
  provenance (`source: vision/{pid}/{node}`, `t_capture` range) and revision
  history, so an overwrite never silently destroys the old value.

## 4. The pipeline SDK (`wf.vision`)

### 4.1 A pipeline

```python
import cv2
from wf.vision import Pipeline, Frame, Result, Item, FramePose, source, node, window

class PickVision(Pipeline):
    """Locate the pallet and find the next blob to pick (cam1, eye-in-hand)."""
    pipeline_name = "pick_vision"
    roles = {"cam": "camera2d"}                        # bound to a cid in cell.yaml
    params = {"thresh": 120, "min_area": 400, "plane": "table"}   # live-editable, unknown keys rejected

    feed   = source("cam", rate_hz=10, scale=0.5, encoding="jpeg")
    gray   = node(feed)                                # Frame -> Frame
    blobs  = node(gray, result=True, overlay=True)     # Frame -> Result
    pallet = node(blobs, frame="pallet_1")             # Result -> FramePose
    hole   = window(gray, action=True, n=5)            # goal: 5 fresh frames -> one Result

    def run_gray(self, f: Frame) -> Frame:
        return f.derive(cv2.cvtColor(f.bgr, cv2.COLOR_BGR2GRAY), encoding="Mono8")

    def run_blobs(self, f: Frame) -> Result:
        _, bw = cv2.threshold(f.gray, self.p["thresh"], 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        items = [Item(bbox=cv2.boundingRect(c), score=1.0)
                 for c in contours if cv2.contourArea(c) >= self.p["min_area"]]
        return Result.of(f, items=items, overlay=[rect(i.bbox) for i in items])

    def run_pallet(self, r: Result) -> FramePose | None:
        if not r.items:
            return None                                # no frame update this result
        xyz = r.frame.ray(*center(r.items[0].bbox)).hit_plane(self.p["plane"])   # optical ray -> world via pose@capture
        return FramePose("pallet_1", parent="world", xyz=xyz, quat=[0, 0, 0, 1], confidence=0.9, ttl_s=300)

    def run_hole(self, frames: list[Frame]) -> Result:
        centers = [find_hole(f.gray) for f in frames]
        return Result.window(frames, data={"uv": median(centers)})
```

- `Pipeline` mirrors `Program`: `pipeline_name` (default: file stem), `roles`
  (role → contract, only `camera2d` and `vision` for now), `params`
  (defaults; overridden in `cell.yaml`; `self.p`), `run_<node>` methods.
  `self.log()`, `self.config` (config service helpers), `self.frames`
  (resolver for named frames/planes at a timestamp — the same
  `wf.core.frametree` the arm uses).
- Node declarations are class attributes so the graph exists at import,
  like `State(...)` / `a.to(b)` for programs. Names are validated at import:
  every declared node needs a `run_` method with a matching signature;
  every input must be a declared node or source; cycles are an import
  error.
- A node may return `None` to publish nothing for this frame.

### 4.2 Node kinds

| declaration | signature | output |
|---|---|---|
| `source(role, rate_hz, scale, roi, encoding)` | — | the camera stream this pipeline asks for (one per role; two sources on one role are merged) |
| `source(pipeline="qr_watch", node="gray")` | — | another pipeline's tapped feed (cross-pipeline edge over the bus) |
| `node(inp)` | `Frame -> Frame` | a feed; tappable |
| `node(inp, result=True, overlay=True)` | `Frame -> Result` / `Result -> Result` | `.../result`, `.../overlay` |
| `node(inp, frame=name\|True)` | `Result -> FramePose \| None` | `{realm}/frames/{name}` |
| `window(inp, action=True, n= / duration_s= / until_close=True)` | `list[Frame] -> Result` | goal-driven, one result per goal |
| `node(inp, action=True)` | `Frame -> Result` | one-shot goal (`once`) — also usable continuously when demanded |
| `sync(a, b, tol_ms=20)` | `(Frame, Frame) -> …` | pairs frames of two sources by `t_capture` (multi-camera) |
| helpers: `debounce(inp, key=, cooldown_s=)`, `changed(inp, key=)` | `Result -> Result \| None` | emit once per new value — QR/barcode watchers |

Flags on any node: `always=True` (no external demand needed),
`max_rate_hz=` (skip frames), `thread=True` (own lane: a slow node must not
hold up a cheap sibling), `publish=dict(scale=0.25, quality=75)` (tap
encoding).

### 4.3 Graph export

`Pipeline.describe()` → `{name, roles, params, nodes: [{id, kind, inputs,
flags, result, overlay, frame, action}], sources, source_anchors}` — the same
shape family as `wf.program.graph.build_graph`, so the existing React Flow
graph card draws it. The live overlay comes from `state/status`: node active
/ idle / error, fps, latency; a tapped node shows a small live thumbnail.
Positions are stored in `config/vision/{name}/layout`.

### 4.4 Offline execution and tests

`wf.vision.offline.run(PipelineClass, frames_iter, params)` drives the graph
without a bus: from image files (pytest fixtures) or from an MCAP via
`wf.services.recording.source.McapSource` filtered to `camera2d/{cid}/image`.
Returns results/overlays/frames per node. This is how node unit tests and
the replay-regression CLI (§8) work; the service is a thin bus adapter
around the same executor.

## 5. The vision service (`wf.services.vision`)

### 5.1 Process model

- **One process per pipeline**: `python -m wf.services.vision --pipeline
  <file> --pid <id> --bind cam=cam1 ...`, spawned by the supervisor (§6) like
  a provider, crash-only, restarted on exit, liveliness token per pid.
  Isolation is the reason: a slow detector or a crashing import must not
  stall the runner or the always-on watcher, and each pipeline can later get
  its own runtime (`launch: external`, container, GPU) without changing the
  design.
- Inside: the executor (§4.4) + bus adapter: source subscribers, demand
  book-keeping, publishers, queryables, action servers, the 1 Hz status loop,
  and the camera arbitration client.

### 5.2 Scheduling

- One **lane** (worker thread + 1-slot latest-wins mailbox) per source; a
  node with `thread=True` gets its own lane fed from its input's output.
  Never backlog: if a lane is busy the newer frame replaces the waiting one
  and `dropped` increments in status — the same policy as `DROP` congestion
  control on image publishers.
- Nodes within a lane run in topological order per frame; a node that is not
  active is skipped (its subtree is not evaluated).
- OpenCV releases the GIL in its kernels, so several lanes in one process
  scale to a few cores; Python-heavy nodes are the reason for `thread=True`
  and, later, for per-pipeline external runtimes.

### 5.3 Camera stream arbitration (decision needed, §11.1)

`camera2d` today has one `StreamParams` and rejects `grab` while streaming.
With two pipelines and the Cameras page on the same camera, one party must
own the stream. Proposed: extend `camera2d` with a ref-counted stream demand,
analogous to the producer lease already in the contract:

```
{realm}/camera2d/{cid}/cmd/stream_demand   {client_id, params: StreamParams, ttl_s} -> Ack
{realm}/camera2d/{cid}/cmd/stream_release  {client_id} -> Ack
{realm}/camera2d/{cid}/state/demand        {clients: [{client_id, params, expires_at}], effective: StreamParams | None}
```

`Camera2dCore` streams the union of live demands (max rate, max scale, raw if
any, ROI union) and stops when the last expires. `stream_start`/`stream_stop`
stay as the un-refcounted operator override (UI Cameras page). A `grab`
while streaming is then served from the stream when the spec is compatible
(the next frame, full res if the stream is raw) instead of being rejected —
calibration grabs and on-demand goals no longer fight the stream.
Fallback for v1 if the contract change is postponed: the vision service is
the sole stream owner per camera and the Cameras page taps a pipeline feed.

### 5.4 Publishing and recording policy

- Results, overlays, frames, status: always published while active (small).
- Feeds: only while tapped, at the tap's `publish` spec (default JPEG q75,
  scale 0.25) — the same preview policy as the camera stream defaults.
- **Record inputs and results, not intermediates.** Camera frames and
  `vision/**/result|overlay|status` are the regression inputs/outputs;
  derived feeds are deterministic functions of the camera frames. Tapped
  feeds are published under the realm and therefore recorded; keep taps at
  preview scale. (Design §4.3's `image/preview` naming stays available if a
  recorder exclusion rule is ever wanted.)
- Budget for reference: `1280×800` `Mono8` ≈ 1 MB/frame — 15 MB/s at 15 Hz on
  localhost, fine for one or two raw consumers; JPEG q75 at scale 0.25 ≈
  20 KB/frame. zenoh SHM is the upgrade if raw full-rate multi-consumer ever
  hurts (§11.5).

### 5.5 Failure modes

- A node raising → the node (and its subtree) reports `error` in status, the
  result carries `ok: false, error`; the lane keeps running (one bad frame
  must not kill a watcher). A goal in flight fails with the error.
- Camera gone (`camera2d` liveliness lost / `connected: false`) → sources
  idle, status `ok: false, error: camera_absent:<cid>`, demand is kept and
  the stream is re-requested when the camera returns.
- Pipeline process dies → the supervisor restarts it; demand from clients is
  re-established by their renewals (the runner re-demands for the active
  state; the UI re-taps). A program goal in flight fails with
  `vision_restart:<pid>`.
- Unknown node / unknown param / two writers for one frame name / missing
  `run_` → rejected at import or activation with a machine-readable reason,
  shown in the inventory like `program_broken:<error>`.

## 6. Cell schema

Pipelines are not hardware: no live/sim/replay sources of their own — they
follow whatever the cameras are (the same rule as `provides` devices).

```yaml
vision:
  qr_watch:
    pipeline: qr_watch                 # deploy/vision/qr_watch.py (cells: deploy/<cell>/vision/)
    bind: { cam: cam0 }
    params: { cooldown_s: 2.0 }        # overrides the class defaults
  pick_vision:
    pipeline: pick_vision
    bind: { cam: cam1 }
    launch: module                     # default; `external` = brought up outside the supervisor
```

- The supervisor validates (`pipeline` importable, roles bound to devices of
  contract `camera2d`, params known, frame names unique) at activation,
  spawns one child per pipeline after the cameras, and lists each pipeline
  in the device inventory as `{id: pid, contract: "vision", model: null,
  active: "on"|"off", config: {pipeline, bind, params}, sources: []}` — so
  `Machine.resolve_bindings` and the role picker work unchanged.
- The runtime overlay may switch a pipeline off: `active_sources:
  {pick_vision: off}` (any other value is `bad_runtime`).
- Discovery mirrors programs: a directory of modules, one `Pipeline`
  subclass per file (or `PIPELINE = …`), rescanned on save from the editor.

## 7. Program integration (`wf.program`)

### 7.1 `VisionProxy` (`self.m.<role>` for a `vision` role)

```python
self.m.vis.latest("blobs")                                  # Result | None (cached from the result topic)
self.m.vis.wait("blobs", cond=lambda r: r.items, fresh_after=t0, timeout_s=5.0)   # Result; False on timeout
self.m.vis.run("hole", timeout_s=10.0)                      # goal `once`/`n` -> Result (cancel-on-exit)
with self.m.vis.window("scan") as w:                        # goal `until_close`
    self.m.arm.move_l(...)                                  # frames collected while the arm sweeps
r = w.result()                                              # close -> one Result
with self.m.vis.enabled("blobs"):                           # imperative demand inside an action
    ...
self.m.vis.set_params(thresh=100)                           # live param change (lease-gated)
self.m.vis.status                                           # PipelineStatus
```

Every blocking call honours the action's `ActionContext`: leaving the state
cancels the goal / releases the demand and raises `ActionCancelled` in the
action thread — identical to arm goals. `wait` raises `ProgramError`
(`vision_error:<pid>:<node>:<error>`) when the node reports an error.

### 7.2 Triggers and demands (declarative, evaluated by the runner)

```python
triggers = [
    on_result("vis", "qr", event="qr_seen"),                 # every published Result of node `qr`
    on_result("vis", "blobs", event="target_found", cond=lambda r: bool(r.items)),
]
demands = [
    while_in("locating", "vis", "blobs"),                    # demand `blobs` while state `locating` is active
    while_in("running", "vis", "pallet"),                    # compound/parallel states work: any active leaf inside
]
```

- `on_result` is the `on_channel` of vision: the runner watches the proxy's
  result stream and injects the event with the `Result` as event data
  (python-statemachine kwargs: `def on_qr_seen(self, result): ...`,
  usable in guards). Debounce / change detection is the pipeline's job
  (`debounce` / `changed` nodes) so the trigger stays dumb.
- `while_in` acquires demand on state entry and releases on exit, renewing
  at half the TTL while active — mirrors cancel-on-exit and needs no action
  code for passive states.

### 7.3 The four shapes, end to end

```python
class DemoVisionPick(Program):
    roles = {"arm": "arm", "io": "dio", "vis": "vision"}
    params = {"cycles": 3, "home": "home", "plane": "table"}
    triggers = [on_result("vis", "qr", event="qr_seen")]     # (c) always-on watcher -> event
    demands = [while_in("locating", "vis", "blobs")]         # (b) detection only while locating

    homing = State(initial=True); locating = State(); measuring = State()
    picking = State(); scanning = State(); done = State(final=True)
    ...

    def run_locating(self, ctx):
        t0 = now_ns()                                        # after the arm settled -> only fresh frames count
        r = self.m.vis.wait("blobs", cond=lambda r: r.items, fresh_after=t0, timeout_s=5.0)
        if not r:
            self.emit("nothing_there"); return
        self.emit("target_found")

    def run_measuring(self, ctx):                            # (a) find a pixel, then move
        r = self.m.vis.run("hole", timeout_s=10.0)           # 5 fresh frames, median centre
        xyz = self.m.frames.ray_hit("cam1", r.data["uv"], plane=self.p["plane"], t=r.t_capture)
        self.m.arm.move_l(frame="world", xyz=xyz, quat=self.p["approach_quat"])
        self.emit("measured")

    def run_picking(self, ctx):                              # the located pallet is just a frame
        self.m.arm.move_l(frame="pallet_1", xyz=[0, 0, 0.05], quat=[0, 0, 0, 1])
        ...

    def run_scanning(self, ctx):                             # (d) all frames between two instants -> one output
        with self.m.vis.window("scan") as w:
            self.m.arm.move_path(self.p["sweep"])
        r = w.result()                                       # e.g. a stitched image or a fitted plane
        self.log(f"scan residual {r.data['residual']:.3f}")  # pipeline node may also have written config/frames/...
        self.emit("scanned")

    def on_qr_seen(self, result):                            # event data from the trigger
        self.log(f"code {result.items[0].label}")
```

Only `pallet` needs no vision code in the program at all: the pipeline
publishes `frames/pallet_1` and the arm resolves `{frame: "pallet_1"}` at
goal accept (execution snapshot records which frame revision was used).

## 8. Sim, replay, regression

- **Sim**: the browser/headless camera renders the twin scene and serves the
  `camera2d` contract; pipelines subscribe to contract keys only, so the real
  vision code runs on rendered frames and its overlays show on the rendered
  image (design §5.4's loop). Sim scenes gain markers (ArUco / QR textures on
  scene objects) so watchers and locators have something to find.
- **Replay**: the replayer republishes camera frames verbatim into
  `replay/{id}`; a pipeline started in that realm recomputes results from
  old pixels. The recorded `vision/**` channels are the reference; the Vision
  page's replay mode shows recorded vs recomputed with a diff strip (GUI
  spec §8).
- **CLI regression**: `wfctl vision replay <file.mcap> --pipeline pick_vision
  [--params …] [--compare]` runs the offline executor (§4.4) over the file's
  `camera2d/{cid}/image` channel and diffs against the recorded results —
  no bus, CI-friendly. This is the fleet-upgrade harness from design §8.4
  for vision.
- Determinism: windows by `t_capture`, freshness by `t_capture`, poses from
  the header — nothing reads "now" except goal acceptance.

## 9. Web

- **Vision page** (GUI spec §8): pipeline list from the inventory + status
  (state dot, cameras, node fps); the pipeline's graph card (reuse of the
  program graph component, read-only, live overlay, click a node to jump to
  its `run_`); 2D pane = a tapped feed or the camera image with overlay
  primitives; 3D pane = frames/frustum at `t_capture`; params panel
  (`cmd/params`, lease-gated); result inspector; "freeze on next fail".
  Viewing a node taps it (demand with the page's `client_id`, renewed while
  visible, released on navigate-away).
- **Cameras page**: the feed picker lists every `**/image` topic — camera or
  pipeline node — so any layer can be viewed where camera quality is checked
  today.
- **Programs tool**: `demands` shown next to triggers in "Waiting for";
  vision goals appear like arm goals in the transition/log view.
- **Editor**: `deploy/vision/*.py` editable like programs (save → rescan →
  the supervisor restarts that pipeline; import errors reported).

## 10. Delivery order

Each step: pytest + `tsc -b` + `npm run build` + a sim e2e.

0. `camera2d` stream demand (`cmd/stream_demand|stream_release`,
   `state/demand`, grab served from a compatible stream) in `Camera2dCore` +
   conformance tests + browser/headless provider parity. Small, self-contained,
   and everything after depends on the arbitration (or: decide §11.1 for the
   v1 fallback and defer).
1. `wf.contracts.vision` (keys, messages) + `wf.vision` SDK (`Frame`,
   `Pipeline`, node declarations + import validation, `Result`/`Overlay`/
   `FramePose`, helpers `debounce`/`changed`/`sync`, graph export, offline
   executor) + unit tests with fixture images. No bus yet.
2. `wf.services.vision` (executor + bus adapter: sources, demand + TTL,
   taps, result/overlay/frame publishing, params, action servers, status,
   camera arbitration client) + supervisor `vision:` schema, spawn,
   inventory entry, runtime `off` + `wfctl vision-status|demand|release|run|params`.
   `deploy/vision/qr_watch.py` (always-on `debounce` watcher) and
   `deploy/vision/pick_vision.py` on the sim camera with markers in the twin
   scene.
3. Program integration: `VisionProxy` + `Machine.vision`, `on_result`,
   `while_in` demands, `self.m.frames.ray_hit`, `deploy/programs/demo_vision_pick.py`
   covering the four shapes; in-process e2e like the program runner suite.
4. Web: Vision page (list, graph card, 2D pane with generic overlay
   renderer, params, result inspector, taps), Cameras page feed picker,
   Programs tool demands.
5. Replay regression: `wfctl vision replay --compare`, Vision page replay
   split view; recorder policy check for tapped feeds.
6. Later, in any order: calibration wizard flows (design §5.5) as
   `window` pipelines writing `config/intrinsics` / hand-eye; ONNX node kind;
   `launch: external` GPU runtime; zenoh SHM sources; YAML composition of
   library nodes editable in the UI.

## 11. Open decisions (defaulting to the proposal unless objected)

1. **Camera arbitration**: contract-level stream demand in `camera2d` (§5.3,
   proposed, step 0) vs. "vision service is the sole stream owner per camera"
   for v1. The former also fixes grab-while-streaming for calibration.
2. **Where pipelines live**: `vision:` section of `cell.yaml` listed as
   inventory devices of contract `vision` (proposed) vs. resources with
   `contract: vision` and no sources. Proposal keeps "resources are
   hardware-shaped" and reuses the `provides`-style "follows its host" rule.
3. **Event semantics of `on_result`**: fire per published result (proposed;
   pipelines dedupe with `debounce`/`changed`) vs. per change in the trigger.
4. **Demand identity for programs**: the runner demands under the program's
   `client_id` (proposed, so a lost lease/abort also drops demand on the
   same TTL) vs. a per-state client id.
5. **Frame transport**: reduced-scale JPEG / Mono8 over zenoh (proposed for
   v1); zenoh SHM when a raw full-rate multi-consumer case appears.
6. **Tapped feeds and the recorder**: record them (simple, proposed — they
   are preview-scale) vs. an exclusion rule (`image/preview` naming).
7. **Params persistence**: live-only via `cmd/params` with `cell.yaml`
   defaults (proposed) vs. a `config/vision/{pid}/params` store family for
   operator-tuned values that survive restarts (operational state per design
   §8.3 — likely wanted once a cell is commissioned; cheap to add later).
