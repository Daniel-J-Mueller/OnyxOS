#!/bin/bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 is required. Install it with: brew install python' >&2
  exit 1
fi
exec python3 "$script_dir/run_vm.py" "$@"
