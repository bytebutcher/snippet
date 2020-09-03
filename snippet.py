#!/usr/bin/env python3
import argcomplete, argparse

from collections import defaultdict, OrderedDict
from enum import Enum

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

from colorama import Fore, Style
from iterfzf import iterfzf
from tabulate import tabulate

app_name = "snippet"
app_version = "1.0v"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".snippet". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".snippet")
home_config_path = os.path.join(str(Path.home()), ".snippet")


def colorize(string: str, color):
    return color + string + Style.RESET_ALL


class FormatArgumentParser:

    @staticmethod
    def parse(format_arguments: str):
        # Accepted data set format:
        #   PLACEHOLDER=VALUE | PLACEHOLDER:FILE [... PLACEHOLDER=VALUE | PLACEHOLDER:FILE]
        result = Data()
        for format_argument in FormatArgumentParser.__reformat_arguments(format_arguments):
            for key, value in FormatArgumentParser.__parse(format_argument).items():
                result.append(key, value)
        return result

    @staticmethod
    def __reformat_arguments(format_arguments: str) -> list:
        """
        Reformat format arguments which were passed as single string but contain multiple placeholders with values
        while missing the necessary quotes to parse them correctly with shlex.
        :param format_arguments: the format arguments (e.g. "placeholder1=a b c placeholder2=d e f")
        :return: a reformatted list of format arguments (e.g. ["placeholder1=a b c", "placeholder2=d e f"])
        """
        reformatted_arguments = []
        reformatted_argument = []
        is_initialized = False
        for format_argument in shlex.split(format_arguments):
            if "=" in format_argument or ":" in format_argument:
                if not is_initialized:
                    is_initialized = True
                    reformatted_argument.append(format_argument)
                else:
                    reformatted_arguments.append(" ".join(reformatted_argument))
                    reformatted_argument = [format_argument]
            else:
                reformatted_argument.append(format_argument)
        reformatted_arguments.append(" ".join(reformatted_argument))
        return reformatted_arguments

    @staticmethod
    def __parse(format_argument: str):
        separator = FormatArgumentParser.__get_separator(format_argument)
        return {
            "=": FormatArgumentParser.__parse_placeholder_value,
            ":": FormatArgumentParser.__parse_placeholder_file,
            "": FormatArgumentParser.__parse_value
        }.get(separator)(format_argument, separator)

    @staticmethod
    def __get_separator(format_argument: str):
        string_sep_pos = format_argument.find("=")
        file_sep_pos = format_argument.find(":")
        if (string_sep_pos <= 0 and file_sep_pos <= 0):
            # When no separator is found, return an empty string
            return ""
        elif (string_sep_pos > 0 and file_sep_pos > 0):
            # When both separators are found, return the first one found in the format argument
            return "=" if string_sep_pos < file_sep_pos else ":"
        else:
            # When one separator is found, return it
            return "=" if string_sep_pos > 0 else ":"

    @staticmethod
    def __parse_placeholder_value(placeholder_value: str, sep: str):
        try:
            placeholder, value = placeholder_value.split(sep)
            return {placeholder: value}
        except:
            raise Exception("Parsing '{}' failed! Unknown error!".format(placeholder_value))

    @staticmethod
    def __parse_placeholder_file(placeholder_file: str, sep: str):
        placeholder, file = placeholder_file.split(sep)
        if not os.path.isfile(file):
            raise Exception("Parsing '{}' failed! File not found!".format(placeholder_file))

        try:
            data = Data()
            with open(file) as f:
                for value in f.read().splitlines():
                    data.append(placeholder, value)
            return data
        except:
            raise Exception("Parsing '{}' failed! Invalid file format!".format(placeholder_file))

    @staticmethod
    def __parse_value(value: str, sep: str):
        return {"": value}


class PlaceholderFormatParser:

    @staticmethod
    def parse(format_string, parse_optional=True):

        def _parse_parts(parts, i=0):
            result = []
            for part in parts:
                if isinstance(part, str):
                    for placeholder in _parse_part(part, i):
                        result.append(placeholder)
                elif isinstance(part, list):
                    for placeholder in _parse_parts(part, i+1):
                        result.append(placeholder)
            return result

        def _parse_part(part, i):
            return list(
                OrderedDict.fromkeys(
                    PlaceholderFormat("<" + placeholder_format + ">", i == 0) \
                        for placeholder_format in \
                            re.findall(r"<(\w+?[:\w+]*(?:[^A-Za-z0-9]?\.\.\.)?(?:=[^>]+)?)>", part or "")))

        if parse_optional:
            return _parse_parts(ParenthesesParser.parse(format_string))
        else:
            return _parse_part(format_string, False)


