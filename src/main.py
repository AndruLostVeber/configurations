import calendar
import getpass
import os
import shlex
import socket
import sys
import time


FIRST_MONTH = 1
LAST_MONTH = 12
FIRST_YEAR = 1
LAST_YEAR = 9999
CAL_WIDTH = 20

WEEK_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
          "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
SHORT_MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг",
                "сен", "окт", "ноя", "дек"]

vfs = {}
current_dir = []


def current_dir_text():
    text = "~"
    for name in current_dir:
        text = text + "/" + name
    return text


def make_prompt():
    user = getpass.getuser()
    host = socket.gethostname()
    short_host = host.split(".")[0]
    return f"{user}@{short_host}:{current_dir_text()}$ "


def print_help():
    print("использование: main.py [--vfs ПУТЬ] [--script ПУТЬ]")
    print("  --vfs ПУТЬ     путь к физическому расположению VFS")
    print("  --script ПУТЬ  путь к стартовому скрипту")
    print("  -h, --help     показать эту справку")


def take_value(argv, position, name):
    if position + 1 >= len(argv):
        print("Ошибка: не указано значение параметра " + name)
        sys.exit(2)
    return argv[position + 1]


def parse_args(argv):
    settings = {"vfs": None, "script": None}
    position = 0
    while position < len(argv):
        name = argv[position]
        if name == "--vfs":
            settings["vfs"] = take_value(argv, position, name)
            position = position + 2
        elif name == "--script":
            settings["script"] = take_value(argv, position, name)
            position = position + 2
        elif name == "-h" or name == "--help":
            print_help()
            sys.exit(0)
        else:
            print("Ошибка: неизвестный параметр " + name)
            sys.exit(2)
    return settings


def describe(value):
    if value is None:
        return "не задан"
    return value


def print_settings(settings):
    print("[отладка] --vfs = " + describe(settings["vfs"]))
    print("[отладка] --script = " + describe(settings["script"]))


def list_folder(path):
    try:
        return sorted(os.listdir(path))
    except OSError:
        print("Ошибка загрузки VFS: не удалось открыть папку: " + path)
        sys.exit(1)


def read_file(path):
    try:
        with open(path, "rb") as source:
            return source.read()
    except OSError:
        print("Ошибка загрузки VFS: не удалось прочитать файл: " + path)
        sys.exit(1)


def read_folder(path):
    folder = {}
    for name in list_folder(path):
        full = os.path.join(path, name)
        if os.path.isdir(full):
            folder[name] = read_folder(full)
        elif os.path.isfile(full):
            folder[name] = read_file(full)
        else:
            print("Ошибка загрузки VFS: неверный формат: " + full)
            sys.exit(1)
    return folder


def load_vfs(path):
    if not os.path.exists(path):
        print("Ошибка загрузки VFS: папка не найдена: " + path)
        sys.exit(1)
    if not os.path.isdir(path):
        print("Ошибка загрузки VFS: это не папка: " + path)
        sys.exit(1)
    return read_folder(path)


def save_folder(folder, path):
    os.makedirs(path, exist_ok=True)
    for name in folder:
        full = os.path.join(path, name)
        if isinstance(folder[name], dict):
            save_folder(folder[name], full)
        else:
            with open(full, "wb") as target:
                target.write(folder[name])


def count_items(folder):
    files = 0
    folders = 0
    for name in folder:
        if isinstance(folder[name], dict):
            folders = folders + 1
            inner_files, inner_folders = count_items(folder[name])
            files = files + inner_files
            folders = folders + inner_folders
        else:
            files = files + 1
    return files, folders


def split_path(path):
    if path == "~" or path.startswith("~/"):
        path = "/" + path[1:]
    if path.startswith("/"):
        parts = []
    else:
        parts = list(current_dir)
    for name in path.split("/"):
        if name == "" or name == ".":
            continue
        if name == "..":
            if len(parts) > 0:
                parts.pop()
        else:
            parts.append(name)
    return parts


def find_node(parts):
    node = vfs
    for name in parts:
        if not isinstance(node, dict) or name not in node:
            return None
        node = node[name]
    return node


def is_folder(node):
    return isinstance(node, dict)


