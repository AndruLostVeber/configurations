"""Проверки ассемблера через команды запуска."""

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT = Path(__file__).resolve().parents[1]
SPECIFICATION = PROJECT / "examples" / "specification.asm"


def run_cli(*args):
    """Запускает CLI так же, как при использовании проекта."""
    return subprocess.run(
        [str(PROJECT / "run.sh"), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class AssemblerTests(unittest.TestCase):
    """Проверяет примеры спецификации и диагностику разбора."""

    def test_specification_fields(self):
        with TemporaryDirectory() as directory:
            result = run_cli(
                "assemble", SPECIFICATION, Path(directory) / "out.bin",
                "--test",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "(A=9, B=10, C=201)",
                "(A=12, B=15, C=860)",
                "(A=10, B=7, C=15, D=9)",
                "(A=14, B=12, C=15)",
                "Ассемблировано команд: 4",
            ],
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
