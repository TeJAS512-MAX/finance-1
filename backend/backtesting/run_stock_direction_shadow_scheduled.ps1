param(
    [string]$TaskName = ""
)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$LogPath = Join-Path $BackendRoot "data\stock_direction_shadow_schedule.log"
$CompletionPath = Join-Path $BackendRoot "data\stock_direction_shadow_schedule_complete.json"

if (-not (Test-Path $Python -PathType Leaf)) {
    throw "Project Python environment was not found: $Python"
}

Push-Location $BackendRoot
try {
    $outputLines = & $Python -m backtesting.stock_direction_shadow 2>&1
    $pythonExitCode = $LASTEXITCODE
    $outputText = $outputLines -join [Environment]::NewLine

    Add-Content -Path $LogPath -Value "[$(Get-Date -Format o)]`n$outputText"
    if ($pythonExitCode -ne 0) {
        throw "Shadow evaluation failed with exit code $pythonExitCode."
    }

    $jsonStart = $outputText.IndexOf("{")
    if ($jsonStart -lt 0) {
        throw "Shadow evaluation did not return a JSON report."
    }
    $result = $outputText.Substring($jsonStart) | ConvertFrom-Json

    if ($result.evaluation_complete -and $TaskName) {
        $completion = [pscustomobject]@{
            evaluation_complete = $true
            completed_at = (Get-Date).ToString("o")
            candidate_id = $result.candidate_id
            sessions_resolved = $result.evaluation_sessions_resolved
        }
        $temporaryCompletionPath = "$CompletionPath.tmp"
        $completion | ConvertTo-Json | Set-Content -Path $temporaryCompletionPath
        Move-Item -LiteralPath $temporaryCompletionPath -Destination $CompletionPath -Force
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Add-Content -Path $LogPath -Value "[$(Get-Date -Format o)] Removed completed task '$TaskName'."
    }
}
finally {
    Pop-Location
}
