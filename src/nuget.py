import json
import re
import xml.etree.ElementTree as element_tree
from urllib.request import urlopen


PACKAGE_ID = r"[a-zA-Z0-9_]+(?:[.-][a-zA-Z0-9_]+)*"
VERSION = (
    r"[0-9]+(?:\.[0-9]+){0,3}"
    r"(-[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?"
    r"(\+[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?"
)


def version_parts(version):
    if not re.fullmatch(VERSION, version):
        raise ValueError(f"Неверная версия NuGet: {version}")
    number, _, label = version.lower().split("+")[0].partition("-")
    parts = [int(part) for part in number.split(".")]
    parts += [0] * (4 - len(parts))
    return parts, label


def normalize_version(version):
    parts, label = version_parts(version)
    if parts[-1] == 0:
        parts.pop()
    number = ".".join(str(part) for part in parts)
    return number + "-" + label if label else number


def download(url):
    with urlopen(url, timeout=15) as response:
        return response.read()


def package_base(repository):
    index = json.loads(download(repository))
    for resource in index["resources"]:
        if resource["@type"] == "PackageBaseAddress/3.0.0":
            return resource["@id"].rstrip("/")
    raise ValueError("repository: не найден PackageBaseAddress в индексе NuGet")


def direct_dependencies(base, package, version):
    url = f"{base}/{package}/{version}/{package}.nuspec"
    root = element_tree.fromstring(download(url))
    result = []
    path = "./{*}metadata/{*}dependencies//{*}dependency"
    for node in root.findall(path):
        name = node.attrib["id"]
        if not re.fullmatch(PACKAGE_ID, name):
            raise ValueError(f"Неверное имя зависимости: {name}")
        dependency = (name, node.get("version", "").strip())
        if dependency not in result:
            result.append(dependency)
    return result
