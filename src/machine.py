"""Общая память, регистры и цикл исполнения УВМ."""

from collections.abc import Iterator

from src.isa import (
    INSTRUCTION_SIZE,
    LOAD,
    MAX_ADDRESS,
    READ,
    REGISTER_COUNT,
    WRITE,
    decode,
)

FIRST_ADDRESS = 0
INITIAL_VALUE = 0


def validate_address(address: int) -> None:
    """Проверяет, что адрес принадлежит памяти машины."""
    if not FIRST_ADDRESS <= address <= MAX_ADDRESS:
        raise ValueError(f"адрес {address} вне диапазона памяти")


class Machine:
    """Исполняет команды, выбирая их из общей с данными памяти."""

    def __init__(self, program: bytes) -> None:
        if len(program) % INSTRUCTION_SIZE:
            raise ValueError("неполная команда в конце бинарного файла")
        self._program_end = len(program)
        self._memory = dict(enumerate(program))
        self._registers = [INITIAL_VALUE] * REGISTER_COUNT
        self._operations = {
            LOAD: self._load,
            READ: self._read,
            WRITE: self._write,
        }

    def run(self) -> None:
        """Выполняет команды от первого адреса до конца программы."""
        addresses = range(FIRST_ADDRESS, self._program_end, INSTRUCTION_SIZE)
        for address in addresses:
            try:
                instruction = decode(self._fetch(address))
                operation = self._operations.get(instruction.opcode)
                if operation is None:
                    raise ValueError(
                        f"операция {instruction.opcode} недоступна на этапе 3.3"
                    )
                operation(*instruction.operands)
            except ValueError as error:
                raise ValueError(f"Адрес команды {address}: {error}") from error

    def _fetch(self, address: int) -> bytes:
        """Считывает из памяти пять байт следующей команды."""
        cells = range(address, address + INSTRUCTION_SIZE)
        return bytes(self._memory[cell] for cell in cells)

    def _load(self, register: int, value: int) -> None:
        """Помещает константу в регистр."""
        self._registers[register] = value

    def _read(self, register: int, address: int) -> None:
        """Читает ячейку по абсолютному адресу в регистр."""
        self._registers[register] = self._memory.get(address, INITIAL_VALUE)

    def _write(self, register: int, offset: int, base: int) -> None:
        """Сохраняет регистр по адресу из базового регистра со смещением."""
        address = self._registers[base] + offset
        validate_address(address)
        self._memory[address] = self._registers[register]

    def dump_cells(self, start: int, end: int) -> Iterator[tuple[int, int]]:
        """Возвращает адреса из включительного диапазона с их значениями."""
        validate_address(start)
        validate_address(end)
        if start > end:
            raise ValueError("начальный адрес больше конечного")
        return (
            (address, self._memory.get(address, INITIAL_VALUE))
            for address in range(start, end + 1)
        )
