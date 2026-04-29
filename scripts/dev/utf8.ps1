param(
    [Parameter(Mandatory = $false)]
    [string] $Command,
    [Parameter(Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]] $Rest
)

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LC_ALL = "C.UTF-8"
$env:LANG = "C.UTF-8"

try {
    chcp.com 65001 | Out-Null
} catch {
    # chcp is unavailable in some non-interactive shells. The .NET stream
    # settings above are the actual guard used by PowerShell and Python.
}

$commandArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Command)) {
    $commandArgs += $Command
}
if ($Rest) {
    $commandArgs += $Rest
}
$commandText = ($commandArgs -join " ").Trim()

if ([string]::IsNullOrWhiteSpace($commandText)) {
    Write-Output "UTF-8 PowerShell harness active."
    Write-Output "Usage in PowerShell: & scripts/dev/utf8.ps1 -Command 'uv run python -X utf8 ...'"
    Write-Output "Usage from Bash/cmd: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev/utf8.ps1 -Command `"uv run python -X utf8 ...`""
    exit 0
}

Invoke-Expression $commandText
if ($global:LASTEXITCODE -is [int]) {
    exit $global:LASTEXITCODE
}
