"""Проверки ассемблера через команды запуска."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests import PROJECT, run_cli

SPECIFICATION = PROJECT / "examples" / "specification.asm"


class AssemblerTests(unittest.TestCase):
    """Проверяет примеры спецификации и диагностику разбора."""

    def test_launcher_uses_its_own_project(self):
        with TemporaryDirectory() as directory:
            other_source = Path(directory) / "src"
            other_source.mkdir()
            (other_source / "__init__.py").touch()
            result = run_cli("--help", cwd=directory)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("assemble", result.stdout)

    def test_specification_bytes(self):
        with TemporaryDirectory() as directory:
            binary = Path(directory) / "out.bin"
            result = run_cli("assemble", SPECIFICATION, binary, "--test")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "0xA9, 0xC9, 0x00, 0x00, 0x00",
                    "0xFC, 0x5C, 0x03, 0x00, 0x00",
                    "0x7A, 0x2F, 0x01, 0x00, 0x00",
                    "0xCE, 0x0F, 0x00, 0x00, 0x00",
                    "Ассемблировано команд: 4",
                ],
            )
            self.assertEqual(
                binary.read_bytes(),
                bytes.fromhex("a9c9000000 fc5c030000 7a2f010000 ce0f000000"),
            )

    def test_field_boundaries_without_test_mode(self):
        commands = [
            "load r0, -8388608",
            "load r15, 8388607",
            "load r1, -1",
            "read r15, 0xffffffff",
            "write r15, 31, r15",
            "sgn r15, r15",
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "bounds.asm"
            binary = Path(directory) / "out.bin"
            source.write_text("\n".join(commands), encoding="utf-8")
            result = run_cli("assemble", source, binary)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "Ассемблировано команд: 6")
            self.assertEqual(
                binary.read_bytes(),
                bytes.fromhex(
                    "0900008000 f9ffff7f00 19ffffff00 "
                    "fcffffffff faff010000 fe0f000000"
                ),
            )

    def test_invalid_instruction_has_line_number(self):
        cases = {
            "stop": "неизвестная команда",
            "load r16, 1": "регистр",
            "load r0,": "число аргументов",
            "load r0, 8388608": "вне диапазона",
            "write r1, 32, r2": "вне диапазона",
            "read r15, -1": "вне диапазона",
        }
        with TemporaryDirectory() as directory:
            source = Path(directory) / "bad.asm"
            binary = Path(directory) / "out.bin"
            for line, message in cases.items():
                with self.subTest(line=line):
                    source.write_text(f"; комментарий\n{line}\n", "utf-8")
                    result = run_cli("assemble", source, binary)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("Строка 2", result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(binary.exists())


if __name__ == "__main__":
    unittest.main()