class ParenthesesParser:

    @staticmethod
    def parse(format_string):

        def _parse_parentheses(format_string, i=0, balance=0):
            components = []
            start = i
            while i < len(format_string):
                c = format_string[i]
                if c == "[":
                    if i > 0:
                        components.append(format_string[start:i])
                    i, result = _parse_parentheses(format_string, i + 1, balance + 1)
                    components.append(result)
                    start = i + 1
                elif c == "]":
                    balance = balance - 1
                    components.append(format_string[start:i])
                    if balance < 0:
                        raise Exception("Unbalanced parentheses!")
                    return i, components
                i = i + 1

            components.append(format_string[start:len(format_string)])
            return i, components

        return _parse_parentheses(format_string)[1]


class FormatStringParser:

    @staticmethod
    def parse(format_string, parameters):
        parentheses = ParenthesesParser.parse(format_string)
        if not parentheses:
            return format_string
        essentials = FormatStringParser._remove_optionals(parentheses, parameters)
        if not essentials:
            return format_string
        return "".join(FormatStringParser._flatten_list(essentials))

    @staticmethod
    def _remove_optionals(parts, arguments):
        result = []
        for part in parts:
            if isinstance(part, str):
                placeholders = PlaceholderFormatParser.parse(part, parse_optional=False)
                for placeholder in placeholders:
                    if not placeholder.name in arguments and not placeholder.default:
                        return []
                result.append(part)
            elif isinstance(part, list):
                result.append(FormatStringParser._remove_optionals(part, arguments))
        return result

    @staticmethod
    def _flatten_list(lst):
        result = []
        for item in lst:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                for i in FormatStringParser._flatten_list(item):
                    result.append(i)
        return result


class PlaceholderFormat:
    """
    A placeholder does have the following format*:

        <NAME{:CODEC}~{{SEPARATOR}...}{=DEFAULT}>

        NAME (required)      = The name of the placeholder (\w).
        CODEC (optional)     = A ist of codecs which should be applied to the assigned argument value.
        ... (optional)       = When multiple values are assigned they are being joined with SEPARATOR (default=<space>).
        =DEFAULT (optional)  = Specifies a default value which is being used when no value is assigned.

    *) optional parts are denoted with curly braces and parts which can be repeated are marked with a tilde.
    """

    def __init__(self, format_string: str, required):
        try:
            assert(format_string.startswith("<") and format_string.endswith(">"))
            self.format_string = format_string[1:-1]
            self.name, codecs, self.repeatable, self.default = re.findall(r"<(\w+)((?::\w+)*)([^A-Za-z0-9]?\.\.\.)?(=[^>]+)?>", format_string.lower()).pop()
            self.codecs = list(filter(None, codecs.split(":")))
            self.default = self.default[1:] if self.default else None # Remove the equal-sign at the beginning.
            self.required = required
        except Exception:
            raise Exception("Transforming placeholders failed! Invalid format!")

    def _get_delimiter(self):
        """ The delimiter used when repeatable (default = " "). """
        return " " if not self.repeatable or len(self.repeatable) == 3 else self.repeatable[0]

    delimiter = property(_get_delimiter)


class Data(defaultdict):
    """
     Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') }
    """

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

    def __init__(self, author, dependencies):
        self.author = author
        self.dependencies = dependencies

    def name(self):
        return self.__class__.__name__

    def run(self, text):
        pass


