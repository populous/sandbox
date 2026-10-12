<#
.SYNOPSIS
  Register this Windows PC as the self-hosted runner for user-sandbox.
.DESCRIPTION
  Requirements: Git for Windows, GitHub CLI (gh) logged in as repo admin.
  -Service installs the runner as a Windows service (run PowerShell as Administrator).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\runner\setup-runner.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\runner\setup-runner.ps1 -Service
#>
param(
  [string]$Repo = 'populous/sandbox',
  [string]$Dir = 'C:\actions-runner-user-sandbox',
  [string]$Name = "$env:COMPUTERNAME-user-sandbox",
  [switch]$Service
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

foreach ($tool in 'git', 'gh') {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "$tool not found. Install: winget install --id Git.Git -e ; winget install --id GitHub.cli -e"
  }
}
if ($Service) {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw '-Service requires an elevated (Administrator) PowerShell.'
  }
}

$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
$version = (gh api repos/actions/runner/releases/latest --jq .tag_name).TrimStart('v')
$pkg = "actions-runner-win-$arch-$version.zip"
Write-Host "runner v$version ($arch) -> $Dir"

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
Set-Location $Dir
if (-not (Test-Path '.\config.cmd')) {
  Invoke-WebRequest -UseBasicParsing -OutFile $pkg -Uri "https://github.com/actions/runner/releases/download/v$version/$pkg"
  Expand-Archive -Path $pkg -DestinationPath $Dir -Force
  Remove-Item $pkg
}

$token = gh api -X POST "repos/$Repo/actions/runners/registration-token" --jq .token
$cfg = @('--unattended', '--replace', '--url', "https://github.com/$Repo", '--token', $token,
         '--name', $Name, '--labels', 'user-sandbox', '--work', '_work')
if ($Service) { $cfg += '--runasservice' }
& .\config.cmd @cfg
if ($LASTEXITCODE) { throw "config.cmd failed ($LASTEXITCODE)" }

if ($Service) { Write-Host 'Installed as Windows service. Check: Get-Service actions.runner.*' }
else { Write-Host "Start interactively: cd $Dir ; .\run.cmd" }
