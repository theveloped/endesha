# Starts the host application services detached; logs in deploy/logs/.
# The recommended development workflow keeps the standard Zenoh router and
# remote-api bridge in Docker, then passes -BridgeInDocker so this script starts
# only the supervisor/providers/config, recorder, and Vite.
#   docker compose -f deploy/compose.yaml up -d --no-build zenoh-router bridge
#   .\deploy\start_stack.ps1 -Runtime deploy/runtime/sim.yaml -BridgeInDocker
# Another cell (e.g. the Ecoclean washer, no arm):
#   .\deploy\start_stack.ps1 -Cell deploy/ecoclean/cell.yaml -Runtime deploy/ecoclean/runtime/sim.yaml -Programs deploy/ecoclean/programs -BridgeInDocker
#
# Without -BridgeInDocker the script starts deploy/bridge/zenoh-bridge-remote-api.exe
# locally and expects a router on tcp/127.0.0.1:7447.
# Stop host processes: .\deploy\stop_stack.ps1
# Stop Docker infrastructure: docker compose -f deploy/compose.yaml stop bridge zenoh-router
param(
    [string]$Cell = "deploy/cell.yaml",
    [string]$Runtime = "deploy/runtime/default.yaml",
    [string]$Programs = "deploy/programs",
    [switch]$BridgeInDocker
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $root "deploy\logs") | Out-Null

# The default overlay's camera replays deploy/recordings/demo.mcap; generate it once if missing so
# the stack always comes up with a working camera.
if (-not (Test-Path (Join-Path $root "deploy\recordings\demo.mcap"))) {
    Write-Host "generating demo recording (deploy/recordings/demo.mcap) for the replay camera…"
    Start-Process -Wait -WindowStyle Hidden -WorkingDirectory $root cmd -ArgumentList '/c', 'pixi run python scripts/make_demo_recording.py'
}

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'wf\.services\.supervisor|wf\.hal\.|wf\.services\.recording|wf\.services\.config|wf\.services\.program_runner|zenoh-bridge-remote-api' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$zcfg = "deploy/zenoh/driver-router.dev.json5"
# The supervisor owns the cell: it realizes cell.yaml + the overlay, spawns the
# arm/camera providers and config service, and serves the device tree
# (cmd/set_source) so sources switch live in the UI. A provider that cannot
# start is logged and left down; switch it back to sim/replay from the tree.
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.supervisor --cell $Cell --runtime $Runtime --realm cell --with-config --programs $Programs --zenoh-config $zcfg > deploy\logs\supervisor.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.recording.recorder --realm cell --out-dir deploy\recordings --zenoh-config $zcfg > deploy\logs\recorder.log 2>&1"
if (-not $BridgeInDocker) {
    Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000 > deploy\logs\bridge.log 2>&1'
}
Start-Process -WindowStyle Hidden cmd -WorkingDirectory (Join-Path $root "web") -ArgumentList '/c', 'npm run dev > ..\deploy\logs\vite.log 2>&1'
$bridgeMode = if ($BridgeInDocker) { "Docker bridge" } else { "local bridge" }
Write-Host "stack starting (namespace 'cell', overlay $Runtime): supervisor (providers + config + device tree) + recorder (idle until 'wfctl record start') + $bridgeMode (ws://127.0.0.1:10000) + Vite (http://localhost:5173); logs in deploy\logs\."
