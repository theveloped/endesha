# Starts the cell (supervisor + recorder + remote-api bridge + web) detached; logs in deploy/logs/.
# Always starts — the default overlay is a fully simulated cell (sim arm + replayed camera) that
# needs NO hardware and NO containers. Hotplug real hardware by switching a device to `live` in the
# UI device tree when it's attached, and back to sim/replay/off when you remove it.
#   .\deploy\start_stack.ps1                                   # default: sim arm + replay camera
#   .\deploy\start_stack.ps1 -Runtime deploy/runtime/dev.yaml  # start everything live (real hardware)
# This is the HOST hardware stack. Bring up ONLY the router first (the rest of
# compose is the all-sim stack and would collide):
#   docker compose -f deploy/compose.yaml up -d zenoh-router
# For the full all-simulated cell + frontend in Docker instead, just run:
#   docker compose -f deploy/compose.yaml up
# Stop everything: .\deploy\stop_stack.ps1
param([string]$Runtime = "deploy/runtime/default.yaml")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $root "deploy\logs") | Out-Null

# The default overlay's camera replays deploy/recordings/demo.mcap; generate it once if missing so
# the stack always comes up with a working camera.
if (-not (Test-Path (Join-Path $root "deploy\recordings\demo.mcap"))) {
    Write-Host "generating demo recording (deploy/recordings/demo.mcap) for the replay camera…"
    Start-Process -Wait -WindowStyle Hidden -WorkingDirectory $root cmd -ArgumentList '/c', 'pixi run python scripts/make_demo_recording.py'
}

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'wf.services.supervisor|wf.hal.aubo_i10|wf.hal.arm_sim|wf.hal.genicam|wf.hal.replay|wf.services.recording|wf.services.config|zenoh-bridge-remote-api' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$zcfg = "deploy/zenoh/driver-router.dev.json5"
# The supervisor owns the cell: it realizes cell.yaml + the overlay, spawns the
# arm/camera providers and config service, and serves the device tree
# (cmd/set_source) so sources switch live in the UI. A provider that cannot
# start is logged and left down; switch it back to sim/replay from the tree.
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.supervisor --cell deploy/cell.yaml --runtime $Runtime --realm cell --with-config --zenoh-config $zcfg > deploy\logs\supervisor.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.recording.recorder --realm cell --out-dir deploy\recordings --zenoh-config $zcfg > deploy\logs\recorder.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000 > deploy\logs\bridge.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory (Join-Path $root "web") -ArgumentList '/c', 'npm run dev > ..\deploy\logs\vite.log 2>&1'
Write-Host "stack starting (namespace 'cell', overlay $Runtime): supervisor (providers + config + device tree) + recorder (idle until 'wfctl record start') + bridge (ws://127.0.0.1:10000) + ui (http://localhost:5173); logs in deploy\logs\. Switch a device's source live in the UI device tree; hardware-free: -Runtime deploy/runtime/replay-debug.yaml."
