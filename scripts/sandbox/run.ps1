<#
  Execute SANDBOX_COMMAND (PowerShell), capture log, write sha256 manifest.
  Env inputs : SANDBOX_COMMAND (required), SANDBOX_WORKDIR (default "."),
               SANDBOX_LABEL (default "manual"), SANDBOX_OUT (output dir),
               SANDBOX_SHELL (optional: powershell.exe | pwsh)
  Outputs    : run.log, command.ps1, outputs\*, manifest.json in SANDBOX_OUT.
               The command writes result files to $env:PPLX_RUN_OUT
               (alias: $env:SANDBOX_ARTIFACTS). Results are stored in git, not
               in Actions artifacts.
  Works on Windows PowerShell 5.1 and PowerShell 7+.
#>
$ErrorActionPreference = 'Stop'

if (-not $env:SANDBOX_COMMAND) { [Console]::Error.WriteLine('SANDBOX_COMMAND is required'); exit 2 }
if (-not $env:SANDBOX_WORKDIR) { $env:SANDBOX_WORKDIR = '.' }
if (-not $env:SANDBOX_LABEL)   { $env:SANDBOX_LABEL = 'manual' }
if (-not $env:SANDBOX_OUT)     { $env:SANDBOX_OUT = Join-Path (Get-Location) '.sandbox-out' }

$repoRoot = (Get-Location).Path
$wd = $env:SANDBOX_WORKDIR
if ([IO.Path]::IsPathRooted($wd) -or $wd -match '\.\.') {
  [Console]::Error.WriteLine('workdir must be a relative path inside the repo'); exit 2
}
$workPath = Join-Path $repoRoot $wd
if (-not (Test-Path -LiteralPath $workPath -PathType Container)) {
  [Console]::Error.WriteLine("workdir not found: $wd"); exit 2
}

$out = $env:SANDBOX_OUT
$outputs = Join-Path $out 'outputs'
New-Item -ItemType Directory -Force -Path $outputs | Out-Null
$env:PPLX_RUN_OUT = $outputs
$env:SANDBOX_ARTIFACTS = $outputs

$utf8 = New-Object System.Text.UTF8Encoding($false)
$cmdFile = Join-Path $out 'command.ps1'
$logFile = Join-Path $out 'run.log'
$body = @(
  '$ErrorActionPreference = ''Stop'''
  '[Console]::OutputEncoding = [Text.Encoding]::UTF8'
  '$OutputEncoding = [Text.Encoding]::UTF8'
  $env:SANDBOX_COMMAND
  'if ($LASTEXITCODE) { exit $LASTEXITCODE }'
) -join "`r`n"
# UTF-8 *with* BOM: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
[IO.File]::WriteAllText($cmdFile, $body, (New-Object System.Text.UTF8Encoding($true)))
[IO.File]::WriteAllText($logFile, '', $utf8)

$shell = $env:SANDBOX_SHELL
if (-not $shell) {
  if ($env:OS -eq 'Windows_NT') { $shell = 'powershell.exe' } else { $shell = 'pwsh' }
}

$started = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
# Decode child output as UTF-8 (default console code page would mangle non-ASCII).
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
Push-Location $workPath
$ErrorActionPreference = 'Continue'
& $shell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $cmdFile 2>&1 | ForEach-Object {
  $line = "$_"
  Write-Host $line
  [IO.File]::AppendAllText($logFile, $line + [Environment]::NewLine, $utf8)
}
$rc = $LASTEXITCODE
if ($null -eq $rc) { $rc = 0 }
$ErrorActionPreference = 'Stop'
Pop-Location
$finished = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

$outFull = (Resolve-Path -LiteralPath $out).Path
$files = @(Get-ChildItem -LiteralPath $outFull -Recurse -File |
  Where-Object { $_.Name -ne 'manifest.json' } |
  ForEach-Object {
    [pscustomobject][ordered]@{
      path   = $_.FullName.Substring($outFull.Length).TrimStart('\', '/').Replace('\', '/')
      sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower()
      bytes  = $_.Length
    }
  } | Sort-Object path)

$manifest = [ordered]@{
  protocol     = 'pplx-thread/1'
  schema       = 'user-sandbox/manifest@1'
  thread_id    = $env:PPLX_THREAD_ID
  label        = $env:SANDBOX_LABEL
  command      = $env:SANDBOX_COMMAND
  workdir      = $wd
  shell        = $shell
  exit_code    = $rc
  started_utc  = $started
  finished_utc = $finished
  git_sha      = $env:GITHUB_SHA
  git_ref      = $env:GITHUB_REF
  run_id       = $env:GITHUB_RUN_ID
  runner_name  = $env:RUNNER_NAME
  host         = [ordered]@{
    os         = [Environment]::OSVersion.VersionString
    machine    = $env:PROCESSOR_ARCHITECTURE
    powershell = $PSVersionTable.PSVersion.ToString()
  }
  files        = $files
}
[IO.File]::WriteAllText((Join-Path $out 'manifest.json'), ($manifest | ConvertTo-Json -Depth 6), $utf8)
Write-Host ('{{"exit_code": {0}, "files": {1}}}' -f $rc, $files.Count)
exit $rc
