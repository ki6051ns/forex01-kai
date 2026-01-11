# Ground Truth Reproduction Script (PowerShell)
# 
# Usage:
#   .\tools\reproduce_ground_truth.ps1 -GroundTruth "18th_commit"
#   .\tools\reproduce_ground_truth.ps1 -GroundTruth "all_spot_TK20"
#
# Note: This script overwrites test\input\. A backup is created automatically.

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("18th_commit", "all_spot_TK20")]
    [string]$GroundTruth,
    
    [Parameter(Mandatory=$false)]
    [string]$Date = "2025-05-20"
)

# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

# パス定義
$RepoRoot = (Get-Location).Path
$BackupDir = Join-Path $RepoRoot "test\input__backup"
$InputDir = Join-Path $RepoRoot "test\input"

if ($GroundTruth -eq "18th_commit") {
    $GroundTruthPath = "D:\forex\18th_commit\program6"
    $RefCsv = "D:\forex\18th_commit\program6\test\output\performance\performance_20250520.csv"
} else {
    $GroundTruthPath = "D:\forex\all_spot_TK20\program6"
    $RefCsv = "D:\forex\all_spot_TK20\program6\test\output\performance\performance_20250520.csv"
}

$GroundTruthInput = Join-Path $GroundTruthPath "test\input"
$NewCsv = Join-Path $RepoRoot "test\output\performance\performance_20250520.csv"

Write-Host ("=" * 80)
Write-Host "Ground Truth Reproduction Script"
Write-Host ("=" * 80)
Write-Host "Ground Truth: $GroundTruth"
Write-Host "Reference Path: $GroundTruthPath"
Write-Host "Date: $Date"
Write-Host ""

# Check if date is Tuesday (test_prod.py only runs on Tuesday, weekday() == 1)
$dateObj = [DateTime]::Parse($Date)
$dayOfWeek = $dateObj.DayOfWeek
$dayOfWeekValue = [int]$dayOfWeek  # 0=Sunday, 1=Monday, ..., 6=Saturday in .NET
# Python weekday(): 0=Monday, 1=Tuesday, ..., 6=Sunday
# So Tuesday in Python = DayOfWeek.Tuesday in .NET = 2
$isTuesday = ($dayOfWeek -eq [DayOfWeek]::Tuesday)
Write-Host "Date check: $Date is $dayOfWeek (DayOfWeek value: $dayOfWeekValue, Python weekday would be: $(if ($dayOfWeekValue -eq 0) { 6 } else { $dayOfWeekValue - 1 }))"
if (-not $isTuesday) {
    Write-Host "WARNING: test_prod.py only runs on Tuesday (Python weekday() == 1)."
    Write-Host "         Current date is $dayOfWeek (Python weekday() would be $(if ($dayOfWeekValue -eq 0) { 6 } else { $dayOfWeekValue - 1 }))."
    Write-Host "         The script will continue, but test_prod.py will not execute."
    Write-Host ""
}

# Step 0: Backup
Write-Host "[Step 0] Backing up test\input\..."
if (Test-Path $BackupDir) {
    Remove-Item -Recurse -Force $BackupDir
}
Copy-Item -Recurse $InputDir $BackupDir
Write-Host "[OK] Backup completed: $BackupDir"
Write-Host ""

# Step 1: Check Ground Truth folder existence
Write-Host "[Step 1] Checking Ground Truth folder existence..."
if (-not (Test-Path $GroundTruthPath)) {
    Write-Host "[ERROR] Ground Truth folder not found: $GroundTruthPath"
    exit 1
}
if (-not (Test-Path $GroundTruthInput)) {
    Write-Host "[ERROR] Ground Truth input folder not found: $GroundTruthInput"
    exit 1
}
if (-not (Test-Path $RefCsv)) {
    Write-Host "[ERROR] Reference CSV not found: $RefCsv"
    exit 1
}
Write-Host "[OK] Ground Truth folder check completed"
Write-Host ""

# Step 2: Copy input data
Write-Host "[Step 2] Copying input data..."
Remove-Item -Recurse -Force "$InputDir\*" -ErrorAction SilentlyContinue
Copy-Item -Recurse "$GroundTruthInput\*" $InputDir -Force
Write-Host "[OK] Input data copy completed"
Write-Host ""

# Step 3: Execute
Write-Host "[Step 3] Executing test_prod.py..."
Write-Host "Command: python test_prod.py $Date"
$pythonError = $null
try {
    $ErrorActionPreference = "Continue"
    $pythonOutput = python test_prod.py $Date 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
} catch {
    $pythonOutput = $_.Exception.Message
    $exitCode = 1
}

# Check if output contains error messages
$hasError = ($exitCode -ne 0 -or $pythonOutput -match "Traceback|Error|Exception|KeyError|TypeError")

if ($hasError) {
    Write-Host "[WARNING] test_prod.py encountered errors (exit code: $exitCode)"
    Write-Host "Note: This may be expected if there are data or code issues."
    Write-Host "Error details (last 1000 chars):"
    if ($pythonOutput.Length -gt 1000) {
        Write-Host $pythonOutput.Substring($pythonOutput.Length - 1000)
    } else {
        Write-Host $pythonOutput
    }
    Write-Host "[INFO] Continuing to check if result CSV was generated anyway..."
    Write-Host ""
} else {
    Write-Host "[OK] test_prod.py execution completed"
    Write-Host ""
}

# Step 4: Check result file
Write-Host "[Step 4] Checking result file existence..."
if (-not (Test-Path $NewCsv)) {
    Write-Host "[ERROR] Result CSV not generated: $NewCsv"
    exit 1
}
Write-Host "[OK] Result CSV check completed: $NewCsv"
Write-Host ""

# Step 5: Compare
Write-Host "[Step 5] Comparing results..."
Write-Host "Command: python tools\compare_performance.py --ref `"$RefCsv`" --new `"$NewCsv`""
python tools\compare_performance.py --ref $RefCsv --new $NewCsv
$CompareExitCode = $LASTEXITCODE

Write-Host ""
if ($CompareExitCode -eq 0) {
    Write-Host "[SUCCESS] Reproduction successful! Results match Ground Truth."
} else {
    Write-Host "[FAILED] Reproduction failed. Results do not match Ground Truth."
    Write-Host "Please refer to tools\REPRODUCTION_STEPS.md for troubleshooting."
}

Write-Host ""
Write-Host ("=" * 80)
Write-Host "Completed"
Write-Host ("=" * 80)
Write-Host ""
Write-Host "To restore backup:"
$restoreCmd1 = "Remove-Item -Recurse -Force `"$InputDir\*`""
$restoreCmd2 = "Copy-Item -Recurse `"$BackupDir\*`" `"$InputDir`" -Force"
Write-Host "  $restoreCmd1"
Write-Host "  $restoreCmd2"
Write-Host ""

exit $CompareExitCode