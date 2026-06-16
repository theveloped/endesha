# Reference Inventory — `calibration_images (1)`

Cross-walk between the v5 architecture design (`automation-framework-design-v5.md`) and the existing
Python scripts in `C:/Users/TobiasScheepers/Downloads/calibration_images (1)/`.
Everything here is **prior art** — non-binding, but battle-tested against the real Aubo i10 and the
FLIR Blackfly. When the design says "wraps your existing CLI logic as a library" it means *this* code.

> **Use this doc to**: locate the exact reference function before writing a HAL or service from
> scratch, copy the SDK incantations and quirks that already work, and avoid rediscovering things
> like the SingleFrame trigger pattern or the sequential autotune ordering.

**Naming policy (load-bearing):** terminology in this document follows the v5 design, never the
reference code. Whenever a reference symbol disagrees with the design, the design wins:

| Concept | This document uses | Reference may say |
|---|---|---|
| Arm flange (kinematic frame at link 6) | `flange`, `arm/r1/flange` | `ee`, `end-effector`, `wrist3_Link` |
| Hand-eye output transform | `T_flange_camera_optical` | `T_ee_camera` |
| Camera optical frame (= TCP-shaped sensor frame) | `camera2d/cam0/optical` (selectable TCP `cam0_optical`, `role: sensor`) | `camera`, `cam` |
| Position vector | `xyz` (meters) | `position`, `translation` |
| Orientation | `quat` = `[qx, qy, qz, qw]` | `quaternion`, `quaternion_xyzw`, `orientation` |
| Pose payload on the bus | `{frame, xyz, quat}` | `[x, y, z, rx, ry, rz]` (Aubo SDK Euler ZYX — stays inside HAL) |
| Resource class (cobot) | `arm` | `robot` |
| Resource class (area-scan camera) | `camera2d` | `camera`, `cam` |
| Resource class (IO block) | `dio` | `io`, `IO` |
| Hardware abstraction package | `hal/aubo_i10`, `hal/genicam`, `hal/arm_sim`, `hal/camera2d_sim`, `hal/modbus_io` | "the driver" |
| Running HAL process | `aubo_driver`, `camera_driver`, `sim_robot`, `sim_camera` (per design §5) | varies |
| Realms | `live`, `sim`, `replay/{session}` | n/a (new) |
| Resource ids in examples | `r1` (arm), `cam0`/`cam1` (camera2d), `io1` (standalone dio) | `robot`, `cam`, `io` |
| Logical site frames | flat reserved names: `pallet_1`, `fixture_a` | `CNYP34X137` (taught/cryptic) |
| Vision-published detection frames | `frames/detections/{pipeline}/{object_id}` | `pallet_X`, ad-hoc |
| Timestamps | `t_capture`, `t_observed`, `t_published` (nanoseconds) | `time.time()` (float seconds), `ts_ns` |
| Clock domain enum | `host \| camera_hw \| robot_controller \| replay` | implicit |
| Goal id | UUIDv7 | n/a |

Path prefix throughout: `C:/Users/TobiasScheepers/Downloads/calibration_images (1)/` — abbreviated `~ref/`.

---

## 1. Inventory by purpose

| Group | File(s) | What it is |
|---|---|---|
| **Aubo SDK wrapper** | `~ref/aubo_cli.py` (1482 lines) | Whole vocabulary of `pyaubo_sdk` calls + Ruckig path execution + IO + capture + autotune + frame/TCP/profile JSON stores + Cartesian `move_line` with frame + TCP composition |
| **URDF + FK** | `~ref/aubo_i10_fk.py` + `~ref/robot_model/aubo_i10/{aubo_i10.urdf, meshes/, config/}` | Pure-Python URDF parser, per-link 4×4 transforms; STL (collision) + DAE (visual) meshes; MoveIt YAMLs for joint/velocity/acceleration limits |
| **Live multi-threaded service** | `~ref/live_robot_rerun.py` (1057 lines) | The 4-thread pattern (RTDE arm-state @ 200 Hz, GigE camera, publish, command loop) + hardware-time synchronizer (offset-based + PTP) — the blueprint for `aubo_driver` + `camera_driver` |
| **Camera intrinsics calibration** | `~ref/calibrate_intrinsics.py` | ChArUco detection + `cv2.calibrateCamera` + per-image reprojection error |
| **Hand-eye calibration** | `~ref/calibrate_hand_eye.py` | `cv2.solvePnP` + `cv2.calibrateHandEye` (5 methods, Andreff best on this rig) + cross-view consistency validation |
| **Shared math + IO** | `~ref/utils.py` (697 lines) | Pose/quaternion/transform helpers, YAML/FileStorage save/load, board config, dataset loader, detector factories |
| **Capture pipelines** | `~ref/aubo_cli.py:cmd_capture`, `~ref/recapture.py`, `~ref/capture_locations.py` | Move → settle → SingleFrame trigger → save `image_NNN.png` + `pose_NNN.yaml` pairs |
| **End-to-end skill** | `~ref/pick_and_place.py` (824 lines) | Detect-OBB → pixel-to-world ray-plane → two-stage approach → grip → symmetry-refined place. This is `skills/vision_guided_pick` in proto form. |
| **Vision pipeline (OBB)** | `~ref/inference_package/inference.py` + `checkpoint_best_ema.pth` (RF-DETR OBB) | OBB detection with polygon NMS; returns `[{corners, score, class_id, center, size, angle_deg}, ...]` per image |
| **Pose-estimation pipelines (Rerun)** | `~ref/export_rerun.py`, `~ref/export_rerun_single_frame.py`, `~ref/export_rerun_ray_pose.py`, `~ref/scene_estimator.py`, `~ref/marker_detector.py`, `~ref/object_definition.py` | Sliding-window 2D-reproj and 3D-ray solvers; ChArUco / ArUco / DataMatrix / QR detection; model-template instance discovery; EKF tracker (bypassed by the two scripts) — overall, **the L3 vision-skills prototype** |
| **Symmetry / grid refinement** | `~ref/symmetry_refinement.py`, `~ref/gridcenter.py`, `~ref/grid_viewer_v3.py`, `~ref/estimate_grid_pose_v5.py`, `~ref/detect_cross_tops.py`, `~ref/detect_grid_simple.py` | Niche refiners called by `pick_and_place` and the cross-template matcher |
| **Persistent state files** | `~ref/tcp_configs.json`, `~ref/saved_frames.json`, `~ref/camera_profiles.json`, `~ref/poses.json`, `~ref/output/intrinsics.yaml`, `~ref/output/hand_eye.yaml` | Today's "config storage" — exact payloads to mirror into Zenoh `config/**` (see §6) |
| **Object configs** | `~ref/configs/{charuco_board, container_*, model_*, example_custom_object}.yaml` | Reusable for `vision/{pipeline}` pipelines |
| **Recordings (Rerun `.rrd`)** | `~ref/pose_estimate*.rrd`, `~ref/rays_recapture_2.rrd`, `~ref/output/rays.rrd` | Existing replayable sessions in a foreign format — useful as smoke-test targets for the MCAP recorder/replayer (record an MCAP of an equivalent session and diff the streams) |
| **Datasets** | `~ref/data/{aruco_and_tray_*, fixed_belt_view_*, recapture_*, capture_*}` | image/pose pairs at 2448×2048; first realistic CI inputs for the `camera2d` + `arm` conformance suites |
| **Docs** | `~ref/README.md` (736 lines), `~ref/agents.md` (148 lines) | Authoritative narrative on the pipeline, board geometry, and calibration numbers actually achieved |

---

## 2. Hardware truths (extracted into design-shaped config)

### 2.1 `cell.yaml` resources (per design §8.2)

