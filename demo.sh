#!/bin/sh
set -eu

project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cd "$project_dir"

printf '%s\n' 'Подготовка окружения' >&2
python3 -m venv .venv >&2
. .venv/bin/activate
python -m pip install -r requirements.txt >&2
export PYTHON="$project_dir/.venv/bin/python"

printf '\n%s\n' 'Мониторинг сервиса — TOML' >&2
printf '%s\n' '[monitoring]'
./run.sh config --input examples/monitoring.cfg

printf '\n%s\n' 'Полив теплицы — TOML' >&2
printf '\n%s\n' '[greenhouse]'
./run.sh config --input examples/greenhouse.cfg

printf '\n%s\n' 'Тесты' >&2
python -m unittest discover -s tests -v >&2

printf '\n%s\n' 'История коммитов' >&2
git --no-pager log --oneline HEAD >&2
