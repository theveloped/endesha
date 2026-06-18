# Starts driver + recorder + remote-api bridge + web dev server detached, logs to deploy/logs/.
# Router is expected up already: docker compose -f deploy/compose.yaml up -d
# Stop everything: .\deploy\stop_stack.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path (Join-Path $root "deploy\logs") | Out-Null

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'aubo_i10|wf.hal.genicam|wf.services.recording|wf.services.config|zenoh-bridge-remote-api' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Namespace is the fixed "cell" token now (source mode is per-device, not a
# realm). Run ONE provider per logical device under "cell": the real aubo arm
# for r1 + genicam for cam0. (For an all-sim cell use the compose sim profile;
# running arm_sim AND aubo under "cell" would collide on cell/arm/r1/**.)
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'pixi run python -m wf.hal.aubo_i10 --cell deploy/cell.dev.yaml --resource r1 --realm cell --zenoh-config deploy/zenoh/driver-router.dev.json5 > deploy\logs\driver.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'pixi run python -m wf.hal.genicam --cell deploy/cell.dev.yaml --resource cam0 --realm cell --zenoh-config deploy/zenoh/driver-router.dev.json5 > deploy\logs\camera.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'pixi run python -m wf.services.recording.recorder --realm cell --out-dir deploy\recordings --zenoh-config deploy/zenoh/driver-router.dev.json5 > deploy\logs\recorder.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'pixi run python -m wf.services.config --dir deploy/config --zenoh-config deploy/zenoh/driver-router.dev.json5 > deploy\logs\config.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory $root -ArgumentList '/c', 'deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000 > deploy\logs\bridge.log 2>&1'
Start-Process -WindowStyle Hidden cmd -WorkingDirectory (Join-Path $root "web") -ArgumentList '/c', 'npm run dev > ..\deploy\logs\vite.log 2>&1'
Write-Host "stack starting (namespace 'cell'): aubo arm driver + camera driver (retries when the camera is off) + recorder (idle until 'wfctl record start') + config service (config/**) + bridge (ws://127.0.0.1:10000) + ui (http://localhost:5173); logs in deploy\logs\. The UI defaults to the CELL namespace. For an all-sim cell instead, use 'docker compose -f deploy/compose.yaml --profile sim up'."