class Config(object):

    verbose = False

    def __init__(self, app_name, paths):
        self.paths = paths
        self.format_template_paths = [os.path.join(path, "templates") for path in paths]
        self.codec_paths = [os.path.join(path, "codecs") for path in paths]
        self.logger = self.__init_logger(app_name, "%(msg)s")
        self.profile = self.__load_profile()
        self.codecs = self.__load_codecs()
        self._reserved_placeholder_values = []

    def __init_logger(self, app_id, log_format="%(module)s: %(lineno)d: %(msg)s"):
        logger = logging.getLogger(app_id)
        logging.root.setLevel(logging.INFO)
        hdlr = logging.StreamHandler(sys.stderr)
        hdlr.setFormatter(logging.Formatter(log_format))
        logger.addHandler(hdlr)
        return logger

    def __load_profile(self):
        for profile_path in self.paths:
            if os.path.exists(profile_path):
                try:
                    # Since the path may contain special characters which can not be processed by the __import__
                    # function we temporary add the path in which the profile.py is located to the PATH.
                    sys.path.append(profile_path)
                    profile = __import__("snippet_profile").Profile()
                    sys.path.pop()
                    return profile
                except:
                    pass
        return None

    def __load_codecs(self):

        def to_camel_case(word):
            return ''.join(x.capitalize() or '_' for x in word.split('_'))

        codecs = {}
        for codec_path in self.codec_paths:
            # Since the path may contain special characters which can not be processed by the __import__
            # function we temporary add the path in which the codecs are located to the PATH.
            if os.path.exists(codec_path):
                dirs = []
                for r, d, f in os.walk(codec_path):
                    for dir in d:
                        if not dir.startswith("__"):
                            dirs.append(dir)

                for dir in dirs:
                    sys.path.append(os.path.join(codec_path, dir))
                    for r, d, f in os.walk(os.path.join(codec_path, dir)):
                        for file in f:
                            filename, ext = os.path.splitext(file)
                            if ext == ".py":
                                classname = str(to_camel_case(filename))
                                try:
                                    codecs[filename] = getattr(__import__(filename), classname)()
                                except Exception:
                                    self.logger.warning("WARNING: Loading codec {} failed!".format(filename))
                    sys.path.pop()

        return codecs

    def _get_template_file(self, format_template_name):
        if not format_template_name:
            return None

        if format_template_name.endswith(".snippet"):
            # Consider template files in the current working directory.
            format_template_file = os.path.join(os.getcwd(), format_template_name)
            return format_template_file if os.path.isfile(format_template_file) else None

        for format_template_path in self.format_template_paths:
            format_template_file = os.path.join(format_template_path, format_template_name)
            if os.path.isfile(format_template_file):
                return format_template_file

        return None

    def _get_editor(self):
        return self.profile.editor

    def get_reserved_placeholders(self):
        if self.profile:
            return self.profile.placeholder_values
        return []

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
                for r, d, f in os.walk(format_template_file_path):
                    relpath = r[len(format_template_file_path) + 1:]
                    for file in f:
                        format_template_files.append(os.path.join(relpath, file))

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
                    if not line.startswith("#"):
                        lines.append(line)
                return format_template_name, os.sep.join(lines)
        except:
            raise Exception("Loading {} failed! Invalid template format!".format(format_template_name or "template"))

    editor = property(_get_editor)


class EscapedSquareBracketCodec:

    @staticmethod
    def encode(str):
        """ Encodes escaped square brackets. """
        return str.replace('\\[', chr(14)).replace('\\]', chr(15))

    @staticmethod
    def decode(str):
        """ Decodes to square brackets. """
        return str.replace(chr(14), "[").replace(chr(15), "]")


class PlaceholderValuePrintFormatter:

    @staticmethod
    def build(format_string, data_frame):
        lines = []
        placeholders = PlaceholderFormatParser.parse(format_string)
        if not placeholders:
            # No placeholders in format string.
            return lines

        placeholder_names = OrderedDict.fromkeys([placeholder.name for placeholder in placeholders])
        placeholder_name_max_len = len(max(placeholder_names, key=len))

        # Print assigned values for each placeholder.
        lines.append(colorize("Placeholders:", Fore.YELLOW))
        for placeholder in placeholders:

            # Only print placeholder name once.
            if placeholder.name not in placeholder_names:
                continue
            else:
                placeholder_names.pop(placeholder.name)

            if placeholder.name not in data_frame:
                required = colorize("(required)", Fore.RED) \
                    if placeholder.required else colorize("(optional)", Fore.GREEN)
                # No value assigned.
                lines.append("   {} {} = {}".format(
                    colorize(placeholder.name.rjust(placeholder_name_max_len), Fore.WHITE),
                    required,
                    colorize("<not assigned>", Fore.LIGHTRED_EX)
                    if placeholder.required else colorize("<not assigned>", Fore.LIGHTGREEN_EX)))
            else:
                required = colorize("(required)", Fore.GREEN) \
                    if placeholder.required else colorize("(optional)", Fore.GREEN)
                # Print list of assigned values.
                values = list(set(data_frame[placeholder.name]))
                for i in range(len(values)):
                    placeholder_name = placeholder.name if i == 0 else len(placeholder.name) * " "
                    value = values[i]
                    lines.append("   {} {} {} {}".format(
                        colorize(placeholder_name.rjust(placeholder_name_max_len), Fore.WHITE),
                        required, "=" if i == 0 else "|", value))
                    if i == 0: required = len("(optional)") * " "  # Show (required/optional) only for the first value.

        return lines


