import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

import main


def run(line):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        main.run_line(line)
    return buffer.getvalue()


def run_script(text):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "script.txt")
    script = open(path, "w", encoding="utf-8")
    script.write(text)
    script.close()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main.run_script(path, "$ ")
    return buffer.getvalue(), code


def catch_exit(argv):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        try:
            main.parse_args(argv)
        except SystemExit as error:
            return buffer.getvalue(), error.code
    return buffer.getvalue(), None


class TestParser(unittest.TestCase):
    def test_expand_known(self):
        os.environ["SHELL_TEST_VAR"] = "abc"
        line = main.expand_vars("ls $SHELL_TEST_VAR")
        self.assertEqual(line, "ls abc")

    def test_expand_unknown(self):
        line = main.expand_vars("ls $NO_SUCH_VARIABLE")
        self.assertEqual(line, "ls ")

    def test_split_quotes(self):
        parts = main.split_line('ls "два слова"')
        self.assertEqual(parts, ["ls", "два слова"])

    def test_unclosed_quote(self):
        self.assertIn("не закрыта кавычка", run('ls "abc'))


class TestCommands(unittest.TestCase):
    def test_ls_args(self):
        self.assertIn("ls: аргументы: -l /home", run("ls -l /home"))

    def test_cd_without_args(self):
        self.assertIn("cd: аргументов нет", run("cd"))

    def test_cd_too_many_args(self):
        self.assertIn("слишком много аргументов", run("cd a b"))

    def test_unknown_command(self):
        self.assertIn("команда не найдена", run("hello"))

    def test_exit_code(self):
        self.assertEqual(main.run_line("exit 3"), 3)

    def test_exit_bad_code(self):
        self.assertIn("нужен числовой аргумент", run("exit abc"))


class TestSettings(unittest.TestCase):
    def test_no_params(self):
        settings = main.parse_args([])
        self.assertEqual(settings, {"vfs": None, "script": None})

    def test_both_params(self):
        settings = main.parse_args(["--vfs", "vfs/minimal",
                                    "--script", "startup/exit.txt"])
        self.assertEqual(settings["vfs"], "vfs/minimal")
        self.assertEqual(settings["script"], "startup/exit.txt")

    def test_unknown_param(self):
        output, code = catch_exit(["--color"])
        self.assertIn("неизвестный параметр --color", output)
        self.assertEqual(code, 2)

    def test_param_without_value(self):
        output, code = catch_exit(["--vfs"])
        self.assertIn("не указано значение параметра --vfs", output)
        self.assertEqual(code, 2)

    def test_help(self):
        output, code = catch_exit(["--help"])
        self.assertIn("--script", output)
        self.assertEqual(code, 0)

    def test_debug_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main.print_settings({"vfs": "vfs/minimal", "script": None})
        output = buffer.getvalue()
        self.assertIn("[отладка] --vfs = vfs/minimal", output)
        self.assertIn("[отладка] --script = не задан", output)


class TestScript(unittest.TestCase):
    def test_shows_input_and_output(self):
        output, code = run_script("ls -l\n")
        self.assertIn("$ ls -l", output)
        self.assertIn("ls: аргументы: -l", output)
        self.assertIsNone(code)

    def test_skips_bad_lines(self):
        output, code = run_script("hello\nls \"abc\nls\n")
        self.assertIn("команда не найдена", output)
        self.assertIn("не закрыта кавычка", output)
        self.assertIn("ls: аргументов нет", output)

    def test_skips_empty_lines(self):
        output, code = run_script("\n\nls\n\n")
        self.assertEqual(output.count("$ "), 1)

    def test_exit_stops_script(self):
        output, code = run_script("ls первый\nexit 0\nls второй\n")
        self.assertEqual(code, 0)
        self.assertNotIn("второй", output)

    def test_missing_script(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.read_script("нет_такого_файла.txt")
        self.assertIn("не удалось прочитать скрипт", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
