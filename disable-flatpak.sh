#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$repo_dir/installed/gtk4-bounce-gnome50-x86_64/manage.py" rollback "$@"