class DataBuilder(object):

    def __init__(self, format_string, data, codec_formats, config):
        self.data = data
        self.config = config
        self.codec_formats = codec_formats
        self._format_string_original = format_string
        self._format_string_minified = self._parse_format_string(format_string)
        self._placeholders = PlaceholderFormatParser.parse(self._format_string_minified)
        for placeholder in self._placeholders:
            for codec in placeholder.codecs:
                if codec not in self.config.codecs:
                    raise Exception(
                        "Parsing '{}' failed! Codec '{}' does not exist!".format(placeholder.format_string, codec))

    def _parse_format_string(self, format_string):
        """
        Initializes the format string.

        This function removes optional parts of the supplied format string which were not set by the user or the
        snippet system (e.g. reserved placeholders).
        """
        # Parameters specified by the user + the reserved placeholders (e.g. <datetime>).
        parameters = list(self.data.keys()) + list(self.config.get_reserved_placeholder_names())
        # Parts enclosed by square brackets (e.g. "<arg1> [<arg2>] <arg3>") are considered optional.
        # Since our parser can not differentiate between user-specified square brackets and those used for specifying
        # optional parts, the user needs to escape them (e.g. \[ or \]).  To make parsing easier we encode escaped
        # square brackets here.
        return FormatStringParser.parse(EscapedSquareBracketCodec.encode(format_string), parameters)

    def transform_data(self):
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
            # Get all placeholders specified in the string format which have the same name.
            _p = [p for p in self.get_placeholders() if p.name == placeholder_name]
            # Get all placeholders specified in the string format which are repeatable and have the same name.
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
                table_data.append(placeholder_name + "...", [[item for item in repeatable_placeholders[placeholder_name]]])

        return table_data

    def get_placeholders(self):
        return list(self._placeholders)

    def _get_placeholder_names(self):
        """ Returns a unique list of placeholder names. """
        return set([placeholder.name for placeholder in self.get_placeholders()])

    def _apply_codecs(self, row_item, placeholder):
        """ Applies the codecs specified in the placeholder to the assigned values. """
        if isinstance(row_item, list):
            values = []
            for value in row_item:
                for codec in placeholder.codecs:
                    value = self.config.codecs[codec].run(value)
                values.append(value)
            return placeholder.delimiter.join(values)
        else:
            value = row_item
            for codec in placeholder.codecs:
                value = self.config.codecs[codec].run(value)
            return value

    def build(self):
        result = []
        if self._format_string_minified:

            placeholders = self.get_placeholders()
            for placeholder in placeholders:
                if placeholder.name not in self.data.keys() and placeholder.default:
                    self.data.append(placeholder.name, placeholder.default)

            data_frame = self.transform_data()

            if self.config.verbose:
                # Print all placeholders and the assigned values (verbose).
                for line in PlaceholderValuePrintFormatter.build(self._format_string_original, data_frame):
                    self.config.logger.info(colorize(" INFO: ", Fore.GREEN) + line)

            # Get all required placeholders which are not assigned. Also consider repeatables (see transform_data).
            unset_placeholders = OrderedDict.fromkeys([
                placeholder.name for placeholder in self.get_placeholders()
                    if placeholder.name not in data_frame.keys() and
                       placeholder.required and
                       placeholder.name + "..." not in data_frame.keys()])
            if unset_placeholders:
                raise Exception("Missing data for {}!".format(', '.join(["<" + item + ">" for item in unset_placeholders])))

            length = len(data_frame[list(data_frame.keys())[0]]) if data_frame.keys() else 0
            if length == 0:
                # No placeholders are defined in the format string.
                result.append(self._format_string_minified)
            else:
                for i in range(0, length):
                    # Replace placeholders in format string with values.
                    output_line = self._format_string_minified
                    for placeholder in self.get_placeholders():
                        row = data_frame[placeholder.name + "..." if placeholder.repeatable else placeholder.name]
                        value = self._apply_codecs(row[i], placeholder)
                        output_line = output_line.replace("<" + placeholder.format_string + ">", value)

                    result.append(output_line)

        # Decode encoded '\['- and '\]'-sequences to '[' and ']' (see __init__ method for more information).
        return [EscapedSquareBracketCodec.decode(line) for line in result]


