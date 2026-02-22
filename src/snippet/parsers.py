import os
import re
from collections import OrderedDict

import pyparsing as pp

from snippet.models import Data, PlaceholderFormat


class ArgumentFormatParser:
    """
    A argument may have the following format*:

        ARGUMENTS = <PLACEHOLDER>=<VALUE> [<VALUE>...] <ARGUMENTS> | <PLACEHOLDER>:<FILE> <ARGUMENTS>

        PLACEHOLDER = The name of the placeholder to which values should be assigned.
        VALUE       = A list of characters.
        FILE        = A relative or absolute filename which needs to exist.

    *) optional parts are denoted with square brackets and parts which can be repeated are marked with three dots.
    """

    def parse(self, format_argument: str) -> dict:
        """
        Parses the argument and adds it into a dict with it's placeholder name and the associated values.

        :param format_argument: the format arguments (e.g. "a b", "ARG1=a b", "ARG2:test.txt")
        :return: a dict with placeholders and a list of values (e.g. {'': ['a b']}, {'ARG1': ['a b']},
                 {'ARG2': ['line1', 'line2'] }).
        """
        placeholder, separator, value = re.findall(r"(?:(\w+)([=:]))?(.*)", format_argument).pop(0)
        return {
            "=": self._parse_placeholder_value,
            ":": self._parse_placeholder_file,
            "": self._parse_value
        }.get(separator)(placeholder, value)

    def _parse_placeholder_value(self, placeholder: str, value: str) -> dict:
        return {placeholder: value}

    def _parse_placeholder_file(self, placeholder: str, value: str) -> dict:
        file = os.path.expanduser(value)
        if not os.path.isfile(file):
            raise Exception(
                "Parsing placeholder '{}' failed! The file '{}' was not found!".format(placeholder, file))

        try:
            data = Data()
            with open(file) as f:
                for value in f.read().splitlines():
                    data.append(placeholder, value)
            return data
        except Exception:
            raise Exception(
                "Parsing placeholder '{}' failed! The file '{}' has an invalid format!".format(placeholder, file))

    def _parse_value(self, placeholder: str, value: str) -> dict:
        return {"": value}


class PlaceholderFormatParser:
    """ Parses a format string into a list of placeholders. """

    # A set of tokens
    LT, GT, EQ, PIPE, COLON = map(pp.Suppress, "<>=|:")

    # A quoted string. Nothing special about that
    quoted_string = pp.QuotedString('\'') | pp.QuotedString('"')

    # Defines how a placeholder name or codec name should look like
    name = pp.Word(pp.alphas, pp.alphanums + "_")

    # Defines how a placeholder can be marked as repeatable
    repeatable = pp.Combine("...").setResultsName("repeatable")

    # Defines how codecs and their arguments can be specified
    codecs = pp.ZeroOrMore(pp.Group(PIPE + (name + pp.ZeroOrMore(COLON + quoted_string)))).setResultsName("codecs")

    # Defines how a default value can be specified
    default = pp.Combine(EQ + quoted_string).setResultsName("default")

    # Defines how a placeholder format should look like
    placeholder_format = pp.Combine(
        LT + \
        name.setResultsName("name").leaveWhitespace() + \
        pp.Optional(repeatable).leaveWhitespace() + \
        pp.Optional(codecs).leaveWhitespace() + \
        pp.Optional(default).leaveWhitespace() + \
        GT
    )

    def parse(self, format_string, opener="<", closer=">") -> list:

        def _parse_parts(parts, i=0) -> list:
            result = []
            for part in parts:
                if isinstance(part, str):
                    for placeholder in _parse_part(part, i):
                        result.append(placeholder)
                elif isinstance(part, list):
                    for placeholder in _parse_parts(part, i + 1):
                        result.append(placeholder)
            return result

        def _parse_part(part, i) -> list:
            from snippet.formatters import EscapedBracketCodec
            return list(
                OrderedDict.fromkeys(
                    PlaceholderFormat(placeholder_format, i == 0)
                    for placeholder_format in self.placeholder_format.scanString(
                        EscapedBracketCodec.encode(part, opener, closer) or "")))

        return _parse_parts(ParenthesesParser().parse(format_string))


