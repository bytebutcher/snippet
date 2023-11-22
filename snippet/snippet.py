#!/usr/bin/env python3
import codecs
import json
from inspect import signature

import argcomplete, argparse

from collections import defaultdict, OrderedDict, namedtuple

import os
import sys
from pathlib import Path
import logging
import shutil
import copy
import subprocess
import traceback

import re
import itertools
import shlex
import pyparsing as pp

from colorama import Fore, Style
from iterfzf import iterfzf

app_name = "snippet"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".snippet". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".snippet")
home_config_path = os.path.join(str(Path.home()), ".snippet")


def log_format_string(format_string, logger):
    logger.info(colorize("Format:", Fore.YELLOW))
    for line in format_string.split(os.linesep):
        if line.startswith("#"):
            logger.info(colorize("   {}".format(line), Fore.BLUE))
        else:
            logger.info(colorize("   {}".format(line), Fore.WHITE))


def log_format_template(format_template_name, logger):
    logger.info(colorize("Template:", Fore.YELLOW))
    logger.info(colorize("   {}".format(format_template_name), Fore.WHITE))


def colorize(string: str, color):
    """ Colorize a string. """
    return color + string + Style.RESET_ALL


def safe_join_path(*argv):
    """
    os.path.join does ignore everything prior to a component starting with a slash.
    This implementation does consider all components and normalizes the path.
    """
    return os.path.normpath(os.sep.join(argv))


def replace_within(string: str, replacement: str, start: int, end: int) -> str:
    """
    Return a copy of string with text replaced within the range of position start and end with the replacement string.

    string: the base string.
    replacement: the text which serves as replacement.
    start: the start position of the range with 0 <= start < len(text) && start <= end.
    end: the end position of the range with 0 <= end < len(text).
    """
    return string[:start] + replacement + string[end:]


def select_line(lines, query=None):
    """ Select format string from list of lines using iterfzf. """
    lines = [colorize(line, Fore.BLUE) if line.startswith("#") else line for line in lines.splitlines()]
    if len(lines) > 1:
        return iterfzf(reversed(lines), query=query, multi=True, ansi=True)
    else:
        return lines


def print_line(line):
    """ Color printing a line of the (evaluated) format string regarding comments. """
    if line.startswith("#"):
        print(colorize(line, Fore.BLUE), file=sys.stderr)
    else:
        print(line)


class Logger:

    # Static logger instance
    _instance = None

    @staticmethod
    def get_instance():
        if Logger._instance is None:
            raise ValueError("Logger instance not initialized. Call initialize first.")
        return Logger._instance

    @staticmethod
    def initialize(app_id, log_format, level):
        if Logger._instance is not None:
            raise ValueError("Logger instance already initialized.")
        Logger._instance = Logger(app_id, log_format, level)
        return Logger._instance

    def __init__(self, app_id, log_format, level):
        self.logger = logging.getLogger(app_id)
        self.handler = logging.StreamHandler(sys.stderr)
        self.handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(self.handler)
        self._set_level(level)

    def _set_level(self, level):
        self.logger.setLevel(level)
        self.handler.setLevel(level)

    def _get_level(self):
        return self.logger.level

    def info(self, message):
        self.logger.info(colorize(" INFO: ", Fore.GREEN) + message)

    def debug(self, message):
        self.logger.debug(colorize("DEBUG: {}".format(message), Fore.LIGHTBLACK_EX))

    def warning(self, message):
        self.logger.warning(colorize(" WARN: ", Fore.LIGHTYELLOW_EX) + message)

    def error(self, message):
        self.logger.info(colorize("ERROR: ", Fore.RED) + message)

    level = property(fset=_set_level, fget=_get_level)


