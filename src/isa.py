"""Поля команд УВМ варианта 21."""

from dataclasses import dataclass


LOAD = 9
READ = 12
WRITE = 10
SGN = 14
REGISTER_BITS = 4
REGISTER_COUNT = 1 << REGISTER_BITS
ADDRESS_BITS = 32


@dataclass(frozen=True)
class OperandSpec:
    """Размер и тип поля команды."""

    bits: int
    signed: bool = False
    register: bool = False


@dataclass(frozen=True)
class InstructionFormat:
    """Код операции и форматы её полей в порядке следования."""

    opcode: int
    operands: tuple[OperandSpec, ...]


@dataclass(frozen=True)
class Instruction:
    """Команда с числовыми значениями полей A, B, C и, при наличии, D."""

    opcode: int
    operands: tuple[int, ...]


REGISTER = OperandSpec(REGISTER_BITS, register=True)
CONSTANT = OperandSpec(24, signed=True)
ADDRESS = OperandSpec(ADDRESS_BITS)
OFFSET = OperandSpec(5)
FORMATS = {
    "load": InstructionFormat(LOAD, (REGISTER, CONSTANT)),
    "read": InstructionFormat(READ, (REGISTER, ADDRESS)),
    "write": InstructionFormat(WRITE, (REGISTER, OFFSET, REGISTER)),
    "sgn": InstructionFormat(SGN, (REGISTER, REGISTER)),
}
