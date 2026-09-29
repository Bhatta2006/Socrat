[CmdletBinding()]
param([string]$OutputDirectory = "backups")

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
if (-not $outputRoot.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Backup output must remain inside the repository workspace.'
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $outputRoot "socrat-$stamp.dump"
$remoteArchive = "/tmp/socrat-$stamp.dump"

try {
    & docker compose exec -T postgres pg_dump -U socrat -d socrat -Fc -f $remoteArchive
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
    & docker compose cp "postgres:$remoteArchive" $archive
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup archive.' }
    Write-Output $archive
}
finally {
    & docker compose exec -T postgres rm -f $remoteArchive 2>$null
}