def log_method_call():
    """
    A decorator for logging method or function calls.

    It logs the name of the method/function and its arguments before the call is executed.
    Can be applied to both standalone functions and class methods.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = Logger.get_instance()
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"Calling {func.__name__}({signature})")
            return func(*args, **kwargs)

        return wrapper

    return decorator


class EscapedBracketCodec:

    @staticmethod
    def encode(str, opener, closer):
        return str.replace('\\' + opener, chr(14)).replace('\\' + closer, chr(15))

    @staticmethod
    def decode(str, opener, closer):
        return str.replace(chr(14), '\\' + opener).replace(chr(15), '\\' + closer)


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


class PlaceholderFormat:
    """ An object representation of a placeholder. """

    Codec = namedtuple('Codec', ['name', 'arguments'])

    def __init__(self, format_string: str, required):
        try:
            data, self.start, self.end = format_string
            self.name = data.get("name").lower()  # Required
            self.codecs = [
                PlaceholderFormat.Codec(codec[0].lower(), codec[1:]) for codec in data.get("codecs", [])]  # Optional
            self.default = data.get("default")  # Optional
            self.repeatable = "repeatable" in data  # True or False
            self.required = required  # True or False
        except Exception:
            raise Exception("Transforming placeholders failed! Invalid format!")

    def __str__(self):
        return json.dumps(self.__dict__)


class Data(defaultdict):
    """ Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') } """

    def __init__(self):
        super().__init__(list)

    def append(self, placeholder, values):
        placeholder_key = placeholder.lower()
        if isinstance(values, list):
            for value in values:
                self[placeholder_key].append(value)
        else:
            if values.startswith('\\(') and values.endswith('\\)'):
                for value in shlex.split(values[2:-2]):
                    self[placeholder_key].append(value)
            else:
                self[placeholder_key].append(values)

    def to_data_frame(self):
        # Create table data with equally sized lists by filling them with empty strings
        # e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','','') }
        table_data = Data()
        max_length = max([len(self[key]) for key in self.keys()])
        for placeholder in self.keys():
            for item in self[placeholder]:
                table_data.append(placeholder, item)
            for i in range(0, max_length - len(self[placeholder])):
                table_data.append(placeholder, "")

        return table_data


class Codec(object):
    """ Abstract codec class used for individual codecs. """

    def __init__(self, author, dependencies):
        self.name = self.__class__.__name__
        self.author = author
        self.dependencies = dependencies

    def run(self, text, *args):
        pass


class StringCodec(Codec):
    pass


class ListCodec(Codec):
    pass


class Config(object):

    def __init__(self, app_name, paths, log_level):
        self.paths = paths
        self.format_template_paths = [safe_join_path(path, "templates") for path in paths]
        self.codec_paths = [safe_join_path(path, "codecs") for path in paths]
        self.logger = Logger.initialize(app_name, "%(msg)s", log_level)
        self.profile = self._load_profile()
        self.codecs = self._load_codecs()
        self._reserved_placeholder_values = []

    def _load_profile(self):
        for profile_path in self.paths:
            profile_file = safe_join_path(profile_path, "snippet_profile" + ".py")
            if os.path.exists(profile_file):
                try:
                    self.logger.debug("Loading profile at {} ...".format(profile_path))
                    # Since the path may contain special characters which can not be processed by the __import__
                    # function we temporarily add the path in which the profile.py is located to the PATH.
                    sys.path.append(profile_path)
                    profile = __import__("snippet_profile").Profile()
                    sys.path.pop()
                    return profile
                except:
                    self.logger.warning("Loading profile at {} failed!".format(profile_path))
        return None

    def _load_codecs(self):

        codecs = {}
        for codec_path in self.codec_paths:
            # Since the path may contain special characters which can not be processed by the __import__
            # function we temporarily add the path in which the codecs are located to the PATH.
            if os.path.exists(codec_path):
                sys.path.append(codec_path)
                filepath = codec_path
                for r, d, f in os.walk(filepath):
                    for file in f:
                        filename, ext = os.path.splitext(file)
                        if ext == ".py":
                            try:
                                self.logger.debug("Loading codec {} at {}...".format(filename, filepath))
                                codecs[filename] = getattr(__import__(filename), "Codec")()
                            except Exception:
                                self.logger.warning("Loading codec {} failed!".format(filename))
                sys.path.pop()

        return codecs

    def _get_template_file(self, format_template_name):
        if not format_template_name:
            return None

        if format_template_name.endswith(".snippet"):
            # Consider template files in the current working directory.
            format_template_file = safe_join_path(os.getcwd(), format_template_name)
            return format_template_file if os.path.isfile(format_template_file) else None

        for format_template_path in self.format_template_paths:
            format_template_file = safe_join_path(format_template_path, format_template_name)
            if os.path.isfile(format_template_file):
                return format_template_file

        return None

    def _get_editor(self):
        return self.profile.editor

    def get_reserved_placeholders(self):
        return self.profile.placeholder_values if self.profile else []

    def get_reserved_placeholder_names(self):
        for reserved_placeholder in self.get_reserved_placeholders():
            yield reserved_placeholder.name

    def get_reserved_placeholder_values(self):
        if self._reserved_placeholder_values:
            return dict(self._reserved_placeholder_values)

        self._reserved_placeholder_values = Data()
        if self.profile:
            for placeholder_value in self.profile.placeholder_values:
                placeholder_name = placeholder_value.name
                self._reserved_placeholder_values.append(placeholder_name, placeholder_value.element())

        return dict(self._reserved_placeholder_values)

    def get_format_template_names(self):
        format_template_files = []
        # Get templates from home or app directory.
        for format_template_file_path in self.format_template_paths:
            if os.path.exists(format_template_file_path):
                exclude_extensions = ['.txt', '.md']
                exclude_directories = ['.git']
                for r, d, f in os.walk(format_template_file_path):
                    d[:] = [dir for dir in d if dir not in exclude_directories]
                    relpath = r[len(format_template_file_path) + 1:]
                    for file in f:
                        if list(filter(lambda x: file.lower().endswith(x), exclude_extensions)):
                            continue
                        format_template_files.append(safe_join_path(relpath, file))

        # Also consider files in the local directory which ends with .snippet.
        for file in os.listdir(os.fsencode(os.getcwd())):
            filename = os.fsdecode(file)
            if os.path.isfile(filename) and filename.endswith(".snippet"):
                format_template_files.append(filename)

        return sorted(list(set(format_template_files)))

    def get_format_template(self, format_template_name):
        format_template_file = self._get_template_file(format_template_name)
        if not format_template_file:
            format_template_name = iterfzf(self.get_format_template_names(), query=format_template_name)

        format_template_file = self._get_template_file(format_template_name)
        if not format_template_file:
            raise Exception("Loading {} failed! Template not found!".format(format_template_name or "template"))

        try:
            with open(format_template_file) as f:
                lines = []
                for line in f.read().splitlines():
                    lines.append(line)
                return format_template_name, os.linesep.join(lines)
        except:
            raise Exception("Loading {} failed! Invalid template format!".format(format_template_name or "template"))

    editor = property(_get_editor)


