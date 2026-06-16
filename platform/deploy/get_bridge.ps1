# Builds the zenoh-ts 1.8.0 remote-api bridge (zenohd 1.8 + remote-api
# plugin statically linked) into platform/deploy/bridge/.
#
# Built from source (cargo, tag 1.8.0) because the zenoh-ts GitHub release
# zips for Windows ship only the plugin DLL — no standalone exe (verified
# for 1.8.0 and 1.9.0; the Linux zips do carry the standalone binary).
# Loading the plugin DLL into a separately-built zenohd is not an option:
# a plugin must ABI-match the router's exact build. The statically-linked
# standalone eliminates that failure class.
#
# Requires a Rust toolchain (cargo). No-cargo fallback: run the Linux musl
# standalone binary from the release zip in docker:
#     zenoh-ts-1.8.0-x86_64-unknown-linux-musl-standalone.zip -> zenoh-bridge-remote-api
#     docker run --rm -p 10000:10000 -v <dir>:/b alpine \
#         /b/zenoh-bridge-remote-api -m peer -e tcp/host.docker.internal:7447 --no-multicast-scouting --ws-port 10000
#
# Run the bridge as a peer of the phase-1 docker router (the router stays the
# hub on tcp/7447), serving ws://127.0.0.1:10000 to browsers. The ws bind
# MUST be an explicit IPv4 address: a bare port binds [::] v6-only on
# Windows and refuses ws://127.0.0.1 connections.
#
#     .\deploy\bridge\zenoh-bridge-remote-api.exe -m peer -e tcp/127.0.0.1:7447 --no-multicast-scouting --ws-port 127.0.0.1:10000
#
# Fallback (bridge cannot reach the router): run the bridge AS the router,
# replacing the docker service:
#
#     .\deploy\bridge\zenoh-bridge-remote-api.exe -m peer -l tcp/0.0.0.0:7447 --ws-port 127.0.0.1:10000

$ErrorActionPreference = "Stop"

$version = "1.8.0"
$exeName = "zenoh-bridge-remote-api.exe"

$destDir = Join-Path $PSScriptRoot "bridge"
$destExe = Join-Path $destDir $exeName
$installRoot = Join-Path $env:TEMP "wf-bridge-install"

if (Test-Path $destExe) {
    Write-Host "$exeName already present at $destExe - delete it to re-build"
    exit 0
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error @"
cargo not found - the bridge is built from source (the zenoh-ts $version
release zips for Windows contain no standalone exe). Install a Rust
toolchain (https://rustup.rs) or use the docker fallback documented in
this script's header.
"@
    exit 1
}

Write-Host "Building zenoh-bridge-remote-api $version from source (several minutes)..."
cargo install --git https://github.com/eclipse-zenoh/zenoh-ts --tag $version zenoh-bridge-remote-api --root $installRoot --locked
if ($LASTEXITCODE -ne 0) {
    Write-Error "cargo install failed (exit $LASTEXITCODE)"
    exit 1
}

$built = Join-Path $installRoot "bin\$exeName"
if (-not (Test-Path $built)) {
    Write-Error "built binary not found at $built"
    exit 1
}

New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Move-Item -Force $built $destExe
Remove-Item -Recurse -Force $installRoot

Write-Host "Installed $exeName -> $destExe"
