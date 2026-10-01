import getpass
import os
import shlex
import socket
import sys


vfs = {}


def make_prompt():
    user = getpass.getuser()
    host = socket.gethostname()
    short_host = host.split(".")[0]
    return f"{user}@{short_host}:~$ "


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


def print_stub(name, args):
    if len(args) == 0:
        print(name + ": аргументов нет")
    else:
        print(name + ": аргументы: " + " ".join(args))


def cmd_cd(args):
    if len(args) > 1:
        print("cd: слишком много аргументов")
        return
    print_stub("cd", args)


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
    if name == "exit":
        return cmd_exit(args)
    if name == "ls":
        print_stub("ls", args)
    elif name == "cd":
        cmd_cd(args)
    elif name == "vfs-save":
        cmd_vfs_save(args)
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


def run_script(path, prompt):
    for line in read_script(path).split("\n"):
        line = line.strip()
        if line == "":
            continue
        print(prompt + line)
        code = run_line(line)
        if code is not None:
            return code
    return None


def repl(prompt):
    while True:
        try:
            line = input(prompt)
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
    prompt = make_prompt()
    if settings["script"] is not None:
        code = run_script(settings["script"], prompt)
        if code is not None:
            return code
    return repl(prompt)


if __name__ == "__main__":
    sys.exit(main())
