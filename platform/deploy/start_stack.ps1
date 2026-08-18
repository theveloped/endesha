# Starts the host application services detached; logs in deploy/logs/.
# The recommended development workflow keeps the standard Zenoh router and
# remote-api bridge in Docker, then passes -BridgeInDocker so this script starts
# only the host API (which owns the config store + the active cell's supervisor
# tree), the recorder, and Vite.
#   docker compose -f deploy/compose.yaml up -d --no-build zenoh-router bridge
#   .\deploy\start_stack.ps1 -Runtime sim -BridgeInDocker
# Cells are the cell.yaml files under deploy/ (deploy/cell.yaml = "default",
# deploy/<dir>/cell.yaml = "<dir>"); overlays are the runtime/*.yaml next to
# them. Pick another cell at start or later from the UI navbar / wfctl:
#   .\deploy\start_stack.ps1 -Cell ecoclean -Runtime sim -BridgeInDocker
#   pixi run python -m wf.tools.wfctl cell activate ecoclean --runtime sim
# Without -Cell the host API restores the last active cell (deploy/host.yaml).
#
# Without -BridgeInDocker the script starts deploy/bridge/zenoh-bridge-remote-api.exe
# locally and expects a router on tcp/127.0.0.1:7447.
# Stop host processes: .\deploy\stop_stack.ps1
# Stop Docker infrastructure: docker compose -f deploy/compose.yaml stop bridge zenoh-router
param(
    [string]$Cell = "",
    [string]$Runtime = "",
    [int]$ApiPort = 8080,
    [switch]$BridgeInDocker
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $root "deploy\logs") | Out-Null

# The default overlay's camera replays deploy/recordings/demo.mcap; generate it once if missing so
# the stack always comes up with a working camera.
if (-not (Test-Path (Join-Path $root "deploy\recordings\demo.mcap"))) {
    Write-Host "generating demo recording (deploy/recordings/demo.mcap) for the replay camera..."
    Start-Process -Wait -WindowStyle Hidden -WorkingDirectory $root cmd -ArgumentList '/c', 'pixi run python scripts/make_demo_recording.py'
}

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'wf\.services\.host_api|wf\.services\.supervisor|wf\.hal\.|wf\.services\.recording|wf\.services\.config|wf\.services\.program_runner|zenoh-bridge-remote-api' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$zcfg = "deploy/zenoh/driver-router.dev.json5"
# The host API is the machine-level control plane: it runs the config store and
# the ACTIVE cell's supervisor (which realizes cell.yaml + overlay, spawns the
# providers + program runner and serves the device tree). Switching cells is
# POST /cells/<id>/activate — from the UI navbar or wfctl.
$apiArgs = "--deploy deploy --port $ApiPort --with-config --zenoh-config $zcfg"
if ($Cell -ne "") { $apiArgs += " --activate $Cell" }
if ($Runtime -ne "") { $apiArgs += " --runtime $Runtime" }
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.host_api $apiArgs > deploy\logs\host_api.log 2>&1"
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', "pixi run python -m wf.services.recording.recorder --realm cell --out-dir deploy\recordings --zenoh-config $zcfg > deploy\logs\recorder.log 2>&1"
if (-not $BridgeInDocker) {
    Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000 > deploy\logs\bridge.log 2>&1'
}
Start-Process -WindowStyle Hidden cmd -WorkingDirectory (Join-Path $root "web") -ArgumentList '/c', 'npm run dev > ..\deploy\logs\vite.log 2>&1'
$bridgeMode = if ($BridgeInDocker) { "Docker bridge" } else { "local bridge" }
$cellMsg = if ($Cell -ne "") { "cell '$Cell'" + $(if ($Runtime -ne "") { " ($Runtime)" } else { "" }) } else { "last active cell (deploy/host.yaml)" }
Write-Host "stack starting: host API (http://localhost:$ApiPort - config store + $cellMsg) + recorder (idle until 'wfctl record start') + $bridgeMode (ws://127.0.0.1:10000) + Vite (http://localhost:5173); logs in deploy\logs\."
