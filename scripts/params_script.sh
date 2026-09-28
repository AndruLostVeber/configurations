#!/bin/sh
cd "$(dirname "$0")/.." || exit 1

echo "=== стартовый скрипт без --vfs ==="
./run.sh --script startup/stage2.txt < /dev/null

echo "=== стартовый скрипт вместе с --vfs ==="
./run.sh --vfs vfs/minimal --script startup/stage2.txt < /dev/null

echo "=== скрипт с командой exit ==="
./run.sh --vfs vfs/minimal --script startup/exit.txt
echo "код возврата: $?"
