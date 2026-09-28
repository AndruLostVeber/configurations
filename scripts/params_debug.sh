#!/bin/sh
cd "$(dirname "$0")/.." || exit 1

echo "=== без параметров ==="
./run.sh < /dev/null

echo "=== только --vfs ==="
./run.sh --vfs vfs/minimal < /dev/null

echo "=== только --script ==="
./run.sh --script startup/exit.txt

echo "=== оба параметра ==="
./run.sh --vfs vfs/minimal --script startup/exit.txt
