"""Командная строка учебной виртуальной машины."""

import argparse
import sys
from pathlib import Path

from src.assembler import assemble
from src.isa import encode


def run_assembler(args: argparse.Namespace) -> None:
    """Ассемблирует исходник и записывает машинный код."""
    instructions = assemble(args.source.read_text(encoding="utf-8"))
    encoded = [encode(instruction) for instruction in instructions]
    args.output.write_bytes(b"".join(encoded))
    if args.test:
        for command in encoded:
            print(", ".join(f"0x{byte:02X}" for byte in command))
    print(f"Ассемблировано команд: {len(instructions)}")


def create_parser() -> argparse.ArgumentParser:
    """Настраивает команды и параметры CLI."""
    parser = argparse.ArgumentParser(description="Учебная виртуальная машина")
    commands = parser.add_subparsers(dest="command", required=True)

    assembler = commands.add_parser("assemble", help="ассемблировать исходник")
    assembler.add_argument("source", type=Path, help="путь к исходному файлу")
    assembler.add_argument("output", type=Path, help="путь к двоичному файлу")
    assembler.add_argument(
        "--test", action="store_true", help="показать байты команд"
    )
    assembler.set_defaults(handler=run_assembler)
    return parser


def main() -> int:
    """Запускает выбранную команду и сообщает об ошибках ввода."""
    args = create_parser().parse_args()
    try:
        args.handler(args)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
