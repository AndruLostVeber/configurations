import argparse
import re
import sys
import xml.etree.ElementTree as element_tree
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from nuget import (
    PACKAGE_ID, VERSION, direct_dependencies, normalize_version, package_base
)


TEST_PACKAGE = r"[A-Z]"


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


def run_nuget(config, repository):
    base = package_base(repository)
    name = config["package"].lower()
    version = normalize_version(config["version"])

    dependencies = direct_dependencies(base, name, version)
    for package, requirement in dependencies:
        print(f"{package} {requirement}".strip())
    if not dependencies:
        print("Прямых зависимостей нет")

def run(stage, config_path):
    config = read_config(config_path)
    repository = repository_path(config, config_path.parent)
    if stage == 1:
        for key in ("package", "repository", "test_mode", "version",
                    "output_file", "ascii_tree"):
            print(f"{key}: {config[key]}")
    elif config["test_mode"]:
        raise ValueError("test_mode: для этапа 2 укажите false")
    else:
        run_nuget(config, repository)


def main():
    parser = argparse.ArgumentParser(
        description="Зависимости NuGet, вариант 21"
    )
    parser.add_argument("stage", type=int, choices=(1, 2))
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
