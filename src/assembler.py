"""Разбор текстовых команд в промежуточное представление."""

import re

from src.isa import FORMATS, REGISTER_COUNT, Instruction, OperandSpec


def parse_operand(text: str, spec: OperandSpec) -> int:
    """Преобразует аргумент в число и проверяет его размер."""
    if spec.register:
        if re.fullmatch(r"r[0-9]+", text) is None:
            raise ValueError(f"ожидался регистр, получено {text!r}")
        value = int(text[1:])
        if value >= REGISTER_COUNT:
            raise ValueError(f"регистр {text!r} вне диапазона")
        return value

    try:
        value = int(text, base=0)
    except ValueError as error:
        raise ValueError(f"ожидалось целое число, получено {text!r}") from error

    upper = 1 << (spec.bits - spec.signed)
    lower = -upper if spec.signed else 0
    if not lower <= value < upper:
        raise ValueError(f"число {text!r} вне диапазона [{lower}, {upper - 1}]")
    return value


def parse_instruction(line: str) -> Instruction:
    """Разбирает одну команду без комментария."""
    mnemonic, *rest = line.split(maxsplit=1)
    arguments = rest[0] if rest else ""
    if mnemonic not in FORMATS:
        raise ValueError(f"неизвестная команда {mnemonic!r}")
    spec = FORMATS[mnemonic]
    fields = [field.strip() for field in arguments.split(",")]
    if len(fields) != len(spec.operands) or not all(fields):
        raise ValueError(f"неверное число аргументов команды {mnemonic!r}")
    operands = tuple(
        parse_operand(field, operand)
        for field, operand in zip(fields, spec.operands)
    )
    return Instruction(spec.opcode, operands)


def assemble(source: str) -> list[Instruction]:
    """Разбирает программу, сохраняя номер строки для диагностики."""
    instructions = []
    for number, line in enumerate(source.splitlines(), start=1):
        code = line.partition(";")[0].strip()
        if not code:
            continue
        try:
            instructions.append(parse_instruction(code))
        except ValueError as error:
            raise ValueError(f"Строка {number}: {error}") from error
    return instructions