```yaml
cell_type: vision-pick-cell@0.1
platform: 0.1.0
resources:
  r1:
    contract: arm
    hal: aubo_i10
    params:
      ip: 192.168.188.20
      rpc_port: 30004                 # commands
      rtde_port: 30010                # high-rate state stream
      login: { user: aubo, pass: '123456' }
      servo_cycle_s: 0.005            # falls back to SDK call when present
      joint_limit_margin_rad: 0.01    # inward clamp before validation
      ruckig_defaults:                # ~ref/aubo_cli.py:generate_ruckig_trajectory
        vmax: [1.5, 1.5, 1.5, 1.5, 1.5, 1.5]   # rad/s
        amax: [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]   # rad/s²
        jmax: [20.0, 20.0, 20.0, 20.0, 20.0, 20.0]   # rad/s³
  cam0:
    contract: camera2d
    hal: genicam
    params:
      serial: "<FLIR Blackfly S BFS-PGE-50S4C serial>"
      ip: 192.168.188.30
      mount: flange                   # eye-in-hand on r1
      pixel_format: BayerRG8          # → BGR via cv2.COLOR_BayerRG2BGR
      cti_path: "C:/Program Files/Teledyne/Spinnaker/cti64/vs2015/Spinnaker_GenTL_v140.cti"
bindings:
  vision_guided_pick:
    arm:     r1
    cam:     cam0
    gripper: r1                       # gripper hangs off arm onboard IO → dio is satisfied by r1
    frames:  { pick_area: pallet_1 }  # logical → site frame
```

> The arm satisfies the `dio` contract for its own onboard IO via `arm/r1/state/io` and
> `arm/r1/cmd/set_do` (design §2.1 — the embedded `dio` shape). A separate `io1: {contract: dio, ...}`
> resource is only declared when a standalone bus coupler is added.

### 2.2 `config/arm/r1/...` (resource descriptor + limits)

`config/arm/r1/limits` (rad — verified against `~ref/robot_model/aubo_i10/config/joint_limits.yaml`,
preferred over the wider URDF values):

```
joint                position_range          max_velocity   max_acceleration
shoulder_joint       [-2.949606, 2.949606]   3.0            2.0
upperArm_joint       [-2.949606, 2.949606]   3.0            2.0
foreArm_joint        [-3.1416,   3.1416]     2.5656         2.0
wrist1_joint         [-2.949606, 2.949606]   3.0            2.0
wrist2_joint         [-2.949606, 2.949606]   3.0            2.0
wrist3_joint         [-3.1416,   3.1416]     3.0            2.0
```

`config/arm/r1/urdf` → bundle of `~ref/robot_model/aubo_i10/aubo_i10.urdf` +
`~ref/robot_model/aubo_i10/meshes/` (STL collision, DAE visual).

### 2.3 `config/camera2d/cam0/...` (current calibration)

`config/camera2d/cam0/intrinsics` (per design §4.4):

```yaml
model: opencv_pinhole
fx: 2949.06
fy: 2949.40
cx: 1247.01
cy: 1027.37
dist: [-0.1559, 0.1669, -0.0005, 0.0008, 0.0139]   # k1, k2, p1, p2, k3
w: 2448
h: 2048
rms: 0.23                              # mean reprojection error, px
```

`config/camera2d/cam0/mount` (per design §4.4):

```yaml
type: flange                           # eye-in-hand
parent_frame: arm/r1/flange
pose: { xyz: [0.0787, 0.0493, 0.0291], quat: [-0.5005, 0.4996, 0.4976, 0.5023] }
# Andreff method, 156 views; residuals — pos_std: 1.42 mm, rot_std: 0.18 deg
```

`config/arm/r1/tcp/cam0_optical` (the same calibration, expressed as a TCP — design §4.5 unifies):

```yaml
parent: arm/r1/flange
xyz:  [0.0787, 0.0493, 0.0291]         # meters
quat: [-0.5005, 0.4996, 0.4976, 0.5023]
role: sensor
selectable_as_tcp: true                # filtered out of default picker per §4.5
source: calib
meta: { method: andreff, n_views: 156, rms_pos_m: 0.00142, rms_rot_rad: 0.00314 }
```

### 2.4 Calibration board

`~ref/configs/charuco_board.yaml`: 28 × 17 squares, 10 mm checker, 7 mm marker,
`DICT_5X5_250`, 238 markers, 432 inner corners.

### 2.5 Arm onboard IO map (current physical wiring)

Observed in `~ref/aubo_cli.py` + `~ref/pick_and_place.py`. Surfaces on the bus as
`arm/r1/state/io` and `arm/r1/cmd/set_do` (the `dio`-shaped slice of the `arm` contract):

| Pin | Function | Source |
|---|---|---|
| `do_1` (standard) | Ringlight on/off | `~ref/pick_and_place.py:462`, `~ref/aubo_cli.py:cmd_autotune:961` |
| `do_3` + `do_11` (standard) | Gripper close / open pneumatic valve pair | `~ref/pick_and_place.py:50–59` (note: `~ref/README.md:509` says DO13 — verify on hardware before encoding into a future `gripper` contract) |

Channel counts: 16 standard DI/DO, 4 tool DI/DO, 2 standard AI/AO, 2 tool AI.

---

## 3. Section-by-section design ↔ reference mapping

### §2.1 Layered model — `core`, `contracts/*`, `hal/*`

| Design layer | What to lift from reference | Notes |
|---|---|---|
| L0 `core.frames` (transform math) | `~ref/utils.py` § "Quaternion/Rotation Conversions" + "Transformation Matrix Helpers": `quaternion_to_rotation_matrix`, `rotation_matrix_to_quaternion`, `make_transform`, `decompose_transform`, `invert_transform`, `rvec_tvec_to_transform`, `transform_to_rvec_tvec`, `pose_to_transform`, `rotation_matrix_to_euler_xyz` | Drop-in primitives. Inputs/outputs are bare matrices; the surrounding `{frame, xyz, quat}` payload shape and the structured errors (§4.5) are new. |
| L0 `core.resolver` (frame tree, time-aware) | — | New. Math in `core.frames`; the tree, TTL, ownership and `resolve(target, source, t) → pose` per §4.5 are new. |
| L0 `core.codecs` (CBOR) | — | New. Today: YAML + OpenCV FileStorage + JSON. |
| L0 `core.action` (server/client, lifecycle) | — | New. Closest analogue is `cmd_move`'s validate-then-execute pattern + `wait_arrival`/`wait_pathbuffer_finished`. |
| L0 `core.registry` + liveliness | — | New (Zenoh liveliness tokens). |
| L1 `contracts/arm` schemas | Field shapes visible in `~ref/aubo_cli.py`: `getRobotState().getJointPositions()` → `q[6]`; `mc.getTcpPose()` → SDK Euler `[x,y,z,rx,ry,rz]` (HAL converts to `{frame, xyz, quat}`); `io.getStandardDigital(In\|Out)put(i)` → 16 bits; `io.get*Analog*(i)` → float | Need to *extend* the RTDE subscription to `R1_actual_qd`, `R1_actual_current` so `state/joints` can carry `{qd, tau}` per design table §4.1. |
| L1 `contracts/camera2d` schemas | Frame payload shape: `(comp.height, comp.width)` raw Bayer + `buf.timestamp_ns` hardware timestamp; intrinsics shape in `~ref/utils.py:save_intrinsics/load_intrinsics`; hand-eye shape in `~ref/utils.py:save_hand_eye/load_hand_eye` | Today: OpenCV FileStorage YAML; design replaces with CBOR + bus. Same fields, different transport. |
| L1 `contracts/dio` | `cmd_io` in `~ref/aubo_cli.py:542` — full IO read/write surface | The single SDK exposes both standard and tool banks. Design `dio` row in §2.1 says "io state stream; set_do/set_ao"; the standard-vs-tool partition is a design extension worth carrying: `cmd/set_do {bank: standard\|tool, pin, value}`. |
| L2 `hal/aubo_i10` | `~ref/aubo_cli.py` minus the argparse layer is exactly the SDK wrapper the design calls for | See §4 below for the refactor map. |
| L2 `hal/genicam` | `~ref/live_robot_rerun.py:GigECamera` (lines 191–255) + `~ref/aubo_cli.py:_trigger_and_grab` (830) + `~ref/aubo_cli.py:cmd_autotune` (926) + `~ref/live_robot_rerun.py:enable_camera_ptp` (258) | Free-run uses `Continuous` + drain; `cmd/grab` uses `SingleFrame`. See §5 below. |
| L2 `hal/arm_sim` | `~ref/aubo_i10_fk.py` + `generate_ruckig_trajectory` in `~ref/aubo_cli.py:192` | URDF + Ruckig profile is the kinematic backbone; sim integrates the same trajectory it would stream to the controller. |
| L2 `hal/camera2d_sim` | — | New. Foundations: `~ref/robot_model/aubo_i10/meshes/` (DAE visuals), `config/camera2d/cam0/intrinsics` (rendering K). pyrender or ModernGL. |

