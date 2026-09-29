[CmdletBinding()]
param([Parameter(Mandatory)][string]$Archive)

$ErrorActionPreference = 'Stop'
$resolved = (Resolve-Path -LiteralPath $Archive).Path
$smokeDatabase = 'socrat_restore_smoke'
$remoteArchive = '/tmp/socrat-restore-smoke.dump'

try {
    & docker compose cp $resolved "postgres:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup archive.' }
    & docker compose exec -T postgres dropdb -U socrat --if-exists $smokeDatabase
    & docker compose exec -T postgres createdb -U socrat $smokeDatabase
    & docker compose exec -T postgres pg_restore -U socrat -d $smokeDatabase --exit-on-error $remoteArchive
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed.' }
    $revision = & docker compose exec -T postgres psql -U socrat -d $smokeDatabase -Atc 'SELECT version_num FROM alembic_version;'
    if ($LASTEXITCODE -ne 0 -or $revision.Trim() -ne '0001') { throw 'Restored schema revision is invalid.' }
    Write-Host '[PASS] Backup restored into an isolated database at schema revision 0001.'
}
finally {
    & docker compose exec -T postgres dropdb -U socrat --if-exists $smokeDatabase 2>$null
    & docker compose exec -T postgres rm -f $remoteArchive 2>$null
}
