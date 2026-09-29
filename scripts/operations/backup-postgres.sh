#!/usr/bin/env bash
set -euo pipefail

output_directory="backups"
compose_file="compose.yaml"
project_name="socrat"
env_file=""

while (($#)); do
  case "$1" in
    --output-directory) output_directory="$2"; shift 2 ;;
    --compose-file) compose_file="$2"; shift 2 ;;
    --project-name) project_name="$2"; shift 2 ;;
    --env-file) env_file="$2"; shift 2 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ "$compose_file" = /* ]] || compose_file="$repo_root/$compose_file"
[[ "$output_directory" = /* ]] || output_directory="$repo_root/$output_directory"
mkdir -p "$output_directory"

compose=(docker compose --project-name "$project_name")
if [[ -n "$env_file" ]]; then
  [[ "$env_file" = /* ]] || env_file="$repo_root/$env_file"
  compose+=(--env-file "$env_file")
fi
compose+=(--file "$compose_file")

stamp="$(date -u +%Y%m%d-%H%M%S)"
archive="$output_directory/socrat-$stamp.dump"
remote_archive="/tmp/socrat-$stamp.dump"
cleanup() { "${compose[@]}" exec -T postgres rm -f "$remote_archive" >/dev/null 2>&1 || true; }
trap cleanup EXIT

"${compose[@]}" exec -T postgres pg_dump -U socrat -d socrat -Fc -f "$remote_archive" >/dev/null
"${compose[@]}" cp "postgres:$remote_archive" "$archive" >/dev/null
chmod 600 "$archive"
printf '%s\n' "$archive"