class PlaceholderValuePrintFormatter:

    @staticmethod
    def build(format_string, data_frame):

        def _unique_placeholders(placeholders):
            """ Returns a list of unique placeholders while preserving the required and default attribute. """
            result = {}
            for placeholder in placeholders:
                if placeholder.name not in result:
                    result[placeholder.name] = placeholder
                result[placeholder.name].required = result[placeholder.name].required or placeholder.required
                result[placeholder.name].default = result[placeholder.name].default or placeholder.default
            return result.values()

        lines = []
        placeholders = PlaceholderFormatParser().parse(format_string)
        if not placeholders:
            # No placeholders in format string.
            return lines

        placeholder_names = OrderedDict.fromkeys([placeholder.name for placeholder in placeholders])
        placeholder_name_max_len = len(max(placeholder_names, key=len))
        unique_placeholders = _unique_placeholders(placeholders)

        # Print assigned values for each placeholder.
        lines.append(colorize("Placeholders:", Fore.YELLOW))
        for placeholder in unique_placeholders:
            # Retrieve values.
            if placeholder.name in data_frame:
                values = list(OrderedDict.fromkeys(data_frame[placeholder.name]))
            elif placeholder.name + "..." in data_frame:
                values = list(OrderedDict.fromkeys(data_frame[placeholder.name + "..."][0]))
            else:
                values = None

            is_default = placeholder.default and values == list(placeholder.default)
            is_set = values is not None
            if not is_set or is_default:
                if placeholder.default:
                    status = colorize(" (default)", Fore.BLUE)
                    value = colorize(placeholder.default, Fore.LIGHTBLUE_EX)
                elif placeholder.required:
                    status = colorize("(required)", Fore.RED)
                    value = colorize("<not assigned>", Fore.LIGHTRED_EX)
                else:
                    status = colorize("(optional)", Fore.GREEN)
                    value = colorize("<not assigned>", Fore.LIGHTGREEN_EX)

                # No value assigned.
                lines.append("   {} {} = {}".format(
                    colorize(placeholder.name.rjust(placeholder_name_max_len), Fore.WHITE), status, value))
            else:
                # Print list of assigned values.
                status = colorize("(required)", Fore.GREEN) \
                    if placeholder.required else colorize("(optional)", Fore.GREEN)
                for i in range(len(values)):
                    placeholder_name = placeholder.name if i == 0 else len(placeholder.name) * " "
                    value = values[i]
                    lines.append("   {} {} {} {}".format(
                        colorize(placeholder_name.rjust(placeholder_name_max_len), Fore.WHITE),
                        status, "=" if i == 0 else "|", value))
                    if i == 0: status = len("(optional)") * " "  # Show (required/optional) only for the first value.

        return lines