### §4.1 Arm telemetry — keys `{realm}/arm/r1/state/...`

| Bus key | Payload (CBOR) | Reference source | Notes |
|---|---|---|---|
| `state/joints` | `{t, q[6], qd[6], tau[6]}` | `~ref/live_robot_rerun.py:rtde_thread_fn` (301) | Today only subscribes to `["timestamp", "R1_actual_q"]` at 200 Hz; extend to `["timestamp", "R1_actual_q", "R1_actual_qd", "R1_actual_current"]`. Callback uses `parser.popDouble()` + `parser.popVectorDouble()` per field, in declared order. |
| `state/flange` | `{t, pose: {frame:"arm/r1/base", xyz, quat}}` | `~ref/aubo_i10_fk.py:AuboI10FK.get_ee_transform(q)` → 4×4 (`get_ee_transform` is the SDK method name; the *frame* it returns is the flange per design naming) | Convert rotation → quaternion via `~ref/utils.py:rotation_matrix_to_quaternion`. |
| `state/tcp` | `{t, tcp_name, pose: {frame:"arm/r1/base", xyz, quat}}` | `mc.getTcpPose()` → SDK Euler ZYX `[x,y,z,rx,ry,rz]` (`~ref/agents.md` §15, `robot_state.h:321`) | Convert Euler → quat at the HAL boundary (design forbids Euler on the bus). |
| `state/io` | `{t, di: bits, do: bits, ai[], ao[]}` (dio shape, design §2.1) | `io.getStandardDigitalInput/Output(i)` × 16, `getStandardAnalogInput/Output(i)` × 2, tool variants — `cmd_io` in `~ref/aubo_cli.py:542` | Embed the `dio` payload so the same IO panel renders for `arm/r1/state/io` and `dio/io1/state/io`. Keepalive 10 Hz, edge-triggered on change. |
| `state/status` | `{mode, servo_on, estop, protective_stop, speed_scale, active_tcp, error}` | Partial today: `robot.getRobotState()` → safety mode; `rc.getTcpOffset()` → active TCP offset; speed scale set via `mc.setSpeedFraction()` | Verify SDK accessors for `protective_stop`/`estop`/`safety_mode` exist (likely on `RobotState` / `SafetyControl`) — not exercised by the reference scripts beyond `freedrive(True/False)`. |
| `state/control_owner` (lease state, §4.2) | `{client_id, user, granted_at, expires_at}` or `null` | — | New. |
| `alive` (Zenoh liveliness token) | — | — | New. |

### §4.2 Arm commands — keys `{realm}/arm/r1/cmd/...` and `action/...`

| Bus key | Payload | Reference | Notes |
|---|---|---|---|
| `cmd/set_do` | `{bank: standard\|tool, pin, value}` (bank is the design extension) | `io.setStandardDigitalOutput(pin, bool(value))` — `~ref/aubo_cli.py:616` and `~ref/pick_and_place.py:gripper_open/close` (50) | Direct map. Reject writes when caller doesn't hold the control lease. |
| `cmd/set_tcp` | `{name}` (selects from TCP store) | `~ref/aubo_cli.py:resolve_tcp` (1095) + `~ref/tcp_configs.json` | Today: `flange` (identity), `camera` (from hand-eye), plus user-defined entries in `tcp_configs.json`. Bus contract selects by name; `T_flange_tcp` lives in `config/arm/r1/tcp/{name}`. |
| `cmd/set_speed_scale` | `{scale}` ∈ [0, 1] | `mc.setSpeedFraction(0..1)` | Clamp at HAL boundary (design §1 non-goals). |
| `cmd/stop` | `{}` (category-2 stop / abort current goal) | `mc.moveStop()` — `~ref/pick_and_place.py:489` | Direct map. Active goal transitions to `aborted`. |
| `cmd/jog` | `{frame, dq[6]\|dxyzrpy[6], speed_scale}` @ 10–20 Hz while held | **Not in reference.** Closest is `cmd_freedrive` (`~ref/aubo_cli.py:391`) which enables physical pushing — entirely different semantics. | New: 250 ms watchdog + control lease (design §4.2 safety) built from scratch in the HAL. |
| `cmd/acquire_control` | `{client_id, user, ttl_s}` → `{granted: bool, lease}` | — | New. |
| `action/execute_path` — `movej` waypoints | goal: `[{type:"movej", target:{q[6]}, speed, accel, blend_radius}]` → `{goal_id}` | `~ref/aubo_cli.py:cmd_move` (452) → `generate_ruckig_trajectory` → `execute_trajectory` (path buffer) | Lift wholesale into the action handler. Trajectory validation against joint limits (`validate_trajectory`, line 331) already there. Use `wait_arrival` + `getExecId()` polling to drive progress feedback. |
| `action/execute_path` — `movel` waypoints | goal target: `{frame, pose:{xyz, quat}}` resolved at acceptance (§4.5) | `~ref/aubo_cli.py:cmd_movel` (1136) | Frame-resolution-at-acceptance is *already implemented*: lines 1158–1209 take `{frame, offset}` + `{tcp}` and compute `T_base_flange = T_base_tcp @ inv(T_flange_tcp)` for `moveLine`. |
| `action/execute_path` — `movec` waypoints | — | — | Not in reference. Aubo SDK has `moveCircle`; add when needed. |
| `action/{goal_id}/feedback` (pub, best-effort) | `{progress, current_wp, state}` | — | New (lifecycle per Appendix A). |
| `action/{goal_id}/result` (pub + queryable, 60 s cached) | `{ok, error?, execution_snapshot}` | — | New. |
| `action/cancel` | `{goal_id}` | `mc.moveStop()` | Same handle as `cmd/stop`; cancel → `canceled`; protective stop → `aborted`. |

### §4.3 Cameras + vision — keys `{realm}/camera2d/cam0/...` and `vision/{pipeline}/...`

| Bus key | Payload | Reference | Notes |
|---|---|---|---|
| `image` (pub) | Zenoh attachment `{t_capture, frame_id, w, h, encoding, exposure, gain, seq}`, body = raw or JPEG bytes | `~ref/live_robot_rerun.py:GigECamera.grab()` (219) — returns `(frame, ts_ns)`; JPEG via `cv2.imencode` (`~ref/export_rerun.py:publish_image`) | All header fields available: `t_capture` ← `buf.timestamp_ns` (via `TimeSynchronizer`), `w/h` from `comp.height/width`, `encoding` is `BayerRG8`, `exposure`/`gain` from `nm.ExposureTime.value` / `nm.Gain.value`. `seq` added by HAL. |
| `image/preview` (pub, ~15 Hz JPEG) | downscaled JPEG | `~ref/live_robot_rerun.py:publish_thread_fn` (461) — `publish_image(cam_frame, jpeg_quality=75)` | Use same quality default; downscale ~1/4 in HAL before publishing. |
| `cmd/configure` (queryable) | `{exposure_us?, gain_db?, auto_exposure?, auto_gain?, auto_wb?, wb_red?, wb_blue?, trigger_mode?, roi?}` | `~ref/aubo_cli.py:cmd_capture` (712–747) shows the GenICam node-write pattern: `nm.ExposureAuto`, `nm.ExposureTime.value`, `nm.GainAuto`, `nm.Gain.value`, `nm.BalanceRatioSelector`, `nm.BalanceRatio.value` | Also: `~ref/aubo_cli.py:cmd_autotune` (926) drives `ExposureAuto = 'Once'` then `GainAuto = 'Once'` then `BalanceWhiteAuto = 'Once'` **sequentially** (parallel "Once" modes fight). |
| `cmd/grab` (queryable) | reply = full-res image (same attachment shape as `image`) | `~ref/aubo_cli.py:_trigger_and_grab` (830) — the canonical clean-grab pattern: `AcquisitionMode='SingleFrame'`, `ia.start()` arms, `ia.fetch(timeout)` returns exactly one fresh exposure, `ia.stop()` resets | Use verbatim. Continuous + drain (`_grab_frame`, line 867) is the fallback path when preview already runs free. |
| `vision/{pipeline}/result` (pub) | `{t_capture, frame_id, items[], debug_overlays?}` | `~ref/inference_package/inference.py:predict_obb` (116) returns `[{corners, score, class_id, center, size, angle_deg}, ...]` | Direct serialize into `items[]`. |
| `vision/{pipeline}/overlay` (pub) | rerun-style primitives `{space: "camera2d/cam0/image" \| "3d", frame, primitives:[{type:"rect"\|"text"\|"points3d"\|...}]}` | Today: `~ref/inference_package/inference.py:draw_detections` (265) burns annotations into pixels (`cv2.polylines`). | **Change for design**: emit primitives as data, let UI render. The pose-estimation scripts already do this — see `~ref/export_rerun_ray_pose.py:publish_rays/publish_object_pose_axes/publish_object_box`. |
| `vision/{pipeline}/cmd/run_once` (design extension) | `{}` → `{result}` | `~ref/pick_and_place.py:527–530` calls `predict_obb` once on demand | Design extension: §4.3 defines streaming `result`, but on-demand triggering needs a queryable. Add per pipeline. |

