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


def write_file(path, text):
    target = open(path, "w", encoding="utf-8")
    target.write(text)
    target.close()


def make_vfs_folder():
    folder = tempfile.mkdtemp()
    os.makedirs(os.path.join(folder, "docs", "drafts"))
    write_file(os.path.join(folder, "readme.txt"), "привет")
    write_file(os.path.join(folder, "docs", "report.txt"), "отчёт")
    write_file(os.path.join(folder, "docs", "drafts", "plan.txt"), "план")
    return folder


class TestVfs(unittest.TestCase):
    def test_load_minimal(self):
        folder = tempfile.mkdtemp()
        write_file(os.path.join(folder, "hello.txt"), "привет")
        loaded = main.load_vfs(folder)
        self.assertEqual(loaded, {"hello.txt": "привет".encode("utf-8")})

    def test_load_deep(self):
        loaded = main.load_vfs(make_vfs_folder())
        self.assertIn("readme.txt", loaded)
        self.assertIn("plan.txt", loaded["docs"]["drafts"])

    def test_count_items(self):
        files, folders = main.count_items(main.load_vfs(make_vfs_folder()))
        self.assertEqual(files, 3)
        self.assertEqual(folders, 2)

    def test_load_missing_folder(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.load_vfs("нет_такой_папки")
        self.assertIn("папка не найдена", buffer.getvalue())

    def test_load_file_instead_of_folder(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "hello.txt")
        write_file(path, "привет")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.load_vfs(path)
        self.assertIn("это не папка", buffer.getvalue())

    def test_save_and_load_back(self):
        source = make_vfs_folder()
        loaded = main.load_vfs(source)
        copy = os.path.join(tempfile.mkdtemp(), "копия")
        main.save_folder(loaded, copy)
        self.assertEqual(main.load_vfs(copy), loaded)

    def test_source_not_changed(self):
        source = make_vfs_folder()
        before = main.load_vfs(source)
        main.save_folder(before, os.path.join(tempfile.mkdtemp(), "копия"))
        self.assertEqual(main.load_vfs(source), before)

    def test_load_unreadable_file(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "secret.txt")
        write_file(path, "секрет")
        os.chmod(path, 0)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.load_vfs(folder)
        os.chmod(path, 0o644)
        self.assertIn("не удалось прочитать файл", buffer.getvalue())

    def test_load_strange_file(self):
        folder = tempfile.mkdtemp()
        os.symlink("нет_такого_файла", os.path.join(folder, "ссылка"))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.load_vfs(folder)
        self.assertIn("неверный формат", buffer.getvalue())

    def test_script_in_other_encoding(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "script.txt")
        with open(path, "wb") as target:
            target.write("ls привет\n".encode("cp1251"))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                main.read_script(path)
        self.assertIn("не удалось прочитать скрипт", buffer.getvalue())

    def test_vfs_save_without_vfs(self):
        main.vfs = {}
        output = run("vfs-save " + os.path.join(tempfile.mkdtemp(), "копия"))
        self.assertIn("VFS не загружена", output)

    def test_vfs_save_without_path(self):
        self.assertIn("использование: vfs-save ПУТЬ", run("vfs-save"))

    def test_vfs_save_message(self):
        main.vfs = {"hello.txt": "привет".encode("utf-8")}
        copy = os.path.join(tempfile.mkdtemp(), "копия")
        self.assertIn("VFS сохранена", run("vfs-save " + copy))
        self.assertEqual(main.load_vfs(copy), main.vfs)

    def test_vfs_save_bad_path(self):
        main.vfs = {"hello.txt": "привет".encode("utf-8")}
        output = run("vfs-save /нельзя/сюда/писать")
        self.assertIn("не удалось сохранить", output)


if __name__ == "__main__":
    unittest.main()