class CodecRunner:
    """ Applies the codecs specified in the placeholder to the assigned values. """

    def __init__(self, codecs):
        self._codecs = codecs

    def run(self, row_item, placeholder):
        def run_codec(codec, input, arguments):
            try:
                expected_parameters = len(signature(codec.run).parameters) - 1  # do not count input
                actual_parameters = 1 if isinstance(arguments, str) else len(arguments)
                if expected_parameters != actual_parameters:
                    raise Exception(
                        "Expected {} parameters, got {}, {}!".format(expected_parameters, actual_parameters, arguments))
                if isinstance(arguments, str):
                    return codec.run(input, arguments)
                elif len(arguments) == 0:
                    return codec.run(input)
                else:
                    return codec.run(input, *arguments)
            except Exception as err:
                # Add the codec name to the exception message to know where this exception is coming from.
                raise Exception("{}: {}".format(codec.name, '.'.join(err.args)))

        if isinstance(row_item, list):  # Repeatable
            values = row_item
            for placeholder_codec in placeholder.codecs:
                codec = self._codecs[placeholder_codec.name]
                if isinstance(codec, StringCodec):
                    values = [run_codec(codec, value, placeholder_codec.arguments) for value in values]
                elif isinstance(codec, ListCodec):
                    values = run_codec(codec, values, placeholder_codec.arguments)
                else:
                    values = [run_codec(codec, values, placeholder_codec.arguments)]
            return " ".join(values)
        else:
            value = row_item
            for placeholder_codec in placeholder.codecs:
                codec = self._codecs[placeholder_codec.name]
                if isinstance(codec, StringCodec):
                    value = run_codec(codec, value, placeholder_codec.arguments)
                elif isinstance(codec, ListCodec):
                    value = " ".join(run_codec(codec, [value], placeholder_codec.arguments))
                else:
                    value = run_codec(codec, value, placeholder_codec.arguments)
            return value


