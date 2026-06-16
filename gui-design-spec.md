# GUI Design Specification — Automation Framework Web Pendant

Companion to the architecture doc (v5). Each page section below is written to be self-contained, so it can be pasted directly as a mockup prompt. Layouts are described spatially with ASCII wireframes; component lists map 1:1 to bus keys from the architecture.

---

## 1. Design language (applies to every page)

**Context of use.** Two physical situations: (a) an engineer at a desktop with 2 monitors, and (b) an operator holding a ~12" tablet standing next to the robot. Pages are desktop-first and information-dense, except **Operate**, which is tablet-first with large touch targets.

**Theme.** Dark industrial UI: near-black charcoal background (`#16181D`), panel surfaces one step lighter (`#1E2128`), hairline borders (`#2C313A`), primary text warm off-white (`#E8E6E1`), secondary text `#8A919E`. Dark because camera images and 3D scenes read best on dark, and because the UI is used in dim production halls.

**The signature — realm tinting.** A 3px line under the top bar, the active-nav indicator, and all primary action buttons are tinted by the active realm:
- **LIVE — signal orange `#FF6A00`.** You are commanding real hardware. Primary buttons in live realm look slightly "hot".
- **SIM — cyan `#22B8CF`.** Safe sandbox; the whole app feels cooler.
- **REPLAY — amber `#E8B931`.** Historical data; all command controls are disabled and visually flattened (ghosted, no fill).
The realm name is always written in the top bar in small caps next to the tint. Nobody should ever need to *remember* which realm they're in — the chrome tells them.

**Safety colors are reserved.** Pure red `#E5484D` is used *exclusively* for safety states (e-stop, protective stop, fault). It never appears as decoration, delete buttons use a muted variant. Green `#46A758` = ok/running, amber = warning/paused.

**Typography.** UI face: a neutral technical grotesque (Inter or IBM Plex Sans). All live numeric values — joint angles, poses, IO counts, timestamps — in a monospace with tabular figures (IBM Plex Mono / JetBrains Mono) so values don't jitter as digits change. Numbers are the protagonist of this interface; treat them typographically as such: large mono readouts with small unit labels (`mm`, `°`, `mm/s`).

**Spatial conventions.** XYZ axes always colored R/G/B (industry standard), used consistently in the 3D triads, jog buttons, and pose readout labels. Frames shown as small triad glyphs; provenance shown as tiny badges: `CAD` (gray), `TAUGHT` (blue), `CAL` (violet), `VISION` (pulsing dot when live-updating).

**Component grammar.** Dockable panels with a slim title bar (panel name + overflow menu); resizable splits. Buttons: filled = primary realm-tinted action, outline = secondary, ghost = tertiary. All destructive or motion-causing actions require either hold-to-activate (motion) or confirm (delete). Toasts bottom-right; safety events never appear as toasts — they take over the status strip.

---

