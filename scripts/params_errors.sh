#!/bin/sh
cd "$(dirname "$0")/.." || exit 1

echo "=== справка ==="
./run.sh -h
./run.sh --help

echo "=== неизвестный параметр ==="
./run.sh --color
echo "код возврата: $?"

echo "=== не указано значение --vfs ==="
./run.sh --vfs
echo "код возврата: $?"

echo "=== не указано значение --script ==="
./run.sh --vfs vfs/minimal --script
echo "код возврата: $?"

echo "=== скрипт не найден ==="
./run.sh --vfs vfs/minimal --script startup/no_such_file.txt
echo "код возврата: $?"