class Snippet(object):

    class ImportEnvironmentMode(Enum):
        default = 1
        append = 2
        replace = 3
        ignore = 4

    def __init__(self, config: Config):
        self._format_string = ""
        self.config = config
        self.codec_formats = {}
        self.data = Data()

    def _get_format_string(self):
        return self._format_string

    def _set_format_string(self, format_string):
        self._log_info(colorize("Format:", Fore.YELLOW))
        for line in format_string.split(os.linesep):
            self._log_info(colorize("   {}".format(line), Fore.WHITE))
        self._format_string = format_string

    def _set_arguments(self, data_values):
        placeholder = None
        unset_placeholders = self.list_unset_placeholders()
        last_assigned_placeholder = None
        for data_value in data_values:
            if data_value:  # Ignore empty string arguments (e.g. ""); use "arg=" instead
                for assigned_placeholder, assigned_values in FormatArgumentParser.parse(data_value).items():
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
                                    self.config.logger.warning(
                                        " WARN: Can not assign '{}' to unknown placeholder!".format(
                                            ", ".join(assigned_values)))
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

    def _set_verbose(self, verbose):
        self.config.verbose = verbose

    def _get_verbose(self):
        return self.config.verbose

    def _log_info(self, msg):
        if self._get_verbose():
            self.config.logger.info(colorize(" INFO: ", Fore.GREEN) + msg)

    def create_or_edit_template(self, template_name):
        home_template_path = os.path.join(home_config_path, "templates")
        home_template_file = os.path.join(home_template_path, template_name)
        if os.path.isfile(home_template_file):
            # Edit existing file in home path
            subprocess.call((self.config.editor, home_template_file))
            return

        try:
            app_template_path = os.path.join(app_config_path, "templates")
            app_template_file = os.path.join(app_template_path, template_name)
            home_template_dir = os.path.dirname(home_template_file)
            os.makedirs(home_template_dir, exist_ok=True)
            if os.path.isfile(app_template_file):
                # If template exists in app path, do not edit here
                # Instead make copy to home path and edit this file
                shutil.copyfile(app_template_file, home_template_file)
            subprocess.call((self.config.editor, home_template_file))
        except:
            raise Exception("Creating '{}' failed!".format(template_name))

    def use_template(self, template_name):
        format_template_name, format_string = self.config.get_format_template(template_name)
        self._log_info(colorize("Template:", Fore.YELLOW))
        self._log_info(colorize("   {}".format(format_template_name), Fore.WHITE))
        self.format_string = format_string

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
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        return tabulate(temporary_data.to_data_frame(), headers="keys")


    def list_placeholders(self):
        return [placeholder.name for placeholder in PlaceholderFormatParser.parse(self._format_string)]

    def list_reserved_placeholders(self):
        return self.config.get_reserved_placeholder_names()

    def list_unset_placeholders(self):
        """ Returns the placeholders in the format string which are not associated with any value yet. """
        unset_placeholders = []
        for placeholder in self.list_placeholders():
            if placeholder not in self.data and \
                    placeholder not in self.list_reserved_placeholders():
                unset_placeholders.append(placeholder)
        return unset_placeholders

    def import_environment(self, mode=ImportEnvironmentMode.default):
        placeholders = self.list_placeholders()
        reserved_placeholders = self.config.get_reserved_placeholder_values().keys()

        def _import_environment(placeholder, data):
            if data and placeholder not in reserved_placeholders:
                self.data.append(placeholder, data)

        if mode != Snippet.ImportEnvironmentMode.ignore:
            for placeholder in placeholders:
                # Do not load upper case environment variables to prevent users from getting into the habit of
                # defining upper case environment variables and messing up their environment.
                # In addition loading upper case environment variables may result in loading unwanted/pre-defined
                # values.
                data = os.environ.get(placeholder) # or os.environ.get(placeholder.upper())
                if data:
                    if mode == Snippet.ImportEnvironmentMode.default:
                        # Only set environment data when not already defined
                        if placeholder not in self.data:
                            _import_environment(placeholder, data)
                    elif mode == Snippet.ImportEnvironmentMode.append:
                        _import_environment(placeholder, data)
                    elif mode == Snippet.ImportEnvironmentMode.replace:
                        if placeholder not in reserved_placeholders:
                            self.data[placeholder] = []
                            _import_environment(placeholder, data)

    def build(self):
        return DataBuilder(self._get_format_string(), self.data, self.codec_formats, self.config).build()

    format_string = property(_get_format_string, _set_format_string)
    arguments = property(_get_arguments, _set_arguments)
    verbose = property(_get_verbose, _set_verbose)


