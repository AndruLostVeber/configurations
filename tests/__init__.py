"""Инструменты для запуска CLI в тестах."""

import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    """Запускает CLI так же, как при использовании проекта."""
    return subprocess.run(
        [str(PROJECT / "run.sh"), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
