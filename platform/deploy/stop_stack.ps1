# Stops the detached driver / recorder / bridge / web dev server started by start_stack.ps1.
# The docker router is left running; stop it with: docker compose -f deploy/compose.yaml down
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'aubo_i10|wf.hal.arm_sim|wf.hal.genicam|wf.services.recording|wf.services.config|zenoh-bridge-remote-api|vite' } |
    ForEach-Object {
        Write-Host "stopping $($_.ProcessId): $($_.CommandLine -replace '\s+', ' ' )"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