## 2. App shell (global chrome on every page)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⬡ cell: venlo-line2   [ LIVE ▾ ]   ●servo  ⛨SAFE  spd ▮▮▮▯ 75%   👤 jeroen  │ ← top bar
│ ═══════════════════════ realm tint line ════════════════════════════════════ │
│┌──┐┌────────────────────────────────────────────────────────────────────────┐│
││▣ ││                                                                        ││
││▣ ││                      page workspace                                    ││
││▣ ││                 (dockable panel layout,                                ││
││▣ ││                  preset per page)                                      ││
││▣ ││                                                                        ││
││▣ ││                                                                        ││
│└──┘└────────────────────────────────────────────────────────────────────────┘│
│ ⚑ 14:02:11 program pick_demo started by jeroen   ⚑ 14:02:09 frame pallet_1…  │ ← event ticker
└──────────────────────────────────────────────────────────────────────────────┘
```

**Top bar, left → right:**
- Cell identity (name + connection dot to the Zenoh router).
- **Realm switcher** — segmented control `LIVE / SIM / REPLAY`; switching re-tints the whole app and re-points every subscription. Switching *to* LIVE requires a confirm.
- **Safety status cluster** — servo state, e-stop / protective-stop indicator (this cluster turns solid red and the page dims 20% when a safety stop is active; it is the only thing allowed to interrupt every page), speed-scale readout.
- **Control lease chip** — shows current owner (`👤 jeroen · 04:12 left`) or `— no one in control —`; clicking requests/releases the lease. If someone else holds it, the chip shows their identity and all motion controls app-wide render disabled with a lock glyph.
- Alarm bell with unread-event count.

**Left rail:** icon-only nav (labels on hover): Overview, Operate, Programs, IO, Cameras, Vision, Frames, Calibration, Recordings, Tasks, System. Active item carries the realm tint.

**Bottom event ticker:** single line, last 2 events from `{realm}/events`, click opens the System → Events log.

**Replay drawer (global):** when realm = REPLAY, a persistent timeline bar docks above the event ticker on *every* page — scrubber with event markers, play/pause, rate (0.25–4×), session picker, data-timestamp readout. Every page works identically in replay; only command controls are flattened.

---

## 3. Page: Cell Overview (home)

**Purpose:** answer "what is the cell doing right now?" in 5 seconds; the page left open on a wall monitor.

```
┌───────────────────────────────────────────────┬──────────────────────┐
│                                               │ STATUS               │
│                                               │ arm r1     ● running │
│              3D viewport                      │ cam0       ● 14.8fps │
│        (robot, scene, frames,                 │ io1        ● ok      │
│         camera frustum, live TCP trail)       │ task: pick_demo 62%  │
│                                               ├──────────────────────┤
│                                               │ ACTIVITY (events)    │
│  [⌖ home] [⊞ frames] [◉ follow TCP]           │ 14:02 program start  │
├───────────────────────────────────────────────┤ 14:01 pallet_1 ↺ vis │
│ cam0 preview (small) │ joints sparkline strip │ 13:58 control: jeroen│
└──────────────────────┴────────────────────────┴──────────────────────┘
```

- **3D viewport (≈60%):** URDF robot at live joint state; scene objects; frame triads (toggleable); camera frustum; faint TCP breadcrumb trail (last 10 s). View presets: home/top/tool.
- **Status column:** one row per resource from the registry descriptors — liveliness dot, key metric (state rate, fps), tap → resource detail in System. Active task with progress if running.
- **Activity feed:** richer slice of the event log with severity icons.
- **Bottom strip:** small camera preview tile per camera + a 60 s joint-velocity sparkline strip.
- **Empty state (no resources alive):** the 3D view shows the scene only, status column lists expected resources from `cell.yaml` grayed with "waiting for driver…" and a hint to check the supervisor.

---

## 4. Page: Operate (the pendant — tablet-first)

**Purpose:** jog, set TCP/frame, quick IO, speed — the page in the operator's hands at the fence. Everything ≥48px touch targets; no hover-dependent UI.

```
┌──────────────────────────────┬───────────────────────────────────────┐
│ POSE (active TCP in base)    │            JOG                        │
│ X  412.31  Y −102.88  Z 305  │  mode: [Joint | Cartesian]            │
│ RX 180.0   RY 0.0    RZ −45  │  frame: [Base ▾]  TCP: [gripper ▾]    │
│ ──────────────────────────── │                                       │
│ JOINTS                       │   ◀ X+ ▶   ◀ Y+ ▶   ◀ Z+ ▶            │
│ J1 ▓▓▓▓▓░░ 84.2°             │   ◀ RX ▶   ◀ RY ▶   ◀ RZ ▶            │
│ J2 ▓▓░░░░░ 23.1°  …J6        │   (hold-to-jog buttons, XYZ=RGB)      │
│ ──────────────────────────── │   step: [cont | 10 | 1 | 0.1 mm]      │
│ QUICK IO                     │                                       │
│ gripper  [● close] [○ open]  │  speed ▮▮▮▮▮▮▮▯▯▯ 70%   [▼10%][▲]     │
│ DI: part_present ●           │  ┌─────────────────────────────────┐  │
│                              │  │      ■  STOP  (always visible)  │  │
└──────────────────────────────┴──┴─────────────────────────────────┴──┘
```

- **Jog pads:** press-and-hold only (publishes the watchdogged setpoint stream; releasing stops). Buttons depress visually and show a thin progress ring while held. Cartesian pad colored by axis convention. Step mode buttons for incremental nudges.
- **TCP picker:** lists only `selectable_as_tcp` frames with `role: tool` by default; an "advanced" expander reveals sensor frames (e.g. `cam0_optical`) with a warning chip.
- **Pose/joints readout:** large tabular mono; joint rows show range bars with soft-limit zones shaded; values flash amber near limits.
- **Quick IO:** pinned favorite signals (configured per cell type).
- **STOP:** full-width bottom-right, always reachable by right thumb, muted-red outline (it is a software stop — the page footer carries the permanent caption *"Software stop — not an emergency stop. E-stop is on the physical pendant."*).
- **Lease behavior:** if the user doesn't hold the control lease, the jog half renders locked with one big "Request control" button.
- **In SIM realm:** identical, cyan-tinted — the training mode. **In REPLAY:** jog half replaced by the message "viewing recording".

---

## 5. Page: Programs (teach & run)

**Purpose:** UR/Aubo-pendant-grade waypoint programming with frame-referenced targets; edit and run modes.

```
┌──────────────┬──────────────────────────────┬───────────────────────┐
│ PROGRAMS     │ WAYPOINT LIST  pick_demo v7  │                       │
│ ▸ pick_demo  │ 1 ⊙ movej  home      100%    │      3D preview       │
│ ▸ scan_plate │ 2 ⊙ movel  appr@pallet_1 …   │  (path drawn through  │
│ ▸ calib_path │ 3 ⊙ movel  pick@pallet_1     │   waypoints, ghost    │
│ + new        │ 4 ⚙ set_do gripper=close     │   robot at selected   │
│              │ 5 ⊙ movel  retreat           │   waypoint, frames    │
│              │ [+ waypoint] [+ io] [⌖touch] │   highlighted)        │
│              ├──────────────────────────────┤                       │
│              │ SELECTED: 3 movel            │                       │
│              │ frame [pallet_1 ▾] blend 5mm │                       │
│              │ speed 250mm/s  pose [edit]   │                       │
├──────────────┴──────────────────────────────┴───────────────────────┤
│ RUN:  [▶ run] [⏭ step] [■ stop]   progress ▮▮▮▮▯▯ wp 3/5   ● running │
└──────────────────────────────────────────────────────────────────────┘
```

- **Waypoint list:** drag-to-reorder rows; icon per type (movej/movel/movec/IO/wait); the *frame* a target references is shown inline as a chip (`@pallet_1`) — frame chips with `VISION` provenance pulse subtly.
- **Touch-up:** with a row selected, "⌖ touch" captures the current robot pose into it (classic pendant gesture).
- **Inspector:** per-waypoint frame picker (from Frames page data), blend radius, speed/accel.
- **3D preview:** full path as a polyline with blend arcs, ghost robot scrubs along it via a mini-slider; unreachable/unresolvable waypoints render red with the resolver's structured error on hover (`FrameStale: pallet_1, last seen 42 min ago`).
- **Run bar:** hold-to-arm then run (live realm); during execution the active waypoint row highlights and follows feedback from the action; stop maps to the contract's cancel. After every run, a link chip appears: "execution snapshot #1284" → opens the immutable resolved record (operator, frame revisions, resolved targets, versions).
- **Run in SIM first** is offered as the default split-button option when in live realm: `[▶ run in sim ▾ | run live]`.
---

## 6. Page: IO

**Purpose:** see and toggle every digital/analog signal in the cell — robot onboard IO and standalone `dio` devices in one uniform grid (they share the same message shapes, so they share the same component).

```
┌──────────────────────────────────────────────────────────────────────┐
│ [arm r1 onboard] [io1 modbus] [all]            filter: ▢ search…     │
├───────────────────────────────┬──────────────────────────────────────┤
│ DIGITAL OUT                   │ DIGITAL IN                           │
│ DO0 gripper_close   [ ● on ]  │ DI0 part_present     ●               │
│ DO1 gripper_open    [ ○ off]  │ DI1 door_closed      ●               │
│ DO2 blow_off        [ ○ off]  │ DI2 vacuum_ok        ○               │
│ …                             │ …                                    │
├───────────────────────────────┴──────────────────────────────────────┤
│ ANALOG   AI0 pressure ▁▂▃▅▆ 4.21 bar   AO0 [────▮────] 5.0 V         │
└──────────────────────────────────────────────────────────────────────┘
```

- DO rows: name (from cell config aliases; raw pin number in small text), large toggle, last-change timestamp on hover. Toggling publishes `cmd/set_do`; the lamp reflects the *state stream*, not the click — so a failed write is visible as a toggle that snaps back.
- DI rows: lamp + name; a tiny 30 s history strip per signal (blips visible even if you looked away).
- Analog: sparkline + current value (mono), AO with a slider + numeric entry.
- Signals referenced by the running program/skill get a small chip showing the role binding (`gripper.grip`).
- REPLAY realm: everything read-only, history strips become the primary element.

---

## 7. Page: Cameras

**Purpose:** live viewing and device control for every `camera2d` resource; the place to verify image quality before vision work.

```
┌────────────────────────────────────────────────┬─────────────────────┐
│                                                │ cam0 — GV12345      │
│                                                │ mount: flange (r1)  │
│            main view: cam0 preview             │ ─ ACQUISITION ───── │
│        (fit/100% zoom, pixel inspector,        │ exposure 8.0 ms ─▮─ │
│         crosshair, optional overlays)          │ gain     2.0 dB ─▮─ │
│                                                │ trigger [free ▾]    │
│                                                │ fps 14.8  drop 0    │
│  [⊕ grab full-res]  [▦ histogram]  [⌗ grid]    │ ─ CALIBRATION ───── │
├──────────────┬─────────────────────────────────┤ intrinsics ✓ 0.21px │
│ cam0 ▣ live  │ cam1 ▢ (configured, offline)    │ hand-eye  ✓ 0.4 mm  │
└──────────────┴─────────────────────────────────┴─────────────────────┘
```

- **Main view:** preview stream; zoom to 100% with panning; pixel inspector (hover → x,y + value); luminance histogram drawer; focus-peaking toggle (edge overlay) for lens setup; grid/crosshair for alignment.
- **Grab:** requests a full-res frame via the `grab` queryable and opens it in a lightbox with the same inspector tools — this is the operator's "is the image sharp" check.
- **Right panel:** GenICam-backed controls (exposure, gain, trigger mode) writing through `cmd/configure`; live fps/drop counters; calibration summary chips linking to the Calibration page; mount info with a mini-diagram (flange-mounted vs fixed).
- **Thumbnail strip:** all cameras in the cell; configured-but-offline cameras shown ghosted with their `cell.yaml` identity.
- Overlay toggles (per vision pipeline) can be enabled here too, but tuning lives on the Vision page.

---

## 8. Page: Vision

**Purpose:** rerun-style inspection of pipelines: inputs, results, overlays in 2D and 3D, parameters — and in replay, regression comparison.

```
┌──────────────┬───────────────────────────────┬───────────────────────┐
│ PIPELINES    │   2D space: cam0/image        │   3D space: world     │
│ ▸ locate_pal │  (frame + detection overlays: │  (scene + detected    │
│   ● running  │   boxes, ids, axes, scores)   │   pallet frame triad, │
│ ▸ qc_surface │                               │   camera frustum ray) │
│   ○ idle     │                               │                       │
│ + new        ├───────────────────────────────┴───────────────────────┤
│              │ RESULT  t=14:02:11.482  conf 0.94  4.2ms              │
│ PARAMS       │ pallet_1: x 812.4 y −33.1 z 0.0 rz 12.4° → frame ↺    │
│ thresh 0.62  │ ───────────────────────────────────────────────────── │
│ roi  [edit]  │ TIMELINE ▁▂▆▅▆▆▂▆ results/s   [⏸ freeze on next fail] │
└──────────────┴────────────────────────────────────────────────────────┘
```

- **Pipeline list:** state dot, input camera, output bindings ("updates frame `pallet_1`" shown explicitly — the binding from the architecture).
- **2D pane:** the source image with overlay primitives rendered from `vision/{pipeline}/overlay` — boxes, keypoints, masks, text, axis gizmos. Layer toggles per primitive group; opacity slider.
- **3D pane:** the same result in world space — detected frame triad, the camera frustum at `t_capture` (resolver-correct: the flange pose *at capture time*), reprojection rays.
- **Result inspector:** latest structured result (mono), confidence, compute time; "freeze on next fail" captures the exact failing frame + overlays for inspection.
- **Params panel:** pipeline parameters with apply; in live realm an "A/B on last frame" button re-runs the pipeline on the frozen frame with edited params.
- **REPLAY mode — the regression view:** the panes split horizontally: *recorded result* (top) vs *current-code result on the same recorded frame* (bottom), with a diff strip (Δ pose, Δ confidence) along the timeline. This is the architecture's replay-regression workflow given a face.

---

## 9. Page: Frames

**Purpose:** the frame tree as a manageable object — provenance, editing, teaching, and trust at a glance.

```
┌────────────────────────────┬─────────────────────────────────────────┐
│ FRAME TREE                 │                                         │
│ world                      │            3D viewport                  │
│ ├─ fixture_a   CAD  ⊿      │   (all triads; selected frame           │
│ ├─ pallet_1   VISION ●42s  │    enlarged with axis labels;           │
│ │   └─ slot_3  CAD         │    parent link drawn as a thin line;    │
│ ├─ arm/r1/base             │    stale frames render desaturated)     │
│ │   └─ …flange             │                                         │
│ │       ├─ tcp/gripper TOOL│                                         │
│ │       └─ tcp/cam0 SENSOR │  [show: ▣CAD ▣taught ▣vision ▣kinematic]│
├────────────────────────────┤─────────────────────────────────────────┤
│ SELECTED: pallet_1         │  x 812.4  y −33.1  z 0.0   rz 12.4°     │
│ parent world · by vision/  │  conf 0.94 · updated 42 s ago · TTL 5m  │
│ locate_pal · rev 17        │  [✎ edit] [⌖ teach 3-point] [⟲ history] │
└────────────────────────────┴─────────────────────────────────────────┘
```

- **Tree:** provenance badges (`CAD`/`TAUGHT`/`CAL`/`VISION`); dynamic frames show freshness (`●42s`) that fades toward the TTL and turns into a `STALE` chip past it; kinematic frames grouped under the robot; role tags (`TOOL`/`SENSOR`) on flange children.
- **Inspector:** pose (editable for static frames), parent, owner, revision; **history** opens the revision list (who/what/when, old→new delta) — config revisions are first-class here.
- **Teach 3-point:** launches a guided modal (touch origin → +X → +XY with the active TCP; big "capture" button mirroring the Operate page style).
- **Import from CAD:** file-drop modal previewing incoming frames as ghost triads in the 3D view, with a name-collision check before commit.
- Scene objects attached to a frame are listed under it and highlight in 3D when the frame is selected — making "this fixture moves with this frame" visible.

---

## 10. Page: Calibration

**Purpose:** wizard-style flows; the only page that is deliberately *linear* rather than a dashboard.

**Layout:** a left stepper rail (steps with check/active/pending states), a large central work area, a right context panel (live readouts relevant to the step). Three flows selectable from a landing grid: **Intrinsics**, **Hand-eye**, **Validate (touch-point)**.

- **Intrinsics flow:** step 1 board setup (board parameters + a live detection check — corners light up green on the preview); step 2 capture (the working area shows the live image with a **coverage heatmap** overlay of where corners have been collected; a target count ring fills); step 3 results (RMS, per-view error bar list — outlier views flagged with retake buttons); step 4 commit (writes config, shows the revision diff).
- **Hand-eye flow:** step 1 prerequisites checklist (intrinsics ✓, board visible ✓, lease held ✓); step 2 pose collection — a checklist of 15–30 target poses rendered as ghost robots in a 3D pane, each turning solid as captured; per-capture the right panel shows settle-detection (pose stable ✓) before allowing the grab; step 3 solve (method picker Park/Daniilidis, residuals in mm/deg with a pass/warn threshold); step 4 commit — explicitly shows *both* writes: camera mount + the `cam0_optical` sensor-TCP, with revision history links.
- **Validate flow:** camera locates a target → UI computes the touch pose → guided slow approach with the gripper TCP → operator confirms contact → reported deviation in mm. Big pass/fail verdict card.
- Every flow ends with the same footer: "This calibration run was recorded — session #id" linking to Recordings.

---

## 11. Page: Recordings & Replay

**Purpose:** browse sessions, scrub them, and launch replay realm; the entry point of every incident review.

```
┌──────────────────────────┬───────────────────────────────────────────┐
│ SESSIONS                 │ session 2026-06-12_13-58  ·  6m42s · 1.2GB│
│ ▸ today 13:58  6m  ⚑3    │ ┌───────────────────────────────────────┐ │
│ ▸ today 09:12  41m ⚑1    │ │ channel lanes (mini-timeline per key  │ │
│ ▸ jun 11 16:40 12m       │ │ group: arm state ▂▃▅▆, images ││││││, │ │
│   …                      │ │ events ⚑  ⚑      ⚑, task spans ▭▭▭ ) │ │
│ filter: ▢ has-faults     │ └───────────────────────────────────────┘ │
│                          │ markers: 14:02:09 protective stop ⚑ red   │
│                          │ [▶ open in replay realm] [⬇ export] [✂clip]│
└──────────────────────────┴───────────────────────────────────────────┘
```

- **Session list:** auto-named by time, badges for event severity counts, version-change markers, size/duration; filters (faults only, by program, by date).
- **Session detail:** stacked channel lanes — a compact multi-track timeline (state density, image-frame ticks, event flags, program-execution spans as colored ranges). Clicking anywhere arms "open in replay at this timestamp".
- **Open in replay realm:** switches the whole app to REPLAY (amber) with the global timeline drawer bound to this session — every other page now shows this moment in time.
- **Clip & export:** select a time range → export a smaller MCAP (for sharing with support or feeding the regression view).

---

## 12. Page: Tasks (flows — later phase)

**Purpose:** run and observe skills/flows; watch the behavior tree think.

**Layout:** left = flow list with role-binding summary (which resources each role resolved to, from `cell.yaml`); center = live BT graph — nodes as rounded cards colored by state (idle gray / running tint / success green / failure red), the active path drawn emphasized, tick rate shown; right = blackboard inspector (key values the tree reads/writes, parameters with edit-before-start). Bottom run bar mirrors the Programs page (`run in sim ▾ | run live`, progress, stop). In REPLAY, the graph re-animates from recorded `task/state` — scrub to any failure and the tree shows exactly which branch failed and why.

---

## 13. Page: System

**Purpose:** the engineer's room — resources, events, versions, cell config, snapshots.

**Tabs:**
- **Resources:** card per resource rendered *from its registry descriptor*: contract + versions, HAL + version, liveliness, capabilities table, limits, restart button (supervisor action). Cards self-build from the descriptor schema — an unfamiliar capability still renders as a generic key/value block.
- **Events:** the full `{realm}/events` log — filterable by severity/source/kind, mono timestamps, expandable data payloads; "jump to recording" per row when a session covers that time.
- **Cell config:** read-only render of `cell.yaml` (bindings visualized as role→instance arrows), platform version pin, cell-type version; **state snapshots** panel: list of snapshots, "create snapshot" (exports operational state), diff viewer between snapshots.
- **Bus inspector (debug):** live key browser with rate/size per key, last payload preview — the `z_sub` equivalent for the browser; invaluable in week 3, hidden behind an "engineering" toggle later.

---

## 14. Responsive & multi-monitor notes

- **Tablet (Operate-centric):** rail collapses to a bottom tab bar with five items (Operate, IO, Cameras, Programs, Overview); Operate is the start page; System/Calibration hidden on tablet.
- **Desktop multi-monitor:** any panel pops out into its own browser window (same bus subscriptions), so 3D view on one monitor + cameras on another is just two windows.
- **Kiosk/wall mode:** Overview with chrome hidden except the safety cluster and realm tint.

## 15. Build-up order (matches the roadmap slice)

1. Shell + realm tint + safety cluster + Overview with 3D viewport (weeks 3–4).
2. IO page + DO toggle, status strip (week 4).
3. Cameras page preview + grab (week 5).
4. Frames page v0 (tree + triads, static editing) (week 6).
5. Recordings + global replay drawer (validates the realm story visually).
6. Operate, Programs, Calibration wizards, Vision, Tasks — in that order, tracking platform phases 7–10.
