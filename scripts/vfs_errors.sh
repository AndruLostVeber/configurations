#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
mkdir -p out

echo "=== папка VFS не найдена ==="
./run.sh --vfs vfs/no_such_folder < /dev/null
echo "код возврата: $?"

echo "=== вместо папки указан файл минимальной VFS ==="
./run.sh --vfs vfs/minimal/hello.txt < /dev/null
echo "код возврата: $?"

echo "=== вместо папки указан файл из VFS с несколькими файлами ==="
./run.sh --vfs vfs/files/notes.txt < /dev/null
echo "код возврата: $?"

echo "=== ошибки vfs-save на VFS с четырьмя уровнями ==="
printf 'vfs-save\nvfs-save a b\nvfs-save /нельзя/сюда/писать\nexit\n' \
  > out/errors.txt
./run.sh --vfs vfs/deep --script out/errors.txt