### §4.4 Configuration store — direct payload mapping

| Bus key | Existing file (today) | Payload today | Design delta |
|---|---|---|---|
| `config/frames/{name}` | `~ref/saved_frames.json` (entries today: `CNYP34X137`, `CNYVPP08LY`, `CNYLK0RLJ7` — cryptic taught IDs) | `{position: [x,y,z], quaternion: [qx,qy,qz,qw]}` | Rename payload to `{parent, pose: {xyz, quat}, source, meta}`. Add `parent` (default `world`), `source: cad\|manual\|calib\|touch_off`. On import, rename cryptic IDs to design's flat names (`pallet_1`, `fixture_a`, …) — the old name can stay in `meta.legacy_id`. |
| `config/arm/r1/tcp/{name}` | `~ref/tcp_configs.json` (user TCPs) + `~ref/output/hand_eye.yaml` (becomes `cam0_optical`) | `{translation: [x,y,z], quaternion: [qx,qy,qz,qw]}` | Rename payload to `{parent: "arm/r1/flange", xyz, quat, role: tool\|sensor\|virtual, selectable_as_tcp, mass?, cog?, source, meta?}`. Hand-eye output writes here as `cam0_optical` with `role: sensor, selectable_as_tcp: true`. |
| `config/arm/r1/urdf` | `~ref/robot_model/aubo_i10/aubo_i10.urdf` + `meshes/` | URDF with `package://aubo_description/meshes/aubo_i10/<link>.{STL,DAE}` references | UI needs the mesh blobs too (content-addressed URL or bundled in the storage). `~ref/aubo_i10_fk.py:get_mesh_paths` enumerates them. |
| `config/camera2d/cam0/intrinsics` | `~ref/output/intrinsics.yaml` (OpenCV FileStorage) | `{camera_matrix (3×3), dist_coeffs, image_width, image_height, reprojection_error, num_images_used}` | Add `model: "opencv_pinhole"`, rename fields: `K`, `dist`, `w`, `h`, `rms` (= `reprojection_error`). See §2.3 above for the converted block. |
| `config/camera2d/cam0/mount` | Implicit today — hand-eye result is co-located in `~ref/output/hand_eye.yaml` | `T_ee_camera` 4×4 + `translation` + `quaternion_xyzw` | Design shape: `{type: flange\|world, parent_frame, pose: {xyz, quat}}`. Eye-in-hand → `type: flange, parent_frame: arm/r1/flange`. Fixed-camera variant needs `cv2.calibrateRobotWorldHandEye` (not yet used). See §2.3 above for the converted block. |
| `config/programs/{name}` | `~ref/poses.json` (joint-only saved poses) | `{name: [q0..q5]}` | Design wants full waypoint programs (`movej`/`movel`/`movec`, blend radii, frame refs, per-move speed). Today's poses are a degenerate subset (single-waypoint `movej` programs). |
| `config/scene/{name}` | `~ref/configs/container_*.yaml` + `~ref/3991-6636-1200.json` "model with locations" | various ad-hoc geometry + location lists | New for the bus. Design shape per §4.4: `{frame, pose: {xyz, quat}, geometry}`. |
| `config/camera2d/cam0/profiles/{name}` (design extension) | `~ref/camera_profiles.json` (entries: `person`, `board`, `filter`) | `{exposure, gain, wb_red, wb_blue}` | §4.4 doesn't list profiles, but `~ref/pick_and_place.py` proves the operational need (`pick_profile`, `place_profile`). Promote to a `config/camera2d/{cid}/profiles/{name}` namespace, populated by the autotune action. |

### §4.5 Frames as first-class citizens

| Capability | Reference | Notes |
|---|---|---|
| Frame storage (static + flange-parented) | `~ref/saved_frames.json` (static) + `~ref/tcp_configs.json` (parent = `arm/r1/flange`) | The split exists; resolver unifies them into one tree rooted at `world`. |
| Resolver math (single hop) | `~ref/aubo_cli.py:cmd_movel` (1136) — `{frame, offset_local}` + `{tcp}` → flange target via `T_base_flange = T_base_tcp @ inv(T_flange_tcp)` | Lift the formula into `core.resolver.resolve(target, source, t) → pose`; extend to arbitrary chains; add cycle detection + ownership checks. |
| "Look at frame origin" orientation hint | `~ref/aubo_cli.py:cmd_movel` lines 1187–1193 — `R_base_tcp` column construction `[+frame_X, -frame_Y, -frame_Z]` for camera-pointing-down | Reuse as the UI's default orientation when adding a waypoint inside a frame. |
| Touch-off teach (3-point) | — | New per design §4.5. Pattern: jog to origin → `+X` → `+XY` point, sample `state/flange` at each, compute `T_base_frame`. |
| Dynamic frames (vision-published) | `~ref/pick_and_place.py:pixel_to_world` (64) + `compute_gripper_rz` (108) — project a 2D detection into base coords given `state/flange` at `t_capture` | Result becomes a `{realm}/frames/pallet_1` publish parented to `world` (or whatever site frame applies). Plumbing trivial; the *contract* (TTL, confidence, ownership) is the new work. |
| Time-aware lookup (ring buffer) | — | New. RTDE @ 200 Hz is plenty; `TimeSynchronizer` already gives the correct wall-clock for `t_capture`. |
| Frame provenance / event log entry on write | `~ref/aubo_cli.py:cmd_save_frame` prints to stdout; no log | New. Tie into `{realm}/events` (§4.6). |
| TCP `role` filter (`tool`/`sensor`/`virtual`) | — | New per §4.5. `cam0_optical` is `role: sensor, selectable_as_tcp: true` — selectable for calibration/debug, filtered out of default operator TCP picker. |
| Structured errors (`FrameUnknown \| FrameStale \| FrameLowConfidence \| NoPathToRoot`) | — | New. |

### §4.6 Cell event log — `{realm}/events`

Today: no event stream. The closest artifact is `~ref/pick_and_place.py` writing `output/pick_and_place_<ts>/run_summary.json`
(line 803). That summary becomes one event of kind `program.finished` with the same fields.

Event kinds to emit from the reference flows when migrated:
- `control.acquired` / `control.released` — from lease state changes
- `program.started` / `program.finished` / `program.aborted` — wrapping `execute_path` action lifecycle, carrying `execution_snapshot_id`
- `frame.updated` — every `config/frames/*` PUT (also dynamic frame publish above a confidence delta)
- `calibration.written` — at the end of every `calib/action/intrinsics` or `calib/action/hand_eye`
- `protective_stop` / `estop` — from `state/status` transitions
- `driver.reconnect` — from liveliness token re-assertion
- `speed_scale.changed` — from `cmd/set_speed_scale`
- `recording.mark` — from `recording/cmd/mark`

