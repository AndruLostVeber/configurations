"""Проверки преобразования конфигурации через командную строку."""

import subprocess
import tempfile
import unittest
from pathlib import Path

RUN_SCRIPT = Path(__file__).resolve().parent.parent / "run.sh"
EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 1
EXCESSIVE_NESTING_DEPTH = 512


def run_config(source: str) -> subprocess.CompletedProcess:
    """Запускает преобразование из каталога с входным файлом."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.cfg"
        path.write_text(source, encoding="utf-8")
        return subprocess.run(
            [str(RUN_SCRIPT), "config", "--input", path.name],
            cwd=directory,
            capture_output=True,
            text=True,
        )


class ConfigurationTest(unittest.TestCase):
    """Проверяет синтаксис, результат в stdout и диагностику в stderr."""

    def assert_translation(self, source: str, expected: str) -> None:
        result = run_config(source)
        self.assertEqual(result.returncode, EXIT_SUCCESS, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, expected)

    def test_nested_arrays_and_both_binary_prefixes(self):
        self.assert_translation(
            """
            /#
            (define ignored 0b2);
            #/
            array(0B11, /# пропуск #/ array(0b1), array())
            """,
            "values = [3, [1], []]\n",
        )

    def test_constant_expressions_and_array_references(self):
        self.assert_translation(
            """
            (define start 0b10);
            (define result array(?{start + 1 + 0b10},
                                 ?{abs((start + -7))}));
            (define copy ?{result});
            ?{copy}
            """,
            "values = [5, 5]\n",
        )

    def test_constant_is_emitted_only_through_reference(self):
        self.assert_translation("(define target_moisture 0b110010);", "")
        self.assert_translation(
            "(define target_moisture 0b110010);\n"
            "array(0b1, ?{target_moisture})",
            "values = [1, 50]\n",
        )

    def test_top_level_values(self):
        self.assert_translation(
            "(define values 0b10); 0b0 ?{values + 1} array(0b11)",
            "values = [0, 3, [3]]\n",
        )
        self.assert_translation("0b1", "values = [1]\n")
        self.assert_translation("array()", "values = []\n")

    def test_example_configurations(self):
        examples = RUN_SCRIPT.parent / "examples"
        cases = {
            "monitoring.cfg": "values = [5, 3, [[80, 443], [8080]]]\n",
            "greenhouse.cfg": "values = [50, [[46, 48], [51, 53]], 4]\n",
        }
        for name, expected in cases.items():
            with self.subTest(example=name):
                source = (examples / name).read_text(encoding="utf-8")
                self.assert_translation(source, expected)

    def test_empty_document_produces_empty_toml(self):
        self.assert_translation("/# только комментарий #/\n", "")

    def test_malformed_input_produces_no_partial_output(self):
        invalid_sources = (
            "(define Name 0b1);",
            "(define wrong 0b102);",
            "(define wrong 2);",
            "(define wrong array(0b1 0b0));",
            "(define missing_semicolon 0b1)",
            "array(01, 0b1)",
            "?{1 - 2}",
            "/# нет конца комментария",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                result = run_config("(define first 0b1);\n" + source)
                self.assertEqual(result.returncode, EXIT_INPUT_ERROR)
                self.assertEqual(result.stdout, "")
                self.assertIn("Строка 2, столбец", result.stderr)

    def test_error_reports_exact_column(self):
        result = run_config("(define first 0b1);\n  ?{first + }")
        self.assertEqual(result.returncode, EXIT_INPUT_ERROR)
        self.assertIn("Строка 2, столбец 13", result.stderr)

    def test_deep_nesting_reports_a_clean_error(self):
        source = (
            "array(" * EXCESSIVE_NESTING_DEPTH
            + "0b1"
            + ")" * EXCESSIVE_NESTING_DEPTH
        )
        result = run_config(source)
        self.assertEqual(result.returncode, EXIT_INPUT_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("слишком глубокая вложенность", result.stderr)

    def test_invalid_constant_operations(self):
        invalid_sources = {
            "?{missing}": "неизвестная константа",
            "(define sample 0b1);": "уже объявлена",
            "?{sample + 1}": "сложение",
            "?{abs(sample)}": "abs",
        }
        for source, expected in invalid_sources.items():
            with self.subTest(source=source):
                result = run_config("(define sample array(0b1));\n" + source)
                self.assertEqual(result.returncode, EXIT_INPUT_ERROR)
                self.assertEqual(result.stdout, "")
                self.assertIn("Строка 2, столбец", result.stderr)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
