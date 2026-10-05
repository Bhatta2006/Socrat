[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Archive,
    [string]$ComposeFile = "compose.yaml",
    [string]$ProjectName = "socrat",
    [string]$EnvFile = "",
    [ValidatePattern('^[0-9]{4}$')][string]$ExpectedRevision = "0005"
)

$ErrorActionPreference = 'Stop'
$resolved = (Resolve-Path -LiteralPath $Archive).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composePath = if ([System.IO.Path]::IsPathFullyQualified($ComposeFile)) {
    [System.IO.Path]::GetFullPath($ComposeFile)
} else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $ComposeFile)) }
if (-not (Test-Path -LiteralPath $composePath -PathType Leaf)) { throw 'Compose file does not exist.' }
$composeArguments = @('compose', '--project-name', $ProjectName)
if ($EnvFile) {
    $envPath = if ([System.IO.Path]::IsPathFullyQualified($EnvFile)) { $EnvFile } else { Join-Path $repoRoot $EnvFile }
    $composeArguments += @('--env-file', [System.IO.Path]::GetFullPath($envPath))
}
$composeArguments += @('--file', $composePath)
$smokeDatabase = 'socrat_restore_smoke'
$remoteArchive = '/tmp/socrat-restore-smoke.dump'

try {
    & docker @composeArguments cp $resolved "postgres:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup archive.' }
    & docker @composeArguments exec -T postgres dropdb -U socrat --if-exists $smokeDatabase
    & docker @composeArguments exec -T postgres createdb -U socrat $smokeDatabase
    & docker @composeArguments exec -T postgres pg_restore -U socrat -d $smokeDatabase --exit-on-error $remoteArchive
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed.' }
    $revision = & docker @composeArguments exec -T postgres psql -U socrat -d $smokeDatabase -Atc 'SELECT version_num FROM alembic_version;'
    if ($LASTEXITCODE -ne 0 -or $revision.Trim() -ne $ExpectedRevision) { throw 'Restored schema revision is invalid.' }
    Write-Host "[PASS] Backup restored into an isolated database at schema revision $ExpectedRevision."
}
finally {
    & docker @composeArguments exec -T postgres dropdb -U socrat --if-exists $smokeDatabase 2>$null
    & docker @composeArguments exec -T postgres rm -f $remoteArchive 2>$null
}