class ParenthesesParser:
    """
    Parses a string with parentheses into a list.

    Example:

        "123[456[787]654]321" => ['123', ['456', ['787'], '654',] '321']

    """

    def parse(self, format_string, opener="[", closer="]") -> list:
        from snippet.formatters import EscapedBracketCodec

        def _parse_parentheses(format_string, i=0, balance=0):
            components = []
            start = i
            while i < len(format_string):
                c = format_string[i]
                if c == opener:
                    if i > 0:
                        components.append(EscapedBracketCodec.decode(format_string[start:i], opener, closer))
                    i, result = _parse_parentheses(format_string, i + 1, balance + 1)
                    components.append(result)
                    start = i + 1
                elif c == closer:
                    balance = balance - 1
                    components.append(EscapedBracketCodec.decode(format_string[start:i], opener, closer))
                    if balance < 0:
                        raise Exception("Unbalanced parentheses!")
                    return i, components
                i = i + 1

            components.append(EscapedBracketCodec.decode(format_string[start:len(format_string)], opener, closer))
            return i, components

        # Parts enclosed by square brackets (e.g. "<arg1> [<arg2>] <arg3>") are considered optional.
        # Since our parser can not differentiate between user-specified square brackets and those used for specifying
        # optional parts, the user needs to escape them (e.g. \[ or \]). To make parsing easier we encode escaped
        # square brackets here.
        return _parse_parentheses(EscapedBracketCodec.encode(format_string, opener, closer))[1]


class FormatStringParser:
    """
    Minimizes a format string by removing optional placeholders inside square brackets which do not have a value
    assigned nor a default value. The resulting format string does not contain square brackets anymore except those
    which were escaped by the user.

    Examples:

        # Value assigned via arguments includes optional part.
        FORMAT_STRING = 'A <arg> B'
        ARGUMENTS     = { 'arg': ['123', '456] }
        RESULT        = 'A <arg> B'

        # No value assigned removes optional part.
        FORMAT_STRING = 'A[ <arg> ]B'
        ARGUMENTS     = {}
        RESULT        = 'AB'

        # Value assigned via default specification includes optional part.
        FORMAT_STRING = 'A[ <arg='value'> ]B'
        ARGUMENTS     = {}
        RESULT        = 'A <arg> B'

        # Value assigned via default but empty value assigned via arguments removes optional part.
        FORMAT_STRING = 'A[ <arg='value'> ]B'
        ARGUMENTS     = { 'arg': [''] }
        RESULT        = 'AB'

        # No optional parts returns original format string.
        FORMAT_STRING = 'A <arg> B'
        ARGUMENTS     = {}
        RESULT        = 'A <arg> B'

        # No placeholders returns original format string.
        FORMAT_STRING = 'A B'
        ARGUMENTS     = {}
        RESULT        = 'A B'

    """

    def __init__(self, config):
        self._logger = config.logger

    def parse(self, format_string: str, arguments: dict) -> str:
        """
        Parses a format string and removes placeholders inside square brackets which do not have a value assigned.

        :param format_string: the format string (e.g. "A <arg1> B")
        :param arguments: a dictionary with argument names as key and booleans as value.
                          The boolean value specifies whether the argument is non-empty (True = non-empty).
        """
        lines = []
        for line in format_string.splitlines():
            if line.startswith("#"):
                lines.append(line)
                continue

            parentheses = ParenthesesParser().parse(line)
            if not parentheses:
                self._logger.debug("No optional arguments found in format string.")
                lines.append(format_string)
                continue

            essentials = self._remove_optionals(parentheses, arguments)
            if not essentials:
                self._logger.debug("Not all essential arguments are set.")
                lines.append(format_string)
                continue

            lines.append("".join(self._flatten_list(essentials)))

        return os.linesep.join(lines)

    def _remove_optionals(self, parts, arguments, required=True):
        result = []
        for part in parts:
            if isinstance(part, str):
                placeholders = PlaceholderFormatParser().parse(part)
                for placeholder in placeholders:
                    not_defined = placeholder.name not in arguments and not placeholder.default
                    if not_defined:
                        # Ignore argument if it is not defined nor a default value is set.
                        # $ snippet -f  "<arg>"             # ignore
                        # $ snippet -f  "<arg='default'>"   # do not ignore
                        self._logger.debug("{}: No argument defined.".format(placeholder.name))
                        return []
                    has_empty_argument = placeholder.name in arguments and not arguments[placeholder.name]
                    if has_empty_argument and not required:
                        # Ignore argument if it is empty and optional.
                        # $ snippet -f "a[<arg>]b" arg=
                        self._logger.debug("{}: Empty argument supplied and optional.".format(placeholder.name))
                        return []
                result.append(part)
            elif isinstance(part, list):
                # The first list of parts is required. Everything beyond is optional.
                # $ snippet -f "a<arg>b[c<arg>d]" arg=
                result.append(self._remove_optionals(part, arguments, required=False))
        return result

    def _flatten_list(self, lst):
        result = []
        for item in lst:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                for i in self._flatten_list(item):
                    result.append(i)
        return result
