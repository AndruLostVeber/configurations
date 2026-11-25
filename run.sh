#!/bin/sh
set -eu
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$project_dir${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" "$project_dir/src/main.py" "$@"
