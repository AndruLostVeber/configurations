#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
rm -rf out
mkdir -p out

for name in minimal files deep; do
  echo "=== VFS $name: загрузка, сохранение, сравнение ==="
  printf 'vfs-save out/%s\nexit\n' "$name" > "out/save_$name.txt"
  ./run.sh --vfs "vfs/$name" --script "out/save_$name.txt"
  if diff -r "vfs/$name" "out/$name" > /dev/null; then
    echo "копия совпадает с оригиналом"
  else
    echo "копия отличается от оригинала"
  fi
  echo "оригинал на диске не изменился:"
  find "vfs/$name" -type f | sort
done
