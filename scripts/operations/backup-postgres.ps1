[CmdletBinding()]
param(
    [string]$OutputDirectory = "backups",
    [string]$ComposeFile = "compose.yaml",
    [string]$ProjectName = "socrat",
    [string]$EnvFile = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$outputRoot = if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory)) }
$composePath = if ([System.IO.Path]::IsPathRooted($ComposeFile)) {
    [System.IO.Path]::GetFullPath($ComposeFile)
} else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $ComposeFile)) }
if (-not (Test-Path -LiteralPath $composePath -PathType Leaf)) { throw 'Compose file does not exist.' }
$composeArguments = @('compose', '--project-name', $ProjectName)
if ($EnvFile) {
    $envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $repoRoot $EnvFile }
    $composeArguments += @('--env-file', [System.IO.Path]::GetFullPath($envPath))
}
$composeArguments += @('--file', $composePath)
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $outputRoot "socrat-$stamp.dump"
$remoteArchive = "/tmp/socrat-$stamp.dump"

try {
    $null = & docker @composeArguments exec -T postgres pg_dump -U socrat -d socrat -Fc -f $remoteArchive
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
    $null = & docker @composeArguments cp "postgres:$remoteArchive" $archive
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup archive.' }
    Write-Output $archive
}
finally {
    $null = & docker @composeArguments exec -T postgres rm -f $remoteArchive 2>$null
}
