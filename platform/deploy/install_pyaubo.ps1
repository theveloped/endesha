# Installs the vendor pyaubo_sdk binding (0.26.0rc6) into the pixi env site-packages.
#
# The 0.26 binding exists only as an installed .pyd in the anaconda
# site-packages (the C++ SDK folder in the reference tree has no wheel).
# If the source .pyd has vanished, fall back to the older PyPI wheel:
#     pixi run python -m pip install pyaubo-sdk==0.24.1
# (cp312 win wheel; lacks moveStop — the HAL's stopMove shim covers it, but
# re-validate setTopic/getRobotInterface during the hardware smoke test.)

$ErrorActionPreference = "Stop"

$platform = Split-Path $PSScriptRoot -Parent
$source = "C:\ProgramData\anaconda3\Lib\site-packages\pyaubo_sdk.cp312-win_amd64.pyd"

if (-not (Test-Path $source)) {
    Write-Error @"
pyaubo_sdk .pyd not found at:
    $source

Fallback: install the (older) PyPI wheel instead:
    pixi run python -m pip install pyaubo-sdk==0.24.1
then re-validate setTopic/getRobotInterface during the hardware smoke test.
"@
    exit 1
}

# Resolve the pixi env's site-packages (conda python=3.12.*; ABI matches the cp312 .pyd).
& pixi run --manifest-path (Join-Path $platform "pixi.toml") python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "pixi env not found - run 'pixi install' in platform/ first"
    exit 1
}
$destDir = & pixi run --manifest-path (Join-Path $platform "pixi.toml") python -c "import site; print(site.getsitepackages()[0])"
$destDir = $destDir.Trim()

Copy-Item -Force $source $destDir
Write-Host "Installed $(Split-Path $source -Leaf) -> $destDir"
