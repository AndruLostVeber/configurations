#!/bin/sh
cd "$(dirname "$0")/.." || exit 1

echo "=== минимальная VFS ==="
./run.sh --vfs vfs/minimal < /dev/null

echo "=== VFS из нескольких файлов ==="
./run.sh --vfs vfs/files < /dev/null

echo "=== VFS с четырьмя уровнями папок ==="
./run.sh --vfs vfs/deep < /dev/null

echo "=== без VFS ==="
./run.sh < /dev/null