### §5 Services — file-by-file refactor map

#### 5.1 `aubo_driver` (`hal/aubo_i10`)

| Target service piece | Reference origin | Refactor verb |
|---|---|---|
| RPC connect/login | `~ref/aubo_cli.py:connect` (68) + `~ref/live_robot_rerun.py:connect_robot` (816) | **Lift** — wrap as `AuboSession` context manager inside `hal/aubo_i10/sdk.py`. |
| Command worker (single thread) | `~ref/aubo_cli.py:cmd_move/cmd_movel/cmd_io/...` (argv-serialized today) | **Build** the queue. Handlers are these `cmd_*` bodies minus argparse. |
| State publisher thread | `~ref/live_robot_rerun.py:rtde_thread_fn` (301) | **Lift** — replace `with state.lock: state.X = ...` with Zenoh `pub.put(...)`. |
| Trajectory execution | `~ref/aubo_cli.py:execute_trajectory` (360) + `wait_pathbuffer_finished` (168) | **Lift verbatim**. Per-50-sample chunk append already there; emit `action/{goal_id}/feedback` from the loop. |
| Joint limit guard | `~ref/aubo_cli.py:get_joint_limits` (92) + `validate_trajectory` (331) | **Lift**. `JOINT_LIMIT_MARGIN = 0.01` rad. |
| Ruckig planner | `~ref/aubo_cli.py:generate_ruckig_trajectory` (192) | **Lift verbatim**. Corner-blend velocity heuristic on lines 250–299 is non-obvious math, do not re-derive. |
| Control lease + jog watchdog | — | **New**. |
| Liveliness | — | **New** — Zenoh tokens. |

#### 5.2 `camera_driver` (`hal/genicam`)

| Piece | Reference | Notes |
|---|---|---|
| Camera open + GenTL setup | `~ref/live_robot_rerun.py:GigECamera.__init__` (194) | `Harvester().add_file(cti).update().create(idx)` |
| Free-run grab loop | `~ref/live_robot_rerun.py:camera_thread_fn` (347) + `GigECamera.grab` (219) | Continuous mode; publish `image` + attach hardware ts. |
| Preview JPEG | `~ref/export_rerun.py:publish_image` (called with `jpeg_quality=75`) | `cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, q])`, then publish on `image/preview`. |
| `cmd/grab` synchronous | `~ref/aubo_cli.py:_trigger_and_grab` (830) | SingleFrame mode — briefly stop the free-run loop, switch mode, trigger, return, switch back. Coordinate via a per-camera mutex. |
| `cmd/configure` | `~ref/aubo_cli.py:cmd_capture` (712–747) + `cmd_autotune` (926) | Sequential auto-modes mandatory (Exposure → Gain → WB). Don't expose "auto everything at once" — oscillates. |
| Hardware timestamp → host time | `~ref/live_robot_rerun.py:TimeSynchronizer.camera_time` (161) | `buf.timestamp_ns` paired with `time.time()` at first frame. PTP path: `enable_camera_ptp` (258) sets `GevIEEE1588=True`, polls `GevIEEE1588Status` for `'Slave'`. Emit with `clock_domain: camera_hw` (or `host` if no PTP). |
| Multi-camera | — (today single FLIR @ idx 0) | The Harvester `device_info_list` enumerates serials; second camera = a second `cam1: {contract: camera2d, hal: genicam, params: {serial: ..., mount: flange\|world}}` entry in `cell.yaml` and a second HAL process. |

#### 5.3 `sim_robot` (`hal/arm_sim`)

Foundation: `~ref/aubo_i10_fk.py` (FK) + `~ref/aubo_cli.py:generate_ruckig_trajectory` (joint-space
profile). Sim = "integrate the Ruckig output at `servo_cycle_s` instead of streaming to the controller".
Publish identical state keys at the same rates. Mirror-mode subscribes to `live/arm/r1/state/joints`
and shadows it (= what replay drives, per §5.3).

#### 5.4 `sim_camera` (`hal/camera2d_sim`)

Not in reference. Foundations: `~ref/robot_model/aubo_i10/meshes/` (DAE visuals), the calibrated
intrinsics block from §2.3, the `cam0_optical` TCP for eye-in-hand pose. Offscreen renderer
(pyrender or ModernGL) → publishes the same `image`/`image/preview` keys.

#### 5.5 `calibration` service

| Action | Reference | Lift / refactor |
|---|---|---|
| `calib/action/intrinsics` | `~ref/calibrate_intrinsics.py:detect_charuco_corners` (32) + `calibrate_camera` (119) | **Lift the math.** Replace `load_dataset` loop with `camera2d/cam0/cmd/grab` queryable calls accumulating in memory. Persist result via `save_intrinsics` → `config/camera2d/cam0/intrinsics`. Emit `calibration.written` event. |
| `calib/action/hand_eye` (eye-in-hand) | `~ref/calibrate_hand_eye.py:estimate_board_poses` (58) + `run_hand_eye_calibration` (126) + `validate_hand_eye` (189) | **Lift.** Per pose: `camera2d/cam0/cmd/grab` + settled read of `arm/r1/state/flange` (via resolver at `t_capture`). Solver: `cv2.calibrateHandEye` method `andreff` (best on this dataset, `~ref/agents.md` §98). Write both `config/camera2d/cam0/mount` AND `config/arm/r1/tcp/cam0_optical`. |
| Fixed-camera variant | — | `cv2.calibrateRobotWorldHandEye` — math not yet exercised; surrounding harness identical. Writes `config/camera2d/{cid}/mount {type: world, parent_frame: world}` instead of a TCP. |
| Replay-driven recompute | — | Possible once recorder/replayer land: replay `image` payloads + `state/flange` at correct timestamps, rerun the solver. The ChArUco detector improving is exactly the use case design §5.5 calls out. |

**Method comparison** (`~ref/calibrate_hand_eye.py:387` `--compare-methods`): runs all 5 methods and
picks the best by position std — keep as an option in the calibration UI.

#### 5.6 `recorder` (MCAP)

The reference has no MCAP; it has Rerun `.rrd` files (`~ref/pose_estimate*.rrd`, `~ref/rays_recapture_2.rrd`).
Useful as a smoke-test target: record an MCAP from a session that we already have an `.rrd` of and
check the joint/image streams align frame-for-frame.

What's already in the reference that informs the recorder:
- Per-message timestamp duality (device time + host time) — `~ref/live_robot_rerun.py:TimeSynchronizer`.
- Channel-per-key idea is anticipated by Rerun's "entity path" model in `~ref/export_rerun.py`.

#### 5.7 `replayer`

Nothing in the reference plays this exact role. The semantics (rewrite `live/**` → `replay/{session}/**`,
honor inter-message timing, publish `replay/{session}/clock`) are new.

#### 5.8 `task_runner` + skills

`~ref/pick_and_place.py` is the reference body for **what a skill looks like end-to-end**. Concrete
decomposition for `skills/vision_guided_pick`:

| BT leaf | Reference lines | Bus call it becomes |
|---|---|---|
| MoveAboveFrame (camera optical TCP) | 506–511 (`mc.moveLine(cam_pick_flange, ...)`) | `arm/r1/action/execute_path` with `[{type:"movel", target:{frame:"pick_area", pose:{xyz:[0,0,cam_z],quat:identity}}, tcp:"cam0_optical"}]` |
| ConfigureCameraProfile (pick) | 514–515 (`apply_camera_profile(nm, pick_profile_settings)`) | `camera2d/cam0/cmd/configure {profile: pick}` (resolves to exposure/gain/wb from `config/camera2d/cam0/profiles/pick`) |
| Grab | 518–524 (`_trigger_and_grab(ia)` + `cv2.imwrite`) | `camera2d/cam0/cmd/grab` (reply image is also recorded into MCAP by the recorder) |
| Detect | 527–530 (`predict_obb(model, pil_img, threshold)`) | `vision/obb_picker/cmd/run_once` → reply `{items[...]}` |
| ValidateDetection | 536–552 (count + size gates) | Pure logic leaf |
| PixelToWorld | 559–569 (`fk.get_ee_transform` + `pixel_to_world`) | Resolver `resolve(target="arm/r1/flange", source="world", t=t_capture)` + `core.pixel_ray_to_plane()` helper |
| ComputePickOrientation | 571–576 (`compute_gripper_rz`) | Pure logic |
| OpenGripper | 597–600 (`gripper_open(io)`) | `arm/r1/cmd/set_do {bank:"standard", pin:11, value:true}` + `{pin:3, value:false}` (later: `gripper/g0/cmd/release` when a `gripper` contract exists) |
| ApproachPick (gripper TCP) | 605–611 | `arm/r1/action/execute_path` movel to approach height, `tcp:"gripper"` |
| DescendToPick | 613–619 | `execute_path` movel at v×0.5 |
| CloseGripper | 621–624 | `arm/r1/cmd/set_do` toggles (same as OpenGripper, inverted) |
| AscendApproach | 626–631 | `execute_path` movel |
| (place phase mirrors pick) | 643–763 + symmetry refinement at 668–711 | Same pattern + `vision/symmetry_refiner/cmd/run_once` |
| RunSummary | 803–820 | `{realm}/events` entry `program.finished` |