class DataBuilder(object):

    def __init__(self, format_string, data, codec_formats, config):
        self.data = data
        self.config = config
        self.codec_formats = codec_formats
        self._codec_runner = CodecRunner(config.codecs)
        self._format_string = format_string
        self._format_string_minified = self._minify_format_string(format_string)
        self._placeholders = PlaceholderFormatParser().parse(self._remove_comments(self._format_string_minified))

    def _remove_comments(self, string):
        return os.linesep.join([line for line in string.splitlines() if not line.startswith("#")])

    def _minify_format_string(self, format_string):
        """
        Initializes the format string.

        This function removes optional parts of the supplied format string which were not set by the user or the
        snippet system (e.g. reserved placeholders).
        """
        # Collect defaults and set them if no value was assigned.
        for placeholder in PlaceholderFormatParser().parse(self._remove_comments(format_string)):
            if placeholder.default is not None and placeholder.name not in self.data.keys():
                self.data.append(placeholder.name, placeholder.default)

        # Check whether parameters are empty.
        parameters = {}

        # Collect parameters specified by the user.
        for parameter in self.data.keys():
            # $ snippet -f "[<arg>]" arg=
            parameters[parameter] = self.data[parameter] != [""]

        # Collect reserved placeholders (e.g. <datetime>).
        for parameter in self.config.get_reserved_placeholder_names():
            parameters[parameter] = True  # is never empty

        return FormatStringParser(self.config).parse(format_string, parameters)

    def transform_data(self) -> Data:
        """
        Transforms the data from a map of placeholders with value lists into a data frame.
        """
        temporary_data = Data()

        # Add all data which has an associated placeholder to a temporary dict.
        placeholder_names = self._get_placeholder_names()
        for placeholder_name in self.data.keys():
            if placeholder_name in placeholder_names:
                temporary_data[placeholder_name] = self.data[placeholder_name]

        # Do not allow using reserved placeholders.
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        if any(reserved_placeholder in temporary_data.keys() for reserved_placeholder in
               reserved_placeholder_values.keys()):
            raise Exception("{} is/are already defined in your profile!".format(
                ', '.join(["<" + placeholder_name + ">" for placeholder_name in reserved_placeholder_values.keys() if
                           placeholder_name in temporary_data])))

        # Add all reserved placeholders which have an associated placeholder to the temporary dict.
        for placeholder_name, value in reserved_placeholder_values.items():
            if placeholder_name in placeholder_names:
                # Add to temporary data. Remove duplicates while preserving order
                temporary_data[placeholder_name] = OrderedDict.fromkeys(value)

        # Move placeholders which are tagged as repeatable (e.g. <ARG...>) to temporary map before creating matrix.
        repeatable_placeholders = {}
        placeholder_names = list(temporary_data.keys())
        for placeholder_name in placeholder_names:
            # Get all placeholders specified in the format string which have the same name.
            _p = [p for p in self.get_placeholders() if p.name == placeholder_name]
            # Get all placeholders specified in the format string which are repeatable and have the same name.
            _r = [p for p in _p if p.repeatable]
            is_repeatable = len(_r) > 0
            if is_repeatable:
                if len(_p) == len(_r):
                    # All placeholders in the format string are repeatable placeholders e.g. "<ARG...> <ARG...>"
                    repeatable_placeholders[placeholder_name] = temporary_data.pop(placeholder_name, None)
                else:
                    # Not repeatable and repeatable placeholders are defined in format string e.g. "<ARG...> <ARG>"
                    repeatable_placeholders[placeholder_name] = copy.deepcopy(temporary_data[placeholder_name])

        # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
        # This list does only contain placeholders which are not tagged as repeatable (e.g. <ARG...>).
        data_matrix = list(itertools.product(*[temporary_data[key] for key in temporary_data.keys()]))

        # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
        # Add placeholders which are tagged as repeatable (e.g. <ARG...>) to the table data again.
        data_keys = list(temporary_data.keys())
        table_data = Data()
        for i in range(0, len(data_matrix)):
            for j in range(0, len(data_keys)):
                table_data.append(data_keys[j], data_matrix[i][j])
            for placeholder_name in repeatable_placeholders:
                # Store repeatable placeholder in table_data as list.
                # Use different key to avoid overwriting placeholders which is not repeatable.
                table_data.append(placeholder_name + "...",
                                  [[item for item in repeatable_placeholders[placeholder_name]]])

        return table_data

    def get_placeholders(self):
        return list(self._placeholders)

    def _get_placeholder_names(self):
        """ Returns a unique list of placeholder names. """
        return set([placeholder.name for placeholder in self.get_placeholders()])

    def _escape_brackets(self, str):
        if str:
            return str.replace("[", "\\[").replace("]", "\\]").replace("<", "\\<").replace(">", "\\>")
        else:
            return str

    def _unescape_brackets(self, str):
        if str:
            return str.replace("\\[", "[").replace("\\]", "]").replace("\\<", "<").replace("\\>", ">")
        else:
            return str

    def _replace_placeholders_in_line(self, line, placeholders, data_frame, line_start, line_end, iteration):
        for placeholder in reversed(placeholders):
            if line_start <= placeholder.start < line_end:
                adjusted_start = placeholder.start - line_start
                adjusted_end = placeholder.end - line_start
                row = data_frame[placeholder.name + "..." if placeholder.repeatable else placeholder.name]
                value = self._codec_runner.run(row[iteration], placeholder)
                line = replace_within(line, self._escape_brackets(value), adjusted_start, adjusted_end)

        return line

    def _process_format_string(self, format_string, data_frame, placeholders):
        result = []
        # Determine the number of outputs to be generated
        num_iterations = len(next(iter(data_frame.values()), []))

        if not num_iterations:
            self.config.logger.debug('No placeholders defined or already set through optionals...')
            # Handling scenarios with no dynamic placeholders or placeholders already set:
            # Example 1: snippet -f "abc def" -> Output: "abc def"
            # Example 2: snippet -f "a[b<arg1='test'>b]a" arg1= -> Output: "aa"
            # Example 3: snippet -f "abc [<arg1> <arg2>]" arg1=test -> Output: "abc "
            return [format_string]

        # Processing format_string multiple times for each set of values in data_frame:
        # Example 1: snippet -f "<arg>" arg=1 -> Output: "1"
        # Example 2: snippet -f "<arg>" arg=1 arg=2 -> Outputs: "1", "2"
        for iteration in range(num_iterations):
            line_start = 0
            processed_lines = []

            # Iterate over each line in format_string for processing
            for line in format_string.splitlines(keepends=True):
                if not line.startswith("#"):
                    # Replace placeholders in non-comment lines
                    line_end = line_start + len(line)
                    line = self._replace_placeholders_in_line(line, placeholders, data_frame, line_start, line_end, iteration)
                    line_start = line_end

                processed_lines.append(line)

            result.append(''.join(processed_lines))

        return result

    def _validate_codecs(self, placeholders):
        for placeholder in placeholders:
            for codec in placeholder.codecs:
                if codec.name not in self.config.codecs:
                    raise Exception(f"Parsing '{self._format_string}' failed! Codec '{codec.name}' does not exist!")

    def _assign_defaults(self, placeholders):
        for placeholder in placeholders:
            if placeholder.name not in self.data.keys() and placeholder.default:
                self.data.append(placeholder.name, placeholder.default)

    def _log_placeholder_values(self, data_frame):
        for output in PlaceholderValuePrintFormatter.build(self._remove_comments(self._format_string), data_frame):
            self.config.logger.info(output)

    def _validate_required_placeholders(self, placeholders, data_frame):
        # Get all required placeholders which are not assigned. Also consider repeatables (see transform_data).
        unset_placeholders = OrderedDict.fromkeys([
            placeholder.name for placeholder in placeholders
            if placeholder.name not in data_frame.keys() and
               placeholder.required and
               placeholder.name + "..." not in data_frame.keys()])

        if unset_placeholders:
            missing_placeholders = ', '.join(f"<{name}>" for name in unset_placeholders)
            raise Exception(f"Missing data for {missing_placeholders}!")

    def _check_for_unmatched_placeholders(self, processed_output):
        # Check for unmatched placeholders in each output, ignoring comments and escaped angle brackets.
        for output in processed_output:
            output_string = ''.join(line for line in output.splitlines() if not line.startswith('#'))
            placeholders = re.findall(r"([\\]?<.*?>)", output_string)
            unescaped_placeholders = [item for item in placeholders if
                                      not (item.startswith('\\<') and item.endswith('\\>'))]

            if unescaped_placeholders:
                raise Exception(f"Invalid placeholder format: {unescaped_placeholders[0]}")

    def build(self):
        if not self._format_string_minified:
            return []

        placeholders = self.get_placeholders()
        self._assign_defaults(placeholders)
        self._validate_codecs(placeholders)

        data_frame = self.transform_data()
        self._log_placeholder_values(data_frame)
        self._validate_required_placeholders(placeholders, data_frame)
        processed_output = self._process_format_string(self._format_string_minified, data_frame, placeholders)
        self._check_for_unmatched_placeholders(processed_output)

        return [self._unescape_brackets(line) for line in processed_output]


