#!/usr/bin/env python3
import shlex
import traceback
from collections import defaultdict, OrderedDict
from enum import Enum

import argcomplete, argparse
import csv
import re
from pathlib import Path
import logging
import os
import sys
import itertools


try:
    import pandas as pd
except:
    sys.stderr.write("Missing python3 package pandas! ")
    sys.stderr.write("Please install requirements using 'pip3 install -r requirements.txt" + os.linesep)
    sys.exit(1)

app_name = "revamp"
app_version = "1.0b"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".revamp". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".revamp")
home_config_path = os.path.join(str(Path.home()), ".revamp")


def init_logger(app_id, log_format="%(module)s: %(lineno)d: %(msg)s"):
    logger = logging.getLogger(app_id)
    logging.root.setLevel(logging.DEBUG)
    hdlr = logging.StreamHandler(sys.stderr)
    hdlr.setFormatter(logging.Formatter(log_format))
    logger.addHandler(hdlr)
    return logger


class FormatArgumentParser(object):

    def parse(self, format_argument):
        # Accepted data set format:
        #   PLACEHOLDER=VALUE
        #   PLACEHOLDER:FILE
        separator = self.__get_separator(format_argument)
        return {
            "=": self.__parse_value,
            ":": self.__parse_file
        }.get(separator)(format_argument, separator)

    def __get_separator(self, format_argument):
        string_sep_pos = format_argument.find("=")
        file_sep_pos = format_argument.find(":")
        if (string_sep_pos <= 0 and file_sep_pos <= 0) or (string_sep_pos > 0 and file_sep_pos > 0):
            raise Exception("Parsing '{}' failed! Invalid format!".format(format_argument))
        is_value_sep = string_sep_pos > 0
        sep = "=" if is_value_sep else ":"
        return sep

    def __parse_value(self, placeholder_value, sep):
        try:
            placeholder, value = placeholder_value.split(sep)
            return {placeholder: value}
        except:
            raise Exception("Parsing '{}' failed! Unknown error!".format(placeholder_value))

    def __parse_file(self, placeholder_file, sep):
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


class Data(defaultdict):
    """
     Map of placeholders with value lists e.g. { 'PLACEHOLDER-1': ('a','b','c'), 'PLACEHOLDER-2': ('d') }
    """

    def __init__(self):
        super().__init__(list)

    def append(self, placeholder, values=None):
        placeholder_key = placeholder.lower()
        if values is None:
            for placeholder, values in FormatArgumentParser().parse(placeholder).items():
                placeholder_key = placeholder.lower()
                if isinstance(values, list):
                    for value in values:
                        self[placeholder_key].append(value)
                else:
                    self[placeholder_key].append(values)
        elif isinstance(values, list):
            for value in values:
                self[placeholder_key].append(value)
        else:
            if values.startswith('\(') and values.endswith('\)'):
                for value in shlex.split(values[2:-2]):
                    self[placeholder_key].append(value)
            else:
                self[placeholder_key].append(values)

    def to_data_frame(self, filter_string=None):
        # Create table data with equally sized lists by filling them with empty strings
        # e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','','') }
        table_data = Data()
        max_length = max([len(self[key]) for key in self.keys()])
        for placeholder in self.keys():
            for item in self[placeholder]:
                table_data.append(placeholder, item)
            for i in range(0, max_length - len(self[placeholder])):
                table_data.append(placeholder, "")

        data_frame = pd.DataFrame(table_data).astype(str)

        if filter_string:
            data_frame = data_frame.query(filter_string)

        return data_frame.T


    def import_from_file(self, import_file_path, delimiter):
        if not os.path.exists(import_file_path):
            raise Exception("Importing '{}' failed! File not found!".format(import_file_path))

        try:
            with open(import_file_path, 'r') as f:
                reader = csv.DictReader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
                for line in reader:
                    for placeholder in line.keys():
                        value = line[placeholder]
                        if value:
                            placeholder_key = placeholder.lower()
                            self.append(placeholder_key, value)
        except:
            raise Exception("Importing '{}' failed! Invalid file format!".format(import_file_path))


class Config(object):

    def __init__(self, paths):
        self.paths = paths
        self.format_template_paths = [os.path.join(path, "templates") for path in paths]
        self.profile = self.__load_profile()
        self._reserved_placeholder_values = []

    def __load_profile(self):
        for profile_path in self.paths:
            if os.path.exists(profile_path):
                try:
                    # Since the path may contain special characters which can not be processed by the __import__
                    # function we temporary add the template path in which the profile.py is located to the PATH.
                    sys.path.append(profile_path)
                    profile = __import__("revamp_profile").Profile()
                    sys.path.pop()
                    return profile
                except:
                    pass
        return None

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
        for format_template_file_path in self.format_template_paths:
            if os.path.exists(format_template_file_path):
                for r, d, f in os.walk(format_template_file_path):
                    relpath = r[len(format_template_file_path) + 1:]
                    for file in f:
                        format_template_files.append(os.path.join(relpath, file))
        return sorted(list(set(format_template_files)))

    def get_format_template(self, format_template_name):
        for format_template_path in self.format_template_paths:
            format_template_file = os.path.join(format_template_path, format_template_name)
            if os.path.exists(format_template_file):
                try:
                    with open(format_template_file) as f:
                        return os.sep.join(f.read().splitlines())
                except:
                    raise Exception("Loading '{}' failed! Invalid template format!".format(format_template_name))
        raise Exception("Loading '{}' failed! Template not found!".format(format_template_name))


