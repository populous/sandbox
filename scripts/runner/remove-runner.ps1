<#
.SYNOPSIS
  Unregister the user-sandbox self-hosted runner.
  Run as Administrator if it was installed as a service.
#>
param(
  [string]$Repo = 'populous/sandbox',
  [string]$Dir = 'C:\actions-runner-user-sandbox'
)
$ErrorActionPreference = 'Stop'
Set-Location $Dir
$token = gh api -X POST "repos/$Repo/actions/runners/remove-token" --jq .token
& .\config.cmd remove --token $token
if ($LASTEXITCODE) { throw "config.cmd remove failed ($LASTEXITCODE)" }
