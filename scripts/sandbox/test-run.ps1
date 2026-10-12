<#
  Regression tests for scripts/sandbox/run.ps1.
  Runs on Windows PowerShell 5.1 (windows-latest) and PowerShell 7 (pwsh).
  Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sandbox\test-run.ps1
#>
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$run = Join-Path $PSScriptRoot 'run.ps1'
$hostExe = if ($PSVersionTable.PSEdition -eq 'Core') { 'pwsh' } else { 'powershell.exe' }
$tmpRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
$failures = 0

function Invoke-Case([string]$name, [string]$command, [string]$workdir, [int]$expected, [scriptblock]$extra) {
  $out = Join-Path $tmpRoot ("tr-" + $name + "-" + [guid]::NewGuid().ToString('N').Substring(0, 6))
  $env:SANDBOX_COMMAND = $command
  $env:SANDBOX_WORKDIR = $workdir
  $env:SANDBOX_LABEL = $name
  $env:SANDBOX_OUT = $out
  Push-Location $repo
  $ErrorActionPreference = 'Continue'
  & $hostExe -NoProfile -ExecutionPolicy Bypass -File $run *> $null
  $rc = $LASTEXITCODE
  $ErrorActionPreference = 'Stop'
  Pop-Location
  $ok = ($rc -eq $expected)
  $detail = "rc=$rc expected=$expected"
  if ($ok -and $extra) {
    try { & $extra $out } catch { $ok = $false; $detail += " check: $($_.Exception.Message)" }
  }
  if ($ok) { Write-Host "PASS $name ($detail)" } else { Write-Host "FAIL $name ($detail)"; $script:failures++ }
}

$psv = $PSVersionTable.PSVersion.ToString()
Write-Host "PowerShell $psv ($hostExe)"

Invoke-Case 'ok' 'Write-Output "hello"; 1024 | Set-Content -Encoding ascii "$env:PPLX_RUN_OUT\r.txt"' '.' 0 {
  param($o)
  $m = Get-Content -Raw -Encoding UTF8 (Join-Path $o 'manifest.json') | ConvertFrom-Json
  if ($m.exit_code -ne 0) { throw 'manifest exit_code' }
  if ($m.protocol -ne 'pplx-thread/1') { throw 'manifest protocol' }
  $paths = @($m.files | ForEach-Object { $_.path })
  foreach ($p in 'command.ps1', 'run.log', 'outputs/r.txt') { if ($paths -notcontains $p) { throw "missing $p" } }
  foreach ($f in $m.files) { if ($f.sha256.Length -ne 64) { throw 'sha256 length' } }
  $log = Get-Content -Raw -Encoding UTF8 (Join-Path $o 'run.log')
  if ($log -notmatch 'hello') { throw 'log content' }
}
Invoke-Case 'native-exit' 'cmd /c exit 3' '.' 3 $null
Invoke-Case 'throw' 'throw "boom"' '.' 1 $null
Invoke-Case 'bad-workdir' 'Write-Output x' '..\' 2 $null
Invoke-Case 'abs-workdir' 'Write-Output x' 'C:\Windows' 2 $null
Invoke-Case 'missing-workdir' 'Write-Output x' 'no-such-dir' 2 $null
# Korean text built from code points so this file stays ASCII-only.
$ko = -join ([char[]](0xD55C, 0xAE00, 0x0020, 0xCD9C, 0xB825))
Invoke-Case 'korean-utf8' ('Write-Output "' + $ko + '"') '.' 0 {
  param($o)
  $log = [IO.File]::ReadAllText((Join-Path $o 'run.log'), [Text.Encoding]::UTF8)
  if (-not $log.Contains($ko)) { throw "log lacks Korean text: $log" }
  $m = [IO.File]::ReadAllText((Join-Path $o 'manifest.json'), [Text.Encoding]::UTF8) | ConvertFrom-Json
  if ($m.command -notlike "*$ko*") { throw 'manifest command lacks Korean text' }
}

if ($failures) { Write-Host "$failures failure(s)"; exit 1 }
Write-Host 'all passed'
