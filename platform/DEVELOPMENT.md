# Local development

The application stack can run almost entirely on the host. This avoids rebuilding Docker images while editing Python, TypeScript, React, configuration, or the simulated camera renderer.

The recommended Windows workflow keeps the standard Zenoh router and remote-api bridge in Docker. These are stable infrastructure containers; after their one-time image setup, start them with `--no-build`. The supervisor, HAL providers, config service, recorder, and Vite development server run locally.

## Services

| Service | Development location | Reload behavior |
| --- | --- | --- |
| Zenoh router | Docker `eclipse/zenoh:1.9.0` image | Leave running |
| Browser bridge | Docker `wf-bridge:latest` image | Leave running |
| Host API (`wf.services.host_api`, http://localhost:8080) | Pixi editable workspace | Cell registry + supervisor lifecycle; restart after Python changes |
| Supervisor and Python providers | Spawned by the host API for the ACTIVE cell | Re-activate the cell (navbar / `wfctl cell activate`) after Python or cell/runtime YAML changes |
| Config service | Spawned by the host API (realm-less, survives cell switches) | UI config edits are applied live |
| Operator UI | Local Vite | React/TypeScript/CSS HMR |
| Browser camera producer | Operator UI tab | Renderer changes follow Vite HMR |
| Headless camera | Local Puppeteer process, optional | Page follows Vite HMR; restart after launcher changes |

## Prerequisites

Install:

- Docker Desktop for the stable Zenoh router and browser bridge.
- [Pixi](https://pixi.sh/) for Python 3.12 and the editable Python workspace.
- Node.js 24 and npm.

Run the one-time application setup from the repository root:

```powershell
pixi install

Push-Location web
npm ci
Pop-Location
```

Pixi installs the workspace packages as editable packages. Python source changes therefore never require a package or image rebuild.

The Docker bridge image is also a one-time setup. If it does not exist yet, the first infrastructure start builds it. Subsequent starts use `--no-build`.


## Recommended: router and bridge in Docker

First stop the full Compose stack so its supervisor and web containers do not collide with the local processes:

```powershell
docker compose -f deploy/compose.yaml down
```

The first time, create the infrastructure containers and bridge image:

```powershell
docker compose -f deploy/compose.yaml up -d zenoh-router bridge
```

For every subsequent start, explicitly prohibit rebuilding:

```powershell
docker compose -f deploy/compose.yaml up -d --no-build zenoh-router bridge
```

Start the host application services with the interactive browser-camera simulation overlay:

```powershell
.\deploy\start_stack.ps1 `
  -Cell default -Runtime sim `
  -BridgeInDocker
```

The PowerShell script is only a convenience process launcher. With `-BridgeInDocker`, it starts:

- the host API (`wf.services.host_api`, <http://localhost:8080>): the cell
  registry (every `cell.yaml` under `deploy/`: `deploy/cell.yaml` is cell
  `default`, `deploy/<dir>/cell.yaml` is cell `<dir>`; overlays are the
  `runtime/*.yaml` next to it, `-Runtime` takes the overlay id) and the
  lifecycle of the ACTIVE cell's supervisor tree — the supervisor spawns the
  providers (simulated arm, browser-camera backend, …) and the program runner;
- the config service (owned by the host API, so it survives cell switches);
- recorder;
- Vite development server.

Without `-Cell` the host API restores the last active cell (`deploy/host.yaml`).
Switch cells from the navbar ("Cells" lists the registry; click one, pick the
overlay, Switch) or with `pixi run python -m wf.tools.wfctl cell list|activate <id> --runtime <overlay>|stop`.
Only one cell runs at a time: one bus, realm `cell`.

It does not build anything and does not start another bridge. The two Docker containers provide native Zenoh on port `7447` and the browser WebSocket endpoint on port `10000`.

Open <http://localhost:5173>, connect to `ws/127.0.0.1:10000`, open **Cameras**, and click **Start producer**. The `sim.yaml` overlay selects:

```yaml
r1: sim
cam0: browser_sim
```

### Logs

The detached launcher writes application logs under `deploy/logs/`:

```powershell
Get-Content -Wait deploy/logs/host_api.log
Get-Content -Wait deploy/logs/supervisor.log
Get-Content -Wait deploy/logs/vite.log
Get-Content -Wait deploy/logs/recorder.log
```

Read infrastructure logs through Compose:

```powershell
docker compose -f deploy/compose.yaml logs -f zenoh-router bridge
```

### Stop and restart

Stop only the local application processes:

```powershell
.\deploy\stop_stack.ps1
```

The router and bridge remain running for quick application restarts. Stop them when finished:

```powershell
docker compose -f deploy/compose.yaml stop bridge zenoh-router
```

Use the following restart loop:

- React, TypeScript, CSS, and shared camera renderer changes: no restart; Vite applies HMR.
- Python changes: run `stop_stack.ps1`, then `start_stack.ps1` again. No dependency installation or image build occurs.
- `deploy/cell.yaml` or runtime overlay changes: restart the host application processes.
- Scene, frame, TCP, and pose changes made through the UI: applied live and persisted under `deploy/config/`.
- `web/package.json` changes: rerun `npm ci` in `web/`, then restart Vite.
- `pixi.toml` or Python dependency changes: rerun `pixi install`, then restart the Python processes.

## Running without the PowerShell launcher

The script is optional. Keep `zenoh-router` and `bridge` running in Docker and run the application processes in foreground terminals instead.

### Terminal 1: host API (config service + the active cell's supervisor and providers)

```powershell
pixi run python -m wf.services.host_api `
  --deploy deploy --port 8080 --with-config `
  --activate default --runtime sim `
  --zenoh-config deploy/zenoh/driver-router.dev.json5
```

(To run a supervisor by hand instead, without the host API:
`pixi run python -m wf.services.supervisor --cell deploy/cell.yaml --runtime deploy/runtime/sim.yaml --realm cell --with-config --zenoh-config deploy/zenoh/driver-router.dev.json5`
— the navbar then shows a single cell.)

### Terminal 2: Vite development server

```powershell
Push-Location web
npm run dev
Pop-Location
```

The recorder is optional during development. Run it in another terminal when needed:

```powershell
pixi run python -m wf.services.recording.recorder `
  --realm cell `
  --out-dir deploy/recordings `
  --zenoh-config deploy/zenoh/driver-router.dev.json5
```

This foreground workflow is functionally equivalent to `start_stack.ps1 -BridgeInDocker`. Use `Ctrl-C` in each terminal to restart only the process being developed.

## Fully local mode without Docker

Rust/Cargo and the local bridge executable are needed only for this mode. Build the executable once with:

```powershell
.\deploy\get_bridge.ps1
```

Then run it as both the native Zenoh router and browser WebSocket bridge:

```powershell
.\deploy\bridge\zenoh-bridge-remote-api.exe `
  -m peer `
  -l tcp/0.0.0.0:7447 `
  --no-multicast-scouting `
  --ws-port 127.0.0.1:10000
```

Run the same supervisor and Vite terminal commands from the previous section.

## Running the autonomous headless camera locally

The normal `sim.yaml` workflow uses `browser_sim`: the operator tab owns rendering. To exercise the autonomous headless provider instead:

1. Start the local infrastructure, supervisor, and Vite as described above.
2. In **Configure → Device sources**, switch `cam0` from `browser_sim` to `sim`.
3. From the `web` directory, launch the headless page:

```powershell
node scripts/serve-camera.mjs "http://localhost:5173/headless.html?ws=ws/127.0.0.1:10000&realm=cell&cid=cam0"
```

The headless page queries the supervisor for the same `cam0` device optics, mount, scene, frame tree, joints, and flange state used by the browser producer. Renderer source changes are served by Vite; restart the Puppeteer command only when the launcher itself changes or HMR does not recover.

Use `Ctrl-C` to stop the headless process. Switch `cam0` back to `browser_sim` before starting an in-tab producer.

## Programs

Authoring reference: [PROGRAMS.md](PROGRAMS.md).

The supervisor spawns the program runner over `deploy/programs/` (any `*.py`
defining a `wf.program.Program` subclass; see `demo_pick.py`). Drive it with
`wfctl` (`--connect tcp/127.0.0.1:7447` when the router is in Docker):

```powershell
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 program-catalog
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 program-load demo_pick --param cycles=2
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 program start      # hold|unhold|stop|abort|clear|reset
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 program-state -f      # incl. what it waits for
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 program-log -f        # self.log() + runner notes
pixi run python -m wf.tools.wfctl --connect tcp/127.0.0.1:7447 dio-force part_present on   # feed the sim a part
```

Debugging a program that "does nothing": it is usually waiting. `program-state`
(and the **Waiting for** card in the Programs tool) lists, for the active
state, the channel edges, timers and events that would move it on — in sim,
force the input on the IO page.

Programs can be written in the browser: Programs tool → **new / edit** (or
**Edit** on a catalog entry) turns the right pane into an editor over
`deploy/programs/*.py` (Ctrl/Cmd+S saves; import errors show inline; Load
sends the file to the unit).

In the browser, the **Programs** tool (`http://localhost:5173/#/cell/programs`)
does the same: load with role bindings and params, Start/Hold/Stop/Reset, live
unit and program state, transition log. `http://localhost:5173/#/hmi` is the
operator page (unit state + PackML buttons only). Views are deep-linkable:
`#/cell/<tool>`, `#/replay/<sid>/<tool>`, `#/hmi`.

While a program runs it holds the cell control lease, so the UI cannot jog or
set outputs; forcing INPUTS stays possible (test override). Editing a program
file is picked up by the next `program-load`; a `python -m wf.services.program_runner`
restart is not needed.

## Other runtime overlays

| Overlay | Arm | Camera | Use |
| --- | --- | --- | --- |
| `deploy/runtime/sim.yaml` | Simulated | Browser producer | Recommended interactive development |
| `deploy/runtime/default.yaml` | Simulated | Replay | Hardware-free startup without a producer tab |
| `deploy/runtime/replay-debug.yaml` | Simulated | Replay | Recording/debug workflow |
| `deploy/runtime/dev.yaml` | Live | Live | Real AUBO and GenICam hardware |

Pass the selected file with `-Runtime` or `--runtime`.

## Other cells (the Ecoclean washer)

`deploy/ecoclean/` is a second cell: one parts washer (`washer` contract, no
arm) whose HAL also provides the raw PLC as a `tags` device. It replaces the
`ecoclean-controller` repo. Host stack:

```powershell
.\deploy\start_stack.ps1 -Cell ecoclean -Runtime sim -BridgeInDocker
# or, with the stack already running: switch in the navbar, or
pixi run python -m wf.tools.wfctl cell activate ecoclean --runtime sim
```

`runtime/sim.yaml` runs the PLC emulation at 10x speed; `runtime/live.yaml`
talks OPC-UA to `opc.tcp://192.168.0.1:4840`. Full Docker stack:
`WF_CELL=ecoclean WF_RUNTIME=sim docker compose -f deploy/compose.yaml up -d`
(or switch from the navbar / `wfctl cell activate` once it is up).
Try it: `wfctl washer-status`, `wfctl washer open_door`, `wfctl washer-recipe`,
load `ecoclean_cycle` and confirm the operator steps on the HMI page.

## Checks before committing

```powershell
pixi run python -m pytest
pixi run docs-check
pixi run wire-check

Push-Location web
npx tsc -b
npm run build
Pop-Location

docker compose -f deploy/compose.yaml config --quiet
```

`npm run build` synchronizes static assets before compiling. Stop any Docker `web` container first if Windows reports that a file under `web/public/assets` is locked.

## Full Docker stack (no host processes)

The compose stack runs everything in containers (router, bridge, the host API
on <http://localhost:8080> with the config service and the active cell's
supervisor + providers + program runner, Vite). It bind-mounts the host
`deploy/` directory, so config edits, programs written in the in-app editor and
the active cell (`deploy/host.yaml`) land in the repo either way.

```powershell
.\deploy\stop_stack.ps1                                   # never run both modes at once (ports 5173/10000)
docker compose -f deploy/compose.yaml up -d
```

Rebuild rules (the images bake dependencies, the code is bind-mounted):

- `pixi.toml` / `pixi.lock` or a NEW package under `packages/` →
  `docker compose -f deploy/compose.yaml build host-api` (builds `wf-sim`), then `up -d`.
- `web/package.json` changed → `docker compose -f deploy/compose.yaml up -d --build
  --force-recreate --renew-anon-volumes web`. The `--renew-anon-volumes` matters:
  the container masks the host `node_modules` with an anonymous volume, and a plain
  restart keeps the OLD volume even after the image was rebuilt ("Failed to
  resolve import ..." in the web container log).

## Troubleshooting

### `npm ci` fails with EPERM on `lightningcss...node`

The host Vite (started by `start_stack.ps1`) holds the file. Run
`.\deploy\stop_stack.ps1` first, then `npm ci`, then start the stack again. An
interrupted `npm ci` leaves `web/node_modules` half-deleted — always rerun it
to completion.


### UI reports `no browser producer`

Confirm `cam0` is set to `browser_sim`, then open **Cameras** and click **Start producer**. Starting a stream does not itself start the browser producer.

### UI cannot connect to the bridge

Check that exactly one process owns port `10000` and that the UI URL is `ws/127.0.0.1:10000`. Do not run the Compose bridge and local bridge simultaneously.

### Port already in use

Stop the full Compose stack and stale host processes:

```powershell
docker compose -f deploy/compose.yaml down
.\deploy\stop_stack.ps1
```

Then restart the router-and-bridge infrastructure workflow.

### `Extension context invalidated` in Chrome

This message originates from a browser extension content script, not the operator UI. Reload or disable the affected extension.

### Python edit is not visible

Python packages are editable, but running Python processes do not auto-reload. Restart the host stack; do not rebuild or reinstall dependencies.
