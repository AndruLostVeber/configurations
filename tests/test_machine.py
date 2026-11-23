"""Проверки исполнения программ и дампов памяти через CLI."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests import PROJECT, run_cli

EXAMPLES = PROJECT / "examples"


class MachineTests(unittest.TestCase):
    """Проверяет адресацию, общую память и ошибки исполнения."""

    def interpret_source(self, source, start, end):
        """Ассемблирует и выполняет программу, возвращает её дамп."""
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            if isinstance(source, str):
                program = workspace / "program.asm"
                program.write_text(source, encoding="utf-8")
            else:
                program = source
            binary = workspace / "program.bin"
            dump = workspace / "memory.json"
            assembly = run_cli("assemble", program, binary)
            self.assertEqual(assembly.returncode, 0, assembly.stderr)
            result = run_cli("interpret", binary, dump, start, end)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(dump.read_text(encoding="utf-8"))

    def test_copy_array(self):
        values = [19, -23, 0, 8388607, -8388608]
        addresses = map(str, range(1000, 1013))
        expected = dict(zip(addresses, values + [0] * 3 + values))
        dump = self.interpret_source(EXAMPLES / "copy.asm", 1000, 1012)
        self.assertEqual(dump, expected)

    def test_program_and_data_share_memory(self):
        program = """
            load r1, 16
            load r2, 42
            write r2, 0, r1
            load r3, 7
            load r4, 256
            write r3, 0, r4
            read r5, 0
            write r5, 1, r4
        """
        self.assertEqual(
            self.interpret_source(program, 256, 257),
            {"256": 42, "257": 0x19},
        )

    def test_uninitialized_cell_at_largest_address(self):
        program = """
            read r1, 0xffffffff
            load r2, 256
            write r1, 0, r2
        """
        self.assertEqual(
            self.interpret_source(program, 256, 256), {"256": 0}
        )

    def test_invalid_binary_and_memory_ranges(self):
        cases = (
            (b"\xa9", 0, 1, "неполная команда"),
            (bytes(5), 0, 1, "неизвестный код операции"),
            (b"", -1, 1, "вне диапазона"),
            (b"", 0, 0x100000000, "вне диапазона"),
            (b"", 2, 1, "начальный адрес больше конечного"),
            (
                bytes.fromhex("09ffffff00 0a00000000"), 0, 1,
                "адрес -1 вне диапазона",
            ),
        )
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "program.bin"
            dump = Path(directory) / "memory.json"
            for data, start, end, message in cases:
                with self.subTest(message=message):
                    binary.write_bytes(data)
                    result = run_cli("interpret", binary, dump, start, end)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(dump.exists())
