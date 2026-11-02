# Вариант 21. Граф зависимостей NuGet

Этап 2.2 читает прямые зависимости указанной версии пакета из файла `.nuspec`.

## Установка

Нужен Python 3.9 или новее. Сборка не требуется.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Запуск

```sh
./run.sh 1
./run.sh 2
```

Пример использует `Microsoft.Bcl.AsyncInterfaces` версии `8.0.0`. Вывод содержит прямую зависимость `System.Threading.Tasks.Extensions 4.5.4`.

## Настройки YAML

| Ключ | Значение |
| --- | --- |
| `package` | Имя пакета. В тестовом режиме одна заглавная латинская буква |
| `repository` | URL индекса NuGet v3 или путь к тестовому YAML относительно конфига |
| `test_mode` | `true` для локального графа, `false` для NuGet |
| `version` | Версия пакета в кавычках, например `"8.0.0"`. В тестовом графе версии не используются |
| `output_file` | Имя SVG-файла для этапа 5 |
| `ascii_tree` | `true` или `false` для режима ASCII-дерева на этапе 5 |

## Тесты

```sh
.venv/bin/python -m unittest discover -s tests
```

Тесты проверяют конфиг и чтение зависимостей через локальный HTTP-сервер.
