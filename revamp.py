#!/usr/bin/env python3
import shlex
import traceback
from collections import defaultdict, OrderedDict, namedtuple
from enum import Enum

import argcomplete, argparse
import csv
import re
from pathlib import Path
import logging
import os
import sys
import itertools

from iterfzf import iterfzf

try:
    import pandas as pd
except:
    sys.stderr.write("Missing python3 package pandas! ")
    sys.stderr.write("Please install requirements using 'pip3 install -r requirements.txt" + os.linesep)
    sys.exit(1)

app_name = "revamp"
app_version = "1.0f"

# Configuration files
# ===================
# Configuration files can be placed into a folder named ".revamp". Either inside the application- or
# inside the home-directory.
app_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".revamp")
home_config_path = os.path.join(str(Path.home()), ".revamp")


class FormatArgumentParser(object):

    def parse(self, format_arguments: str):
        # Accepted data set format:
        #   PLACEHOLDER=VALUE | PLACEHOLDER:FILE [... PLACEHOLDER=VALUE | PLACEHOLDER:FILE]
        result = Data()
        for format_argument in self.__reformat_arguments(format_arguments):
            for key, value in self.__parse(format_argument).items():
                result.append(key, value)
        return result

    def __reformat_arguments(self, format_arguments: str) -> list:
        """
        Reformats format arguments which were passed as single string but contain multiple placeholders with values
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

    def __parse(self, format_argument: str):
        separator = self.__get_separator(format_argument)
        return {
            "=": self.__parse_placeholder_value,
            ":": self.__parse_placeholder_file,
            "": self.__parse_value
        }.get(separator)(format_argument, separator)

    def __get_separator(self, format_argument: str):
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

    def __parse_placeholder_value(self, placeholder_value: str, sep: str):
        try:
            placeholder, value = placeholder_value.split(sep)
            return {placeholder: value}
        except:
            raise Exception("Parsing '{}' failed! Unknown error!".format(placeholder_value))

    def __parse_placeholder_file(self, placeholder_file: str, sep: str):
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

    def __parse_value(self, value: str, sep: str):
        return {"": value}


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


class Codec(object):

    def __init__(self, author, dependencies):
        self.author = author
        self.dependencies = dependencies

    def name(self):
        return self.__class__.__name__

    def run(self, text):
        pass


CodecFormat = namedtuple("CodecFormat", "placeholder placeholder_new codecs")


class CodecFormatStringParser(object):

    def parse(self, codec_format_string):
        # PLACEHOLDER[=NEW_PLACEHOLDER]:CODEC[:CODEC ...]
        placeholder = None
        placeholder_new = None
        codecs = None
        try:
            if "=" in codec_format_string:
                new_placeholder, codec_format_string = codec_format_string.split("=")
            codecs = codec_format_string.split(":")
            placeholder = codecs.pop(0)
        except:
            raise Exception("Transforming placeholders failed! Invalid codec format!")

        if not codecs:
            raise Exception("Transforming placeholders failed! Invalid codec format!")

        return CodecFormat(placeholder, placeholder_new, codecs)


class Config(object):

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
                    profile = __import__("revamp_profile").Profile()
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
                                except Exception as e:
                                    self.logger.warning("WARNING: Loading codec {} failed!".format(filename))
                    sys.path.pop()

        return codecs

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

    def __init__(self, format_string, data, codec_formats, config):
        self._format_string = format_string
        self._placeholders = []
        self.data = data
        self.config = config
        self.codec_formats = codec_formats

    def get_placeholders(self):
        if self._placeholders:
            return list(self._placeholders)

        if self._format_string:
            # Parse placeholders from format string
            # Remove duplicate placeholders while preserving order
            self._placeholders = list(
                OrderedDict.fromkeys(placeholder for placeholder in re.findall(r"<(\w+)>", self._format_string)))
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
        if any(reserved_placeholder in temporary_data.keys() for reserved_placeholder in
               reserved_placeholder_values.keys()):
            raise Exception("{} is/are already defined in your profile!".format(
                ', '.join(["<" + placeholder + ">" for placeholder in reserved_placeholder_values.keys() if
                           placeholder in temporary_data])))

        for placeholder, value in reserved_placeholder_values.items():
            if placeholder in placeholders:
                # Add to temporary data. Remove duplicates while preserving order
                temporary_data[placeholder] = OrderedDict.fromkeys(value)

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

    def apply_codecs(self, data_frame):
        for placeholder in data_frame.keys():
            if placeholder in self.codec_formats.keys():
                new_values = []
                for value in data_frame[placeholder]:
                    new_value = value
                    for codec in self.codec_formats[placeholder].codecs:
                        new_value = self.config.codecs[codec].run(new_value)
                    new_values.append(new_value)

                placeholder_new = self.codec_formats[placeholder].placeholder_new
                if placeholder_new:
                    if placeholder_new in data_frame.keys():
                        raise Exception("Transforming placeholder {} to {} failed! The placeholder {} is already defined!".format(
                            placeholder, placeholder_new, placeholder_new
                        ))
                    data_frame[placeholder_new] = new_values
                else:
                    data_frame[placeholder] = new_values

    def build(self, filter_string=None):
        result = []
        if self._format_string:
            data_frame = self.transform_data(filter_string)

            placeholders = self.get_placeholders()
            unset_placeholders = [placeholder for placeholder in placeholders if placeholder not in data_frame.keys()]
            if unset_placeholders:
                raise Exception("Missing data for {}!".format(', '.join(["<" + item + ">" for item in unset_placeholders])))

            if len(data_frame) == 0:
                return [self._format_string]

            self.apply_codecs(data_frame)

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
    codec_formats = {}
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

    def list_codecs(self, filter_string=None):
        if filter_string:
            return sorted([codec_name for codec_name in self.config.codecs.keys() if
                    filter_string in self.config.codecs.keys()])
        else:
            return sorted(self.config.codecs.keys())

    def list_environment(self, filter_string=None):
        temporary_data = Data()
        for placeholder in self.data.keys():
            temporary_data[placeholder] = self.data[placeholder]
        reserved_placeholder_values = self.config.get_reserved_placeholder_values()
        for placeholder in reserved_placeholder_values.keys():
            temporary_data[placeholder] = reserved_placeholder_values[placeholder]
        return temporary_data.to_data_frame()

    def list_placeholders(self):
        return DataBuilder(self.format_string, self.data, self.codec_formats, self.config).get_placeholders()

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
        return DataBuilder(self.format_string, self.data, self.codec_formats, self.config).build(filter_string)


def __main__():
    config = Config(app_name, [home_config_path, app_config_path])
    logger = config.logger
    revamp = Revamp(config)

    def argparse_template_completer(prefix, parsed_args, **kwargs):
        return config.get_format_template_names()

    parser = argparse.ArgumentParser(
        description='revamp',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Placeholder presets:
    
    """ + os.linesep.join(["  {} {}".format(("<" + x.name + ">").ljust(20), x.description) for x in
                           config.get_reserved_placeholders()]) + """
    
    Examples:
    
        # A rather simple string format example using revamp
        $ revamp -f "hello <arg1>" revamp
        
        # Assigning multiple values and making use of presets
        $ revamp -f "ping -c 1 <rhost> > ping_<rhost>_<date_time>.log;" rhost=localhost github.com
        
        # Using templates and reading arguments from a file
        $ revamp -t net/scan/nmap-ping rhost:hosts.txt
        
        # Transforming strings
        $ revamp -f "echo 'hello <arg1> (<arg2>)';" -c arg2=arg1:b64 revamp
        """
    )
    parser.add_argument('data_values', metavar='VALUE | PLACEHOLDER=VALUE | PLACEHOLDER:FILE', nargs='*',
                        help='When no placeholder is specified the first unset placeholder found in the format string will '
                             'be replaced with the value(s). Otherwise the specified placeholder will be replaced with '
                             'the value or the content of the file. A list of values can be assigned by explicitly '
                             'declaring the placeholder (e.g. "ARG1=val1" "ARG1=val2").')
    parser.add_argument('-f', '--format-string', action="store", metavar="FORMAT_STRING",
                        dest='format_string',
                        help="The format of the data to generate. "
                             "The placeholders are identified by less than (<) and greater than (>) signs.")
    parser.add_argument('-i', '--import', action="store", metavar="FILE", dest='import_file',
                        help="Replace the placeholders found in the format string with the values found in the specified "
                             "file. The file should start with a header which specifies the placeholders. Values should "
                             "be separated by a tab character which can be customized in the profile file. ")
    parser.add_argument('-t', '--template', action="store", metavar="FILE",
                        dest='template_name',
                        help="The template to use as format string.") \
        .completer = argparse_template_completer
    parser.add_argument('-tV', '--template-view', action="store_true",
                        dest='view_template',
                        help="Views the template instead of using it as generator. Can only be used in combination with "
                             "the --template argument.")
    parser.add_argument('-tL', '--templates-list', action="store_true",
                        dest='list_templates',
                        help="Lists all available templates.")
    parser.add_argument('-c', '--codec', action="append", metavar="[NEW_PLACEHOLDER=]PLACEHOLDER:CODEC[:CODEC ...]",
                        dest='codec_format_strings',
                        help="Transforms the value assigned to the placeholder using the specified codecs. The result does "
                             "either replace the initial value or is accessible under the new placeholder name.")
    parser.add_argument('-cL', '--codec-list', action="store_true",
                        dest='codec_list',
                        help="Lists all available codecs.")
    parser.add_argument('--filter', action="store", metavar="STRING", dest='filter',
                        help="The filter to include/exclude results "
                             "(e.g. --filter 'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').")
    parser.add_argument('-e', '--environment', action="store_true",
                        dest='environment',
                        help="Shows all environment variables.")
    parser.add_argument('-d', '--debug', action="store_true",
                        dest='debug',
                        help="Activates the debug mode.")

    argcomplete.autocomplete(parser)
    arguments = parser.parse_args()

    config.logger.setLevel(logging.DEBUG if arguments.debug else logging.INFO)

    try:
        if arguments.codec_list and arguments.list_templates:
            raise Exception("--codec-list can not be used in combination with --template-list!")

        if arguments.list_templates:
            template_names = revamp.list_templates()
            if not template_names:
                logger.warning("WARNING: No templates found!")
            for template_name in template_names:
                print(template_name)
            sys.exit(0)

        if arguments.codec_list:
            codec_names = revamp.list_codecs()
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
            revamp.format_string = arguments.format_string

        if arguments.template_name:
            format_string = revamp.use_template(arguments.template_name)
            if arguments.view_template:
                print(format_string)
                sys.exit(0)

        if not sys.stdin.isatty():
            revamp.format_string = sys.stdin.readline().rstrip()

        if arguments.codec_format_strings:
            codec_formats = {}
            for codec_format_string in arguments.codec_format_strings:
                codec_format = CodecFormatStringParser().parse(codec_format_string)
                for codec in codec_format.codecs:
                    if codec not in revamp.list_codecs():
                        raise Exception("Unknown codec {}!".format(codec))
                codec_formats[codec_format.placeholder] = codec_format
            revamp.codec_formats = codec_formats

        if not revamp.format_string:
            revamp.format_string = os.environ.get("FORMAT_STRING")

        if arguments.import_file:
            revamp.import_data_file(arguments.import_file)

        if arguments.data_values:
            unset_placeholders = revamp.list_unset_placeholders()
            for data_val in arguments.data_values:
                if data_val:  # Ignore empty string arguments (e.g. ""); use "arg=" instead
                    for placeholder, values in FormatArgumentParser().parse(data_val).items():
                        if not placeholder:
                            if len(unset_placeholders) == 0:
                                logger.warning(
                                    "WARNING: Can not assign '{}' to unknown placeholder!".format(", ".join(values)))
                                continue
                            placeholder = unset_placeholders.pop(0)
                        revamp.data.append(placeholder, values)

        revamp.import_environment(Revamp.ImportEnvironmentMode.default)

        if arguments.environment:
            print(revamp.list_environment())
            sys.exit(0)

        if not revamp.format_string:
            template_name = iterfzf(revamp.list_templates())
            if not template_name:
                sys.exit(1)

            format_string = revamp.use_template(template_name)
            if arguments.view_template:
                print(format_string)
                sys.exit(0)

        for line in revamp.build(arguments.filter):
            print(line)

        sys.exit(0)
    except Exception as e:
        logger.error("ERROR: {}".format(e))
        if arguments.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    __main__()