def expand_vars(line):
    result = ""
    position = 0
    while position < len(line):
        if line[position] != "$":
            result = result + line[position]
            position = position + 1
            continue
        position = position + 1
        name = ""
        while position < len(line) and is_name_char(line[position]):
            name = name + line[position]
            position = position + 1
        if name == "":
            result = result + "$"
        else:
            result = result + os.environ.get(name, "")
    return result


def is_name_char(symbol):
    return symbol.isalnum() or symbol == "_"


def split_line(line):
    return shlex.split(line)


LS_KEYS = "lha"
SIZE_UNITS = ["K", "M", "G", "T"]


def parse_ls_args(args):
    keys = ""
    paths = []
    for arg in args:
        if arg.startswith("-") and arg != "-":
            for key in arg[1:]:
                if key not in LS_KEYS:
                    print("ls: неверный ключ -" + key)
                    return None
            keys = keys + arg[1:]
        else:
            paths.append(arg)
    if len(paths) > 1:
        print("ls: слишком много аргументов")
        return None
    if len(paths) == 0:
        paths.append(".")
    return keys, paths[0]


def human_size(size):
    if size < 1024:
        return str(size)
    value = size
    unit = ""
    for name in SIZE_UNITS:
        if value < 1024:
            break
        value = value / 1024
        unit = name
    if value < 10:
        return f"{value:.1f}{unit}"
    return f"{round(value)}{unit}"


def print_ls_line(name, node, keys):
    if "l" not in keys:
        print(name)
        return
    if is_folder(node):
        print("d " + str(len(node)).rjust(6) + " " + name)
        return
    size = str(len(node))
    if "h" in keys:
        size = human_size(len(node))
    print("- " + size.rjust(6) + " " + name)


def ls_entries(parts, node, keys):
    entries = []
    if "a" in keys:
        entries.append((".", node))
        entries.append(("..", find_node(parts[:-1])))
    for name in sorted(node):
        if "a" in keys or not name.startswith("."):
            entries.append((name, node[name]))
    return entries


def cmd_ls(args):
    parsed = parse_ls_args(args)
    if parsed is None:
        return
    keys, path = parsed
    parts = split_path(path)
    node = find_node(parts)
    if node is None:
        print(f"ls: {path}: нет такого файла или папки")
        return
    if not is_folder(node):
        print_ls_line(path, node, keys)
        return
    entries = ls_entries(parts, node, keys)
    if "l" in keys:
        for name, child in entries:
            print_ls_line(name, child, keys)
    elif len(entries) > 0:
        names = []
        for name, child in entries:
            names.append(name)
        print("  ".join(names))


def cmd_cd(args):
    global current_dir
    if len(args) > 1:
        print("cd: слишком много аргументов")
        return
    if len(args) == 0:
        current_dir = []
        return
    parts = split_path(args[0])
    node = find_node(parts)
    if node is None:
        print(f"cd: {args[0]}: нет такого файла или папки")
        return
    if not is_folder(node):
        print(f"cd: {args[0]}: это не папка")
        return
    current_dir = parts


def format_date(now):
    day = WEEK_DAYS[now.tm_wday]
    month = SHORT_MONTHS[now.tm_mon - 1]
    clock = time.strftime("%H:%M:%S %Z", now)
    return f"{day} {now.tm_mday:02d} {month} {now.tm_year} {clock}"


def cmd_date(args):
    if len(args) > 1:
        print("date: слишком много аргументов")
        return
    now = time.localtime()
    if len(args) == 0:
        print(format_date(now))
        return
    if not args[0].startswith("+"):
        print(f"date: неверный формат '{args[0]}'")
        return
    try:
        print(time.strftime(args[0][1:], now))
    except ValueError:
        print(f"date: неверный формат '{args[0]}'")


def parse_number(text, smallest, biggest):
    if not text.isdigit():
        return None
    number = int(text)
    if number < smallest or number > biggest:
        return None
    return number