def __main__():
    config = Config(app_name, [home_config_path, app_config_path])
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
    
""" + os.linesep.join(["  {}  {}".format(x.rjust(20, ' '), config.codecs[x].__doc__.splitlines()[1].strip()) for x in
                           config.codecs.keys()]) + """
    
    Examples:
    
        # A rather simple string format example using snippet
        $ snippet -f "hello <arg1>" snippet
        
        # Assigning multiple values and making use of presets
        $ snippet -f "ping -c 1 <rhost> > ping_<rhost>_<datetime>.log;" rhost=localhost github.com
        
        # Using templates and reading arguments from a file
        $ snippet -t net/scan/nmap-ping rhost:hosts.txt
        
        # When no template is specified an interactive template search prompt is displayed
        $ snippet rhost:hosts.txt
        
        # Using codecs
        $ snippet -f "echo 'hello <arg1> (<arg1:b64>)';" snippet
        
        # Using optional arguments
        $ snippet -f "echo '<arg1>[ <arg2>]'" snippet 
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
                             "The placeholders are identified by less than (<) and greater than (>) signs.")
    parser.add_argument('-t', '--template', action="store", metavar="FILE",
                        dest='template_name',
                        help="The template to use as format string.") \
        .completer = argparse_template_completer
    parser.add_argument('-l', '--list-templates', action="store_true",
                        dest='list_templates',
                        help="Lists all available templates.")
    parser.add_argument('--list-codecs', action="store_true",
                        dest='list_codecs',
                        help="Lists all available codecs.")
    parser.add_argument('--env', '--environment', action="store_true",
                        dest='environment',
                        help="Shows all environment variables.")
    parser.add_argument('-v', '--verbose', action="store_true",
                        dest='verbose',
                        help="Prints additional information (e.g. string format, template).")
    parser.add_argument('-d', '--debug', action="store_true",
                        dest='debug',
                        help="Prints additional debug information (e.g. stack traces).")

    argcomplete.autocomplete(parser)
    arguments = parser.parse_args()

    config.logger.setLevel(logging.DEBUG if arguments.debug else logging.INFO)

    try:
        if arguments.verbose:
            snippet.verbose = True

        if arguments.edit:
            snippet.create_or_edit_template(arguments.edit)
            sys.exit(0)

        if arguments.list_codecs and arguments.list_templates:
            raise Exception("--codec-list can not be used in combination with --template-list!")

        if arguments.list_templates:
            template_names = snippet.list_templates()
            if not template_names:
                logger.warning("WARNING: No templates found!")
            for template_name in template_names:
                print(template_name)
            sys.exit(0)

        if arguments.list_codecs:
            codec_names = snippet.list_codecs()
            if not codec_names:
                logger.warning("WARNING: No codecs found!")
            for codec_name in codec_names:
                print(codec_name)
            sys.exit(9)

        if arguments.format_string and arguments.template_name:
            raise Exception("--format-string can not be used in conjunction with --template!")

        if arguments.format_string and not sys.stdin.isatty():
            raise Exception("--format-string can not be used in conjunction with piped input!")

        if arguments.template_name and not sys.stdin.isatty():
            raise Exception("--template can not be used in conjunction with piped input!")

        if arguments.format_string:
            snippet.format_string = arguments.format_string

        if arguments.template_name:
            snippet.use_template(arguments.template_name)

        if not sys.stdin.isatty():
            snippet.format_string = sys.stdin.readline().rstrip()

        if not snippet.format_string:
            snippet.format_string = os.environ.get("FORMAT_STRING") or ""

        if arguments.data_values:
            snippet.arguments = arguments.data_values

        snippet.import_environment(Snippet.ImportEnvironmentMode.default)

        if arguments.environment:
            print(snippet.list_environment())
            sys.exit(0)

        if not snippet.format_string:
            parser.print_usage()
            sys.exit(1)

        for lines in snippet.build():
            # Handle format strings with line separators
            for line in lines.split(os.linesep):
                print(line)

        sys.exit(0)
    except Exception as e:
        logger.error(colorize("ERROR: ", Fore.RED) + str(e))
        if arguments.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    __main__()
