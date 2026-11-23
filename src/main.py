"""Командная строка учебной виртуальной машины."""

import argparse
import sys
from pathlib import Path

from src.assembler import assemble
from src.isa import encode
from src.machine import Machine


def run_assembler(args: argparse.Namespace) -> None:
    """Ассемблирует исходник и записывает машинный код."""
    instructions = assemble(args.source.read_text(encoding="utf-8"))
    encoded = [encode(instruction) for instruction in instructions]
    args.output.write_bytes(b"".join(encoded))
    if args.test:
        for command in encoded:
            print(", ".join(f"0x{byte:02X}" for byte in command))
    print(f"Ассемблировано команд: {len(instructions)}")


def run_interpreter(args: argparse.Namespace) -> None:
    """Выполняет бинарную программу и сохраняет JSON-дамп."""
    machine = Machine(args.program.read_bytes())
    machine.run()
    cells = machine.dump_cells(args.start, args.end)
    with args.dump.open("w", encoding="utf-8") as stream:
        stream.write("{")
        for address, value in cells:
            separator = "\n" if address == args.start else ",\n"
            stream.write(f'{separator}  "{address}": {value}')
        stream.write("\n}\n")


def create_parser() -> argparse.ArgumentParser:
    """Настраивает команды и параметры CLI."""
    parser = argparse.ArgumentParser(
        prog="run.sh", description="Учебная виртуальная машина"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    assembler = commands.add_parser("assemble", help="ассемблировать исходник")
    assembler.add_argument("source", type=Path, help="путь к исходному файлу")
    assembler.add_argument("output", type=Path, help="путь к двоичному файлу")
    assembler.add_argument(
        "--test", action="store_true", help="показать байты команд"
    )
    assembler.set_defaults(handler=run_assembler)

    interpreter = commands.add_parser("interpret", help="выполнить программу")
    interpreter.add_argument(
        "program", type=Path, help="путь к бинарному файлу"
    )
    interpreter.add_argument("dump", type=Path, help="путь к JSON-дампу")
    interpreter.add_argument("start", type=int, help="первый адрес дампа")
    interpreter.add_argument("end", type=int, help="последний адрес дампа")
    interpreter.set_defaults(handler=run_interpreter)
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