class DataBuilder(object):

    def __init__(self, format_string, data, config):
        self._format_string = format_string
        self._placeholders = []
        self.data = data
        self.config = config

    def get_placeholders(self):
        if self._placeholders:
            return list(self._placeholders)

        if self._format_string:
            # Parse placeholders from format string
            # Remove duplicate placeholders while preserving order
            self._placeholders = list(OrderedDict.fromkeys(placeholder for placeholder in re.findall("<(\w+)>", self._format_string)))
            return list(self._placeholders)
        else:
            return []

    def transform_data(self, filter_string=None):
        """
        Transforms the data from a map of placeholders with value lists into a data frame.
        """
        temporary_data = Data()

        placeholders = [placeholder.lower() for placeholder in self.get_placeholders()]
        for placeholder in self.data.keys():
            if placeholder in placeholders:
                # Add to temporary data. Remove duplicates while preserving order
                temporary_data[placeholder] = OrderedDict.fromkeys(self.data[placeholder])

        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        if any(reserved_placeholder in temporary_data.keys() for reserved_placeholder in reserved_placeholder_values.keys()):
            raise Exception("{} is/are already defined in your profile!".format(
                    ', '.join(["<" + placeholder + ">" for placeholder in reserved_placeholder_values.keys() if placeholder in temporary_data])))

        for placeholder, value in reserved_placeholder_values.items():
            if placeholder in placeholders:
                # Add to temporary data. Remove duplicates while preserving order
                temporary_data[placeholder] = OrderedDict.fromkeys(value)

        unset_placeholders = [placeholder for placeholder in placeholders if placeholder not in temporary_data]
        if unset_placeholders:
            raise Exception("Missing data for {}!".format(', '.join(["<" + item + ">" for item in unset_placeholders])))

        # Create matrix from data e.g. (('a','d'), ('b','d'), ('c','d'))
        data_matrix = list(itertools.product(*[temporary_data[key] for key in temporary_data.keys()]))

        # Create table data from matrix e.g. { 'placeholder-1': ('a','b','c'), 'placeholder-2': ('d','d','d') }
        data_keys = list(temporary_data.keys())
        table_data = Data()
        for i in range(0, len(data_matrix)):
            for j in range(0, len(data_keys)):
                table_data.append(data_keys[j], data_matrix[i][j])

        # Create data frame from table data
        # Handle everything as string which requires that the user needs to put quotes around every value in the filter.
        # This makes it easier to write such filter-queries in the long run since no one needs to think about whether
        # to put quotes around a value or not.
        data_frame = pd.DataFrame(table_data).astype(str)

        if filter_string:
            data_frame = data_frame.query(filter_string)

        return data_frame

    def build(self, filter_string=None):
        result = []
        if self._format_string:
            data_frame = self.transform_data(filter_string)
            if len(data_frame) == 0:
                return [self._format_string]

            placeholders = self.get_placeholders()
            for index, row in data_frame.iterrows():
                # Replace placeholders in format string with values
                output_line = self._format_string
                for placeholder in placeholders:
                    output_line = output_line.replace("<" + placeholder + ">", row[placeholder.lower()])
                result.append(output_line)

        return result


class Revamp(object):

    class ImportEnvironmentMode(Enum):
        default = 1
        append = 2
        replace = 3
        ignore = 4

    format_string = None
    data = Data()

    def __init__(self, config: Config):
        self.config = config

    def use_template(self, template_name):
        self.format_string = self.config.get_format_template(template_name)
        return self.format_string

    def list_templates(self, filter_string=None):
        template_names = self.config.get_format_template_names()
        if filter_string:
            return [template_name for template_name in template_names if filter_string in template_name]
        else:
            return template_names

    def list_options(self, filter_string=None):
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        return temporary_data.to_data_frame()

    def list_placeholders(self):
        return DataBuilder(self.format_string, self.data, self.config).get_placeholders()

    def list_reserved_placeholders(self):
        return self.config.get_reserved_placeholder_names()

    def list_unset_placeholders(self):
        unset_placeholders = []
        for placeholder in [p.lower() for p in self.list_placeholders()]:
            if placeholder not in self.data and placeholder not in self.list_reserved_placeholders():
                unset_placeholders.append(placeholder)
        return unset_placeholders

    def import_data_file(self, import_file_path, delimiter=None):
        if not delimiter:
            delimiter = self.config.profile.csv_delimiter if self.config.profile else '\t'
        self.data.import_from_file(import_file_path, delimiter)

    def import_environment(self, mode=ImportEnvironmentMode.default):
        placeholders = [placeholder.lower() for placeholder in self.list_placeholders()]
        reserved_placeholders = self.config.get_reserved_placeholder_values().keys()

        def _import_environment(placeholder, data):
            if data and placeholder not in reserved_placeholders:
                self.data.append(placeholder, data)

        if mode != Revamp.ImportEnvironmentMode.ignore:
            for placeholder in placeholders:
                data = os.environ.get(placeholder)
                if data:
                    if Revamp.ImportEnvironmentMode.default == mode:
                        # Only set environment data when not already defined
                        if placeholder not in self.data:
                            _import_environment(placeholder, data)
                    elif Revamp.ImportEnvironmentMode.append == mode:
                        _import_environment(placeholder, data)
                    elif Revamp.ImportEnvironmentMode.replace == mode:
                        if placeholder not in reserved_placeholders:
                            self.data[placeholder] = []
                            _import_environment(placeholder, data)

    def build(self, filter_string=None):
        return DataBuilder(self.format_string, self.data, self.config).build(filter_string)