def print_month(month, year):
    title = MONTHS[month - 1] + " " + str(year)
    print(title.center(CAL_WIDTH).rstrip())
    print(" ".join(WEEK_DAYS))
    for week in calendar.monthcalendar(year, month):
        line = ""
        for day in week:
            if day == 0:
                line = line + "   "
            else:
                line = line + str(day).rjust(2) + " "
        print(line.rstrip())


def cmd_cal(args):
    if len(args) == 0:
        now = time.localtime()
        print_month(now.tm_mon, now.tm_year)
        return
    if len(args) != 2:
        print("использование: cal [МЕСЯЦ ГОД]")
        return
    month = parse_number(args[0], FIRST_MONTH, LAST_MONTH)
    if month is None:
        print(f"cal: {args[0]}: неверный месяц")
        return
    year = parse_number(args[1], FIRST_YEAR, LAST_YEAR)
    if year is None:
        print(f"cal: {args[1]}: неверный год")
        return
    print_month(month, year)


def print_tree(folder, prefix):
    names = sorted(folder)
    for index in range(len(names)):
        name = names[index]
        if index == len(names) - 1:
            print(prefix + "└── " + name)
            inner_prefix = prefix + "    "
        else:
            print(prefix + "├── " + name)
            inner_prefix = prefix + "│   "
        if is_folder(folder[name]):
            print_tree(folder[name], inner_prefix)


def cmd_tree(args):
    if len(args) > 1:
        print("tree: слишком много аргументов")
        return
    path = "."
    if len(args) == 1:
        path = args[0]
    node = find_node(split_path(path))
    if node is None:
        print(f"tree: {path}: нет такого файла или папки")
        return
    if not is_folder(node):
        print(f"tree: {path}: это не папка")
        return
    print(path)
    print_tree(node, "")
    files, folders = count_items(node)
    print()
    print(f"папок {folders}, файлов {files}")


def cmd_exit(args):
    if len(args) > 1:
        print("exit: слишком много аргументов")
        return None
    if len(args) == 0:
        return 0
    if not args[0].isdigit():
        print(f"exit: {args[0]}: нужен числовой аргумент")
        return None
    return int(args[0])


def cmd_vfs_save(args):
    if len(args) != 1:
        print("использование: vfs-save ПУТЬ")
        return
    if len(vfs) == 0:
        print("vfs-save: VFS не загружена")
        return
    try:
        save_folder(vfs, args[0])
    except OSError:
        print("vfs-save: не удалось сохранить в '" + args[0] + "'")
        return
    print(f"VFS сохранена в {args[0]}")


def run_command(parts):
    name = parts[0]
    args = parts[1:]
    commands = {
        "ls": cmd_ls,
        "cd": cmd_cd,
        "date": cmd_date,
        "cal": cmd_cal,
        "tree": cmd_tree,
        "vfs-save": cmd_vfs_save,
    }
    if name == "exit":
        return cmd_exit(args)
    if name in commands:
        commands[name](args)
    else:
        print(name + ": команда не найдена")
    return None


def run_line(line):
    expanded = expand_vars(line)
    try:
        parts = split_line(expanded)
    except ValueError:
        print("ошибка синтаксиса: не закрыта кавычка")
        return None
    if len(parts) == 0:
        return None
    return run_command(parts)


def read_script(path):
    try:
        with open(path, encoding="utf-8") as script:
            return script.read()
    except (OSError, UnicodeDecodeError):
        print("Ошибка: не удалось прочитать скрипт " + path)
        sys.exit(1)


def run_script(path):
    for line in read_script(path).split("\n"):
        line = line.strip()
        if line == "":
            continue
        print(make_prompt() + line)
        code = run_line(line)
        if code is not None:
            return code
    return None


def repl():
    while True:
        try:
            line = input(make_prompt())
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        code = run_line(line)
        if code is not None:
            return code


def main():
    global vfs
    settings = parse_args(sys.argv[1:])
    print_settings(settings)
    if settings["vfs"] is not None:
        vfs = load_vfs(settings["vfs"])
        files, folders = count_items(vfs)
        print(f"[отладка] VFS загружена: папок {folders}, файлов {files}")
    if settings["script"] is not None:
        code = run_script(settings["script"])
        if code is not None:
            return code
    return repl()


if __name__ == "__main__":
    sys.exit(main())
