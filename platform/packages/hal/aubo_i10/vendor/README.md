# Vendored Aubo SDK

`aubo_sdk-0.26.0-rc.6-Windows_AMD64+d2cc0fb/` is the vendor **C++ SDK**
distribution (DLLs, headers, CMake configs, examples) matching the Python
binding `pyaubo_sdk.cp312-win_amd64.pyd` installed by
`deploy/install_pyaubo.ps1`.

It is kept here for provenance and future C++/rebuild work. It is NOT
importable from Python and is NOT part of the `wf-hal-aubo-i10` wheel
(hatch only packages `src/wf`).

API note: this binding exposes `MotionControl.stopMove` (not `moveStop`);
`wf.hal.aubo_i10.sdk.AuboSession._motion_stop` resolves whichever exists.