class Snippet(object):

    def __init__(self, config: Config):
        self._format_string = ""
        self.config, self.logger = config, config.logger
        self.codec_formats = {}
        self.data = Data()

    def _get_format_string(self):
        return self._format_string

    def _set_format_string(self, format_string):
        if format_string:
            if isinstance(format_string, list):
                self._format_string = os.linesep.join(format_string)
            else:
                self._format_string = format_string

    def _set_arguments(self, data_values):
        placeholder = None
        unset_placeholders = self.list_unset_placeholders()
        last_assigned_placeholder = None
        for data_value in data_values:
            if data_value:  # Ignore empty string arguments (e.g. ""); use "arg=" instead
                for assigned_placeholder, assigned_values in ArgumentFormatParser().parse(data_value).items():
                    if assigned_placeholder:
                        # $ snippet -f "<arg>" arg=val
                        placeholder = assigned_placeholder
                        last_assigned_placeholder = assigned_placeholder
                    else:
                        # $ snippet -f "<arg>" val
                        if last_assigned_placeholder:
                            # Use the last assigned placeholder if any.
                            # $ snippet -f "<arg>" arg=val1 val2
                            placeholder = last_assigned_placeholder
                        else:
                            # Use the next not-assigned placeholder in the format string.
                            # $ snippet -f "<arg>" val1 val2
                            if len(unset_placeholders) == 0:
                                if not placeholder:
                                    # No placeholders left to assign values to.
                                    # $ snippet -f "text" val1
                                    self.logger.warning(
                                        "Can not assign '{}' to unknown placeholder!".format(assigned_values))
                                    continue
                                else:
                                    # Use the last placeholder if any.
                                    # $ snippet -f "<arg1> <arg2>" val1 val2 val3
                                    pass
                            else:
                                placeholder = unset_placeholders.pop(0)
                    self.data.append(placeholder, assigned_values)

    def _get_arguments(self):
        return self.data

    def create_or_edit_template(self, template_name, format_string):
        home_template_path = safe_join_path(home_config_path, "templates")
        home_template_file = safe_join_path(home_template_path, template_name)

        if os.path.isfile(home_template_file):
            # Edit existing file in home path
            subprocess.call((self.config.editor, home_template_file))
            return

        try:
            app_template_path = safe_join_path(app_config_path, "templates")
            app_template_file = safe_join_path(app_template_path, template_name)
            home_template_dir = os.path.dirname(home_template_file)
            os.makedirs(home_template_dir, exist_ok=True)
            if os.path.isfile(app_template_file):
                # App files should not be altered.
                # If template exists in app path, do not edit here.
                # Instead make copy to home path and edit this file.
                # Templates in home path override templates in app path.
                shutil.copyfile(app_template_file, home_template_file)

            if format_string:
                with open(home_template_file, 'w') as f:
                    f.write(format_string)

            subprocess.call((self.config.editor, home_template_file))
            self.logger.info("Successfully created template '{}'!".format(template_name))
        except:
            raise Exception("Creating template '{}' failed!".format(template_name))

    def get_template(self, template_name):
        return self.config.get_format_template(template_name)

    def list_templates(self, filter_string=None):
        template_names = self.config.get_format_template_names()
        if filter_string:
            return [template_name for template_name in template_names if filter_string in template_name]
        else:
            return template_names

    def list_codecs(self, filter_string=None):
        if filter_string:
            return sorted([codec_name for codec_name in self.config.codecs.keys() if
                           filter_string in self.config.codecs.keys()])
        else:
            return sorted(self.config.codecs.keys())

    def list_environment(self):
        result = []
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        for placeholder, values in temporary_data.items():
            if len(values) == 1:
                result.append("export {}=\"{}\"".format(placeholder, values[0]))
            else:
                result.append("export {}=\"\\('{}'\\)\"".format(placeholder, "' '".join(values)))
        return result

    def list_placeholders(self):
        """ Returns all the placeholders found in the format string. """
        return [placeholder.name for placeholder in PlaceholderFormatParser().parse(self._format_string)]

    def list_reserved_placeholders(self):
        """ Returns the list of reserved placeholders (aka Presets) e.g. 'datetime', 'date', ... """
        return self.config.get_reserved_placeholder_names()

    def list_unset_placeholders(self):
        """ Returns the placeholders in the format string which are not associated with any value yet. """
        unset_placeholders = []
        for placeholder in self.list_placeholders():
            if placeholder not in self.data and \
                    placeholder not in self.list_reserved_placeholders():
                unset_placeholders.append(placeholder)
        return unset_placeholders

    def import_environment(self):
        """
        Import values found in environment variables which name match the placeholder names found in the format string.
        Note, that an environment variable matching a placeholder is only loaded when no value is assigned yet.
        """

        reserved_placeholders = self.config.get_reserved_placeholder_values().keys()

        def _import_environment(placeholder, data):
            if data and placeholder not in reserved_placeholders:
                self.data.append(placeholder, data)

        for placeholder, data in os.environ.items():
            if not placeholder.islower() or placeholder.startswith("_"):
                # Do not load upper case environment variables to prevent users from getting into the habit of
                # defining upper case environment variables and messing up their environment.
                # In addition loading upper case environment variables may result in loading unwanted/pre-defined
                # values.
                # Do not load placeholders which start with underscore as these are usually private variables used
                # by other applications.
                continue

            # Only set environment data when not already defined
            if placeholder not in self.data:
                _import_environment(placeholder, data)

    def build(self):
        return DataBuilder(self._get_format_string(), self.data, self.codec_formats, self.config).build()

    format_string = property(_get_format_string, _set_format_string)
    arguments = property(_get_arguments, _set_arguments)


