# Stops host processes started by start_stack.ps1. Docker infrastructure is
# left running; stop it with: docker compose -f deploy/compose.yaml stop bridge zenoh-router
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'wf\.services\.supervisor|wf\.hal\.|wf\.services\.recording|wf\.services\.config|zenoh-bridge-remote-api|vite' } |
    ForEach-Object {
        Write-Host "stopping $($_.ProcessId): $($_.CommandLine -replace '\s+', ' ' )"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
