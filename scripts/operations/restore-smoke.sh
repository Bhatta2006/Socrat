#!/usr/bin/env bash
set -euo pipefail

archive=""
compose_file="compose.yaml"
project_name="socrat"
env_file=""

while (($#)); do
  case "$1" in
    --archive) archive="$2"; shift 2 ;;
    --compose-file) compose_file="$2"; shift 2 ;;
    --project-name) project_name="$2"; shift 2 ;;
    --env-file) env_file="$2"; shift 2 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -z "$archive" || ! -f "$archive" ]]; then
  printf '%s\n' '--archive must identify an existing trusted Socrat dump.' >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ "$compose_file" = /* ]] || compose_file="$repo_root/$compose_file"
compose=(docker compose --project-name "$project_name")
if [[ -n "$env_file" ]]; then
  [[ "$env_file" = /* ]] || env_file="$repo_root/$env_file"
  compose+=(--env-file "$env_file")
fi
compose+=(--file "$compose_file")

smoke_database="socrat_restore_smoke"
remote_archive="/tmp/socrat-restore-smoke.dump"
cleanup() {
  "${compose[@]}" exec -T postgres dropdb -U socrat --if-exists "$smoke_database" >/dev/null 2>&1 || true
  "${compose[@]}" exec -T postgres rm -f "$remote_archive" >/dev/null 2>&1 || true
}
trap cleanup EXIT

"${compose[@]}" cp "$archive" "postgres:$remote_archive" >/dev/null
"${compose[@]}" exec -T postgres dropdb -U socrat --if-exists "$smoke_database" >/dev/null
"${compose[@]}" exec -T postgres createdb -U socrat "$smoke_database"
"${compose[@]}" exec -T postgres pg_restore -U socrat -d "$smoke_database" --exit-on-error "$remote_archive"
revision="$("${compose[@]}" exec -T postgres psql -U socrat -d "$smoke_database" -Atc 'SELECT version_num FROM alembic_version;' | tr -d '\r[:space:]')"
if [[ "$revision" != "0003" ]]; then
  printf 'Restored schema revision is invalid: %s\n' "$revision" >&2
  exit 1
fi
printf '%s\n' '[PASS] Backup restored into an isolated database at schema revision 0003.'
