# Starts the cell (supervisor + recorder + remote-api bridge + web) detached; logs in deploy/logs/.
# The supervisor reads the canonical deploy/cell.yaml + a runtime overlay (default
# deploy/runtime/dev.yaml = real hardware: r1=live, cam0=live) and spawns one provider per
# device, the config service, and the always-on vision runtime. Switch a device's source
# (live/sim/replay/off) live from the UI device tree. For a hardware-free cell, pass
#   .\deploy\start_stack.ps1 -Runtime deploy/runtime/replay-debug.yaml
# Router is expected up already: docker compose -f deploy/compose.yaml up -d
# Stop everything: .\deploy\stop_stack.ps1
param([string]$Runtime = "deploy/runtime/dev.yaml")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $root "deploy\logs") | Out-Null

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'wf.services.supervisor|wf.hal.aubo_i10|wf.hal.arm_sim|wf.hal.genicam|wf.hal.replay|wf.services.vision|wf.services.task_runner|wf.services.recording|wf.services.config|zenoh-bridge-remote-api' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$zcfg = "deploy/zenoh/driver-router.dev.json5"
# The supervisor owns the cell: it realizes cell.yaml + the overlay and spawns the
# providers (arm + camera), the config service (--with-config), and the vision runtime,
# and serves the device tree (cmd/set_source) so sources switch live in the UI. A
# provider that can't start (e.g. live with no hardware attached) is logged and left
# down, not fatal — flip it to sim/replay from the tree.
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.supervisor --cell deploy/cell.yaml --runtime $Runtime --realm cell --with-config --zenoh-config $zcfg > deploy\logs\supervisor.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.recording.recorder --realm cell --out-dir deploy\recordings --zenoh-config $zcfg > deploy\logs\recorder.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000 > deploy\logs\bridge.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory (Join-Path $root "web") -ArgumentList '/c', 'npm run dev > ..\deploy\logs\vite.log 2>&1'
Write-Host "stack starting (namespace 'cell', overlay $Runtime): supervisor (providers + config + vision + device tree) + recorder (idle until 'wfctl record start') + bridge (ws://127.0.0.1:10000) + ui (http://localhost:5173); logs in deploy\logs\. Switch a device's source live in the UI device tree; hardware-free: -Runtime deploy/runtime/replay-debug.yaml."