config = Config([home_config_path, app_config_path])
revamp = Revamp(config)


def argparse_template_completer(prefix, parsed_args, **kwargs):
    return config.get_format_template_names()


logger = init_logger(app_name, "%(msg)s")

parser = argparse.ArgumentParser(
    description='revamp',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Placeholder presets:

""" + os.linesep.join(["  {} {}".format(("<" + x.name + ">").ljust(20), x.description) for x in config.get_reserved_placeholders()]) + """

Examples:

  revamp -s target=localhost     -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
  revamp -s target:./targets.txt -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
    """
)
parser.add_argument('data_value', metavar='VALUE', nargs='*',
                    help='Replaces the first unset placeholder found in the format string with a value or a list of '
                         'values. A list of values can be asigned by enclosing them inside \\( and \\).')
parser.add_argument('-f', '--format-string', action="store", metavar="FORMAT_STRING",
                    dest='format_string',
                    help="The format of the data to generate. "
                         "The placeholders are identified by less than (<) and greater than (>) signs.")
parser.add_argument('-s', '--set', action="append", metavar="PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE", dest='data_set',
                    help="Replaces the placeholder found in the format string with a value or a list of values. "
                         "A list of values can be asigned by enclosing them inside \\( and \\) or by specifying a "
                         "file location where values are loaded from.")
parser.add_argument('-i', '--import', action="store", metavar="FILE", dest='import_file',
                    help="Replace the placeholders found in the format string with the values found in the specified "
                         "file. The file should start with a header which specifies the placeholders. Values should "
                         "be separated by a tab character which can be customized in the profile file. ")
parser.add_argument('-t', '--template', action="store", metavar="FILE",
                    dest='template_name',
                    help="The template to use as format string.")\
    .completer = argparse_template_completer
parser.add_argument('-v', '--view-template', action="store_true",
                    dest='view_template',
                    help="Views the template instead of using it as generator. Can only be used in combination with "
                         "the --template argument.")
parser.add_argument('-l', '--list-templates', action="store_true",
                    dest='list_templates',
                    help="Lists all available templates.")
parser.add_argument('--filter', action="store", metavar="STRING", dest='filter',
                    help="The filter to include/exclude results "
                         "(e.g. --filter 'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').")
parser.add_argument('-d', '--debug', action="store_true",
                    dest='debug',
                    help="Activates the debug mode.")

argcomplete.autocomplete(parser)
arguments = parser.parse_args()

try:
    if arguments.list_templates:
        template_names = revamp.list_templates()
        if not template_names:
            logger.warning("WARNING: No templates found!")
        for template_name in template_names:
            print(template_name)
        sys.exit(0)

    if arguments.format_string and arguments.template_name:
        raise Exception("--format-string can not be used in conjunction with --template!")

    if arguments.format_string:
        revamp.format_string = arguments.format_string

    if arguments.view_template and not arguments.template_name:
        raise Exception("--view-template must be used in combination with --template!")

    if arguments.template_name:
        format_string = revamp.use_template(arguments.template_name)
        if arguments.view_template:
            print(format_string)
            sys.exit(0)

    if not revamp.format_string:
        revamp.format_string = os.environ.get("FORMAT_STRING")

    if arguments.import_file:
        revamp.import_data_file(arguments.import_file)

    if arguments.data_set:
        for _data in arguments.data_set:
            revamp.data.append(_data)

    revamp.import_environment(Revamp.ImportEnvironmentMode.default)

    if arguments.data_value:
        for placeholder in revamp.list_unset_placeholders():
            if len(arguments.data_value) > 0:
                revamp.data.append(placeholder, arguments.data_value.pop(0))

    if revamp.format_string:
        for line in revamp.build(arguments.filter):
            print(line)
    else:
        print(revamp.list_options())
except Exception as e:
    logger.error("ERROR: {}".format(e))
    if arguments.debug:
        traceback.print_exc()
    sys.exit(1)
