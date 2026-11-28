param(
    [string]$TaskName = ""
)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$DataDirectory = Join-Path $BackendRoot "data"
$LogPath = Join-Path $DataDirectory "stock_direction_cross_sectional_shadow_schedule.log"
$TrainingStatePath = Join-Path $DataDirectory "stock_direction_cross_sectional_shadow_schedule_state.json"
$TrainingReportPath = Join-Path $DataDirectory "stock_direction_cross_sectional_report.json"
$CompletionPath = Join-Path $DataDirectory "stock_direction_cross_sectional_shadow_schedule_complete.json"
$PriorCompletionPath = Join-Path $DataDirectory "stock_direction_shadow_schedule_complete.json"

if (-not (Test-Path $Python -PathType Leaf)) {
    throw "Project Python environment was not found: $Python"
}

if (-not (Test-Path $PriorCompletionPath -PathType Leaf)) {
    Add-Content -Path $LogPath -Value "[$(Get-Date -Format o)] Waiting for the schema-10 shadow evaluation to complete."
    exit 0
}

$priorCompletion = Get-Content -LiteralPath $PriorCompletionPath -Raw | ConvertFrom-Json
if (-not $priorCompletion.evaluation_complete) {
    throw "The schema-10 shadow completion marker is invalid."
}

Push-Location $BackendRoot
try {
    if (-not (Test-Path $TrainingStatePath -PathType Leaf)) {
        $trainingLines = & $Python -m backtesting.train_stock_direction_cross_sectional 2>&1
        $trainingExitCode = $LASTEXITCODE
        $trainingText = $trainingLines -join [Environment]::NewLine
        Add-Content -Path $LogPath -Value "[$(Get-Date -Format o)] Challenger training`n$trainingText"
        if ($trainingExitCode -ne 0) {
            throw "Cross-sectional challenger training failed with exit code $trainingExitCode."
        }

        $trainingJsonStart = $trainingText.IndexOf("{")
        if ($trainingJsonStart -lt 0) {
            throw "Cross-sectional training did not return a JSON report."
        }
        $trainingReport = $trainingText.Substring($trainingJsonStart) | ConvertFrom-Json
        $trainingState = [pscustomobject]@{
            candidate_id = $trainingReport.artifact_training.generated_at
            trained_through = $trainingReport.artifact_training.through
        }
        $temporaryTrainingStatePath = "$TrainingStatePath.tmp"
        $trainingState | ConvertTo-Json | Set-Content -Path $temporaryTrainingStatePath
        Move-Item -LiteralPath $temporaryTrainingStatePath -Destination $TrainingStatePath -Force
    } else {
        $trainingState = Get-Content -LiteralPath $TrainingStatePath -Raw | ConvertFrom-Json
        $trainingReport = Get-Content -LiteralPath $TrainingReportPath -Raw | ConvertFrom-Json
        if ($trainingReport.artifact_training.generated_at -ne $trainingState.candidate_id) {
            throw "Cross-sectional candidate changed during its shadow evaluation."
        }
    }

    $shadowLines = & $Python -m backtesting.stock_direction_cross_sectional_shadow 2>&1
    $shadowExitCode = $LASTEXITCODE
    $shadowText = $shadowLines -join [Environment]::NewLine
    Add-Content -Path $LogPath -Value "[$(Get-Date -Format o)] Cross-sectional shadow evaluation`n$shadowText"
    if ($shadowExitCode -ne 0) {
        throw "Cross-sectional shadow evaluation failed with exit code $shadowExitCode."
    }

    $shadowJsonStart = $shadowText.IndexOf("{")
    if ($shadowJsonStart -lt 0) {
        throw "Cross-sectional shadow evaluation did not return a JSON report."
    }
    $shadowReport = $shadowText.Substring($shadowJsonStart) | ConvertFrom-Json
    if ($shadowReport.evaluation_complete -and $TaskName) {
        $completion = [pscustomobject]@{
            evaluation_complete = $true
            completed_at = (Get-Date).ToString("o")
            candidate_id = $shadowReport.candidate_id
            sessions_resolved = $shadowReport.evaluation_sessions_resolved
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
