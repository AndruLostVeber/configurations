"""Трансляция конфигурационного языка варианта 21 в TOML."""

from typing import Union

import pyparsing as pp

BINARY_BASE = 2
SINGLE_VALUE_COUNT = 1

ConfigValue = Union[int, list["ConfigValue"]]


def add_terms(
    source: str, position: int, terms: pp.ParseResults
) -> list[ConfigValue]:
    """Вычисляет сумму или возвращает значение единственного операнда."""
    if len(terms) == SINGLE_VALUE_COUNT:
        return list(terms)
    if not all(isinstance(term, int) for term in terms):
        raise pp.ParseFatalException(
            source, position, "сложение допускается только для чисел"
        )
    return [sum(terms)]


def absolute(source: str, position: int, args: pp.ParseResults) -> int:
    """Вычисляет модуль целого числа."""
    (value,) = args
    if not isinstance(value, int):
        raise pp.ParseFatalException(source, position, "abs ожидает число")
    return abs(value)


def make_value_parser(
    name: pp.ParserElement, constants: dict[str, ConfigValue]
) -> pp.ParserElement:
    """Описывает числа, массивы и константные выражения."""

    def resolve(
        source: str, position: int, names: pp.ParseResults
    ) -> list[ConfigValue]:
        """Подставляет значение ранее объявленной константы."""
        (key,) = names
        if key not in constants:
            raise pp.ParseFatalException(
                source, position, f"неизвестная константа {key!r}"
            )
        return [constants[key]]

    value = pp.Forward().set_name("значение")
    expression = pp.Forward().set_name("константное выражение")
    left, right = pp.Suppress.using_each("()")
    binary = pp.Regex(r"0[bB][01]+(?![a-zA-Z0-9_])").set_name(
        "двоичное число"
    ).set_parse_action(lambda tokens: int(*tokens, base=BINARY_BASE))
    decimal = pp.Regex(r"-?[0-9]+(?![a-zA-Z0-9_])").set_name(
        "десятичное число"
    ).set_parse_action(lambda tokens: int(*tokens))
    contents = pp.Group(pp.Opt(pp.DelimitedList(value)), aslist=True)
    array = (pp.Suppress(pp.Keyword("array")) + left) - contents - right

    reference = name.copy().set_parse_action(resolve)
    parens = left - expression - right
    modulus = (pp.Suppress(pp.Keyword("abs")) + left) - expression - right
    modulus.set_parse_action(absolute)
    atom = (binary | decimal | array | modulus | parens | reference)
    atom.set_name("операнд")
    terms = atom + pp.ZeroOrMore(pp.Suppress("+") - atom)
    expression <<= terms.set_parse_action(add_terms)

    calculated = pp.Suppress("?{") - expression - pp.Suppress("}")
    value <<= binary | array | calculated
    return value


def make_document_parser(constants: dict[str, ConfigValue]) -> pp.ParserElement:
    """Разбирает значения документа и сохраняет константы для подстановки."""

    def define(
        source: str, position: int, fields: pp.ParseResults
    ) -> list[ConfigValue]:
        """Добавляет объявление в таблицу констант."""
        key, value = fields
        if key in constants:
            raise pp.ParseFatalException(
                source, position, f"константа {key!r} уже объявлена"
            )
        constants[key] = value
        return []

    name = pp.Regex(r"[a-z][a-z0-9_]*").set_name("имя константы")
    value = make_value_parser(name, constants)
    begin = pp.Suppress("(") - pp.Suppress(pp.Keyword("define"))
    end = pp.Suppress(")") - pp.Suppress(";")
    definition = (begin - name - value - end).set_parse_action(define)

    document = pp.ZeroOrMore(definition | value)
    document.ignore(pp.Regex(r"/#[\s\S]*?#/"))
    return document.parse_with_tabs()


def format_value(value: ConfigValue) -> str:
    """Форматирует целые числа и вложенные массивы в синтаксисе TOML."""
    if isinstance(value, int):
        return str(value)
    return "[" + ", ".join(map(format_value, value)) + "]"


def translate(source: str) -> str:
    """Преобразует полный документ и сообщает позицию ошибки."""
    constants: dict[str, ConfigValue] = {}
    try:
        parsed = make_document_parser(constants).parse_string(
            source, parse_all=True
        )
    except pp.ParseBaseException as error:
        raise ValueError(
            f"Строка {error.lineno}, столбец {error.col}: {error.msg}"
        ) from error

    if not parsed:
        return ""
    values = list(parsed)
    if len(values) == SINGLE_VALUE_COUNT and isinstance(values[0], list):
        values = values[0]
    return f"values = {format_value(values)}\n"
