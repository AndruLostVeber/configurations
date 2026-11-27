"""Командная строка транслятора конфигураций."""

import argparse
import sys
from pathlib import Path

from src.configuration import translate

EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 1


def run_config(input_path: Path) -> None:
    """Читает исходную конфигурацию и выводит TOML."""
    source = input_path.read_text(encoding="utf-8")
    try:
        output = translate(source)
    except RecursionError as error:
        raise ValueError("слишком глубокая вложенность") from error
    sys.stdout.write(output)


def create_parser() -> argparse.ArgumentParser:
    """Настраивает команду преобразования и её параметры."""
    parser = argparse.ArgumentParser(
        prog="run.sh", description="Транслятор учебных конфигураций"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    config = commands.add_parser("config", help="преобразовать в TOML")
    config.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="путь к конфигурации в UTF-8",
    )
    return parser


def main() -> int:
    """Запускает транслятор и сообщает об ошибках ввода."""
    args = create_parser().parse_args()
    try:
        run_config(args.input)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
