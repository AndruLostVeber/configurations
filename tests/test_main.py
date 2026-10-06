import io
import os
import sys
import tempfile
import time
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
        code = main.run_script(path)
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
    def setUp(self):
        main.vfs = {"readme.txt": b"hi"}
        main.current_dir = []

    def test_shows_input_and_output(self):
        output, code = run_script("ls -l\n")
        self.assertIn("$ ls -l", output)
        self.assertIn("readme.txt", output)
        self.assertIsNone(code)

    def test_skips_bad_lines(self):
        output, code = run_script("hello\nls \"abc\nls\n")
        self.assertIn("команда не найдена", output)
        self.assertIn("не закрыта кавычка", output)
        self.assertIn("readme.txt", output)

    def test_skips_empty_lines(self):
        output, code = run_script("\n\nls\n\n")
        self.assertEqual(output.count("$ "), 1)

    def test_exit_stops_script(self):
        output, code = run_script("cd первый\nexit 0\ncd второй\n")
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


def make_test_vfs():
    main.vfs = {
        "readme.txt": b"hello",
        "etc": {"hosts": b"127.0.0.1"},
        "home": {
            "user": {
                "docs": {"report.txt": b"report"},
                "music": {},
            },
        },
    }
    main.current_dir = []


class TestPath(unittest.TestCase):
    def setUp(self):
        make_test_vfs()

    def test_relative(self):
        self.assertEqual(main.split_path("home/user"), ["home", "user"])

    def test_absolute(self):
        main.current_dir = ["home"]
        self.assertEqual(main.split_path("/etc"), ["etc"])

    def test_dots(self):
        main.current_dir = ["home", "user"]
        self.assertEqual(main.split_path("../user/./docs"),
                         ["home", "user", "docs"])

    def test_up_from_root(self):
        self.assertEqual(main.split_path("../.."), [])

    def test_tilde(self):
        main.current_dir = ["home"]
        self.assertEqual(main.split_path("~/etc"), ["etc"])

    def test_find_missing(self):
        self.assertIsNone(main.find_node(["readme.txt", "x"]))


class TestLs(unittest.TestCase):
    def setUp(self):
        make_test_vfs()
        main.vfs[".profile"] = b"secret"
        main.vfs["big.bin"] = b"x" * 2048

    def test_root(self):
        self.assertEqual(run("ls"), "big.bin  etc  home  readme.txt\n")

    def test_path(self):
        self.assertEqual(run("ls home/user"), "docs  music\n")

    def test_empty_folder(self):
        self.assertEqual(run("ls home/user/music"), "")

    def test_file(self):
        self.assertEqual(run("ls /etc/hosts"), "/etc/hosts\n")

    def test_long(self):
        output = run("ls -l")
        self.assertIn("d      1 etc", output)
        self.assertIn("-      5 readme.txt", output)

    def test_missing(self):
        output = run("ls нет")
        self.assertIn("ls: нет: нет такого файла или папки", output)

    def test_hidden_not_shown(self):
        self.assertNotIn(".profile", run("ls"))
        self.assertNotIn(".profile", run("ls -l"))

    def test_all(self):
        output = run("ls -a")
        self.assertEqual(output, ".  ..  .profile  big.bin  etc  home  readme.txt\n")

    def test_all_in_folder(self):
        self.assertEqual(run("ls -a home"), ".  ..  user\n")

    def test_long_size_in_bytes(self):
        self.assertIn("-   2048 big.bin", run("ls -l"))

    def test_human(self):
        output = run("ls -lh")
        self.assertIn("-   2.0K big.bin", output)
        self.assertIn("-      5 readme.txt", output)

    def test_human_without_long(self):
        self.assertEqual(run("ls -h"), run("ls"))

    def test_long_all(self):
        output = run("ls -la home")
        self.assertIn("d      1 .", output)
        self.assertIn("d      5 ..", output)
        self.assertIn("d      2 user", output)

    def test_keys_in_any_order(self):
        expected = run("ls -lha")
        self.assertIn("-   2.0K big.bin", expected)
        self.assertIn("-      6 .profile", expected)
        self.assertEqual(run("ls -hal"), expected)
        self.assertEqual(run("ls -l -h -a"), expected)
        self.assertEqual(run("ls -a -lh"), expected)

    def test_keys_after_path(self):
        self.assertEqual(run("ls etc -l"), run("ls -l etc"))

    def test_human_on_file(self):
        self.assertEqual(run("ls -lh big.bin"), "-   2.0K big.bin\n")

    def test_human_size(self):
        self.assertEqual(main.human_size(0), "0")
        self.assertEqual(main.human_size(1023), "1023")
        self.assertEqual(main.human_size(1536), "1.5K")
        self.assertEqual(main.human_size(20 * 1024), "20K")
        self.assertEqual(main.human_size(3 * 1024 * 1024), "3.0M")

    def test_bad_key(self):
        self.assertIn("ls: неверный ключ -x", run("ls -x"))

    def test_bad_key_in_group(self):
        output = run("ls -lax")
        self.assertEqual(output, "ls: неверный ключ -x\n")

    def test_too_many_args(self):
        self.assertIn("слишком много аргументов", run("ls etc home"))