**Skill params** (from `~ref/pick_and_place.py:209` argparse) — become the `params:` block of
`skills/vision_guided_pick/skill.yaml` per design §8.2:

- `cam_z_m`, `approach_z_m`, `pick_z_m`, `place_z_m`
- `pick_profile`, `place_profile`
- `min_size`, `max_size`, `threshold`
- `pitch_m` (symmetry refinement)
- `settle_time`, `speed_fraction`, `velocity`, `acceleration`, `gripper_dwell`

**Role bindings** (design §8.2 shape) — see §2.1 cell.yaml above. Logical frame `pick_area` binds to
site frame `pallet_1` (the cryptic `CNYP34X137` from `~ref/saved_frames.json` becomes `pallet_1` on
import; the old name lives in `meta.legacy_id`).

#### 5.9 Web bridge

Reference has no web UI; the design's "zenoh-ts in the browser, talking to the router's remote-api
plugin" is brand new. The Rerun viewer in `~ref/live_robot_rerun.py` is the closest visualization
analog (different transport, different render stack).

### §6 Data model — convention check

| Convention | Reference state | Action |
|---|---|---|
| Position in meters | ✓ — `~ref/utils.py:load_pose_yaml` (304), `~ref/aubo_cli.py:cmd_movel` (mm→m at 1172) | Keep. |
| Quaternion as `quat = [qx, qy, qz, qw]` | ✓ — `~ref/saved_frames.json`, `~ref/tcp_configs.json`, `~ref/utils.py:rotation_matrix_to_quaternion` | Rename field on the bus to `quat` (today: `quaternion`, `quaternion_xyzw`, `orientation`). |
| Pose payload = `{frame, xyz, quat}` | Partial — `~ref/aubo_cli.py:cmd_movel --frame` carries it; `state/tcp` source is SDK Euler in base | Centralize the Euler → quat conversion at the `hal/aubo_i10` boundary. |
| Timestamp = int nanoseconds | Mixed — `time.time()` (s float) for host, `buf.timestamp_ns` for camera (ns), `getControlSystemTime()` (ns) for arm controller. `TimeSynchronizer` normalizes to s float. | Promote to int ns on the bus; synchronizer math stays. |
| `clock_domain ∈ {host, camera_hw, robot_controller, replay}` | Implicit in `TimeSynchronizer` (`ptp_mode` flag, two epochs) | Make the enum explicit on the wire. |
| `t_capture` = exposure midpoint | `buf.timestamp_ns` is *end of exposure* on FLIR Blackfly | Subtract `exposure_us / 2 × 1e3` in the HAL before stamping `t_capture`. |
| `goal_id` = UUIDv7 | — | New. |

### §7 UI panels — what the reference already proves works

| Panel | Reference signal |
|---|---|
| 3D viewport | `~ref/export_rerun.py:publish_robot_meshes_static` + `publish_robot_transforms` drive an R3F-equivalent view from URDF + joint stream. DAE meshes look correct on this Aubo. |
| Camera frustum | `~ref/export_rerun.py:publish_calibration(K, w, h, depth)` — Rerun renders the pinhole frustum from `K` directly. Mirror as a Three.js helper parameterized the same way. |
| Trajectory preview ("ghost path") | `~ref/aubo_cli.py:generate_ruckig_trajectory` runs entirely offline — invoke for preview without `execute_trajectory`. Design's `plan_preview` queryable wraps this. |
| IO panel | `~ref/aubo_cli.py:cmd_io` no-arg branch (lines 550–579) is the layout: DI lamps × 16, DO toggles × 16, AI/AO gauges × 2, tool DI/DO × 4, tool AI × 2. |
| Frame manager | `~ref/aubo_cli.py:cmd_list_frames` (1293) + `~ref/saved_frames.json` provides 80% — needs the provenance + role badges from §4.5. |
| Calibration wizard | Coverage heatmap not yet implemented; ChArUco per-image corner detection in `~ref/calibrate_intrinsics.py:32`. Heatmap = 2D histogram of corner pixel positions across used views. |
| Camera pane | `~ref/export_rerun.py:publish_image` does JPEG + auto-display; bus pattern is the same payload, browser-side `<img>` or a `Blob`. |

### §9 Risks — reference baselines

| Risk (design §9) | What the reference tells us |
|---|---|
| Arm state rate & jitter | 200 Hz proven by `~ref/live_robot_rerun.py:rtde_thread_fn:331` (`setTopic(..., 200, 0)`). Publish the achieved rate in `state/status`. |
| Raw GigE bandwidth | 2448 × 2048 BayerRG @ 1 byte/px = 5 MB/frame. At 15 fps that's 75 MB/s on the wire — keep raw on the wired NIC, JPEG-preview ~10× for the browser. |
| Hand-eye accuracy | 1.42 mm pos std, 0.18° rot std (Andreff, 156 views). Set this as the conformance pass threshold. |
| Sim/real motion-timing parity | Ruckig profile semantics (`vmax/amax/jmax`) match the controller's path buffer — `hal/arm_sim` integrating the same trajectory is the right starting point. |

---

## 4. `hal/aubo_i10` package layout — refactor map

Translate the CLI into a library inside the HAL package (no Aubo-specific code leaks into `core`,
per design §2.1 L0):

```
hal/aubo_i10/
  __main__.py          # the running process — registered in design §5.1 as `aubo_driver`
  sdk.py               # AuboSession wrapper around pyaubo_sdk RPC
  rtde.py              # RtdeStream — 200 Hz state subscriber
  trajectory.py        # ruckig_trajectory + validate
  fk.py                # AuboI10FK (URDF parser → per-link 4×4) — lifted from ~ref/aubo_i10_fk.py
  timesync.py          # TimeSynchronizer (arm-controller epoch ↔ host)
```

```
hal/aubo_i10/sdk.py — AuboSession
  AuboSession(ip, rpc_port, login)             ← ~ref/aubo_cli.py:connect/disconnect
    .joint_limits()                              ← get_joint_limits
    .servo_cycle()                               ← get_servo_cycle
    .joint_positions()                           ← getRobotState().getJointPositions()
    .tcp_pose_sdk()                              ← mc.getTcpPose() → SDK Euler ZYX (HAL converts to {frame, xyz, quat})
    .tcp_offset_sdk()                            ← rc.getTcpOffset()
    .io.read_di/do/ai/ao/tdi/tdo/tai             ← all io.* getters from cmd_io
    .io.write_do(bank, pin, value)               ← setStandardDigitalOutput / setToolDigitalOutput
    .io.write_ao(pin, value)                     ← setStandardAnalogOutput
    .set_speed_scale(s)                          ← mc.setSpeedFraction
    .stop()                                      ← mc.moveStop
    .freedrive(on)                               ← getRobotManage().freedrive
    .controller_time_ns()                        ← rpc.getSystemInfo().getControlSystemTime
    .move_joint(q[6])                            ← move_to_joint (blocking via wait_arrival)
    .move_line_sdk(pose_zyx_euler[6], accel, vel, blend=0, dur=0)   ← mc.moveLine
                                                  # HAL accepts {frame, xyz, quat}; converts here
    .execute_path_buffer(samples, name, vmax, amax)  ← execute_trajectory
```

