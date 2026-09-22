
import io
import os
import sys
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


if __name__ == "__main__":
    unittest.main()