class TestCd(unittest.TestCase):
    def setUp(self):
        make_test_vfs()

    def test_go_down_and_up(self):
        run("cd home/user/docs")
        self.assertEqual(main.current_dir, ["home", "user", "docs"])
        run("cd ..")
        self.assertEqual(main.current_dir, ["home", "user"])

    def test_without_args(self):
        main.current_dir = ["home", "user"]
        run("cd")
        self.assertEqual(main.current_dir, [])

    def test_prompt(self):
        run("cd home/user")
        self.assertTrue(main.make_prompt().endswith(":~/home/user$ "))

    def test_ls_after_cd(self):
        run("cd home")
        self.assertEqual(run("ls"), "user\n")

    def test_missing(self):
        output = run("cd нет")
        self.assertIn("cd: нет: нет такого файла или папки", output)
        self.assertEqual(main.current_dir, [])

    def test_file(self):
        self.assertIn("cd: readme.txt: это не папка", run("cd readme.txt"))


class TestTree(unittest.TestCase):
    def setUp(self):
        make_test_vfs()

    def test_folder(self):
        output = run("tree home")
        expected = ("home\n"
                    "└── user\n"
                    "    ├── docs\n"
                    "    │   └── report.txt\n"
                    "    └── music\n"
                    "\n"
                    "папок 3, файлов 1\n")
        self.assertEqual(output, expected)

    def test_current(self):
        output = run("tree")
        self.assertTrue(output.startswith(".\n"))
        self.assertIn("├── etc", output)
        self.assertIn("└── readme.txt", output)
        self.assertIn("папок 5, файлов 3", output)

    def test_file(self):
        self.assertIn("это не папка", run("tree readme.txt"))

    def test_missing(self):
        self.assertIn("нет такого файла или папки", run("tree нет"))

    def test_too_many_args(self):
        self.assertIn("слишком много аргументов", run("tree a b"))


class TestDate(unittest.TestCase):
    def test_default(self):
        output = run("date")
        year = str(time.localtime().tm_year)
        self.assertIn(year, output)

    def test_format(self):
        expected = time.strftime("%Y") + "\n"
        self.assertEqual(run("date +%Y"), expected)

    def test_bad_format(self):
        self.assertIn("date: неверный формат 'abc'", run("date abc"))

    def test_too_many_args(self):
        self.assertIn("слишком много аргументов", run("date a b"))


class TestCal(unittest.TestCase):
    def test_month(self):
        lines = run("cal 2 2024").split("\n")
        self.assertEqual(lines[0].strip(), "Февраль 2024")
        self.assertEqual(lines[1], "Пн Вт Ср Чт Пт Сб Вс")
        self.assertEqual(lines[2], "          1  2  3  4")
        self.assertEqual(lines[6], "26 27 28 29")

    def test_current(self):
        month = main.MONTHS[time.localtime().tm_mon - 1]
        self.assertIn(month, run("cal"))

    def test_bad_month(self):
        self.assertIn("cal: 13: неверный месяц", run("cal 13 2026"))

    def test_bad_year(self):
        self.assertIn("cal: abc: неверный год", run("cal 1 abc"))

    def test_wrong_args(self):
        self.assertIn("использование: cal", run("cal 2026"))


if __name__ == "__main__":
    unittest.main()