```
hal/aubo_i10/rtde.py
  RtdeStream(ip, fields=["timestamp","R1_actual_q","R1_actual_qd","R1_actual_current"], hz=200)
    .start(on_sample)                            ← rtde_thread_fn pattern
    .stop()
```

```
hal/aubo_i10/trajectory.py
  ruckig_trajectory(waypoints, dt, vmax, amax, jmax, blend_mm=None)  ← generate_ruckig_trajectory verbatim
  validate(traj, jmin, jmax, margin=0.01)                              ← validate_trajectory verbatim
```

Then the process entrypoint:

```
hal/aubo_i10/__main__.py — service body (= aubo_driver per design §5.1)
  - load cell.yaml resource entry for r1 → ip, ports, params
  - open Zenoh session in realm from env (live | sim | replay/...)
  - assert liveliness token at {realm}/arm/r1/alive
  - publish resource descriptor at {realm}/registry/r1 (contract: arm, hal: aubo_i10, capabilities, limits)
  - start RtdeStream → publish state/joints (+ derive state/flange via fk, state/tcp via sdk + Euler→quat)
  - start IO poller → publish state/io (dio shape; edge + 10 Hz keepalive)
  - start status poller → publish state/status, state/control_owner
  - declare cmd/* queryables: set_do, set_tcp, set_speed_scale, stop, jog, acquire_control
  - declare action/execute_path with the Appendix-A lifecycle
  - serialize all commands through a single threading.Queue consumed by one worker
    (Aubo SDK constraint — already implicit in the CLI's argv-serialized model)
```

**Gotchas the reference proves but the design doesn't repeat:**
- `pathBufferEval` must finish (`pathBufferValid` polling, ~50 ms) before `movePathBuffer` — see `execute_trajectory` lines 380–385. Don't skip the wait.
- Chunked append at 50 samples (`execute_trajectory` line 373). Larger chunks have been observed to fail silently on some controllers.
- `moveLine` blend_radius=0 and duration=0 is "as fast as the planner allows respecting accel/vel". Set explicit blend_radius for cartesian sequences; we don't have a reference for that yet.
- `wait_arrival` polls `mc.getExecId() == -1` with 50 ms ticks — first waits for it to become non-`-1`, then waits for it to return. Two-stage poll is intentional (line 154–165).
- The reference imports `pyaubo_sdk` lazily (`def connect(): import pyaubo_sdk; ...`) so the module loads without the SDK installed. Keep this pattern in `hal/aubo_i10/sdk.py` so `contracts/arm` conformance tests can run in CI on machines without the vendor SDK.

---

## 5. `hal/genicam` package layout — refactor map

Two acquisition modes coexist on the same `ImageAcquirer`:

| Mode | When | Pattern |
|---|---|---|
| **Continuous (free-run)** | `image` / `image/preview` streams are active | `AcquisitionMode=Continuous` + `ia.start()` once + tight `fetch(timeout=1.0)` loop. Drain stale frames with `fetch(timeout=0.001)` before any read that must be fresh (`~ref/aubo_cli.py:867`). |
| **SingleFrame (triggered)** | `cmd/grab` is invoked or calibration captures | `AcquisitionMode=SingleFrame` + `ia.start()` arms exactly one exposure + `ia.fetch(timeout=5)` returns it + `ia.stop()`. No stale buffers possible. (`~ref/aubo_cli.py:830`) |

The HAL needs a small mode FSM: in Continuous, pause the loop, switch to SingleFrame, trigger,
return reply, switch back. `threading.Event` or asyncio lock.

Per-feature mapping (GenICam node → bus field):

```
ExposureAuto.value         → cmd/configure {auto_exposure: bool}
ExposureTime.value         → cmd/configure {exposure_us}         attachment header: {exposure}
GainAuto.value             → cmd/configure {auto_gain: bool}
Gain.value                 → cmd/configure {gain_db}              attachment header: {gain}
BalanceWhiteAuto.value     → cmd/configure {auto_wb: bool}
BalanceRatioSelector +
  BalanceRatio             → cmd/configure {wb_red, wb_blue}
AcquisitionMode            → driven by HAL mode FSM (not user-facing)
GevIEEE1588 + GevIEEE1588Status → params.ptp_enable in cell.yaml → enable_camera_ptp pattern
buf.timestamp_ns           → attachment header {t_capture} (minus exposure/2),
                             clock_domain: camera_hw (PTP) or host (no PTP)
```

**Profiles** (`~ref/camera_profiles.json`): promote to `config/camera2d/cam0/profiles/{name}` and
populate via the autotune action. `pick_and_place` proves the operational need (`pick_profile` ≠
`place_profile` — different scenes, different exposure).

---

## 6. Persistent state — bus migration

Each file becomes a Zenoh storage key with the design-shaped payload:

```
~ref/tcp_configs.json          → config/arm/r1/tcp/{name}
                                  payload: {parent, xyz, quat, role, selectable_as_tcp, source, meta?}
~ref/saved_frames.json         → config/frames/{name}
                                  payload: {parent, pose: {xyz, quat}, source, meta?}
                                  rename cryptic IDs (CNYP34X137 etc.) → pallet_1, fixture_a, ...
                                  keep old name in meta.legacy_id
~ref/camera_profiles.json      → config/camera2d/cam0/profiles/{name}
                                  payload: {exposure_us, gain_db, wb_red, wb_blue}
~ref/poses.json                → config/programs/{name}
                                  payload: [{type:"movej", target:{q:[...]}, speed, accel, blend_radius}]
~ref/output/intrinsics.yaml    → config/camera2d/cam0/intrinsics
                                  payload: {model:"opencv_pinhole", K, dist, w, h, rms}
~ref/output/hand_eye.yaml      → config/camera2d/cam0/mount
                                  payload: {type:"flange", parent_frame:"arm/r1/flange", pose:{xyz, quat}}
                               → config/arm/r1/tcp/cam0_optical
                                  payload: {parent:"arm/r1/flange", xyz, quat,
                                            role:"sensor", selectable_as_tcp: true,
                                            source:"calib", meta:{method, n_views, rms_pos_m, rms_rot_rad}}
```

Migration: "read JSON/YAML, CBOR-encode with design field names, `session.put(key, payload)`". Write
a one-shot `bootstrap_config.py` to load a real cell.

---

## 7. Vision pipeline scaffold

Pieces ready to assemble. The two pose-estimation scripts are L3 candidates (full skills), the
detector + scene tracker primitives are sub-skill infrastructure:

| Component | Reference module |
|---|---|
| **Detector ABC + ArUco/Zxing/Composite implementations** | `~ref/marker_detector.py` — `MarkerDetector`, `ArUcoDetector`, `ZxingDetector`, `CompositeDetector`, `DetectedMarker` |
| **Object definitions (YAML)** | `~ref/object_definition.py` — `ObjectDefinition`, `MarkerDefinition`, `ModelTemplate` |
| **Scene tracker (EKF, bypassed but available)** | `~ref/scene_estimator.py` — `SceneEstimator`, `ObjectTracker`, `TrackerConfig.for_datamatrix()`, template discovery, marker→object routing |
| **2D reprojection windowed solver** | `~ref/export_rerun_single_frame.py:solve_windowed_pose` (sliding window, `soft_l1` loss) |
| **3D ray solver** | `~ref/export_rerun_ray_pose.py:solve_windowed_rays` + MC sensitivity for per-DOF trust |
| **Overlay primitives (port to design overlay protocol)** | `~ref/export_rerun.py` + `publish_rays/publish_object_pose_axes/publish_object_box/publish_covariance_ellipsoid` |
| **DataMatrix grid extraction** | `~ref/marker_detector.py:ZxingDetector._compute_grid_correspondences` (default on; up to 19× more constraints than 4 corners) |
| **Pixel → world (ray-plane)** | `~ref/pick_and_place.py:pixel_to_world` (64) — promote to `core.pixel_ray_to_plane` |
| **OBB detection (RF-DETR)** | `~ref/inference_package/inference.py:predict_obb` + `~ref/inference_package/checkpoint_best_ema.pth` |
| **Symmetry refinement (grid offset)** | `~ref/symmetry_refinement.py:estimate_grid_center` |

