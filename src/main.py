import getpass
import os
import shlex
import socket
import sys


def make_prompt():
    user = getpass.getuser()
    host = socket.gethostname()
    short_host = host.split(".")[0]
    return user + "@" + short_host + ":~$ "


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
        print("exit: " + args[0] + ": нужен числовой аргумент")
        return None
    return int(args[0])


def run_command(parts):
    name = parts[0]
    args = parts[1:]
    if name == "exit":
        return cmd_exit(args)
    if name == "ls":
        print_stub("ls", args)
    elif name == "cd":
        cmd_cd(args)
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


def main():
    prompt = make_prompt()
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


if __name__ == "__main__":
    sys.exit(main())