def main():
    log_level = logging.DEBUG if "--debug" in sys.argv or "-d" in sys.argv else logging.WARN
    config = Config(app_name, [home_config_path, app_config_path], log_level)
    logger = config.logger
    snippet = Snippet(config)

    def argparse_template_completer(prefix, parsed_args, **kwargs):
        return config.get_format_template_names()

    parser = argparse.ArgumentParser(
        description='snippet',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Placeholder presets:
    
""" + os.linesep.join(["  {}  {}".format(("<" + x.name + ">").rjust(20, ' '), x.description) for x in
                       config.get_reserved_placeholders()]) + """

    Codecs:
    
""" + os.linesep.join(["  {}  {}".format(x.rjust(20, ' '), config.codecs[x].__doc__.strip()) for x in
                       config.codecs.keys()]) + """
    
    Examples:
    
        # Add a new snippet to the database
        $ snippet -e archive/extract-tgz -f 'tar -xzvf <archive>'
        
        # Edit a snippet (will open vim)
        $ snippet -e archive/extract-tgz
             
        # Search a snippet which include the term "extract" (will open fzf)
        $ snippet -t extract
        
        # Fill snippet with a value
        $ snippet -t archive/extract-tgz /path/to/foo.tar.gz
        
        # Fill snippet with multiple values
        $ snippet -t archive/extract-tgz /path/to/foo.tar.gz /path/to/bar.tar.gz
        
        # Fill snippet with multiple values while using repeatable placeholders (e.g. <file...>)
        $ snippet -f "tar -czvf <archive> <file...>" /path/to/foo.tar file=foo bar
        
        # Using presets (e.g. '<datetime>' to include current datetime)
        $ snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file=foo bar
        
        # Import values from file
        $ snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file:files.txt
        
        # Using optionals
        $ snippet -f "python3 -m http.server[ --bind <lhost>][ <lport>]" lport=4444
        
        # Using defaults
        $ snippet -f "python3 -m http.server[ --bind <lhost>] <lport=8000>"
        
        # Using codecs
        $ snippet -f "tar -czvf <archive:squote> <file:squote...>" /path/to/foo.tar file=foo bar
        """
    )
    parser.add_argument('data_values', metavar='VALUE | PLACEHOLDER=VALUE | PLACEHOLDER:FILE', nargs='*',
                        help='When no placeholder is specified the first unset placeholder found in the format string will '
                             'be replaced with the value(s). Otherwise the specified placeholder will be replaced with '
                             'the value or the content of the file. A list of values can be assigned by explicitly '
                             'declaring the placeholder (e.g. "ARG1=val1" "ARG2=val2").')
    parser.add_argument('-e', '--edit', action="store", metavar="NAME",
                        dest='edit',
                        help="Edit (or create) a snippet with the specified name.") \
        .completer = argparse_template_completer
    parser.add_argument('-f', '--format-string', action="store", metavar="FORMAT_STRING",
                        dest='format_string',
                        help="The format of the data to generate. "
                             "The placeholders are identified by angle brackets (<, >). "
                             "Optional parts can be denoted using square brackets ([, ]).")
    parser.add_argument('-t', '--template', action="store", metavar="FILE",
                        dest='template_name',
                        help="The template to use as format string.") \
        .completer = argparse_template_completer
    parser.add_argument('--list-templates', action="store_true",
                        dest='list_templates',
                        help="Lists all available templates.")
    parser.add_argument('--list-codecs', action="store_true",
                        dest='list_codecs',
                        help="Lists all available codecs.")
    parser.add_argument('--env', '--environment', action="store_true",
                        dest='environment',
                        help="Shows all environment variables.")
    parser.add_argument('-q', '--quiet', action="store_false",
                        dest='verbose',
                        help="Do not print additional information (e.g. format string, template, ...).")
    parser.add_argument('-d', '--debug', action="store_true",
                        dest='debug',
                        help="Prints additional debug information (e.g. stack traces).")

    argcomplete.autocomplete(parser)
    arguments = parser.parse_args()

    if arguments.debug:
        config.logger.level = logging.DEBUG
    elif arguments.verbose:
        config.logger.level = logging.INFO
    else:
        config.logger.level = logging.WARN

    try:
        if arguments.edit:
            snippet.create_or_edit_template(arguments.edit, arguments.format_string)
            sys.exit(0)

        if arguments.list_codecs and arguments.list_templates:
            raise Exception("--codec-list can not be used in combination with --template-list!")

        if arguments.list_templates:
            template_names = snippet.list_templates()
            if not template_names:
                logger.warning("No templates found!")
            for template_name in template_names:
                print(template_name)
            sys.exit(0)

        if arguments.list_codecs:
            codec_names = snippet.list_codecs()
            if not codec_names:
                logger.warning("No codecs found!")
            for codec_name in codec_names:
                print(codec_name)
            sys.exit(0)

        if arguments.format_string and arguments.template_name:
            raise Exception("--format-string can not be used in conjunction with --template!")

        if arguments.format_string and not sys.stdin.isatty():
            raise Exception("--format-string can not be used in conjunction with piped input!")

        if arguments.template_name and not sys.stdin.isatty():
            raise Exception("--template can not be used in conjunction with piped input!")

        format_string = arguments.format_string
        if arguments.template_name:
            format_template_name, format_string = snippet.get_template(arguments.template_name)
            log_format_template(format_template_name, logger)

        if not sys.stdin.isatty():
            format_string = "".join(sys.stdin.readlines())

        if not format_string:
            format_string = os.environ.get("FORMAT_STRING")

        # Make sure that escape sequences like \n, \t, etc. are handled correctly.
        snippet.format_string = codecs.decode(format_string or '', 'unicode_escape')
        if snippet.format_string:

            if arguments.data_values:
                snippet.arguments = arguments.data_values

            snippet.import_environment()

            if arguments.environment:
                for line in snippet.list_environment():
                    print(line)
                sys.exit(0)

        if not snippet.format_string:
            parser.print_usage(file=sys.stderr)
            sys.exit(1)

        log_format_string(format_string, logger)
        for lines in snippet.build():
            # Handle format strings with line separators
            for line in lines.splitlines():
                print_line(line)
        sys.exit(0)
    except Exception as e:
        logger.error(str(e))
        if arguments.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