L3 candidates: `skills/locate_with_camera`, `skills/vision_guided_pick`, `skills/palletize_pattern`,
`skills/touch_off_frame`. The `services/vision` runtime hosts them; each is contract-typed and
role-parameterized per design §8.2.

---

## 8. Time + provenance

| Design concept | Reference location | Reuse note |
|---|---|---|
| `t_capture` for images | `buf.timestamp_ns` (`~ref/live_robot_rerun.py:GigECamera.grab` line 231) | Buffer hardware timestamp is *end of exposure* on FLIR Blackfly. For the exposure midpoint design prefers, subtract `exposure_us / 2 × 1e3`. |
| `t_observed` (host receive) | `time.time()` immediately after `fetch()` returns (`~ref/live_robot_rerun.py:384`) | Capture in HAL right after `fetch()` returns. |
| `clock_domain` enum | Inferred from `TimeSynchronizer`'s two epochs + `ptp_mode` flag | Make explicit on the wire: `host \| camera_hw \| robot_controller \| replay`. |
| Arm-controller clock | `rpc.getSystemInfo().getControlSystemTime()` returns ns since controller boot (`~ref/live_robot_rerun.py:133`) | Paired with `time.time()` at startup → `controller_epoch_ns`; per-sample `unified_ns = controller_epoch_ns + ctrl_uptime_ns`. Tag with `clock_domain: robot_controller`. |
| PTP path | `~ref/live_robot_rerun.py:enable_camera_ptp` (258) sets `GevIEEE1588=True` and polls `GevIEEE1588Status` for `'Slave'` | Use as the camera-side enable; the network needs a PTP master. |

---

## 9. Gotchas worth carrying forward

1. **OpenCV 4.12 removed `calibrateCameraCharuco`** — use `cv2.calibrateCamera` with manually
   constructed obj/img point lists (`~ref/calibrate_intrinsics.py:131`).
2. **Aubo `moveLine` targets the FLANGE, not the active TCP** — the controller's `TcpOffset` is not
   applied by the motion planner. Always compute `T_base_flange = T_base_tcp_desired @ inv(T_flange_tcp)`
   at the HAL boundary before calling `moveLine`. (`~ref/agents.md` §15; `~ref/aubo_cli.py:cmd_movel` 1208.)
3. **Aubo SDK Euler convention** is ZYX (`R = Rz(rz) @ Ry(ry) @ Rx(rx)`), matching
   `scipy.spatial.transform.Rotation.from_euler('xyz', [rx, ry, rz])`. Confirmed against
   `robot_state.h:321`. The bus uses `quat` everywhere; Euler stays inside `hal/aubo_i10`.
4. **Autotune must be sequential** (Exposure → Gain → WB). Parallel "Once" modes oscillate.
   (`~ref/aubo_cli.py:cmd_autotune` 969–1009.)
5. **SingleFrame mode is the only way to guarantee a fresh grab** synchronized with arm pose
   (`~ref/aubo_cli.py:_trigger_and_grab` 830 vs `_grab_frame` 867 with drain). For calibration grabs
   and `cmd/grab`, never use the continuous path.
6. **GigE buffer timestamps drift** — `TimeSynchronizer` recomputes the offset at startup. If the
   camera runs for hours, schedule periodic re-calibration or rely on PTP.
7. **Arm joint limits**: query at runtime via `getRobotConfig().getJointMaxPositions()`, fall back to
   `~ref/robot_model/aubo_i10/config/joint_limits.yaml`. The URDF has wider limits (`±3.04`) than
   MoveIt (`±2.9496`) — trust MoveIt for `shoulder_joint`/`upperArm_joint`/`wrist1_joint`/`wrist2_joint`.
8. **`daniilidis` hand-eye method is bad on this rig** — exclude from the default short-list or
   down-weight in the trust UI. Andreff is the empirical winner (1.42 mm std).
9. **`data/mixed_tray_belt_1` has bad pose frames 051–099** — when wiring datasets into CI for the
   `camera2d`/`arm` conformance suites, skip or partition.
10. **Arm onboard IO discrepancy**: README says `do_3`+`do_13` for the gripper, code uses
    `do_3`+`do_11`. Verify on hardware before encoding into a future `gripper` contract.
    (`~ref/pick_and_place.py:50–59` vs `~ref/README.md:509`.)

---

## 10. What is genuinely new (not in the reference)

Building from zero, in priority order:

1. Zenoh router config, `core` session bootstrap, CBOR codecs.
2. Action pattern (goal lifecycle, idempotency, result retention) per Appendix A.
3. Control lease (identity-bearing from day one) + jog watchdog.
4. Frame resolver subsystem with TTL, provenance, structured errors (`FrameUnknown \| FrameStale \| FrameLowConfidence \| NoPathToRoot`), time-aware ring buffer.
5. MCAP recorder + replayer (Rerun `.rrd` files are conceptually similar but not the chosen format).
6. Cell event log (`{realm}/events`, design §4.6) — today's `run_summary.json` files are the only event artifact.
7. Conformance test suite skeleton (`contracts/{arm,camera2d,dio}/conformance/`).
8. Resource descriptor + `{realm}/registry/{id}` + supervisor (§2.1).
9. UI bus citizenship (zenoh-ts or thin gateway) + R3F shell + panel plugins keyed by contract.
10. `hal/camera2d_sim` offscreen renderer.
11. `task_runner` with `py_trees` + skill role binding (§8.2).

Everything in §1–§9 above is already proven on this hardware and can be lifted with light refactoring.

---

## 11. Quick file index for week-1 work

| Want to implement | Open this first |
|---|---|
| `aubo_driver` skeleton | `~ref/aubo_cli.py:connect/disconnect/cmd_io`, `~ref/live_robot_rerun.py:rtde_thread_fn` |
| `arm/r1/action/execute_path` (movej) | `~ref/aubo_cli.py:cmd_move/generate_ruckig_trajectory/execute_trajectory/validate_trajectory` |
| `arm/r1/action/execute_path` (movel, frame-aware) | `~ref/aubo_cli.py:cmd_movel` (1136) |
| `arm/r1/cmd/set_do` queryable | `~ref/aubo_cli.py:cmd_io` lines 608–626 |
| `arm/r1/state/flange` publisher | `~ref/aubo_i10_fk.py:AuboI10FK.get_ee_transform` (the SDK method name; the *frame* is `arm/r1/flange`) |
| `camera_driver` skeleton | `~ref/live_robot_rerun.py:GigECamera`, `camera_thread_fn`, `TimeSynchronizer` |
| `camera2d/cam0/cmd/grab` | `~ref/aubo_cli.py:_trigger_and_grab` |
| `camera2d/cam0/cmd/configure` | `~ref/aubo_cli.py:cmd_capture` lines 712–747; `cmd_autotune` for the auto modes |
| `calib/action/intrinsics` | `~ref/calibrate_intrinsics.py` (whole file) |
| `calib/action/hand_eye` | `~ref/calibrate_hand_eye.py` (whole file) |
| Static frames + TCP frames + resolver v0 | `~ref/aubo_cli.py:cmd_movel/resolve_tcp/cmd_save_frame`, `~ref/saved_frames.json`, `~ref/tcp_configs.json` |
| First skill (`skills/vision_guided_pick`) | `~ref/pick_and_place.py` (whole file) — already structured as a sequence of leaves |
| URDF asset for `config/arm/r1/urdf` | `~ref/robot_model/aubo_i10/{aubo_i10.urdf, meshes/}` |
| Pose YAML seed data for replay tests | `~ref/utils.py:load_pose_yaml/load_dataset` + `~ref/data/aruco_and_tray_1/` |

---

*This document is a navigation aid, not a contract. Re-read the source before committing to any
specific snippet; the reference is being maintained alongside its own evolution. Pin a reference
commit (or copy what you lift into the platform repo with attribution) before relying on a line
number to stay stable.*
