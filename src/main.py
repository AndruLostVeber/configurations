import argparse
import re
import sys
import xml.etree.ElementTree as element_tree
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from nuget import (
    PACKAGE_ID,
    VERSION,
    dependency_version,
    direct_dependencies,
    normalize_version,
    package_base,
)


TEST_PACKAGE = r"[A-Z]"
DIRECT_STAGE = 2


def read_yaml(path):
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def read_config(path):
    config = read_yaml(path)
    if not isinstance(config, dict):
        raise ValueError("Конфиг должен содержать пары ключ-значение")

    for key in ("test_mode", "ascii_tree"):
        if type(config.get(key)) is not bool:
            raise ValueError(f"{key}: укажите true или false")

    for key in ("package", "repository", "version", "output_file"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip() or "\0" in value:
            raise ValueError(f"{key}: укажите непустую строку")
        config[key] = value.strip()

    validate_config_values(config)
    return config


def validate_config_values(config):
    pattern = TEST_PACKAGE if config["test_mode"] else PACKAGE_ID
    if not re.fullmatch(pattern, config["package"]):
        raise ValueError("package: неверное имя пакета")
    if not re.fullmatch(VERSION, config["version"]):
        raise ValueError("version: укажите версию, например \"1.0.0\"")
    if not re.fullmatch(r'[^/\\:*?"<>|]+\.svg', config["output_file"]):
        raise ValueError("output_file: укажите имя файла с расширением .svg")


def repository_path(config, folder):
    source = config["repository"]
    if config["test_mode"]:
        path = folder / source
        if not path.is_file():
            raise ValueError(f"repository: файл {path} не найден")
        return path

    try:
        url = urlsplit(source)
        if url.scheme in ("http", "https") and url.hostname:
            if not any(char.isspace() for char in source) and url.port != 0:
                return source
    except ValueError:
        pass
    raise ValueError("repository: укажите URL индекса NuGet")


def read_test_repository(path):
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("repository: нужен словарь пакетов и зависимостей")
    for name, dependencies in data.items():
        if not isinstance(name, str) or not re.fullmatch(TEST_PACKAGE, name):
            raise ValueError(f"repository: неверное имя пакета {name}")
        if not isinstance(dependencies, list):
            raise ValueError(f"repository: зависимости {name} задаются списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in data:
                raise ValueError(f"repository: пакет {dependency} не описан")
    return data


def bfs(level, graph, get_dependencies):
    if not level:
        return graph

    next_level = []
    for package in level:
        if package in graph:
            continue
        graph[package] = get_dependencies(package)
        for dependency in graph[package]:
            if dependency not in graph:
                next_level.append(dependency)
    return bfs(next_level, graph, get_dependencies)


def print_graph(graph):
    for name, dependencies in graph.items():
        print(f"{name}: {', '.join(dependencies) or '—'}")


def run_nuget(stage, config, repository):
    base = package_base(repository)
    name = config["package"].lower()
    version = normalize_version(config["version"])

    if stage == DIRECT_STAGE:
        dependencies = direct_dependencies(base, name, version)
        for package, requirement in dependencies:
            print(f"{package} {requirement}".strip())
        if not dependencies:
            print("Прямых зависимостей нет")
        return

    versions = {}

    def get_dependencies(node):
        package, version = node.split("@")
        result = []
        for name, requirement in direct_dependencies(base, package, version):
            name = name.lower()
            key = (name, requirement)
            if key not in versions:
                versions[key] = dependency_version(base, name, requirement)
            dependency = f"{name}@{versions[key]}"
            if dependency not in result:
                result.append(dependency)
        return result

    print_graph(bfs([f"{name}@{version}"], {}, get_dependencies))


def run(stage, config_path):
    config = read_config(config_path)
    repository = repository_path(config, config_path.parent)
    if stage == 1:
        for key in ("package", "repository", "test_mode", "version",
                    "output_file", "ascii_tree"):
            print(f"{key}: {config[key]}")
    elif config["test_mode"]:
        if stage == DIRECT_STAGE:
            raise ValueError("test_mode: для этапа 2 укажите false")
        data = read_test_repository(repository)
        name = config["package"]
        if name not in data:
            raise ValueError(f"Пакет {name} не найден")
        print_graph(bfs([name], {}, data.__getitem__))
    else:
        run_nuget(stage, config, repository)


def main():
    parser = argparse.ArgumentParser(
        description="Зависимости NuGet, вариант 21"
    )
    parser.add_argument("stage", type=int, choices=(1, DIRECT_STAGE, 3))
    default_config = Path(__file__).resolve().parents[1] / "config.yml"
    parser.add_argument("config", type=Path, nargs="?", default=default_config)
    args = parser.parse_args()

    try:
        run(args.stage, args.config)
    except (
        OSError, ValueError, KeyError, element_tree.ParseError, yaml.YAMLError
    ) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
